# Slate808 Operator Console v1 Contract

## Purpose

The Operator Console v1 is an internal UI for testing, reviewing, and operating Slate808.

It is not a customer-facing product.
It is not a booking platform.
It is not a live execution dashboard.

Its purpose is to make Slate easier to inspect, trust, and evaluate during stable v1.

---

## Stable v1 UI Principle

The console must be useful before it is beautiful.

The goal is to expose Slate808's planning, clarification, readiness, workflow, approval, and handoff behavior clearly enough for operator review.

The UI must not hide engine state behind polish.

---

## Layout

The console has three sections:

1. Request Workspace
2. Plan Output
3. System State Panel

---

## 1. Request Workspace

Must support:

- entering a new travel request
- sending clarification replies
- sending correction-style updates
- resetting the current session
- submitting approval responses such as `Approved` or `Declined`

Should support:

- showing recent submitted inputs
- showing whether the next input is a new request or continuation
- clear reset warning before clearing session state

Must not support:

- customer login
- payment
- live booking
- live calendar writes
- vendor messaging

---

## 2. Plan Output

Must display:

- Status
- Goal
- Travel Brief
- Steps
- Checks
- Risks
- Execution Readiness
- Operator Workflow
- Handoff Summary

The UI may visually separate these sections, but it must not rewrite their meaning.

The UI should improve readability, not reinterpret the engine result.

---

## 3. System State Panel

Must display:

- current workflow state
- clarification state
- missing fields
- readiness level
- requested action
- action allowed / blocked
- approval state
- blockers
- recovery guidance
- handoff packet summary if present

This panel is diagnostic infrastructure, not decoration.

If Slate gets stuck, this panel should help explain why.

---

## Required Controls

The console may expose these controls:

- Submit request
- Continue clarification
- Reset session
- Approve
- Decline
- View handoff summary
- Run dry-run review

Controls must not bypass Slate808 readiness, approval, or execution-adapter rules.

---

## Explicitly Out of Scope for v1

The console must not perform:

- live calendar writes
- live booking actions
- payment handling
- vendor API calls
- customer notifications
- CRM writes
- account management
- multi-user roles
- customer-facing itinerary portals

These belong to later execution phases only after stable v1 proves operational value.

---

## Data Boundary

The console talks to Slate808 through a local application boundary.

The UI sends:

- raw user input
- session reset command
- approval command
- decline command

The UI receives:

- formatted engine output
- structured state summary if available
- readiness state
- workflow state
- blockers
- recovery guidance
- handoff packet summary

The console must not mutate external systems.

---

## Recommended Implementation Path

### Phase 1: Contract

Document the UI boundary and acceptance criteria.

### Phase 2: Local Backend Wrapper

Create a small local backend around:

```python
engine.clarification_runner.run()