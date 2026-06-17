# Goal Drift in Multi-Step AI Agent Tasks

## Overview

This is an independent AI safety research project measuring goal drift failure modes in multi-step AI agent tasks. As AI agents are deployed across longer-horizon tasks with increasing autonomy, a critical and underexamined risk emerges: the agent's operative goal diverges from the user's original intent without explicit failure or error signal. This study systematically induces, observes, and categorizes goal drift events across controlled multi-step task sequences, producing a labeled dataset of drift episodes and quantitative metrics that characterize when, how, and why agents lose alignment with their assigned objectives.

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
- **AnyForge SDK** — Drives automated trial execution, managing agent instantiation, step sequencing, and structured output collection across large trial batches without manual intervention.
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

## About

**Researcher:** Olivia Leavitt
**Collaboration:** Edwin Poot, Founder of Anyforge.ai
**Repository:** github.com/livleavitt/goal-drift-study

This research targets AI safety with a focus on agent observability, specifically the question of how to detect and characterize misalignment in deployed agents using only the behavioral traces they leave behind. The goal is to produce findings and tooling that are practically useful for teams building long-horizon AI systems who need rigorous methods for auditing agent fidelity to user intent.
