from nltk.tokenize import sent_tokenize, word_tokenize

def word_overlap_distance(xwords, ywords):
    xset = set(xwords)
    yset = set(ywords)
    intersection = set.intersection(xset, yset)
    return -(len(intersection) / len(xset))

distance_metric = word_overlap_distance

def get_sentences(article):
    """Extract the sentences from the article's paragraphs, and store them.
    """
    sentences = []
    for p in article['paragraphs']:
        sentences.extend(sent_tokenize(p))
    article['sentences'] = sentences
    return article

def get_claims(article, method='sentences'):
    """Extract the claims from the article's paragraphs, and store them.
    """
    if method == 'sentences':
        article['claims'] = article['sentences']
    elif method == 'openie':
        article['claims'] = None
    elif method == 'openai':
        article['claims'] = article['openai_claims'] if 'openai_claims' in article else []
    return article

def link_claims(article):
    linked_claims = []
    tokenized_sentences = [word_tokenize(s) for s in article['sentences']]
    for claim in article['claims']:
        tokenized_claim = word_tokenize(claim)
        sorted_sentences = sorted(
            enumerate(tokenized_sentences),
            key=lambda x: distance_metric(tokenized_claim, x[1]))
        best_match = list(sorted_sentences)[0]
        linked_claims.append({
            'claim': claim,
            'sentence_id': best_match[0],
            'article_id': article['id'],
            'sentence': article['sentences'][best_match[0]],
        })
    article['claims'] = linked_claims
    return article