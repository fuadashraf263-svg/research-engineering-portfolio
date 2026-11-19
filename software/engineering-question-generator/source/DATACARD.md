# Engineering Questions — Training Dataset

**100,000 unique, machine-verified engineering questions** with computed answers, worked solution steps, and metadata. Built for training/fine-tuning.

## Files

- `engineering_questions.jsonl` — one JSON object per line (primary training format)
- `engineering_questions.csv` — same data, flat table (solution steps joined with ` | `)
- `engineering_question_generator.zip` — the full parametric generator + verification suite, so you can reproduce, extend, or rebalance the set

## Record schema (JSONL)

```json
{
  "id": "EQ-000001",
  "branch": "Engineering Mathematics",
  "topic": "Calculus",
  "difficulty": "easy",
  "question": "Find the derivative of f(x) = -2x^3 + 5x^2 - 4x + 2 evaluated at x = -4.",
  "answer": "-140",
  "answer_value": -140.0,
  "unit": null,
  "solution_steps": [
    "f(x) = -2x^3 + 5x^2 - 4x + 2",
    "f'(x) = -6x^2 + 10x - 4",
    "f'(-4) = 3(-2)(-4)^2 + 2(5)(-4) + (-4)",
    "Answer: f'(-4) = -140"
  ],
  "solution": "f(x) = -2x^3 + 5x^2 - 4x + 2\nf'(x) = -6x^2 + 10x - 4\nf'(-4) = 3(-2)(-4)^2 + 2(5)(-4) + (-4)\nAnswer: f'(-4) = -140",
  "formula": "f'(x) = 3a x^2 + 2b x + c",
  "tags": [
    "derivative",
    "polynomial"
  ],
  "template_id": "ENG-0000",
  "parameters": {
    "a": -2,
    "b": 5,
    "c": -4,
    "d": 2,
    "x0": -4
  }
}
...
```

| Field | Meaning |
|---|---|
| `id` | Unique record id |
| `branch` | Engineering field |
| `topic` | Sub-topic |
| `difficulty` | easy / medium / hard |
| `question` | Problem statement |
| `answer` | Final answer with unit |
| `answer_value` | Numeric answer (null for non-numeric, e.g. binary strings) |
| `unit` | Answer unit |
| `solution_steps` | Ordered list of worked steps |
| `solution` | Steps as one string |
| `formula` | Governing formula |
| `tags` | Topic tags |
| `template_id` | Source template |
| `parameters` | Exact inputs — lets you recompute/verify any record |

## How it was built (why it is correct)

Every question comes from a **parametric template whose answer is computed in Python** — answers are correct by construction, not hand-typed. Correctness is enforced by three independent layers:

1. **Anchor tests** — 33 hand-computed known values pin representative formulas across every field.
2. **Numeric cross-checks** — derivatives re-checked by finite differences, integrals by numeric quadrature, roots by back-substitution, linear algebra by NumPy, etc.
3. **End-to-end re-derivation** — every one of the 100,000 shipped records is independently recomputed from its stored `parameters` and must match its stored answer.

Result on this build: **100,000 / 100,000 records re-derived correctly, 0 duplicates**, and all independent numeric cross-checks passed.

## Contents

- Records: **100,000** (all questions unique)
- Fields: **10** | Topics: **60** | Templates: **166**

**By field:**

| Field | Questions | Topics |
|---|---:|---:|
| Mechanical Engineering | 22,344 | 7 |
| Engineering Mathematics | 20,611 | 12 |
| Electrical Engineering | 17,130 | 7 |
| Civil Engineering | 14,818 | 8 |
| Chemical Engineering | 8,398 | 6 |
| Computer Science & Engineering | 6,398 | 7 |
| Industrial Engineering | 4,529 | 4 |
| Materials Engineering | 2,229 | 3 |
| Instrumentation & Measurement | 1,774 | 3 |
| Aerospace Engineering | 1,769 | 3 |

**By difficulty:** medium 49,940, easy 38,365, hard 11,695

## Usage notes

- For instruction tuning, map `question` -> prompt and `solution` (or `answer`) -> target.
- `difficulty` and `branch` support curriculum or stratified sampling.
- Field balance reflects template capacity; to rebalance or grow beyond 100k, edit/add templates in the generator (`tmpl_*.py`) and rerun `generate.py`. Re-run `verify_dataset.py` to re-validate.
- Content is synthetic and computational (numeric problem-solving). It complements, but does not replace, conceptual/theory Q&A.
