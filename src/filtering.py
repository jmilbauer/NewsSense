from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

embedding_model = None

def init_embedding_model(device=None):
    global embedding_model
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    if device is not None:
        embedding_model = embedding_model.to(device)
        
def get_similarity_scores(sentences):
    if embedding_model is None:
        raise Exception("embedding model not initialized")
    embeddings = embedding_model.encode(sentences)
    similarity_scores = cosine_similarity(embeddings)
    return similarity_scores    
    
def get_sentencepairs(articles):
    sentence_pairs = []
    sentences = set([])
    sentence2urls = {}
    for i, a1 in enumerate(articles):
        url1 = a1['url']
        for j, a2 in enumerate(articles):
            url2 = a2['url']
            if i == j:
                continue
                
            for s1 in a1['claims']:
                c1 = s1['claim']
                if c1 in sentence2urls:
                    sentence2urls[c1].add(url1)
                else:
                    sentence2urls[c1] = set([url1])
                    
                for s2 in a2['claims']:
                    c2 = s2['claim']
                    sentence_pairs.append((c1, c2))
                    sentences.add(c1)
                    sentences.add(c2)
                    
                    if c2 in sentence2urls:
                        sentence2urls[c2].add(url2)
                    else:
                        sentence2urls[c2] = set([url2])
                        
    sentences = [x for x in list(sorted(sentences)) if len(x) > 0]
    return sentences, sentence_pairs, sentence2urls