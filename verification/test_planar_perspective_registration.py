import unittest
import cv2
import numpy as np

from drawing_view_registration import register_planar_perspective_from_quad


class PerspectiveRegistrationTests(unittest.TestCase):
    def test_projective_recovery(self):
        base=np.full((180,260),255,dtype=np.uint8)
        cv2.rectangle(base,(25,25),(235,155),0,3)
        cv2.line(base,(40,90),(220,90),0,2)
        cv2.line(base,(130,40),(130,140),0,2)
        src=np.asarray([[0.,0.],[259.,0.],[259.,179.],[0.,179.]],dtype=np.float32)
        q=np.asarray([[35.,20.],[238.,6.],[255.,168.],[12.,176.]],dtype=np.float32)
        h=cv2.getPerspectiveTransform(src,q)
        warped=cv2.warpPerspective(base,h,(280,200),borderValue=255)
        out=register_planar_perspective_from_quad(warped,q,output_size=(260,180))
        self.assertEqual(out["status"],"REGISTERED")
        recovered=out["registered_image"]
        a=base<180
        b=recovered<180
        i=np.logical_and(a,b).sum()
        u=np.logical_or(a,b).sum()
        self.assertGreater(i/u,0.70)

    def test_nonconvex_rejected(self):
        img=np.full((100,100),255,dtype=np.uint8)
        with self.assertRaises(ValueError):
            register_planar_perspective_from_quad(img,[[0,0],[90,0],[0,90],[90,90]])

    def test_tiny_rejected(self):
        img=np.full((100,100),255,dtype=np.uint8)
        with self.assertRaises(ValueError):
            register_planar_perspective_from_quad(img,[[0,0],[1,0],[1,1],[0,1]])

    def test_output_scope_is_nonsemantic(self):
        img=np.full((100,100),255,dtype=np.uint8)
        out=register_planar_perspective_from_quad(img,[[5,5],[95,7],[93,95],[6,92]],output_size=(100,100))
        self.assertFalse(out["terminal_authority"])
        self.assertIn("PLANAR_PROJECTIVE",out["scope"])


if __name__=="__main__":
    unittest.main()
