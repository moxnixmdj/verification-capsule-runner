#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, inspect, json, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_crypto_escrow_v1_sol"
RUNTIME=SUB/"shadow_cryptographic_escrow_v1.py"
TEST=SUB/"test_shadow_cryptographic_escrow_v1.py"
GOV=SUB/"SHADOW_CRYPTOGRAPHIC_ESCROW_IMPLEMENTATION_V1.json"

EXPECTED={
 RUNTIME:"63a87e2d715b3ceb4355f84196bcb1fa58fdf673",
 TEST:"2719951d54e88fe9c126556a179f3b0150adf69e",
 GOV:"792eda7aab475bfff27b4e9943aae48610b48973",
}

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\x00"+b).hexdigest()

for p,s in EXPECTED.items():
    assert blob(p)==s,(p,blob(p),s)

spec=importlib.util.spec_from_file_location("escrow",RUNTIME)
assert spec and spec.loader
escrow=importlib.util.module_from_spec(spec)
sys.modules["escrow"]=escrow
spec.loader.exec_module(escrow)

params=set(inspect.signature(escrow.write_encrypted_result).parameters)
assert all("private" not in p.lower() for p in params),params

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    reducer=root/"reducer_only"
    writer=root/"writer"
    reducer.mkdir(mode=0o700)
    writer.mkdir(mode=0o700)
    key=reducer/"private.pem"
    cert=writer/"recipient.crt"

    subprocess.run([
      "openssl","req","-x509","-newkey","rsa:2048","-nodes",
      "-subj","/CN=ProjectBrainEscrowVerifier",
      "-keyout",str(key),"-out",str(cert),"-days","1"
    ],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    assert key.is_file() and cert.is_file()
    assert not any("private" in p.name.lower() for p in writer.iterdir())

    cert_sha=hashlib.sha256(cert.read_bytes()).hexdigest()
    payload_a=b"A"
    payload_b=(b"RESULT-B"*10000)

    out_a=writer/"a"
    out_b=writer/"b"
    lease="a"*64
    ra=escrow.write_encrypted_result(
      payload=payload_a,lease_digest_sha256=lease,
      recipient_cert_path=cert,expected_recipient_cert_sha256=cert_sha,
      escrow_dir=out_a
    )
    rb=escrow.write_encrypted_result(
      payload=payload_b,lease_digest_sha256=lease,
      recipient_cert_path=cert,expected_recipient_cert_sha256=cert_sha,
      escrow_dir=out_b
    )

    assert ra["status"]==rb["status"]=="ESCROW_WRITE_OK"
    assert ra["object_name"]==rb["object_name"]==escrow.output_name(lease)
    assert ra["ciphertext_bytes"]==rb["ciphertext_bytes"]
    assert ra["padded_plaintext_bytes"]==rb["padded_plaintext_bytes"]==escrow.DEFAULT_PADDED_PLAINTEXT_BYTES
    assert ra["private_key_required_by_writer"] is False
    assert ra["result_body_disclosed"] is False
    assert ra["result_score_disclosed"] is False
    assert ra["result_summary_disclosed"] is False
    assert ra["result_release_authority"] is False
    assert ra["acceptance_credit_authorized"] is False

    forbidden={"payload","answer","score","summary","result","result_body"}
    assert not forbidden.intersection(ra.keys())
    assert not forbidden.intersection(rb.keys())

    ca=(out_a/ra["object_name"]).read_bytes()
    cb=(out_b/rb["object_name"]).read_bytes()
    assert payload_a not in ca
    assert payload_b[:100] not in cb
    assert len(ca)==len(cb)==ra["ciphertext_bytes"]

    dec=root/"decrypted.bin"
    subprocess.run([
      "openssl","cms","-decrypt","-inform","DER",
      "-in",str(out_a/ra["object_name"]),
      "-recip",str(cert),"-inkey",str(key),"-out",str(dec)
    ],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    recovered=escrow.recover_fixed_plaintext(dec.read_bytes())
    assert recovered==payload_a

    try:
        escrow.write_encrypted_result(
          payload=b"second",lease_digest_sha256=lease,
          recipient_cert_path=cert,expected_recipient_cert_sha256=cert_sha,
          escrow_dir=out_a
        )
        raise AssertionError("duplicate escrow write unexpectedly succeeded")
    except escrow.EscrowError as e:
        assert str(e)=="ESCROW_OBJECT_ALREADY_EXISTS"

gov=json.loads(GOV.read_text())
assert gov["implementation"]["production_recipient_bound"] is False
assert gov["accounting"]["terminal_cases_consumed"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False

print(json.dumps({
 "status":"PASS",
 "runtime_git_blob_sha":blob(RUNTIME),
 "test_git_blob_sha":blob(TEST),
 "governance_git_blob_sha":blob(GOV),
 "writer_private_key_parameter":False,
 "fixed_ciphertext_length":True,
 "plaintext_disk_write":False,
 "duplicate_write_fail_closed":True,
 "separate_private_key_recovery":True,
 "production_recipient_bound":False,
 "terminal_cases_consumed":0,
 "incremental_spend_usd":0
},sort_keys=True))
