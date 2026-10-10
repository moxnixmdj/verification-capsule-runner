from __future__ import annotations
import hashlib, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

XSD_URL="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.xsd"
LAB_URL="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928_lab.xml"
UA="ProjectBrain verification research@example.com"
NS="https://www.apple.com/20240928"
LOCAL="LesseeOperatingAndFinanceLeaseLiabilityToBePaid"
EXPECTED_DOC="Amount of lessee's undiscounted obligation for lease payments for operating and finance leases."
XS="http://www.w3.org/2001/XMLSchema"
XBRLI="http://www.xbrl.org/2003/instance"
LINK="http://www.xbrl.org/2003/linkbase"
XLINK="http://www.w3.org/1999/xlink"
DOC_ROLE="http://www.xbrl.org/2003/role/documentation"

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/xml,text/xml;q=0.9,*/*;q=0.1","Accept-Encoding":"identity"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read(4_000_001)
        assert r.status==200,(url,r.status)
        assert r.geturl()==url,(url,r.geturl())
        assert len(raw)<=4_000_000,len(raw)
        return raw

xsd=fetch(XSD_URL); lab=fetch(LAB_URL)
assert b"<!DOCTYPE" not in xsd[:200000].upper() and b"<!ENTITY" not in xsd[:200000].upper()
assert b"<!DOCTYPE" not in lab[:200000].upper() and b"<!ENTITY" not in lab[:200000].upper()

xr=ET.fromstring(xsd)
assert xr.tag=="{"+XS+"}schema",xr.tag
assert xr.attrib.get("targetNamespace")==NS,xr.attrib.get("targetNamespace")
els=[e for e in xr.findall("{"+XS+"}element") if e.attrib.get("name")==LOCAL]
assert len(els)==1,len(els)
e=els[0]
eid=e.attrib["id"]
meta={
 "element_id":eid,
 "xsd_type":e.attrib.get("type"),
 "substitution_group":e.attrib.get("substitutionGroup"),
 "period_type":e.attrib.get("{"+XBRLI+"}periodType"),
 "balance":e.attrib.get("{"+XBRLI+"}balance"),
 "abstract":e.attrib.get("abstract"),
 "nillable":e.attrib.get("nillable"),
}
assert meta["xsd_type"]=="xbrli:monetaryItemType",meta
assert meta["period_type"]=="instant",meta
assert meta["balance"]=="credit",meta

lr=ET.fromstring(lab)
docs=[]
for ll in lr.findall(".//{"+LINK+"}labelLink"):
    locs=set()
    for loc in ll.findall("{"+LINK+"}loc"):
        if urllib.parse.urlsplit(loc.attrib.get("{"+XLINK+"}href","")).fragment==eid:
            labid=loc.attrib.get("{"+XLINK+"}label","").strip()
            if labid: locs.add(labid)
    if not locs: continue
    resources={}
    for labnode in ll.findall("{"+LINK+"}label"):
        lid=labnode.attrib.get("{"+XLINK+"}label","").strip()
        role=labnode.attrib.get("{"+XLINK+"}role","").strip()
        txt="".join(labnode.itertext()).strip()
        resources.setdefault(lid,[]).append((role,txt))
    for arc in ll.findall("{"+LINK+"}labelArc"):
        if arc.attrib.get("{"+XLINK+"}from","").strip() in locs:
            to=arc.attrib.get("{"+XLINK+"}to","").strip()
            for role,txt in resources.get(to,[]):
                if role==DOC_ROLE and txt: docs.append(txt)
docs=list(dict.fromkeys(docs))
assert docs==[EXPECTED_DOC],docs
print("PASS__LIVE_SEC_ISSUER_EXTENSION_CUSTOM_CONCEPT_SEMANTICS")
print("concept_qname={"+NS+"}"+LOCAL)
print("element_id="+eid)
print("documentation="+docs[0])
print("xsd_sha256="+hashlib.sha256(xsd).hexdigest())
print("label_sha256="+hashlib.sha256(lab).hexdigest())
print("metadata="+repr(meta))
