import math, pathlib, wave
import numpy as np

SR=22050
dur=2.0
t=np.arange(int(SR*dur),dtype=np.float32)/SR
# synthetic C-major SATB chord, deliberately generic/non-task audio
freqs=[130.8128,196.0,261.6256,329.6276]
x=sum(0.18*np.sin(2*np.pi*f*t) for f in freqs)
x=np.clip(x,-0.95,0.95)
p=pathlib.Path("/tmp/satb_generic.wav")
with wave.open(str(p),"wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x*32767).astype("<i2").tobytes())

from basic_pitch import ICASSP_2022_MODEL_PATH, ONNX_PRESENT, TF_PRESENT
from basic_pitch import inference
assert ONNX_PRESENT, "ONNX runtime unavailable"
assert not TF_PRESENT, "Smoke must prove explicit ONNX-only path, not TensorFlow fallback"
model=inference.Model(ICASSP_2022_MODEL_PATH)
out,midi,events=inference.predict(p, model)
assert {"note","onset","contour"} <= set(out)
assert out["note"].shape[0] > 0
assert isinstance(events,list)
print("BASIC_PITCH_ONNX_PY312_PASS", ICASSP_2022_MODEL_PATH, len(events))

from music21 import stream, note, meter, clef, key, bar
score=stream.Score()
for i,(pid,name,pitch,clf) in enumerate([
    ("P1","Soprano","E4",clef.TrebleClef()),
    ("P2","Alto","C4",clef.TrebleClef()),
    ("P3","Tenor","G3",clef.TrebleClef()),
    ("P4","Bass","C3",clef.BassClef()),
]):
    part=stream.Part(id=pid); part.partName=name
    m=stream.Measure(number=1)
    m.insert(0,meter.TimeSignature("4/4")); m.insert(0,key.KeySignature(0)); m.insert(0,clf)
    n=note.Note(pitch); n.quarterLength=4
    m.append(n); m.rightBarline=bar.Barline("final")
    part.append(m); score.append(part)
xml=pathlib.Path("/tmp/generic.musicxml")
score.write("musicxml", fp=str(xml))
parsed=stream.Score()
from music21 import converter
parsed=converter.parse(str(xml))
assert len(parsed.parts)==4
assert [p.partName for p in parsed.parts]==["Soprano","Alto","Tenor","Bass"]
print("MUSIC21_MUSICXML_PY312_PASS", xml.stat().st_size)
