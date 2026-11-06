import unittest
import numpy as np
from multimodal.index import lexical_scores,rank
class MultimodalTests(unittest.TestCase):
 def test_text_retrieval(self):
  scores=lexical_scores([{'text':'delivery rate orders'},{'text':'electricity energy chart'}],'energy')
  self.assertEqual(rank(scores,[0,0],'text')[0],1)
 def test_visual_can_retrieve_image_only_page(self):
  self.assertEqual(rank([0,0],[.1,.9],'hybrid')[0],1)
 def test_hybrid_is_deterministic(self):
  self.assertEqual(rank([.8,.1],[.2,.9]),rank([.8,.1],[.2,.9]))
 def test_unknown_mode_rejected(self):
  with self.assertRaises(ValueError):rank([1],[1],'unknown')
 def test_empty_text(self):
  np.testing.assert_array_equal(lexical_scores([{'text':''}],'question'),[0])
