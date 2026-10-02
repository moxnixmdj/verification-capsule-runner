import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from hle_strict_reference_scorer import extract_declared_answer, score_predictions, strict_reference_verdict

def main():
    assert strict_reference_verdict("Answer: Paris","Paris").correct
    assert strict_reference_verdict("Explanation: x\nAnswer: Paris\nConfidence: 80%","Paris").correct
    assert not strict_reference_verdict("Answer: paris","Paris").correct
    assert not strict_reference_verdict("Answer: 0.5","1/2").correct
    assert not strict_reference_verdict("Answer: four","4").correct
    assert not strict_reference_verdict("Answer: A\nAnswer: B","A").correct
    assert not strict_reference_verdict("Explanation: Paris","Paris").correct
    a,r=extract_declared_answer("Answer: A\nAnswer: B")
    assert a is None and r=="ANSWER_LINE_COUNT_2"
    out=score_predictions(
      {"q1":"Answer: A","q2":"Answer: wrong"},
      [{"id":"q1","answer":"A"},{"id":"q2","answer":"B"},{"id":"q3","answer":"C"}],
    )
    assert out["correct"]==1 and out["total"]==3
    assert out["official_score_equivalence_claimed"] is False
    print("HLE_STRICT_SCORER_PUBLIC_PREFLIGHT_PASS")

if __name__=="__main__":
    main()
