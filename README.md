# Goal Drift in Multi-Step AI Agent Tasks

## Overview

This is an independent AI safety research project measuring goal drift failure modes in multi-step AI agent tasks. As AI agents are deployed across longer-horizon tasks with increasing autonomy, a critical and underexamined risk emerges: the agent's operative goal diverges from the user's original intent without explicit failure or error signal. This study systematically induces, observes, and categorizes goal drift events across controlled multi-step task sequences, producing a labeled dataset of drift episodes and quantitative metrics that characterize when, how, and why agents lose alignment with their assigned objectives.

---

## Key Findings

62 trials completed across 3 domains. See [`writeup/findings.md`](writeup/findings.md) for the full analysis.

| Metric | Result |
|---|---|
| Total trials | 62 |
| Overall drift rate | 12.9% (8 of 62) |
| Drift types detected | goal_substitution only |
| goal_forgetting rate | 0.0% |
| goal_narrowing rate | 0.0% |
| Average drift onset | step 1.6 after perturbation injection |
| Most dangerous perturbation | new_salient_information (26.7% drift rate) |
| Most vulnerable domain | research_synthesis (30.0% drift rate) |
| Most stable domains | financial_allocation and task_queue_management (4.8% each) |

---

## Research Questions

1. **At what task depth does goal drift first manifest?** Across multi-step sequences of varying length, what is the median step at which an agent's behavior measurably diverges from the original objective?
2. **Which drift type is most prevalent across task categories?** Do goal substitution, goal forgetting, and goal narrowing occur at different rates depending on task domain, prompt structure, or context window pressure?
3. **Can drift be detected from audit traces alone?** Is it possible to build a classifier that reliably identifies drift episodes from immutable control-layer logs without access to ground-truth human evaluation?

---

## Drift Taxonomy

| Type | Definition |
|---|---|
| **Goal Substitution** | The agent replaces the original objective with a related but distinct goal it finds more tractable or salient. |
| **Goal Forgetting** | The agent loses track of the original objective entirely as task context accumulates, defaulting to locally coherent but globally misaligned actions. |
| **Goal Narrowing** | The agent retains the original goal but progressively strips away scope, constraints, or success criteria until only a degenerate subgoal remains. |

---

## Architecture

This study uses a **Flight Recorder** setup designed to capture complete, tamper-evident records of agent behavior at every step of a trial.

- **Claude Code** — Used for experiment scripting, prompt construction, and post-hoc analysis of trial outputs. Provides the primary interface for designing task sequences and evaluating drift candidates.
- **Anthropic API** — Trials are executed via direct Anthropic API calls using the `anthropic` Python package (v0.115.0). The `sdk_runner.py` script constructs multi-turn conversations for each trial, injects perturbations at defined steps, and saves the full trace to `audit_logs/raw_control_traces/`.
- **AnyForge Control Layer** — Installed as an MCP server connected to Claude Code via `claude mcp add anyforge`. It captures immutable audit trails of every agent reasoning step and writes them append-only to `audit_logs/raw_control_traces/`. The Control Layer owns the log independently — the agent under study has no write access to its own trace.

---

## Repository Structure

```
goal-drift-study/
├── experiments/                    # Trial definitions and prompt scaffolds
├── data/
│   ├── raw/                        # Unprocessed trial outputs
│   └── processed/                  # Cleaned and labeled datasets
├── audit_logs/
│   └── raw_control_traces/         # Immutable Flight Recorder logs
├── infrastructure/                 # AnyForge SDK configs and runner scripts
├── analysis/
│   └── notebooks/                  # Jupyter notebooks for drift analysis
├── results/
│   └── figures/                    # Plots and visualizations
├── writeup/                        # Draft papers and research notes
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Running the Experiments

Follow these steps in order from the repository root to execute a full trial batch and produce the drift-frequency summary.

**1. Set your Anthropic API key:**

```bash
export ANTHROPIC_API_KEY=your_key_here
```

**2. Run trials for each domain:**

```bash
python infrastructure/sdk_runner.py --mode financial_allocation
python infrastructure/sdk_runner.py --mode research_synthesis
python infrastructure/sdk_runner.py --domain task_queue_management
```

Each command executes 20 trials for the specified domain and writes audit traces to `audit_logs/raw_control_traces/`.

**3. Classify all audit traces and write the results CSV:**

```bash
python analysis/batch_classify.py
```

Output is written to `data/processed/research_synthesis_results.csv`.

**4. Compute summary statistics and write the drift summary:**

```bash
python analysis/statistics.py
```

Output is printed to stdout and written to `results/drift_summary.txt`.

**5. Inspect a single trace interactively (ad-hoc):**

```bash
python analysis/drift_classifier.py <trace_path> --pretty
```

Replace `<trace_path>` with the path to any `.json` audit trace, e.g.:

```bash
python analysis/drift_classifier.py audit_logs/raw_control_traces/sample_trace.json --pretty
```

---

## About

**Researcher:** Olivia Leavitt
**Collaboration:** Edwin Poot, Founder of Anyforge.ai
**Repository:** github.com/livleavitt/goal-drift-study

This research targets AI safety with a focus on agent observability, specifically the question of how to detect and characterize misalignment in deployed agents using only the behavioral traces they leave behind. The goal is to produce findings and tooling that are practically useful for teams building long-horizon AI systems who need rigorous methods for auditing agent fidelity to user intent.
