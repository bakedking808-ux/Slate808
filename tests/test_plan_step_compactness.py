import re

from engine.runner import run_engine


def _extract_plan_steps(output: str) -> list[str]:
    lines = output.splitlines()
    steps = []
    collecting = False

    for line in lines:
        if line.strip() == "Plan Steps:":
            collecting = True
            continue

        if collecting and line.strip() in {"Checks:", "Risks:", "Draft Itinerary:"}:
            break

        if collecting and re.match(r"^\d+\.\s+", line.strip()):
            steps.append(line.strip())

    return steps


def test_nakuru_relaxed_steps_are_compact_and_not_suffix_stacked():
    output = run_engine("Plan a relaxed trip to Nakuru for 2 people at 12th June with a budget of 20000")
    steps = _extract_plan_steps(output)

    assert len(steps) == 5

    joined_text = "\n".join(steps)
    joined = joined_text.lower()

    assert "destination to nakuru" not in joined_text
    assert "destination to Nakuru" in joined_text

    assert "coastal" not in joined
    assert "beach" not in joined
    assert "water activities" not in joined

    for step in steps:
        assert step.count(";") <= 1
        assert " with " not in step.lower().split(" with ", 1)[-1], step
        assert "that keep physical effort light; in quieter settings" not in step.lower()
        assert "relaxed rhythm keep enough room" not in step.lower()
