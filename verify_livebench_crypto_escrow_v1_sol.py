#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, inspect, json, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_crypto_escrow_v1_sol"
RUNTIME=SUB/"shadow_cryptographic_escrow_v1.py"
TEST=SUB/"test_shadow_cryptographic_escrow_v1.py"
GOV=SUB/"SHADOW_CRYPTOGRAPHIC_ESCROW_IMPLEMENTATION_V1.json"
CERT=SUB/"livebench_shadow_escrow_v1_public.crt"
RECIPIENT=SUB/"LIVEBENCH_SHADOW_ESCROW_RECIPIENT_BINDING_V1.json"

EXPECTED={
 RUNTIME:"63a87e2d715b3ceb4355f84196bcb1fa58fdf673",
 TEST:"2719951d54e88fe9c126556a179f3b0150adf69e",
 GOV:"792eda7aab475bfff27b4e9943aae48610b48973",
 CERT:"99dea0cf31467df8051ba745d74d8768c7d218a4",
 RECIPIENT:"75b90e595e759b55659063201fd5aa18c60efd01",
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
    payload_a=b"PROJECT_BRAIN_ESCROW_PLAINTEXT_MARKER_7f91d6c2a83e4b5fa0d1c9e8"
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

cert_sha=hashlib.sha256(CERT.read_bytes()).hexdigest()
assert cert_sha=="f11521c6e83d3394a79df41963992c01507121787c503989cc503c1b31dfb2a5"
pub_der=subprocess.check_output(
  "openssl x509 -in "+str(CERT)+" -pubkey -noout | openssl pkey -pubin -outform DER",
  shell=True,
)
assert hashlib.sha256(pub_der).hexdigest()=="aec0a39931a202874626bf40b9fe5d86dee4920a2ed2de7ef2bde4f647fcf666"
subprocess.run(["openssl","verify","-CAfile",str(CERT),str(CERT)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
subprocess.run(["openssl","x509","-in",str(CERT),"-checkend","0","-noout"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
subject=subprocess.check_output(["openssl","x509","-in",str(CERT),"-noout","-subject"],text=True)
assert "Project Brain LiveBench Shadow Escrow V1" in subject
assert b"BEGIN PRIVATE KEY" not in CERT.read_bytes()
assert b"BEGIN RSA PRIVATE KEY" not in CERT.read_bytes()

recipient=json.loads(RECIPIENT.read_text())
assert recipient["recipient"]["certificate_sha256"]==cert_sha
assert recipient["recipient"]["public_key_der_sha256"]=="aec0a39931a202874626bf40b9fe5d86dee4920a2ed2de7ef2bde4f647fcf666"
assert recipient["recipient"]["production_recipient_bound"] is True
assert recipient["recipient"]["private_key_in_github"] is False
assert recipient["recipient"]["evaluation_runner_private_key_access"] is False
assert recipient["private_key_custody"]["outside_github"] is True
assert recipient["accounting"]["terminal_cases_consumed"]==0
assert recipient["execution_authority"] is False
assert recipient["promotion_authority"] is False
assert recipient["fresh_reality_authority"] is False

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
 "production_recipient_bound":True,
 "recipient_certificate_sha256":cert_sha,
 "recipient_self_signature_verified":True,
 "terminal_cases_consumed":0,
 "incremental_spend_usd":0
},sort_keys=True))
