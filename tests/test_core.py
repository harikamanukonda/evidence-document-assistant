import unittest
from core import Retriever, answer, corpus, run

class RetrievalTests(unittest.TestCase):
    def setUp(self): self.retriever = Retriever(corpus())
    def test_sources_support_extractive_answer(self):
        result = answer(self.retriever, 'How long are application logs retained?')
        self.assertFalse(result['abstained'])
        self.assertEqual(result['sources'][0]['id'], 'logs-01')
        for source in result['sources']:
            self.assertIn(source['text'], result['answer'])
            self.assertIn(f"[{source['id']}]", result['answer'])
    def test_unknown_vocabulary_abstains_even_at_zero_threshold(self):
        self.assertTrue(answer(self.retriever, 'quasar zeppelin', 0)['abstained'])
    def test_threshold_one_abstains_on_partial_match(self):
        self.assertTrue(answer(self.retriever, 'application logs', 1)['abstained'])
    def test_ranking_is_deterministic(self):
        self.assertEqual(self.retriever.search('model promotion'),self.retriever.search('model promotion'))
    def test_rejects_invalid_request(self):
        for params in [{'question':''},{'question':[]},{'threshold':'nan'},{'top_k':1.5}]:
            with self.assertRaises(ValueError): run(params)
    def test_duplicate_document_ids_rejected(self):
        with self.assertRaises(ValueError): Retriever([corpus()[0],corpus()[0]])

if __name__ == '__main__': unittest.main()
