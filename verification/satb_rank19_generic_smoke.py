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

from music21 import stream, note, meter, clef, key, bar
score=stream.Score(id="synthetic")
names=["Soprano","Alto","Tenor","Bass"]
pitches4=["E4","C4","G3","C3"]
for idx,(name,pn) in enumerate(zip(names,pitches4),1):
    p=stream.Part(id=f"P{idx}")
    p.partName=name
    m=stream.Measure(number=1)
    m.insert(0,meter.TimeSignature("4/4"))
    m.insert(0,key.KeySignature(0))
    m.insert(0,clef.BassClef() if name=="Bass" else clef.TrebleClef())
    q=note.Note(pn,quarterLength=4)
    m.append(q)
    m.rightBarline=bar.Barline("final")
    p.append(m); score.append(p)
xml=tmp/"synthetic.musicxml"
score.write("musicxml",fp=xml)
from music21 import converter
s2=converter.parse(xml)
parts=list(s2.parts)
assert [p.id for p in parts]==["P1","P2","P3","P4"]
assert [p.partName for p in parts]==names
assert len(parts)==4
print("MUSIC21_MUSICXML_ROUNDTRIP_PASS",xml.stat().st_size)

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
