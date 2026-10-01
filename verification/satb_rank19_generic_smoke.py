import math, wave, tempfile, pathlib, json, os
import numpy as np

# Synthetic dry four-voice harmonic texture. This is not task audio.
sr=22050
dur=8.0
n=int(sr*dur)
x=np.zeros(n,dtype=np.float32)
chords=[
 [48,55,60,64],
 [50,57,62,65],
 [52,59,64,67],
 [53,60,65,69],
]
def hz(m): return 440.0*(2.0**((m-69)/12.0))
seg=n//len(chords)
for ci,ch in enumerate(chords):
    lo=ci*seg
    hi=n if ci==len(chords)-1 else (ci+1)*seg
    tt=np.arange(hi-lo,dtype=np.float32)/sr
    env=np.ones_like(tt)
    fade=min(int(0.03*sr),len(tt)//4)
    if fade>1:
        env[:fade]=np.linspace(0,1,fade)
        env[-fade:]=np.linspace(1,0,fade)
    for midi in ch:
        f=hz(midi)
        y=np.zeros_like(tt)
        # Harmonic-rich but deterministic choir/organ-like synthetic tone.
        for k,amp in ((1,1.0),(2,.35),(3,.18),(4,.10)):
            y += amp*np.sin(2*math.pi*f*k*tt)
        x[lo:hi] += 0.12*env*y
x=np.clip(x,-.95,.95)
tmp=pathlib.Path(tempfile.mkdtemp(prefix="rank19-stageb-"))
wav=tmp/"poly4.wav"
with wave.open(str(wav),"wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((x*32767).astype("<i2").tobytes())

import onnxruntime as ort
from basic_pitch import FilenameSuffix, build_icassp_2022_model_path
from basic_pitch.inference import Model, predict
onnx_path=build_icassp_2022_model_path(FilenameSuffix.onnx)
assert onnx_path.exists(), onnx_path
model=Model(onnx_path)
assert model.model_type.name=="ONNX", model.model_type
providers=model.model.get_providers()
assert "CPUExecutionProvider" in providers, providers
out,midi_data,note_events=predict(str(wav),model)
assert len(note_events)>0, "generic polyphonic AMT produced no note events"
pitches=sorted({int(e[2]) for e in note_events})
assert len(pitches)>=3, pitches
print("BASIC_PITCH_CPU_SMOKE_PASS",len(note_events),pitches[:16],providers)

from xml.etree import ElementTree as ET
from music21 import converter

# Deterministic MusicXML 3.1 serializer smoke with exact IDs.
score=ET.Element("score-partwise",version="3.1")
part_list=ET.SubElement(score,"part-list")
names=["Soprano","Alto","Tenor","Bass"]
for idx,name in enumerate(names,1):
    sp=ET.SubElement(part_list,"score-part",id=f"P{idx}")
    ET.SubElement(sp,"part-name").text=name
for idx,(name,pn) in enumerate(zip(names,["E4","C4","G3","C3"]),1):
    part=ET.SubElement(score,"part",id=f"P{idx}")
    meas=ET.SubElement(part,"measure",number="1")
    attrs=ET.SubElement(meas,"attributes")
    ET.SubElement(attrs,"divisions").text="2"
    key_el=ET.SubElement(attrs,"key"); ET.SubElement(key_el,"fifths").text="0"
    time_el=ET.SubElement(attrs,"time")
    ET.SubElement(time_el,"beats").text="4"; ET.SubElement(time_el,"beat-type").text="4"
    clef_el=ET.SubElement(attrs,"clef")
    ET.SubElement(clef_el,"sign").text="F" if name=="Bass" else "G"
    ET.SubElement(clef_el,"line").text="4" if name=="Bass" else "2"
    ne=ET.SubElement(meas,"note")
    pe=ET.SubElement(ne,"pitch")
    step=pn[0]; octave=pn[-1]
    ET.SubElement(pe,"step").text=step
    ET.SubElement(pe,"octave").text=octave
    ET.SubElement(ne,"duration").text="8"
    ET.SubElement(ne,"type").text="whole"
    bl=ET.SubElement(meas,"barline",location="right")
    ET.SubElement(bl,"bar-style").text="light-heavy"
xml=tmp/"synthetic.musicxml"
ET.ElementTree(score).write(xml,encoding="utf-8",xml_declaration=True)

raw=ET.parse(xml).getroot()
assert raw.tag=="score-partwise" and raw.attrib.get("version")=="3.1"
assert [x.attrib["id"] for x in raw.findall("./part-list/score-part")]==["P1","P2","P3","P4"]
assert [x.attrib["id"] for x in raw.findall("./part")]==["P1","P2","P3","P4"]
assert [x.findtext("part-name") for x in raw.findall("./part-list/score-part")]==names
assert all(x.findtext("./measure/barline/bar-style")=="light-heavy" for x in raw.findall("./part"))
parsed=converter.parse(xml)
assert len(parsed.parts)==4
assert [p.partName for p in parsed.parts]==names
print("DETERMINISTIC_MUSICXML_MUSIC21_PARSE_PASS",xml.stat().st_size)

# Generic deterministic constraint/mutant canaries.
def noncross_ok(states):
    return all(s>=a>=t>=b for s,a,t,b in states)
good=[(64,60,55,48),(65,62,57,50)]
bad=[(60,64,55,48)]
assert noncross_ok(good)
assert not noncross_ok(bad)

allowed_ticks={1,2,3,4,6,8} # eighth-note units
assert all(v in allowed_ticks for v in [1,2,3,4,6,8])
assert 5 not in allowed_ticks

def grid_ok(events):
    return all(float(v).is_integer() for ev in events for v in ev)
assert grid_ok([(0,2),(2,4),(4,8)])
assert not grid_ok([(0,2.5)])

print("DETERMINISTIC_MUTANT_CANARIES_PASS")
