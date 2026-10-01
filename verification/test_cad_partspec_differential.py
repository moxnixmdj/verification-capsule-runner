import json, random, unittest
from pydantic import ValidationError
import verification.brain_cad_partspec as b
import verification.donor_cad_partspec as d

def same_result(payload):
    bo=b.PartSpec.model_validate(payload)
    do=d.PartSpec.model_validate(payload)
    assert bo.model_dump()==do.model_dump(), (bo.model_dump(),do.model_dump())
    assert bo.bbox()==do.bbox(), (bo.bbox(),do.bbox())
    assert bo.sanity_check()==do.sanity_check(), (bo.sanity_check(),do.sanity_check())
    br=b.PartSpec.model_validate_json(bo.model_dump_json())
    dr=d.PartSpec.model_validate_json(do.model_dump_json())
    assert br.model_dump()==dr.model_dump()

class CadPartSpecDifferential(unittest.TestCase):
    def test_pinned_donor_examples(self):
        cases=[
          {"geometry":{"kind":"extruded","profile_kind":"rectangle","width":50,"height":30,"thickness":5},"holes":[{"x":25,"y":15,"diameter":10}]},
          {"units":"mm","profile_kind":"rectangle","width":50,"height":30,"thickness":5,"holes":[{"x":25,"y":15,"diameter":10,"through":True}]},
          {"geometry":{"kind":"revolved","segments":[{"z_start":0,"z_end":8,"outer_diameter":76,"inner_diameter":28},{"z_start":8,"z_end":26,"outer_diameter":48,"inner_diameter":28}]},
           "holes":[{"id":"mounting_hole","x":38,"y":66,"diameter":5.3,"hole_type":"counterbore","counterbore_diameter":7.8,"counterbore_depth":4}]},
          {"geometry":{"kind":"unsupported","reason":"bent sheet metal","visible_features":["two bends"]}},
          {"geometry":{"kind":"multibody","bodies":[{"shape":"box","dx":116,"dy":105,"dz":105}]},"dimensions":[{"name":"overall_depth","nominal":100,"tol_plus":.1,"tol_minus":.1}]}
        ]
        for c in cases: same_result(c)

    def test_randomized_supported_specs_match(self):
        rng=random.Random(20261001)
        for i in range(1200):
            typ=i%4
            if typ==0:
                w=rng.uniform(1,200); h=rng.uniform(1,200); t=rng.uniform(.2,50)
                payload={"units":"mm","geometry":{"kind":"extruded","profile_kind":"rectangle","width":w,"height":h,"thickness":t,
                    "corner_radius":rng.uniform(0,min(w,h)*.6)},
                    "holes":[{"x":rng.uniform(-10,w+10),"y":rng.uniform(-10,h+10),"diameter":rng.uniform(.1,30),"hole_type":rng.choice(["through","blind"]),
                              "depth":rng.uniform(.1,max(.11,t*1.2))} for _ in range(rng.randint(0,3))]}
            elif typ==1:
                segs=[]; z=0.0
                for j in range(rng.randint(1,5)):
                    length=rng.uniform(.1,30); od=rng.uniform(1,100); inner=rng.uniform(0,od*.9)
                    segs.append({"z_start":z,"z_end":z+length,"outer_diameter":od,"inner_diameter":inner}); z+=length
                payload={"geometry":{"kind":"revolved","segments":segs}}
            elif typ==2:
                bodies=[]
                for j in range(rng.randint(1,8)):
                    if rng.random()<.6:
                        bodies.append({"shape":"box","operation":"add","x":rng.uniform(-20,20),"y":rng.uniform(-20,20),"z":rng.uniform(-20,20),
                          "dx":rng.uniform(.1,50),"dy":rng.uniform(.1,50),"dz":rng.uniform(.1,50)})
                    else:
                        bodies.append({"shape":"cylinder","operation":rng.choice(["add","cut"]),"x":rng.uniform(-20,20),"y":rng.uniform(-20,20),"z":rng.uniform(-20,20),
                          "diameter":rng.uniform(.1,30),"length":rng.uniform(.1,50),"axis":rng.choice(["x","y","z"])})
                payload={"geometry":{"kind":"multibody","bodies":bodies}}
            else:
                payload={"geometry":{"kind":"unsupported","reason":"unknown topology","visible_features":["x"],"envelope_width":rng.choice([None,rng.uniform(1,200)]),
                  "envelope_height":rng.choice([None,rng.uniform(1,200)]),"envelope_depth":rng.choice([None,rng.uniform(1,200)])}}
            same_result(payload)

    def test_invalid_payload_accept_reject_equivalence(self):
        bad=[
          {},
          {"geometry":{"kind":"extruded","profile_kind":"rectangle","thickness":3}},
          {"geometry":{"kind":"revolved","segments":[]}},
          {"geometry":{"kind":"multibody","bodies":[]}}
        ]
        for payload in bad:
            def outcome(mod):
                try:
                    x=mod.PartSpec.model_validate(payload)
                    return ("ok",x.sanity_check())
                except Exception as e:
                    return ("err",type(e).__name__)
            self.assertEqual(outcome(b),outcome(d))

if __name__=="__main__":
    unittest.main()
