from engine.generator import generate_plan
from engine.checker import check_plan
from engine.fixer import fix_plan
from engine.logger import log_run, create_log_entry, log_event
from engine.input_gate import assess_input
from engine.task_personality import apply_task_personality
from engine.task_checks import apply_task_checks
from engine.plan_refiner import refine_plan
from engine.execution_readiness import evaluate_execution_readiness
from engine.formatter import format_output
from contracts.execution_readiness_contract import ExecutionReadinessRequest
from uuid import uuid4


_PENDING_EXECUTION_CONTEXT: dict | None = None


def set_execution_observability_context(**context) -> None:
    global _PENDING_EXECUTION_CONTEXT
    _PENDING_EXECUTION_CONTEXT = dict(context)


def _consume_execution_observability_context() -> dict:
    global _PENDING_EXECUTION_CONTEXT
    context = dict(_PENDING_EXECUTION_CONTEXT or {})
    _PENDING_EXECUTION_CONTEXT = None
    return context


def is_llm_enabled() -> bool:
    return False


def generate_with_llm(request: str) -> list | None:
    return None


def _decision_path(*stages: str) -> str:
    return ">".join(stage for stage in stages if stage)


def run_engine(request: str) -> str:
    fixer_actions = []
    llm_used = False
    llm_raw_steps = None
    initial_checker_result = None
    run_trace_id = str(uuid4())
    execution_context = _consume_execution_observability_context()

    gate = assess_input(request)

    if gate["status"] == "blocked":
        final_output = {
            "status": "fail",
            "errors": [gate["reason"]],
            "goal": request.strip(),
            "steps": ["Request blocked due to unsafe instruction pattern."],
            "checks": [],
            "risks": [],
            "brief": None,
            "mode": "normal",
            "clarification_needed": None,
            "clarification_response": None,
        }

        log_entry = create_log_entry(
            trace_id=run_trace_id,
            input_text=request,
            task_type="unknown",
            generated_steps=[],
            checker_result={"status": "fail", "errors": [gate["reason"]]},
            fixer_actions=[],
            final_output=final_output,
        )

        log_entry["llm_used"] = False
        log_entry["llm_raw_steps"] = None
        log_entry["initial_checker_result"] = None
        log_entry["input_gate"] = gate
        log_entry["pipeline_stop"] = "blocked_input_hard_stop"

        log_event(
            filename="engine.log",
            source="runner",
            layer="execution",
            event="execution_blocked",
            status="blocked",
            trace_id=run_trace_id,
            details={
                "reason": gate["reason"],
                "decision_path": _decision_path("input_gate", "blocked_input_hard_stop"),
                "transition": "blocked_input_hard_stop",
                "pipeline_stop": "blocked_input_hard_stop",
            }
        )

        log_run(log_entry)
        return format_output(final_output)

    if gate["status"] == "reject":
        final_output = {
            "status": "fail",
            "errors": [gate["reason"]],
            "goal": request.strip(),
            "steps": [],
            "checks": [],
            "risks": [],
            "brief": None,
            "mode": "normal",
            "clarification_needed": None,
            "clarification_response": None,
        }

        log_entry = create_log_entry(
            trace_id=run_trace_id,
            input_text=request,
            task_type="unknown",
            generated_steps=[],
            checker_result={"status": "fail", "errors": [gate["reason"]]},
            fixer_actions=[],
            final_output=final_output,
        )

        log_entry["llm_used"] = False
        log_entry["llm_raw_steps"] = None
        log_entry["initial_checker_result"] = None
        log_entry["input_gate"] = gate
        log_entry["pipeline_stop"] = "rejected_input_hard_stop"

        log_event(
            filename="engine.log",
            source="runner",
            layer="execution",
            event="execution_rejected",
            status="rejected",
            trace_id=run_trace_id,
            details={
                "reason": gate["reason"],
                "decision_path": _decision_path("input_gate", "rejected_input_hard_stop"),
                "transition": "rejected_input_hard_stop",
                "pipeline_stop": "rejected_input_hard_stop",
            }
        )

        log_run(log_entry)
        return format_output(final_output)

    if gate["status"] == "weak":
        final_output = {
            "status": "fail",
            "errors": [gate["reason"]],
            "goal": request.strip(),
            "steps": ["Please provide a little more detail about what you want to plan."],
            "checks": [],
            "risks": [],
            "brief": None,
            "mode": "normal",
            "clarification_needed": None,
            "clarification_response": None,
        }

        log_entry = create_log_entry(
            trace_id=run_trace_id,
            input_text=request,
            task_type="unknown",
            generated_steps=[],
            checker_result={"status": "fail", "errors": [gate["reason"]]},
            fixer_actions=[],
            final_output=final_output,
        )

        log_entry["llm_used"] = False
        log_entry["llm_raw_steps"] = None
        log_entry["initial_checker_result"] = None
        log_entry["input_gate"] = gate
        log_entry["pipeline_stop"] = "weak_input_hard_stop"

        log_event(
            filename="engine.log",
            source="runner",
            layer="execution",
            event="execution_weak",
            status="weak",
            trace_id=run_trace_id,
            details={
                "reason": gate["reason"],
                "decision_path": _decision_path("input_gate", "weak_input_hard_stop"),
                "transition": "weak_input_hard_stop",
                "pipeline_stop": "weak_input_hard_stop",
            }
        )

        log_run(log_entry)
        return format_output(final_output)

    plan = generate_plan(request)

    if plan.get("task_type") == "unsupported":
        final_output = {
            "status": plan.get("status", "fail"),
            "errors": plan.get("errors", []),
            "goal": plan.get("goal", request.strip()),
            "steps": plan.get("steps", []),
            "checks": plan.get("checks", []),
            "risks": plan.get("risks", []),
            "brief": None,
            "mode": plan.get("mode", "normal"),
            "clarification_needed": None,
            "clarification_response": None,
        }

        log_entry = create_log_entry(
            trace_id=plan.get("trace_id"),
            input_text=request,
            task_type=plan.get("task_type"),
            generated_steps=plan.get("steps", []),
            checker_result={"status": "fail", "errors": plan.get("errors", [])},
            fixer_actions=[],
            final_output=final_output,
        )

        log_entry["llm_used"] = False
        log_entry["llm_raw_steps"] = None
        log_entry["initial_checker_result"] = None
        log_entry["input_gate"] = gate
        log_entry["pipeline_stop"] = "unsupported_non_travel_hard_stop"

        log_event(
            filename="engine.log",
            source="runner",
            layer="execution",
            event="execution_blocked",
            status="unsupported",
            trace_id=plan.get("trace_id"),
            details={
                "reason": "Task type is not a travel request",
                "task_type": plan.get("task_type"),
                "decision_path": _decision_path("input_gate", "generate_plan", "unsupported_non_travel_hard_stop"),
                "transition": "unsupported_non_travel_hard_stop",
                "pipeline_stop": "unsupported_non_travel_hard_stop",
            }
        )

        log_run(log_entry)
        return format_output(final_output)

    result = check_plan(plan)
    initial_checker_result = result.copy()

    if result["status"] == "fail":
        plan, fixer_actions = fix_plan(plan, result["errors"])
        result = check_plan(plan)

    plan = apply_task_personality(plan)
    plan = apply_task_checks(plan)

    # Critical repair pass after personality/check layers
    result = check_plan(plan)
    if result["status"] == "fail":
        repaired_plan, late_fixer_actions = fix_plan(plan, result["errors"])
        fixer_actions.extend(late_fixer_actions)

        recheck = check_plan(repaired_plan)
        if recheck["status"] == "pass":
            plan = repaired_plan
            result = recheck
        else:
            plan = repaired_plan
            result = recheck

    if result["status"] == "pass":
        plan = refine_plan(
            plan,
            brief=plan.get("brief"),
            planning_constraints=plan.get("planning_constraints"),
        )

    execution_readiness = None
    if result["status"] == "pass" and plan.get("task_type") == "trip":
        execution_readiness = evaluate_execution_readiness(
            ExecutionReadinessRequest(
                brief=plan.get("brief") or {},
                planning_constraints=plan.get("planning_constraints"),
                plan_status=result["status"],
            )
        ).model_dump()

    decision_path = ["input_gate", "generate_plan", "check_plan"]
    if initial_checker_result and initial_checker_result["status"] == "fail":
        decision_path.extend(["fix_plan", "check_plan"])
    decision_path.extend(["apply_task_layers", "check_plan"])
    if len(fixer_actions) > 0 and decision_path[-2:] != ["fix_plan", "check_plan"]:
        decision_path.extend(["fix_plan", "check_plan"])

    final_output = {
        "status": result["status"],
        "errors": result["errors"],
        "goal": plan.get("goal", ""),
        "steps": plan.get("steps", []),
        "checks": plan.get("checks", []),
        "risks": plan.get("risks", []),
        "brief": plan.get("brief"),
        "mode": plan.get("mode", "normal"),
        "clarification_needed": None,
        "clarification_response": None,
        "execution_readiness": execution_readiness,
    }

    log_entry = create_log_entry(
        trace_id=plan.get("trace_id"),
        input_text=request,
        task_type=plan.get("task_type"),
        generated_steps=plan.get("steps", []),
        checker_result=result,
        fixer_actions=fixer_actions,
        final_output=final_output,
    )

    log_entry["llm_used"] = llm_used
    log_entry["llm_raw_steps"] = llm_raw_steps
    log_entry["initial_checker_result"] = initial_checker_result
    log_entry["input_gate"] = gate
    log_entry["pipeline_stop"] = None

    log_event(
        filename="engine.log",
        source="runner",
        layer="execution",
        event="execution_completed",
        status="success",
        trace_id=plan.get("trace_id"),
        details={
            "task_type": plan.get("task_type"),
            "flow_shape": execution_context.get("flow_shape", "direct_ready_completion"),
            "used_repair": bool(fixer_actions),
            "decision_path": _decision_path(*decision_path),
            "final_status": result["status"],
            "transition": "execution_completed",
        }
    )

    log_run(log_entry)

    return format_output(final_output)
