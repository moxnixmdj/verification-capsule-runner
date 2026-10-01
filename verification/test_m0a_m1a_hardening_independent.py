import unittest, numpy as np, cv2
from drawing_perspective_rectification import rectify_from_quad
from drawing_robust_preprocess import robust_ink_mask
from gdt_feature_control_parser import parse_feature_control_frame
from explicit_definition_reference_graph import compile_reference_graph

class Verify(unittest.TestCase):
    def test_perspective(self):
        img=np.full((200,300),255,np.uint8); q=np.array([[30,20],[270,15],[285,180],[20,190]],np.float32)
        cv2.rectangle(img,(60,60),(240,150),0,2)
        o=rectify_from_quad(img,q); self.assertEqual(o["status"],"RECTIFIED")
    def test_perspective_degenerate(self):
        img=np.full((100,100),255,np.uint8)
        self.assertEqual(rectify_from_quad(img,[[1,1],[2,2],[3,3],[4,4]])["status"],"FAIL_CLOSED")
    def test_robust_preprocess(self):
        x=np.linspace(130,255,300,dtype=np.float32); img=np.tile(x,(180,1)).astype(np.uint8)
        cv2.line(img,(20,50),(280,50),20,2)
        self.assertEqual(robust_ink_mask(img)["status"],"NORMALIZED")
    def test_uniform_fails(self):
        self.assertEqual(robust_ink_mask(np.full((80,80),200,np.uint8))["status"],"FAIL_CLOSED")
    def test_gdt(self):
        o=parse_feature_control_frame("POSITION | DIA 0.10 MMC | A | B MMC | C")
        self.assertEqual(o["status"],"PARSED"); self.assertEqual(o["characteristic"],"POSITION")
    def test_gdt_unknown_fails(self):
        self.assertEqual(parse_feature_control_frame("MAGIC | 0.1 | A")["status"],"FAIL_CLOSED")
    def test_cross_sentence_definition(self):
        o=compile_reference_graph("Critical artifact means a signed release package. Every Critical artifact must be archived.")
        self.assertEqual(o["status"],"COMPILED"); self.assertEqual(len(o["references"]),1)
    def test_conflict_fails(self):
        o=compile_reference_graph("Mode means alpha. Mode means beta. Mode must be used.")
        self.assertEqual(o["status"],"FAIL_CLOSED")
    def test_cycle_fails(self):
        o=compile_reference_graph("Alpha means Beta. Beta means Alpha. Alpha must be emitted.")
        self.assertEqual(o["status"],"FAIL_CLOSED")
    def test_pronoun_not_claimed(self):
        o=compile_reference_graph("Primary record means newest valid row. It must be returned.")
        self.assertEqual(o["references"],[])

if __name__=="__main__": unittest.main()
