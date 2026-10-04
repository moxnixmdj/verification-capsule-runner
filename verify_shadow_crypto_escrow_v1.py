#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, subprocess, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"subject/shadow_crypto_escrow_v1"
EXPECTED={
 "runtime.py":"3d88aee0701083d4996c0a573f2425026e9dcc7d",
 "tests.py":"45759363c52459d5638b740c886d5ab258cc3aed",
 "candidate.json":"8f96955383fceaf3e634f55e9b93907b2526cf7f",
}
def git_blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,e in EXPECTED.items():
    g=git_blob(P/n)
    assert g==e,(n,g,e)

spec=importlib.util.spec_from_file_location("escrow",P/"runtime.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
candidate=json.loads((P/"candidate.json").read_text())
assert candidate["status"].startswith("CANDIDATE__ENCRYPTION_ONLY")
assert candidate["execution_authority"] is False
assert candidate["shadow_collection_authority"] is False

with tempfile.TemporaryDirectory() as td:
    t=pathlib.Path(td)
    key=t/"key.pem"; cert=t/"cert.pem"
    subprocess.run(["openssl","genpkey","-algorithm","RSA","-pkeyopt","rsa_keygen_bits:2048","-out",str(key)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(["openssl","req","-new","-x509","-sha256","-key",str(key),"-subj","/CN=Escrow Independent Test","-days","1","-out",str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    c=cert.read_bytes(); sha=hashlib.sha256(c).hexdigest()
    r1=m.write_encrypted_result(result_bytes=b'{"score":1}',recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256="1"*64,output_dir=t/"o1",padded_plaintext_bytes=4096)
    r2=m.write_encrypted_result(result_bytes=b'x'*1000,recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256="2"*64,output_dir=t/"o2",padded_plaintext_bytes=4096)
    assert r1["ciphertext_bytes"]==r2["ciphertext_bytes"]
    assert r1["plaintext_length_disclosed"] is False
    assert r1["plaintext_sha256_disclosed"] is False
    assert r1["score_or_result_signal_disclosed"] is False
    assert r1["decryption_path_present_in_writer"] is False
    out=t/"o1"/("1"*64+".cms.der")
    dec=subprocess.run(["openssl","cms","-decrypt","-binary","-inform","DER","-in",str(out),"-inkey",str(key),"-recip",str(cert)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    n=int.from_bytes(dec[:8],"big")
    assert dec[8:8+n]==b'{"score":1}'
    try:
        m.write_encrypted_result(result_bytes=b"x",recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256="1"*64,output_dir=t/"o1",padded_plaintext_bytes=4096)
    except m.EscrowWriteFailure as e:
        assert "ESCROW_RESULT_ALREADY_EXISTS" in str(e)
    else:
        raise AssertionError("replay not rejected")
    try:
        m.write_encrypted_result(result_bytes=b"x",recipient_certificate_pem=c,expected_certificate_sha256="0"*64,lease_digest_sha256="3"*64,output_dir=t/"o3",padded_plaintext_bytes=4096)
    except m.EscrowWriteFailure as e:
        assert "RECIPIENT_CERTIFICATE_SHA256_MISMATCH" in str(e)
    else:
        raise AssertionError("cert mismatch not rejected")
print("PASS: exact shadow crypto escrow writer independently verified; fixed-size encryption, exclusive create, and zero-authority semantics preserved")
