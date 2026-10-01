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


    def semantic_payload(self):
        text="Must write file and return status.\n"
        atoms=sc.atomize_source(text,"compound.md")
        atom=atoms[0]
        split=atom.text.index(" and ")
        spans=[
            (0, split, "BEHAVIOR", "WRITE_FILE"),
            (split, len(atom.text), "BEHAVIOR", "RETURN_STATUS"),
        ]
        def units():
            out=[]
            for start,end,kind,fp in spans:
                frag=atom.text[start:end]
                out.append({
                    "atom_id":atom.atom_id,
                    "start":start,
                    "end":end,
                    "text_sha256":__import__("hashlib").sha256(frag.encode()).hexdigest(),
                    "kind":kind,
                    "semantic_fingerprint":fp,
                    "rationale":"independently extracted obligation",
                })
            return out
        sids=[sc.semantic_unit_id(atom.atom_id,s,e) for s,e,_,_ in spans]
        requirements=[
            {"id":"R_WRITE","source_semantic_unit_ids":[sids[0]]},
            {"id":"R_RETURN","source_semantic_unit_ids":[sids[1]]},
        ]
        return text,atoms,{"extractor-a":units(),"extractor-b":units()},requirements

    def test_dual_semantic_span_consensus_passes(self):
        text,atoms,units,reqs=self.semantic_payload()
        self.assertEqual(
            sc.validate_semantic_consensus(
                source_text=text,atoms=atoms,extractor_units=units,requirements=reqs
            ),[]
        )

    def test_compound_obligation_cannot_collapse_to_one_unit(self):
        text,atoms,units,reqs=self.semantic_payload()
        atom=atoms[0]
        frag=atom.text
        one={
            "atom_id":atom.atom_id,"start":0,"end":len(frag),
            "text_sha256":__import__("hashlib").sha256(frag.encode()).hexdigest(),
            "kind":"BEHAVIOR","semantic_fingerprint":"COMPOUND",
            "rationale":"collapsed compound claim",
        }
        units={"extractor-a":[one],"extractor-b":[dict(one)]}
        errors=sc.validate_semantic_consensus(
            source_text=text,atoms=atoms,extractor_units=units,requirements=reqs
        )
        self.assertTrue(any(x.startswith("SEMANTIC_OBLIGATION_UNDERSEGMENTED:") for x in errors))

    def test_semantic_boundary_disagreement_blocks(self):
        text,atoms,units,reqs=self.semantic_payload()
        atom=atoms[0]
        b=[dict(x) for x in units["extractor-b"]]
        b[0]["end"] += 1
        frag=atom.text[b[0]["start"]:b[0]["end"]]
        b[0]["text_sha256"]=__import__("hashlib").sha256(frag.encode()).hexdigest()
        b[1]["start"] += 1
        frag=atom.text[b[1]["start"]:b[1]["end"]]
        b[1]["text_sha256"]=__import__("hashlib").sha256(frag.encode()).hexdigest()
        units["extractor-b"]=b
        errors=sc.validate_semantic_consensus(
            source_text=text,atoms=atoms,extractor_units=units,requirements=reqs
        )
        self.assertTrue(any(x.startswith("SEMANTIC_EXTRACTOR_DISAGREEMENT:") for x in errors))

    def test_semantic_fingerprint_disagreement_blocks(self):
        text,atoms,units,reqs=self.semantic_payload()
        units["extractor-b"][0]["semantic_fingerprint"]="WRITE_SOMETHING_ELSE"
        errors=sc.validate_semantic_consensus(
            source_text=text,atoms=atoms,extractor_units=units,requirements=reqs
        )
        self.assertTrue(any(x.startswith("SEMANTIC_EXTRACTOR_DISAGREEMENT:") for x in errors))

    def test_operative_semantic_unit_requires_requirement(self):
        text,atoms,units,reqs=self.semantic_payload()
        reqs=reqs[:1]
        errors=sc.validate_semantic_consensus(
            source_text=text,atoms=atoms,extractor_units=units,requirements=reqs
        )
        self.assertTrue(any(x.startswith("OPERATIVE_SEMANTIC_UNIT_WITHOUT_REQUIREMENT:") for x in errors))

    def test_ambiguous_consensus_remains_blocking_hole(self):
        text,atoms,units,reqs=self.semantic_payload()
        for extractor in units.values():
            extractor[1]["kind"]="AMBIGUOUS"
            extractor[1]["semantic_fingerprint"]="AMBIGUOUS_RETURN"
        errors=sc.validate_semantic_consensus(
            source_text=text,atoms=atoms,extractor_units=units,requirements=reqs
        )
        self.assertTrue(any(x.startswith("OPEN_SPECIFICATION_HOLE:") for x in errors))


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
