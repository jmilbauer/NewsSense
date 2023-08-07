from bs4 import BeautifulSoup
from collections import Counter
import copy
import functools
import gc
import json
import os
from pathlib import Path
import sys
from tqdm import tqdm
import urllib.request

import openai
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import pipeline
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.scrapers import get_google_story
import src.filtering
import src.entailment

import src.article_utils as AU

stops = stopwords.words('english')
url = sys.argv[1]

#############################
### STEP 1: DOWNLOAD INFO ###
#############################

titles, texts, links, venues, urls = get_google_story(url, n=20)

indices_of_substantial = [i for i,text in enumerate(texts) if len(text) > 10]

titles_ = [titles[i] for i in indices_of_substantial]
texts_ = [texts[i] for i in indices_of_substantial]
links_ = [links[i] for i in indices_of_substantial]
venues_ = [venues[i] for i in indices_of_substantial]
urls_ = [urls[i] for i in indices_of_substantial]

title_tokens = []
for t in titles_:
    toks = t.lower().split()
    words = []
    for tok in toks:
        if tok in stops:
            continue
        w = ""
        for c in tok:
            if c.isalnum():
                w += c
        if len(w) > 0:
            words.append(w)
    title_tokens.extend(words)
    
histogram = Counter(title_tokens)
ranked = sorted(histogram, key=lambda x: histogram[x], reverse=True)
merged_title = '_'.join(ranked[:5])
print("Save title: ", merged_title)
article_dir = Path(f'articles/{merged_title}')

if not article_dir.exists():
    os.makedirs(article_dir)
    
with open(article_dir / 'articles.jsonl', 'w') as fp:
    for i in range(len(titles_)):
        obj = {
            'title': titles_[i],
            'url': urls_[i],
            'text': ' '.join(texts_[i]),
            'paragraphs': texts_[i],
            'links': list(links_[i]),
            'venue': venues_[i],
            # 'polarization': scores_[i]
        }
        fp.write(f"{json.dumps(obj)}\n")
        
############################
### STEP 2: SEGMENT TEXT ###
############################

openai.api_key = ""
models = openai.Model.list()
names = [x['id'] for x in models.data]

model_name = 'text-davinci-003'

segmentation_template = """Extract all the claims from a sentence, ignoring extraneous words such as unimportan adverbs. A sentence may contain multiple claims. Each claim should be of the form <subject> <predictate> <object>, and should have the first occurence of any pronouns replaced by their antecedents.

Sentence: "The 3rd and 4th stations all announced that they would be postponed, and the Monaco station was subsequently cancelled."
Claim: Monaco station was cancelled.
Claim: 4th stations announced they would be postponed.
Claim: The 3rd stations announced they would be postponed.
Claim: The 4th stations postponed.
Claim: The 3rd stations postponed.

Sentence: "Lewis Hamilton and Mercedes have once again confirmed themselves as drivers and constructors world champions."
Claim: Mercedes confirmed themselves as constructors world champions.
Claim: Lewis Hamilton confirmed themselves as drivers world champions.

Sentence: "Local organizers in East Palestine, Ohio on Monday said their activism has successfully pressured rail company Norfolk Southern to agree to a limited relocation plan for some residents affected by last month's train derailment, but added they have no intention of backing down from their demand for justice for thousands of people in the area who are struggling in the aftermath of the accident."
Claim: Local organizers said their activism has pressued rail company Norfolk Southern to agree to a limited relocation plan.
Claim: Local organizers have no intention of backing down from their demand for justice.
Claim: Rail company Norfolk Southern agree to a limited relocation plan.

Sentence: """

def make_prompt(sentence, template=segmentation_template):
    return f"{template} {sentence}"

def get_claims(sentence):
    prompt = make_prompt(' '.join(sentence.split())),
    completion = openai.Completion.create(
        model=model_name,
        prompt=prompt,
        max_tokens=128,
        temperature=0,
    )
    claims = completion.choices[0].text.strip().split('\n')
    claims = [c for c in claims if c[:6] == 'Claim:']
    claims = [c[6:].strip() for c in claims]
    return completion, claims

articles = []
with open(article_dir / 'articles.jsonl') as fp:
    for line in fp:
        articles.append(json.loads(line.strip()))
        
def merge_paragraphs(paragraphs, min_words, max_words):
    ps = copy.deepcopy(paragraphs)
    
    while True:
        lens = [len(p.split()) for p in ps]
        merges = [(x+y, i) for i, (x,y) in enumerate(zip(lens, lens[1:])) if x < min_words or y < min_words]
        valid_merges = [(len_, pos_) for len_, pos_ in merges if len_ < max_words]
        if len(valid_merges) == 0:
               break
        _, best_merge = list(sorted(valid_merges))[0]
        
        joined = ' '.join([ps[best_merge], ps[best_merge + 1]])
        ps = ps[:best_merge] + [joined] + ps[best_merge+2:]
        
    return ps

article2claims = {}

for article in articles:
    if article['title'] in article2claims:
        continue
    
    print(article['venue'])
    merged_p = merge_paragraphs(article['paragraphs'], min_words=100, max_words=1000)
    article_claims = []
    print([len(p) for p in merged_p])
    
    for p in merged_p:
        print(len(p.split()))
        response, claims = get_claims(p)
        reason = response.choices[0]['finish_reason']
        total_text = p + response.choices[0].text

        tries = 0
        while reason != 'stop' or tries > 4: 
            print('trying again...')
            response, claims = get_claims(total_text)
            reason = response.choices[0]['finish_reason']
            total_text += response.choices[0].text
            tries += 1

        article_claims.extend(claims)
        
    for c in article_claims:
        print(c)
    print()
    
    article2claims[article['title']] = article_claims
    
json.dump(article2claims, open(article_dir / 'article2claims.json', 'w'))

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(device)

articles = []
with open(article_dir / 'articles.jsonl') as fp:
    for i, line in enumerate(fp):
        obj = json.loads(line)
        obj['id'] = i
        articles.append(obj)

article2claims = {}
with open(article_dir / 'article2claims.json') as fp:
    article2claims = json.load(fp)
    
for a in articles:
    if a['title'] in article2claims:
        print('added claims')
        a['openai_claims'] = article2claims[a['title']]
    else:
        a['openai_claims'] = []

articles = [AU.get_sentences(article) for article in tqdm(articles) if article['title'] in article2claims]
articles = [AU.get_claims(article, method='openai') for article in tqdm(articles)]
articles = [AU.link_claims(article) for article in tqdm(articles)]

sentences, sentence_pairs, sentence2urls = src.filtering.get_sentencepairs(articles)

src.filtering.init_embedding_model(device)
similarity_scores = src.filtering.get_similarity_scores(sentences)
most_similar = np.argsort(similarity_scores, axis=1)[:, ::-1]
most_similar = most_similar[:, 1:21]

pairs = []
for i, row in tqdm(enumerate(most_similar)):
    sentence_i = sentences[i]
    for j in row:
        if i == j:
            continue
        sentence_j = sentences[j]
        if all([s in sentence2urls[sentence_j] for s in sentence2urls[sentence_i]]):
            continue
        pairs.append((sentence_i, sentence_j))
    
src.entailment.init_model(device)
probabilities = src.entailment.classify_nli(pairs, device)
contr_thresh = [x for x in list(sorted(probabilities[:, 0], reverse=True)) if x > .7][:100][-1].item()
entai_thresh = [x for x in list(sorted(probabilities[:, 2], reverse=True)) if x > .7][:100][-1].item()

contradiction_idx = probabilities[:, 0] > contr_thresh
entailment_idx = probabilities[:, 2] > entai_thresh

contradictions = [(p, probabilities[i]) for i, p in enumerate(pairs) if contradiction_idx[i]]
entailments = [(p, probabilities[i]) for i, p in enumerate(pairs) if entailment_idx[i]]
print(f"Contradictions: {len(contradictions)}")
print(f"Entailments: {len(entailments)}")

s2support = {}
s2contradict = {}

for x in sentence2urls:
    sentence2urls[x] = list(sentence2urls[x])
    
for (p, h), _ in entailments:
    if h not in s2support:
        s2support[h] = []
    s2support[h].append((sentence2urls[p], p))
    
for (p, h), _ in contradictions:
    if h not in s2contradict:
        s2contradict[h] = []
    s2contradict[h].append((sentence2urls[p], p))
    
claim2sent = {}
for a in articles:
    for claim in a['claims']:
        if claim['claim'] in claim2sent:
            print("DUPLEX")
        else:
            claim2sent[claim['claim']] = claim['sentence']
            
for a in articles:
    supports = []
    contras = []
    for claim in a['claims']:
        if claim['claim'] in s2support:
            x = {}
            x['my_claim'] = claim['sentence']
            x['links'] = []
            for link in s2support[claim['claim']]:
                x['links'].append({'their_claim': claim2sent[link[1]], 'source':link[0]})
            supports.append(x)
            
        if claim['claim'] in s2contradict:
            x = {}
            x['my_claim'] = claim['sentence']
            x['links'] = []
            for link in s2contradict[claim['claim']]:
                x['links'].append({'their_claim': claim2sent[link[1]], 'source':link[0]})
            contras.append(x)

    a['supports'] = supports
    a['contradicts'] = contras
    
json.dump(articles, open(article_dir / 'articles_with_links.json', 'w'))

