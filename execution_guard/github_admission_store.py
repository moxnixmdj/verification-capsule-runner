"""GitHub Contents adapter for immutable execution admission records."""
import base64, binascii, hashlib, json, re
from urllib.parse import quote

class StoreUnavailable(RuntimeError): pass
class RateLimited(StoreUnavailable):
    def __init__(self,reset_at=None,retry_after=None):
        self.reset_at=reset_at; self.retry_after=retry_after
        super().__init__("GITHUB_RATE_LIMIT_NO_RETRY")

def _integer(value):
    try:return int(value)
    except (ValueError,TypeError):return None
def _safe_path(path):
    if not isinstance(path,str) or not re.fullmatch(r"[A-Za-z0-9_.\-/]+",path):
        raise ValueError("INVALID_RECORD_PATH")
    if any(part in ("",".","..") for part in path.split("/")): raise ValueError("INVALID_RECORD_PATH")
    return path
def _blob_sha(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

class GitHubContentsStore:
    def __init__(self,request,repository,branch,namespace="admissions"):
        if not callable(request): raise ValueError("REQUEST_TRANSPORT_REQUIRED")
        if not isinstance(repository,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repository):
            raise ValueError("INVALID_REPOSITORY")
        if not isinstance(branch,str) or not branch.strip() or branch in ("main","master"):
            raise ValueError("EXPLICIT_COORDINATION_BRANCH_REQUIRED")
        self.request=request; self.repository=repository; self.branch=branch; self.namespace=_safe_path(namespace)
    def _path(self,key):
        relative=self.namespace+"/"+_safe_path(key)
        return "/repos/"+self.repository+"/contents/"+relative,relative
    def _request(self,method,path,payload):
        try: status,body,headers=self.request(method,path,payload)
        except Exception as exc: raise StoreUnavailable("TRANSPORT_UNCERTAIN_NO_RETRY") from exc
        if type(status) is not int or not isinstance(headers,dict): raise StoreUnavailable("MALFORMED_HTTP_REPLY")
        headers={str(k).lower():v for k,v in headers.items()}
        message=str(body.get("message","")) if isinstance(body,dict) else ""
        if status==429 or (status==403 and (str(headers.get("x-ratelimit-remaining"))=="0" or "rate limit" in message.lower())):
            raise RateLimited(_integer(headers.get("x-ratelimit-reset")),_integer(headers.get("retry-after")))
        return status,body
    def create(self,key,value):
        path,relative=self._path(key)
        if not isinstance(value,dict): raise ValueError("RECORD_OBJECT_REQUIRED")
        raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        if len(raw)>65536: raise ValueError("RECORD_TOO_LARGE")
        payload={"message":"Reserve immutable execution evidence","branch":self.branch,
                 "content":base64.b64encode(raw).decode("ascii")}
        status,body=self._request("PUT",path,payload)
        if status in (409,422): return False
        if status!=201 or not isinstance(body,dict): raise StoreUnavailable("CREATE_NOT_CONFIRMED")
        content=body.get("content")
        if not isinstance(content,dict) or content.get("path")!=relative or content.get("sha")!=_blob_sha(raw):
            raise StoreUnavailable("CREATE_RECEIPT_BINDING_MISMATCH")
        return True
    def read(self,key):
        path,relative=self._path(key)
        status,body=self._request("GET",path+"?ref="+quote(self.branch,safe=""),None)
        if status==404:return None
        if status!=200 or not isinstance(body,dict): raise StoreUnavailable("READ_NOT_CONFIRMED")
        if body.get("type")!="file" or body.get("path")!=relative or body.get("encoding")!="base64":
            raise StoreUnavailable("MALFORMED_RECORD_ENVELOPE")
        try:
            encoded=body["content"]
            if not isinstance(encoded,str) or len(encoded)>100000: raise ValueError("oversized record")
            raw=base64.b64decode("".join(encoded.split()),validate=True)
            if len(raw)>65536 or body.get("sha")!=_blob_sha(raw): raise ValueError("blob hash mismatch")
            value=json.loads(raw)
            if not isinstance(value,dict): raise ValueError("record is not object")
        except (KeyError,ValueError,TypeError,UnicodeError,binascii.Error) as exc:
            raise StoreUnavailable("MALFORMED_OR_CORRUPT_RECORD") from exc
        return value
