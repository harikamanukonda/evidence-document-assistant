"""Local TF-IDF passage retrieval with extractive answers and explicit abstention."""
import json
import math
import re
from collections import Counter
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
STOP = set('a an the is are of to and in for what how does do our it can'.split())

def tokens(text):
    return [word for word in re.findall(r'[a-z0-9]+', text.lower()) if word not in STOP]

class Retriever:
    def __init__(self, documents):
        if not documents or len({d['id'] for d in documents}) != len(documents):
            raise ValueError('Documents need unique IDs and a nonempty corpus')
        self.documents = documents
        counts = [Counter(tokens(d['text'])) for d in documents]
        self.vocab = sorted(set().union(*(set(c) for c in counts)))
        self.idf = np.array([math.log((1+len(documents))/(1+sum(w in c for c in counts)))+1 for w in self.vocab])
        self.matrix = np.array([self.vector(c) for c in counts])
    def vector(self, counts):
        values = np.array([counts.get(w, 0) for w in self.vocab], dtype=float) * self.idf
        norm = np.linalg.norm(values)
        return values / norm if norm else values
    def search(self, query, top_k=3):
        vector = self.vector(Counter(tokens(query)))
        scores = self.matrix @ vector
        order = np.argsort(-scores, kind='stable')[:top_k]
        return [dict(self.documents[i], score=round(float(scores[i]), 4)) for i in order]

def corpus():
    return json.loads((ROOT / 'data/documents.json').read_text())

def answer(retriever, question, threshold=.12, top_k=2):
    sources = [d for d in retriever.search(question, top_k) if d['score'] >= threshold and d['score'] > 0]
    if not sources:
        return {'answer': 'Insufficient evidence in the indexed documents to answer this question.', 'abstained': True, 'sources': []}
    text = '\n\n'.join(f"{d['text']} [{d['id']}]" for d in sources)
    return {'answer': text, 'abstained': False, 'sources': sources}

def evaluate(retriever, threshold=.12):
    fixtures = json.loads((ROOT / 'data/evaluation.json').read_text())
    answerable = [f for f in fixtures if f['relevant_ids']]
    unanswerable = [f for f in fixtures if not f['relevant_ids']]
    recalls = []
    for item in answerable:
        found = {d['id'] for d in retriever.search(item['question'], 3)}
        recalls.append(len(found.intersection(item['relevant_ids']))/len(item['relevant_ids']))
    abstentions = [answer(retriever, f['question'], threshold)['abstained'] for f in unanswerable]
    return {'recall_at_3': round(float(np.mean(recalls)), 3),
            'abstention_accuracy': round(float(np.mean(abstentions)), 3),
            'answerable_cases': len(answerable), 'unanswerable_cases': len(unanswerable),
            'note': 'Small illustrative fixture, not an independent generalization benchmark.'}

def run(params):
    question = params.get('question', 'How long are application logs retained?')
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise ValueError('question must contain 1–1000 characters')
    threshold = float(params.get('threshold', .12))
    top_raw = float(params.get('top_k', 2))
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('threshold must be between 0 and 1')
    if not np.isfinite(top_raw) or not top_raw.is_integer() or not 1 <= top_raw <= 3:
        raise ValueError('top_k must be 1, 2, or 3')
    retriever = Retriever(corpus())
    return dict(answer(retriever, question, threshold, int(top_raw)),
                question=question, method='TF-IDF cosine retrieval + verbatim extractive response',
                evaluation=evaluate(retriever, threshold))
