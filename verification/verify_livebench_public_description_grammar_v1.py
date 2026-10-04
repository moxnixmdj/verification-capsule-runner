#!/usr/bin/env python3
import ast
import hashlib
import importlib.util
import json
import pathlib
import string
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "verification_inputs" / "ifbench_public_description_grammar_compiler_v1.py"
EXPECTED_CANDIDATE_BLOB = "5130c4f61083b900bd8ead1ad3bc2b11d4ebca6a"

SOURCES = {
    "modern_instructions": (
        "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py",
        "02b2dfeb50f036b89bec3df34522c73f756d8f44",
    ),
    "modern_registry": (
        "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions_registry.py",
        "adfed4832877566e62970257b50c6fa32c302fb2",
    ),
    "legacy_instructions": (
        "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/instruction_following_eval/instructions.py",
        "4997bab885a676d92545fd91a9a20b48d234a2b2",
    ),
    "legacy_registry": (
        "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/instruction_following_eval/instructions_registry.py",
        "903ed738398648c7cfac61d5ffa478c22f1f0891",
    ),
}
EXPECTED_RESIDUAL = {
    ("ratio:overlap", "reference_text"),
    ("repeat:repeat_span", "prompt_to_repeat"),
    ("combination:repeat_prompt", "prompt_to_repeat"),
}

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def fetch(url: str, expected: str) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read()
    got=git_blob(raw)
    assert got==expected,(url,got,expected)
    return raw.decode("utf-8")

def load_candidate():
    raw=CANDIDATE.read_bytes()
    assert git_blob(raw)==EXPECTED_CANDIDATE_BLOB,(git_blob(raw),EXPECTED_CANDIDATE_BLOB)
    spec=importlib.util.spec_from_file_location("candidate_grammar",CANDIDATE)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

def sym(node):
    if isinstance(node,ast.Name):
        return node.id
    if isinstance(node,ast.Attribute):
        b=sym(node.value)
        return (b+"." if b else "")+node.attr
    if isinstance(node,ast.Call):
        if isinstance(node.func,ast.Attribute) and not node.args:
            return sym(node.func.value)
        if isinstance(node.func,ast.Name) and len(node.args)==1 and node.func.id in {"str","int","float","list","tuple","set"}:
            return sym(node.args[0])
    if isinstance(node,ast.IfExp):
        a,b=sym(node.body),sym(node.orelse)
        return a if a==b else None
    return None

def static_str(node, env):
    if isinstance(node,ast.Constant) and isinstance(node.value,str):
        return node.value
    if isinstance(node,ast.Name):
        return env.get(node.id)
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
        a,b=static_str(node.left,env),static_str(node.right,env)
        return a+b if a is not None and b is not None else None
    return None

def registry_map(src: str):
    tree=ast.parse(src)
    env={}
    changed=True
    while changed:
        changed=False
        for st in tree.body:
            if isinstance(st,ast.Assign) and len(st.targets)==1 and isinstance(st.targets[0],ast.Name):
                k=st.targets[0].id
                if k in env: continue
                v=static_str(st.value,env)
                if v is not None:
                    env[k]=v; changed=True
    for st in tree.body:
        targets=st.targets if isinstance(st,ast.Assign) else ([st.target] if isinstance(st,ast.AnnAssign) else [])
        if not any(isinstance(t,ast.Name) and t.id=="INSTRUCTION_DICT" for t in targets):
            continue
        assert isinstance(st.value,ast.Dict)
        out={}
        for k,v in zip(st.value.keys,st.value.values):
            key=static_str(k,env)
            assert key is not None
            assert isinstance(v,ast.Attribute)
            out[key]=v.attr
        return out
    raise AssertionError("INSTRUCTION_DICT_NOT_FOUND")

def method(cls,name):
    return next((x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name==name),None)

def arg_keys(cls):
    m=method(cls,"get_instruction_args_keys")
    if m:
        for x in ast.walk(m):
            if isinstance(x,ast.Return) and isinstance(x.value,(ast.List,ast.Tuple)):
                vals=[]
                for e in x.value.elts:
                    if not isinstance(e,ast.Constant) or not isinstance(e.value,str):
                        break
                    vals.append(e.value)
                else:
                    return tuple(vals)
    m=method(cls,"get_instruction_args")
    if m:
        for x in ast.walk(m):
            if isinstance(x,ast.Return) and isinstance(x.value,ast.Dict):
                vals=[]
                for k in x.value.keys:
                    if not isinstance(k,ast.Constant) or not isinstance(k.value,str):
                        break
                    vals.append(k.value)
                else:
                    return tuple(vals)
    return ()

def getter_symbols(cls):
    m=method(cls,"get_instruction_args")
    if not m: return {}
    for x in ast.walk(m):
        if isinstance(x,ast.Return) and isinstance(x.value,ast.Dict):
            out={}
            for k,v in zip(x.value.keys,x.value.values):
                if not isinstance(k,ast.Constant) or not isinstance(k.value,str):
                    return {}
                out[k.value]=sym(v)
            return out
    return {}

def visible_symbols_and_fields(cls):
    m=method(cls,"build_description")
    assert m is not None, cls.name
    rendered=set()
    fields=set()
    local_templates={}
    for x in ast.walk(m):
        if isinstance(x,ast.Assign):
            for t in x.targets:
                s=sym(t)
                if s and isinstance(x.value,ast.Constant) and isinstance(x.value.value,str):
                    local_templates[s]=x.value.value
    for x in ast.walk(m):
        if isinstance(x,ast.JoinedStr):
            for part in x.values:
                if isinstance(part,ast.FormattedValue):
                    s=sym(part.value)
                    if s: rendered.add(s)
        if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=="format":
            base=sym(x.func.value)
            template=local_templates.get(base)
            if isinstance(x.func.value,ast.Constant) and isinstance(x.func.value.value,str):
                template=x.func.value.value
            if template:
                for _,field,_,_ in string.Formatter().parse(template):
                    if field: fields.add(field.split(".",1)[0].split("[",1)[0])
            for kw in x.keywords:
                if kw.arg:
                    s=sym(kw.value)
                    if s: rendered.add(s)
    return rendered,fields

def independent_residual(instructions_src, registry_src):
    tree=ast.parse(instructions_src)
    classes={x.name:x for x in tree.body if isinstance(x,ast.ClassDef)}
    reg=registry_map(registry_src)
    residual=set()
    for iid,cname in reg.items():
        cls=classes[cname]
        keys=arg_keys(cls)
        getters=getter_symbols(cls)
        rendered,fields=visible_symbols_and_fields(cls)
        for key in keys:
            gs=getters.get(key)
            if key in fields or (gs is not None and gs in rendered):
                continue
            residual.add((iid,key))
    return reg,residual

def main():
    src={k:fetch(*v) for k,v in SOURCES.items()}
    cand=load_candidate()
    modern=cand.compile_grammar(src["modern_instructions"],src["modern_registry"])
    legacy=cand.compile_grammar(src["legacy_instructions"],src["legacy_registry"])
    combined=cand.combine_grammars(modern,legacy)

    mreg,mres=independent_residual(src["modern_instructions"],src["modern_registry"])
    lreg,lres=independent_residual(src["legacy_instructions"],src["legacy_registry"])
    independent=mres|lres

    assert len(mreg)==58,len(mreg)
    assert len(lreg)==25,len(lreg)
    assert len(mreg)+len(lreg)==83
    assert combined["active_checker_count"]==83
    assert combined["visible_complete_count"]==80
    assert combined["hidden_parameter_checker_count"]==3
    candidate_residual={
        (x["instruction_id"],k)
        for x in combined["checkers"]
        for k in x["hidden_parameter_keys"]
    }
    assert candidate_residual==EXPECTED_RESIDUAL,candidate_residual
    assert independent==EXPECTED_RESIDUAL,independent

    print(json.dumps({
        "status":"PASS",
        "candidate_blob":EXPECTED_CANDIDATE_BLOB,
        "modern_active":58,
        "legacy_active":25,
        "total_active":83,
        "visible_complete":80,
        "hidden_parameter_semantics":sorted([list(x) for x in independent]),
        "independent_ast_implementation":True,
        "terminal_prompt_content_used":False,
        "acceptance_credit":False
    },sort_keys=True))

if __name__=="__main__":
    main()
