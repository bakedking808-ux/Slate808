# Slate808

Slate808 is a deterministic travel-planning engine designed to enforce structured reasoning, eliminate ambiguity, and prevent unsafe execution.

It is not a chatbot.

It is a controlled system that separates parsing, validation, clarification, and execution into strict, testable layers.

---

## 🧭 Core Purpose

Slate808 exists to:

- force clarity before action
- expose weak or missing information
- prevent unsafe or premature execution
- produce structured, predictable outcomes

---

## ⚙️ How It Works

Slate808 follows a deterministic pipeline:

input → normalize → extract → validate → clarify →  
admission → (state-shape | execute) → result

Each stage has a single responsibility.

---

## 🧠 System Principles

- Deterministic over generative  
- Structure over speed  
- Fail loudly over silent errors  
- One step at a time  
- No hidden state  
- No unsafe execution  

---

## 🧩 Architecture Overview

### 1. Input & Normalization
- cleans and standardizes user input

### 2. Extraction
- identifies destination, timing, traveller count

### 3. Validation
- enforces cross-field consistency
- blocks invalid states

### 4. Clarification
- tracks missing fields
- asks one precise question at a time
- preserves state across turns

### 5. Runtime Admission
- determines if an action is allowed
- separates:
  - state-shaping (pre-readiness)
  - execution-triggering (post-readiness)

### 6. State Shaping
- updates clarification state safely
- example: `supply_field`

### 7. Execution (Guarded)
- runs only when readiness is satisfied
- first supported path: `complete_flow`

### 8. Result Reporting
All runtime outcomes are structured:

- status  
- transition (`blocked`, `failed`, `succeeded`, `rejected_by_action_guard`)  
- admission  
- state  
- result  
- error  

---

## 🧪 Testing Strategy

Slate808 is fully test-driven.

### Test cadence:

- Each change → targeted test  
- After fix → full suite  
- Every few days → full suite + log review  
- Weekly → bug review + regression expansion  

### Run tests:

```bash
venv/bin/pytest -q tests/
