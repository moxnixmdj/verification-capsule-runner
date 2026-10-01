import importlib.util
from pathlib import Path
import unittest
import sys

ROOT=Path(__file__).resolve().parent

def load(name, rel):
    spec=importlib.util.spec_from_file_location(name, ROOT / rel)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

sc=load("source_contract_compiler","independent/brain_core_hardening/source_contract_compiler.py")
ar=load("execution_authority_reducer","independent/brain_core_hardening/execution_authority_reducer.py")


class SourceContractCompilerTests(unittest.TestCase):
    def setUp(self):
        self.text="Must write /app/result.txt.\nThis paragraph is background.\nIf input is missing, fail closed.\n"
        self.atoms=sc.atomize_source(self.text,"instruction.md")

    def valid_payload(self):
        a0,a1,a2=self.atoms
        requirements=[
            {"id":"R1","source_atom_ids":[a0.atom_id]},
            {"id":"R2","source_atom_ids":[a2.atom_id]},
        ]
        dispositions=[
            {"atom_id":a0.atom_id,"kind":"BEHAVIOR","rationale":"required output","requirement_ids":["R1"]},
            {"atom_id":a1.atom_id,"kind":"INFORMATIVE","rationale":"background only","requirement_ids":[]},
            {"atom_id":a2.atom_id,"kind":"BEHAVIOR","rationale":"required failure behavior","requirement_ids":["R2"]},
        ]
        return dispositions,requirements

    def test_lossless_roundtrip_and_complete_mapping_pass(self):
        d,r=self.valid_payload()
        self.assertEqual(sc.reconstruct_source(self.atoms),self.text)
        self.assertEqual(sc.validate_contract_coverage(source_text=self.text,atoms=self.atoms,dispositions=d,requirements=r),[])

    def test_unaccounted_source_atom_fails(self):
        d,r=self.valid_payload()
        d=d[:-1]
        errors=sc.validate_contract_coverage(source_text=self.text,atoms=self.atoms,dispositions=d,requirements=r)
        self.assertTrue(any(x.startswith("UNACCOUNTED_SOURCE_ATOM:") for x in errors))

    def test_ambiguity_is_explicit_blocking_hole(self):
        d,r=self.valid_payload()
        a2=self.atoms[2]
        d[2]={"atom_id":a2.atom_id,"kind":"AMBIGUOUS","rationale":"two plausible readings","requirement_ids":[],"interpretations":["fail task","skip field"],"discriminator":"authoritative clarification required"}
        errors=sc.validate_contract_coverage(source_text=self.text,atoms=self.atoms,dispositions=d,requirements=r)
        self.assertIn("OPEN_SPECIFICATION_HOLE:"+a2.atom_id,errors)

    def test_normative_atom_cannot_be_dismissed_as_informative(self):
        d,r=self.valid_payload()
        a0=self.atoms[0]
        d[0]={"atom_id":a0.atom_id,"kind":"INFORMATIVE","rationale":"attempted dismissal","requirement_ids":[]}
        errors=sc.validate_contract_coverage(source_text=self.text,atoms=self.atoms,dispositions=d,requirements=r)
        self.assertIn("NORMATIVE_OR_HIGH_RISK_ATOM_MARKED_INFORMATIVE:"+a0.atom_id,errors)

    def test_traceability_must_be_bidirectional(self):
        d,r=self.valid_payload()
        r[0]={"id":"R1","source_atom_ids":[self.atoms[2].atom_id]}
        errors=sc.validate_contract_coverage(source_text=self.text,atoms=self.atoms,dispositions=d,requirements=r)
        self.assertIn("TRACEABILITY_NOT_BIDIRECTIONAL:"+self.atoms[0].atom_id+":R1",errors)


class AuthorityReducerTests(unittest.TestCase):
    def chain(self, types):
        events=[]
        prev=None
        for seq,typ in enumerate(types):
            e={"schema":ar.SCHEMA,"event_id":f"e{seq}","task":"t","seq":seq,"prev_event_sha256":prev,"type":typ}
            e["event_sha256"]=ar.canonical_event_hash(e)
            prev=e["event_sha256"]
            events.append(e)
        return events

    def grant_chain(self):
        return self.chain([
            "STAGE_A_PASS","STAGE_B_PASS","SOURCE_BOUNDARY_PASS",
            "EXECUTION_SURFACE_PASS","LEASE_ISSUED","CARRIER_OPEN"
        ])

    def test_complete_fresh_grant_can_execute(self):
        x=ar.derive_authority(self.grant_chain(),task="t",execution_budget=1,verifier_budget=1)
        self.assertTrue(x["valid"])
        self.assertTrue(x["can_execute"])
        self.assertFalse(x["can_verify"])

    def test_later_revocation_dominates_grant(self):
        events=self.grant_chain()
        prev=events[-1]["event_sha256"]
        e={"schema":ar.SCHEMA,"event_id":"e6","task":"t","seq":6,"prev_event_sha256":prev,"type":"LEASE_REVOKED"}
        e["event_sha256"]=ar.canonical_event_hash(e)
        events.append(e)
        x=ar.derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
        self.assertFalse(x["can_execute"])
        self.assertFalse(x["can_verify"])

    def test_closed_carrier_cannot_execute(self):
        events=self.grant_chain()
        prev=events[-1]["event_sha256"]
        e={"schema":ar.SCHEMA,"event_id":"e6","task":"t","seq":6,"prev_event_sha256":prev,"type":"CARRIER_CLOSED"}
        e["event_sha256"]=ar.canonical_event_hash(e)
        events.append(e)
        self.assertFalse(ar.derive_authority(events,task="t",execution_budget=1,verifier_budget=1)["can_execute"])

    def test_broken_hash_chain_fails_closed(self):
        events=self.grant_chain()
        events[3]=dict(events[3])
        events[3]["prev_event_sha256"]="0"*64
        x=ar.derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
        self.assertFalse(x["valid"])
        self.assertFalse(x["can_execute"])

    def test_consumed_execution_exhausts_budget_and_enables_verifier(self):
        events=self.grant_chain()
        prev=events[-1]["event_sha256"]
        e={"schema":ar.SCHEMA,"event_id":"e6","task":"t","seq":6,"prev_event_sha256":prev,"type":"EXECUTION_CONSUMED"}
        e["event_sha256"]=ar.canonical_event_hash(e)
        events.append(e)
        x=ar.derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
        self.assertFalse(x["can_execute"])
        self.assertTrue(x["can_verify"])

    def test_consumed_verifier_exhausts_verifier_budget(self):
        events=self.grant_chain()
        prev=events[-1]["event_sha256"]
        for seq,typ in [(6,"EXECUTION_CONSUMED"),(7,"VERIFIER_CONSUMED")]:
            e={"schema":ar.SCHEMA,"event_id":f"e{seq}","task":"t","seq":seq,"prev_event_sha256":prev,"type":typ}
            e["event_sha256"]=ar.canonical_event_hash(e)
            prev=e["event_sha256"]
            events.append(e)
        x=ar.derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
        self.assertFalse(x["can_verify"])


if __name__=="__main__":
    unittest.main()
