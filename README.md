# Slate808

Slate808 is a deterministic travel-planning engine for turning messy travel requests into structured, testable, operator-ready planning output.

It is not a chatbot.

Slate808 separates travel parsing, validation, clarification, planning policy, readiness checks, operator workflow, and guarded execution into strict layers. The goal is to make travel planning clearer, safer, and easier to operate without allowing premature or unsafe execution.

---

## Core Purpose

Slate808 exists to:

- extract structured travel details from natural language
- expose missing or weak information
- ask precise clarification questions
- produce deterministic travel plans
- generate operator-facing checks and risks
- separate planning from execution
- block unsafe or premature execution-like actions
- keep every major state transition testable

Guiding rule:

> Do not let poetry outrun structure.

---

## What Slate808 Is

Slate808 is:

- a deterministic travel-planning engine
- an internal operator support tool
- a structured reasoning pipeline
- a readiness and workflow gatekeeper
- a test-protected backend for travel operations

Slate808 is not:

- a general chatbot
- a live booking engine
- a customer-facing marketplace
- a supplier availability system
- a live calendar mutation system
- a tool that invents hotels, prices, suppliers, routes, or availability

---

## Current Pipeline

Slate808 follows this high-level pipeline:

```text
input
→ normalization
→ travel intent gate
→ travel brief extraction
→ clarification
→ planning policy
→ constraint policy
→ plan generation
→ plan refinement
→ checks and risks
→ draft itinerary rendering
→ execution readiness
→ operator workflow
→ runtime admission
→ guarded execution path
→ formatted output
→ operator console
```

Each layer has a defined responsibility. A layer should not silently take over another layer’s job.

---

## Main Components

### Input and Normalization

Normalizes user input before extraction and planning.

Responsibilities:

- clean request text
- preserve travel intent
- reduce ambiguity before deeper processing

---

### Travel Intent Gate

Blocks unsupported non-travel requests.

Slate808 is travel-focused. Non-travel requests should not silently enter the planning pipeline.

---

### Travel Brief Extraction

Builds the structured travel brief.

Current extracted fields include:

- destination
- traveller count
- timing
- budget amount
- budget level
- structured budget fields
- trip mood
- child-traveller signal

Structured budget support includes:

- KES / KSH / sh
- USD / EUR / GBP
- `$`, `€`, and `£`
- compact `k` shorthand
- per-person budgets
- per-adult budgets
- per-child / per-kid budgets
- known but unranked budgets using `budget_level="specified"`

Foreign currency is recognized but not converted. Slate808 does not pretend that a USD, EUR, or GBP amount is a KES amount.

---

### Timing Extraction

Slate808 supports several timing states:

- exact timing
- date ranges
- relative timing
- month-only timing
- duration-only timing
- vague or ambiguous timing
- missing timing

Examples of supported exact timing:

```text
10 April to 12 April
4th May to 8th May
7th August through the 15th Aug
August 7 through 15
```

A single date can support planning, but execution readiness may still require a full date range.

---

### Clarification

Clarification handles missing or unclear information.

Responsibilities:

- ask one precise question at a time
- preserve collected fields
- avoid repeating questions for known fields
- accept follow-up answers
- update clarification state safely

Clarification is state-shaping, not execution.

---

### Planning Policy

Planning policy derives operational meaning from the travel brief.

It handles:

- destination policy
- timing policy
- budget policy
- traveller policy
- mood policy
- constraint policy
- conflict flags
- resolved constraints
- refinement flags

Structured budgets with `budget_level="specified"` are treated as known but unranked. They do not automatically trigger low-budget, value-focused, or premium assumptions.

---

### Constraint Policy

Slate808 applies deterministic planning constraints such as:

- family safety
- child suitability
- group coordination
- slow pace
- quiet preference
- low mobility
- value focus
- premium avoidance
- destination-specific movement needs

Constraint wording is composed compactly. Plan steps should preserve important meaning without stacking repeated suffixes.

---

### Plan Generation and Refinement

Slate808 generates structured plan steps from the extracted brief and policy layers.

Plan steps should be:

- deterministic
- readable
- compact
- destination-aware
- constraint-aware
- free from fake supplier or venue claims

The generator and refiner compose transport, activity, and timing steps using compact role-aware clauses.

---

### Checks and Risks

Slate808 produces operator-facing checks and risks.

Checks answer:

```text
What must the operator verify?
```

Risks answer:

```text
What could go wrong if this is not verified?
```

Risk labels are kept distinct to avoid duplicate label confusion.

Examples:

```text
Budget Coordination Risk
Budget Gap Risk
Budget Stretch
Supplier Reliability Risk
Activity Constraint Risk
Guest Comfort Risk
Access Rule Risk
```

---

### Draft Itinerary

Slate808 can render a draft itinerary when the brief has enough structure.

The Draft Itinerary is a planning aid, not a confirmed operational schedule.

It must not name unverified venues, suppliers, prices, or availability.

---

### Execution Readiness

Execution readiness decides whether a plan is safe to move beyond planning.

Readiness levels include:

```text
not_plan_ready
plan_ready_only
execution_ready
```

Important rule:

```text
execution_ready does not mean execution is authorized
```

Execution-like actions still require workflow and approval gates.

---

### Operator Workflow

Operator workflow maps readiness into operational state.

It handles:

- allowed operator actions
- blocked operator actions
- human approval requirements
- execution prep eligibility
- recovery actions
- recovery guidance
- handoff packet creation
- audit tags

This layer protects the boundary between planning and execution.

---

### Runtime Admission

Runtime admission separates safe state-shaping from execution-triggering actions.

State-shaping actions can happen before execution readiness when safe.

Execution-triggering actions fail closed unless the full authorization gate is satisfied.

Execution-triggering admission requires:

- compatible readiness
- explicit requested action
- `action_allowed is True`
- compatible workflow state
- empty blockers
- requested action not blocked
- valid approval state when approval is required

`complete_flow` cannot execute from coarse readiness alone.

---

### Guarded Execution

Execution is guarded and limited.

Slate808 does not currently perform real bookings, payments, supplier actions, or live calendar mutation.

Execution results are structured and include:

- status
- transition
- admission
- state
- result
- error

---

## Operator Console

Slate808 includes a local operator console for internal review.

The console is not a full product UI. It is a thin control surface for testing and operating the engine.

It shows:

- request input
- formatted Slate output
- travel brief
- plan steps
- checks
- risks
- draft itinerary
- execution readiness
- operator workflow
- handoff summary
- system state
- clarification session state
- latest run state

The console separates:

```text
Clarification Session State
≠
Latest Run State
```

This prevents stale clarification/session state from being confused with the latest readiness and workflow output.

---

## Logging and Auditability

Slate808 uses local structured logs for traceability.

Current logging concerns include:

- engine events
- clarification events
- execution events
- decision logs
- trace IDs
- trace origins
- session-aware logging
- category-specific logs

Planning decision logs include `trace_origin` so entries with `trace_id=None` are not ambiguous.

Supported trace origins:

```text
manual_run
operator_console
test_run
direct_policy_call
unknown
```

The goal is structured honesty, not heavy enterprise observability.

---

## Destination Catalogue

Slate808 uses a deterministic destination profile catalogue.

The catalogue supports:

- domestic Kenya destination recognition
- aliases and spelling variants
- destination profile metadata
- travel scope classification
- destination-aware checks, risks, and itinerary notes

The catalogue should remain one source of truth.

Future catalogue governance should define:

- required profile fields
- allowed destination types
- allowed profile categories
- alias rules
- duplicate prevention
- tests required for new destinations
- what must never be added without verification

---

## Security and Safety Principles

Slate808 follows these safety principles:

- no unsafe execution
- no external mutation without explicit gates
- no booking prep without readiness and approval gates
- no calendar scheduling without authorization
- no fake suppliers
- no fake prices
- no fake availability
- no unsupported destination claims
- no silent conversion of foreign currency
- no hidden execution from state-shaping paths
- fail closed when authorization fields are missing

Security hardening priorities include:

1. input safety
2. operator action authorization
3. log safety and auditability
4. output truthfulness
5. catalogue governance
6. contract boundary validation

---

## Testing Strategy

Slate808 is test-driven.

Testing discipline:

- run targeted tests after focused changes
- run the full suite after stable fixes
- review logs regularly
- add regression tests for every bug class
- merge only after green tests
- tag meaningful stable checkpoints

Run the full suite:

```bash
venv/bin/pytest -q tests/
```

Examples of targeted test runs:

```bash
venv/bin/pytest -q tests/test_engine.py
venv/bin/pytest -q tests/test_execution_readiness_contract.py
venv/bin/pytest -q tests/test_operator_workflow_contract.py
venv/bin/pytest -q tests/test_operator_runtime_admission_contract.py
venv/bin/pytest -q tests/test_operator_runtime_execution_contract.py
venv/bin/pytest -q tests/test_operator_console_backend.py
```

Before any commit or merge, run the relevant targeted tests and then the full suite.

---

## Git Workflow

Use feature branches for focused changes.

Create a branch:

```bash
git checkout main
git pull origin Slate-main
git checkout -b harden/example-change
```

Commit after green tests:

```bash
git status
git add <changed files>
git commit -m "Clear focused commit message"
```

Merge only after validation:

```bash
git checkout main
git pull origin Slate-main
git merge <branch-name>
venv/bin/pytest -q tests/
git push origin main:Slate-main
```

Use annotated tags for meaningful stable checkpoints:

```bash
git tag -a slate-vX.Y.Z-description -m "Slate vX.Y.Z description"
git log --oneline --decorate -5
```

---

## Current Development Status

Slate808 currently supports:

- travel request parsing
- travel brief extraction
- clarification flow
- structured budget recognition
- date and date-range timing extraction
- destination profile recognition
- deterministic plan generation
- checks and risks
- draft itinerary rendering
- execution readiness evaluation
- operator workflow mapping
- runtime admission checks
- guarded execution seams
- operator console review
- decision and runtime logging

Slate808 does not yet support:

- real bookings
- real supplier availability
- live calendar mutation
- payment handling
- live currency conversion
- customer-facing account flows
- full SaaS-style UI

---

## Recent Hardening Areas

Recent work has strengthened:

- Kenya destination recognition
- destination profile formatting
- draft itinerary visual hierarchy
- `through` date-range timing extraction
- duplicate budget risk labels
- compact constraint suffix composition
- worldwide structured budget extraction
- `budget_level="specified"` compatibility
- trace origin logging
- operator console state-source separation
- runtime execution authorization

---

## Next Likely Work

Likely next work areas:

1. booking prep adapter consistency
2. requested action normalization
3. `calendar_review` / `review_calendar` naming alignment
4. destination catalogue governance
5. date-based log cleanup
6. extraction trace policy for lower-level decision hooks

---

## Project Position

Slate808 is currently a local deterministic planning engine with an internal operator console and strong regression coverage.

Its job is to make the plan clear, the gaps visible, and the execution boundary safe.

