from engine.runner import run_engine


def _extract_plan_steps(output: str) -> list[str]:
    steps = []
    collecting = False

    for line in output.splitlines():
        stripped = line.strip()

        if stripped == "Plan Steps:":
            collecting = True
            continue

        if collecting and stripped in {"Checks", "Checks:", "Risks", "Risks:", "Draft Itinerary", "Draft Itinerary:"}:
            break

        if collecting:
            prefix = stripped.split(" ", 1)[0]
            if prefix.endswith(".") and prefix[:-1].isdigit():
                steps.append(stripped)

    return steps


def test_ol_kalau_relaxed_group_steps_do_not_suffix_stack():
    output = run_engine("Plan a relaxed trip to Ol Kalau for 4 people at 22nd June with a budget of 200000")
    steps = _extract_plan_steps(output)

    assert len(steps) == 5
    joined = "\n".join(steps)

    assert "destination to Ol Kalau" in joined

    for step in steps:
        assert step.count(";") <= 1, step
        assert " with " not in step.lower().split(" with ", 1)[-1], step
        assert "that keep physical effort light; in quieter settings" not in step.lower()
        assert "fewer activities and more recovery time; a lighter arrival-day pace" not in step.lower()
        assert "relaxed rhythm while confirming the shared schedule for the group; keep enough room" not in step.lower()


def test_unknown_or_unprofiled_destination_steps_stay_neutral_and_readable():
    output = run_engine("Plan a relaxed trip to Ol Kalau for 4 people at 22nd June with a budget of 200000")
    steps = _extract_plan_steps(output)
    joined = "\n".join(steps).lower()

    forbidden = [
        "coastal",
        "beach",
        "beachfront",
        "marine",
        "water activities",
        "game drive",
        "wildlife viewing",
    ]

    for phrase in forbidden:
        assert phrase not in joined


def test_nakuru_relaxed_steps_remain_compact_after_structured_composition():
    output = run_engine("Plan a relaxed trip to Nakuru for 2 people at 12th June with a budget of 20000")
    steps = _extract_plan_steps(output)

    assert len(steps) == 5

    joined = "\n".join(steps)
    lowered = joined.lower()

    assert "destination to Nakuru" in joined
    assert "destination to nakuru" not in joined
    assert "coastal" not in lowered
    assert "beach" not in lowered
    assert "water activities" not in lowered

    for step in steps:
        assert step.count(";") <= 1, step
        assert "relaxed rhythm keep enough room" not in step.lower()
