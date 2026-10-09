from __future__ import annotations
import importlib.util, json, pathlib, tempfile, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/"source"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m

p=load("sec_issuer_extension_concept_semantics_v1",SRC/"sec_issuer_extension_concept_semantics_v1.py")
v=load("sec_issuer_extension_concept_semantics_verify_v1",SRC/"sec_issuer_extension_concept_semantics_verify_v1.py")

XSD_URL="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.xsd"
LAB_URL="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928_lab.xml"
NS="https://www.apple.com/20240928"
LOCAL="LesseeOperatingAndFinanceLeaseLiabilityToBePaid"
DOC="Amount of lessee's undiscounted obligation for lease payments for operating and finance leases."
UA="ProjectBrain verification research@example.com"
XSD=f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xbrli="http://www.xbrl.org/2003/instance"
 targetNamespace="{NS}">
 <xs:element id="aapl_{LOCAL}" name="{LOCAL}" type="xbrli:monetaryItemType"
  substitutionGroup="xbrli:item" xbrli:periodType="instant" xbrli:balance="credit"
  abstract="false" nillable="true"/>
</xs:schema>""".encode()
LAB=f"""<?xml version="1.0"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
 xmlns:xlink="http://www.w3.org/1999/xlink">
 <link:labelLink xlink:type="extended">
  <link:loc xlink:type="locator" xlink:href="aapl-20240928.xsd#aapl_{LOCAL}" xlink:label="loc"/>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/label" xlink:label="std">Operating and finance lease payments due</link:label>
  <link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/documentation" xlink:label="doc">{DOC}</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="std"/>
  <link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc"/>
 </link:labelLink>
</link:linkbase>""".encode()

class Resp:
    def __init__(self,raw,url,ctype="application/xml",status=200):
        self.raw,self.url,self.status=raw,url,status
        self.headers={"Content-Type":ctype}
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,n=-1): return self.raw if n<0 else self.raw[:n]
    def geturl(self): return self.url

def args():
    return {
        "config_path":"cfg.json",
        "xsd_output_path":"xsd.xml",
        "label_output_path":"lab.xml",
        "semantic_output_path":"sem.json",
    }

def cfg(root,ns=NS,local=LOCAL,label_url=LAB_URL):
    (root/"cfg.json").write_text(json.dumps({
        "xsd_url":XSD_URL,"label_url":label_url,
        "concept_namespace":ns,"local_name":local,"sec_user_agent":UA,
    }))

def synthetic(root,xsd=XSD,lab=LAB,redirect=False):
    cfg(root)
    def fake(req,timeout=30):
        url=req.full_url
        if url==XSD_URL: return Resp(xsd,url)
        if url==LAB_URL: return Resp(lab,"https://example.com/tampered.xml" if redirect else url)
        raise AssertionError(url)
    with patch.object(p.urllib.request,"urlopen",side_effect=fake):
        return p.run(args(),root)

passes=[]
def ok(name,fn):
    fn(); passes.append(name)

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    def positive():
        out=synthetic(root)
        assert out["concept_qname"]=="{"+NS+"}"+LOCAL
        assert out["concept_metadata"]["xsd_type"]=="xbrli:monetaryItemType"
        assert out["concept_metadata"]["period_type"]=="instant"
        assert out["concept_metadata"]["balance"]=="credit"
        assert out["documentation_label"]==DOC
        assert out["semantic_truth_authority"] is False
    ok("synthetic_positive",positive)

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    def verify_positive():
        synthetic(root)
        got=v.verify(root=root,xsd_path="xsd.xml",label_path="lab.xml",semantic_path="sem.json")
        assert got["verified"] is True,got
        assert got["producer_independent"] is True
    ok("independent_verifier",verify_positive)

def expect_error(name,mut_xsd=XSD,mut_lab=LAB,redirect=False,needle=""):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        try:
            synthetic(root,xsd=mut_xsd,lab=mut_lab,redirect=redirect)
        except Exception as exc:
            assert needle in str(exc),(name,type(exc).__name__,str(exc))
            passes.append(name)
            return
        raise AssertionError(name+" did not fail")

expect_error("namespace_mismatch",XSD.replace(NS.encode(),b"https://example.com/wrong"),needle="XSD_TARGET_NAMESPACE_MISMATCH")
expect_error("missing_concept",XSD.replace(LOCAL.encode(),b"OtherConcept"),needle="XSD_CONCEPT_NOT_UNIQUE")
expect_error("wrong_locator",mut_lab=LAB.replace(("aapl_"+LOCAL).encode(),b"aapl_OtherConcept"),needle="DOCUMENTATION_LABEL_NOT_UNIQUE")
extra='<link:label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/documentation" xlink:label="doc2">Different issuer definition.</link:label><link:labelArc xlink:type="arc" xlink:from="loc" xlink:to="doc2"/>'.encode()
expect_error("conflicting_documentation",mut_lab=LAB.replace(b"</link:labelLink>",extra+b"</link:labelLink>"),needle="DOCUMENTATION_LABEL_NOT_UNIQUE")
expect_error("dtd_entity",mut_xsd=b'<!DOCTYPE x [<!ENTITY e "x">]>'+XSD,needle="XSD_DTD_OR_ENTITY_FORBIDDEN")
expect_error("redirect",redirect=True,needle="LABEL_FINAL_URL_MISMATCH")

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    def tamper():
        synthetic(root)
        q=root/"sem.json"
        d=json.loads(q.read_text())
        d["documentation_label"]="invented"
        q.write_text(json.dumps(d))
        got=v.verify(root=root,xsd_path="xsd.xml",label_path="lab.xml",semantic_path="sem.json")
        assert not got["verified"]
        assert "SEMANTIC_FIELD_MISMATCH:documentation_label" in got["errors"]
    ok("tamper_rejected",tamper)

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    def authority():
        synthetic(root)
        q=root/"sem.json"
        d=json.loads(q.read_text())
        d["semantic_truth_authority"]=True
        q.write_text(json.dumps(d))
        got=v.verify(root=root,xsd_path="xsd.xml",label_path="lab.xml",semantic_path="sem.json")
        assert not got["verified"]
        assert "AUTHORITY_BOUNDARY_INVALID:semantic_truth_authority" in got["errors"]
    ok("authority_self_promotion_rejected",authority)

# Live SEC replay through the exact production producer.
# Discover the issuer namespace from the source XSD itself, then require the
# production extractor and independent verifier to reproduce that exact binding.
req=urllib.request.Request(XSD_URL,headers={"User-Agent":UA,"Accept":"application/xml,text/xml;q=0.9,*/*;q=0.1","Accept-Encoding":"identity"})
with urllib.request.urlopen(req,timeout=30) as rr:
    live_xsd=rr.read(4_000_001)
    assert rr.status==200 and rr.geturl()==XSD_URL
live_root=ET.fromstring(live_xsd)
live_ns=live_root.attrib["targetNamespace"]
parsed_ns=urllib.parse.urlsplit(live_ns)
assert parsed_ns.hostname=="www.apple.com",(live_ns,parsed_ns)
assert parsed_ns.path=="/20240928",live_ns
assert parsed_ns.scheme in {"http","https"},live_ns

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    cfg(root,ns=live_ns)
    out=p.run(args(),root)
    got=v.verify(root=root,xsd_path="xsd.xml",label_path="lab.xml",semantic_path="sem.json")
    assert got["verified"] is True,got
    assert out["concept_qname"]=="{"+live_ns+"}"+LOCAL
    assert out["documentation_label"]==DOC,out["documentation_label"]
    assert out["concept_metadata"]["xsd_type"]=="xbrli:monetaryItemType",out["concept_metadata"]
    assert out["concept_metadata"]["period_type"]=="instant",out["concept_metadata"]
    assert out["concept_metadata"]["balance"]=="credit",out["concept_metadata"]
    assert out["semantic_truth_authority"] is False
    assert out["terminal_credit_delta"]==0
    passes.append("live_sec_exact_production_replay")
    print("LIVE_NAMESPACE="+live_ns)
    print("LIVE_XSD_SHA256="+out["xsd_sha256"])
    print("LIVE_LABEL_SHA256="+out["label_sha256"])
    print("LIVE_ELEMENT_ID="+out["concept_metadata"]["element_id"])
    print("LIVE_STANDARD_LABEL="+str(out["standard_label"]))
    print("LIVE_DOCUMENTATION="+out["documentation_label"])

assert len(passes)==11,passes
print("PASS__EXACT_BRAIN_SEC_ISSUER_EXTENSION_SEMANTICS__11_OF_11")
print(json.dumps({
    "tests":passes,
    "concept_qname":"{"+NS+"}"+LOCAL,
    "public_live_source":"SEC_APPLE_2024_10K_EXTENSION_TAXONOMY",
    "semantic_truth_authority":False,
    "terminal_credit_delta":0,
},sort_keys=True))
