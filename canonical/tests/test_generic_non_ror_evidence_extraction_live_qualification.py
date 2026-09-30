#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, importlib.util, pathlib, subprocess, urllib.request, unittest
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"
EXPECTED={
    "objective_evidence_unit_extract.py":"6598ba92307c55fe6e645b4ecba070d2259818e2",
    "open_research_source_frontend.py":"46fe82d74a35d9318a134fb95e1d5cecfc2dd485",
    "objective_relevance_bm25.py":"95d2b6bac6f6ffb5db97526407fcd22cbcc6c790",
    "source_candidate_provenance_verify.py":"1dc26e68d18010b66211d1d83f7b2024c8ad1fcf",
}

def load(name):
    path=BC/name
    spec=importlib.util.spec_from_file_location("qual_"+name.replace(".py",""),path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress=0
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {"script","style","noscript","svg"}:
            self.suppress+=1
    def handle_endtag(self,tag):
        if tag.lower() in {"script","style","noscript","svg"} and self.suppress:
            self.suppress-=1
    def handle_data(self,data):
        if not self.suppress:
            value=" ".join(str(data or "").split())
            if value:
                self.parts.append(value)

def fetch(url,timeout=25):
    req=urllib.request.Request(url,headers={
        "User-Agent":"ProjectBrain-Independent-Generic-Extraction-Oracle/1.0",
        "Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.2",
    })
    with urllib.request.urlopen(req,timeout=timeout) as response:
        raw=response.read(3_000_000)
        final=response.geturl()
        ctype=str(response.headers.get("Content-Type") or "")
        status=int(getattr(response,"status",200))
    return raw,final,ctype,status

def independent_visible(raw,ctype):
    text=raw.decode("utf-8","replace")
    if "html" not in ctype.lower() and "<html" not in text[:2000].lower():
        return " ".join(text.split())
    parser=Visible()
    parser.feed(text)
    return " ".join(html.unescape(" ".join(parser.parts)).split())

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor=load("objective_evidence_unit_extract.py")
        cls.rank=load("objective_relevance_bm25.py")
        cls.prov=load("source_candidate_provenance_verify.py")

    def test_exact_candidate_blobs(self):
        for name,expected in EXPECTED.items():
            got=subprocess.check_output(["git","hash-object",str(BC/name)],text=True).strip()
            self.assertEqual(got,expected,(name,got,expected))

    def _case(self,objective,candidates,expected_url_fragment):
        relevance=self.rank.rank(objective,candidates)
        self.assertEqual(relevance.get("status"),"LEXICAL_RELEVANCE_RANKED",relevance)
        idx=int(relevance["top_candidate_original_index"])
        selected=candidates[idx]
        self.assertIn(expected_url_fragment,selected["url"],(selected,relevance))

        provenance=self.prov.verify(selected,timeout=25)
        self.assertEqual(provenance.get("status"),"RETRIEVAL_PROVENANCE_VERIFIED",provenance)

        out=self.extractor.extract(
            objective,selected,provenance,relevance,timeout=25,max_units=8
        )
        self.assertEqual(out.get("status"),"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)
        self.assertEqual(out.get("evidence_extraction_status"),"VERIFIED",out)
        self.assertGreaterEqual(int(out.get("evidence_unit_count") or 0),1,out)
        self.assertEqual(out.get("model_dependency_count"),0,out)
        self.assertEqual(out.get("incremental_spend_usd"),0,out)
        self.assertEqual(out.get("claim_relation_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("factual_correctness_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED",out)

        raw2,final2,ctype2,status2=fetch(provenance["final_url"])
        self.assertEqual(status2,200)
        self.assertEqual(final2,provenance["final_url"])
        visible=independent_visible(raw2,ctype2).lower()
        for unit in out["evidence_units"]:
            text=" ".join(unit["text"].split())
            self.assertIn(text.lower(),visible,(selected["url"],text[:160]))
            self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(),unit["text_sha256"])
            self.assertGreaterEqual(len(unit["matched_objective_tokens"]),2)
        return out

    def test_python_floating_point_non_ror_route(self):
        self._case(
            "Assess Python floating point representation error and accurate summation behavior",
            [
                {
                    "url":"https://docs.python.org/3/tutorial/floatingpoint.html",
                    "title":"Floating-Point Arithmetic: Issues and Limitations",
                    "snippet":"Representation error, floating point arithmetic, math.fsum and accurate summation.",
                },
                {
                    "url":"https://docs.python.org/3/library/email.html",
                    "title":"email package",
                    "snippet":"Email message parsing and handling package.",
                },
                {
                    "url":"https://docs.python.org/3/library/venv.html",
                    "title":"Creation of virtual environments",
                    "snippet":"Virtual environment creation and package isolation.",
                },
            ],
            "floatingpoint",
        )

    def test_sqlite_wal_non_ror_route(self):
        self._case(
            "Assess SQLite write ahead logging checkpoint behavior and concurrency",
            [
                {
                    "url":"https://www.sqlite.org/wal.html",
                    "title":"Write-Ahead Logging",
                    "snippet":"SQLite WAL checkpoint behavior, readers writers and concurrency.",
                },
                {
                    "url":"https://www.sqlite.org/json1.html",
                    "title":"JSON Functions And Operators",
                    "snippet":"SQLite JSON parsing functions and operators.",
                },
                {
                    "url":"https://www.sqlite.org/lang_vacuum.html",
                    "title":"VACUUM",
                    "snippet":"Rebuild a database file with VACUUM.",
                },
            ],
            "wal",
        )

    def test_no_ror_or_authority_input_is_used(self):
        import inspect
        params=list(inspect.signature(self.extractor.extract).parameters)
        self.assertEqual(params[:4],["objective","candidate","provenance","relevance"],params)
        self.assertNotIn("authority_identity",params)

if __name__=="__main__":
    unittest.main(verbosity=2)
