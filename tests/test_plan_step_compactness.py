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


def _assert_no_repeated_phrase(step: str, phrase: str):
    assert step.lower().count(phrase) <= 1, step


def _assert_compact_step(step: str):
    assert step.count(";") <= 2, step
    for phrase in ("family-friendly", "shared", "comfortable", "aligned"):
        _assert_no_repeated_phrase(step, phrase)


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


def test_family_naivasha_exact_steps_compose_constraints_once():
    output = run_engine("Plan a family trip to Naivasha for 4 people at 12th May")
    steps = _extract_plan_steps(output)
    activity = steps[3].lower()
    timing = steps[4].lower()

    assert "boat rides, scenic views, and calm nature experiences" in activity
    assert "keep pacing light, coordinated, and recovery-aware" in activity
    assert "align bookings and align transport" not in timing
    assert timing.count("family") <= 1
    for step in steps:
        _assert_compact_step(step)


def test_family_naivasha_next_weekend_steps_do_not_repeat_group_language():
    output = run_engine("Plan a family trip to naivasha for 2 adults and 3 kids next weekend with a medium budget")
    steps = _extract_plan_steps(output)
    joined = "\n".join(steps).lower()

    assert "family" in joined
    assert "safe, comfortable, and coordinated" in joined
    for step in steps:
        _assert_compact_step(step)


def test_relaxed_naivasha_steps_merge_low_strain_and_recovery_language():
    output = run_engine("Plan a relaxed trip to Naivasha for 2 people 4th May to 8th May")
    steps = _extract_plan_steps(output)
    activity = steps[3].lower()

    assert "boat rides, scenic views, and calm nature experiences" in activity
    assert "keep activities calm, low-strain, and recovery-aware" in activity
    assert "lighter arrival-day" not in activity
    for step in steps:
        _assert_compact_step(step)


def test_family_coast_steps_do_not_suffix_stack_family_coordination():
    output = run_engine("Plan a family trip to the coast for 4 people next weekend")
    steps = _extract_plan_steps(output)
    joined = "\n".join(steps).lower()

    assert "family-friendly" in joined
    assert "shared meeting points and aligned movement" not in joined
    for step in steps:
        _assert_compact_step(step)
