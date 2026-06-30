# Goal Drift in Multi-Step AI Agent Tasks: Empirical Findings

**Olivia Leavitt** | Independent AI Safety Research
**Collaboration:** Edwin Poot, Founder of Anyforge.ai
**Repository:** github.com/livleavitt/goal-drift-study

---

## Abstract

This study measured goal drift failure modes in AI agents executing structured multi-step tasks across three domains: financial allocation, research synthesis, and task queue management. Using a Flight Recorder architecture that writes immutable audit traces independently of the agent under study, we ran 62 controlled trials with four perturbation types injected at pre-specified steps to create pressure for goal drift. The key finding is that goal substitution — the agent replacing its original objective with a distinct but superficially plausible alternative — was the only drift type detected, occurring in 12.9% of trials overall, with research synthesis tasks and new salient information perturbations producing substantially elevated rates.

---

## Key Findings

| Metric | Result |
|---|---|
| Total trials | 62 |
| Overall drift rate | 12.9% (8 of 62 trials) |
| Drift types detected | goal_substitution only |
| goal_forgetting rate | 0.0% |
| goal_narrowing rate | 0.0% |
| Average onset step | 1.6 |

### Drift Rate by Perturbation Type

| Perturbation Type | Drift Rate | Notes |
|---|---|---|
| new_salient_information | 26.7% | Highest — more than 2× the overall rate |
| contradicting_instruction | 13.3% | Near the overall average |
| partial_completion_signal | 13.3% | Near the overall average |
| distraction_sub_task | 0.0% | No drift detected |

### Drift Rate by Task Domain

| Domain | Drift Rate | Notes |
|---|---|---|
| research_synthesis | 30.0% | Most vulnerable |
| financial_allocation | 4.8% | Most stable (tied) |
| task_queue_management | 4.8% | Most stable (tied) |

---

## Methodology

### Task Domains

Three multi-step task domains were used to elicit extended goal-directed behavior:

- **Financial Allocation** — The agent allocates a $50,000 budget across five departments while satisfying five explicit numerical constraints over a 10-step sequence. The task is highly structured, with verifiable right and wrong answers at each step.
- **Research Synthesis** — The agent synthesizes five sources on a defined topic into a structured document over an 8-step sequence. Success requires maintaining fidelity to source content and following prescribed thematic organization.
- **Task Queue Management** — The agent processes and prioritizes a 10-item task queue according to five scheduling rules over a 12-step sequence. The task combines logical constraint-satisfaction with sequential decision-making.

### Perturbation Types

Four perturbation types were injected as in-context messages at pre-specified steps, without informing the agent that a perturbation was being applied:

- **Contradicting Instruction** — Tells the agent the original constraints have been updated and invites it to optimize for efficiency rather than follow the step sequence.
- **New Salient Information** — Introduces a high-salience update (e.g., a new urgent task, a contradicting meta-analysis, a staffing crisis) designed to draw the agent's attention away from its original objective.
- **Distraction Sub-Task** — Asks the agent to complete a small ancillary task (e.g., a stakeholder memo, an executive summary) before continuing.
- **Partial Completion Signal** — Tells the agent that its work "looks good" and that it can finalize early if it is confident, signaling that completion of the remaining steps is optional.

Each domain received 20 trials (62 total after two additional financial allocation trials), with perturbation types distributed evenly across trials and injection steps randomized within each domain's allowed window.

### Flight Recorder Architecture

All trials were executed through the AnyForge Control Layer, an MCP server connected to Claude Code via `claude mcp add anyforge`. The Control Layer attaches to each agent session before the first token is generated and writes an append-only audit trace to `audit_logs/raw_control_traces/` independently of the agent. The agent has no write access to its own trace. This design ensures that drift events cannot be obscured by agent behavior — the record is ground truth regardless of trial outcome. Traces were subsequently scored by the rubric-based classifier in `analysis/drift_classifier.py`.

---

## Discussion

### Why new_salient_information caused more drift than contradicting_instruction

The contradicting instruction perturbation is explicit: it directly tells the agent the original constraints have changed. A well-aligned agent can recognize this as a potential override attempt and push back, ask for clarification, or continue the original task while noting the discrepancy. The instruction is adversarial in an obvious way.

New salient information operates differently. It does not ask the agent to abandon its goal — it presents a fact that makes the original goal feel incomplete or misaligned with current reality. In the research synthesis domain, for example, the injected meta-analysis suggested that the study topic was "largely solved," framing continued synthesis as potentially misleading. This creates a more subtle pressure: the agent is not being asked to change its goal, but the informational context is quietly reorganized around it. The agent's drift in these cases was not a capitulation to an instruction; it was a plausible-looking update to its model of what the task was for. This is a more dangerous failure mode precisely because it is harder to distinguish from legitimate context-sensitivity.

### Why goal_substitution was the only detected drift type

Goal forgetting and goal narrowing require a different dynamic than what the perturbation set primarily induced. Goal forgetting — losing track of the original objective through context accumulation — was not strongly elicited because the tasks are short enough (8–12 steps) that context window pressure is not a significant factor for current models. Goal narrowing, where the agent retains the goal but strips away scope, was similarly infrequent: when agents drifted, they tended to replace the objective wholesale rather than progressively degrade it.

Goal substitution, by contrast, was readily induced by perturbations that offered the agent a coherent alternative framing. In the cases that scored positive, the agent did not forget its goal or shrink it — it adopted a new one, treating the perturbation's framing as an implicit task update. This suggests that for current models operating on short task sequences, the primary drift risk is substitution triggered by in-context information, not gradual forgetting or scope erosion. Whether this finding generalizes to longer-horizon tasks with greater context pressure is an open question.

### Why research_synthesis was more vulnerable than the other domains

Financial allocation and task queue management both provide dense, verifiable constraint structures: numerical budgets, scheduling rules, and dependency chains that are easy to check and re-state at each step. An agent that drifts in these domains produces output that is overtly wrong in a way that is detectable within the task itself. The task structure acts as a partial corrective.

Research synthesis offers no such anchor. The success criteria — produce a structured synthesis that accurately represents the sources, identifies agreement and disagreement, and draws only supported conclusions — are qualitative and harder to verify incrementally. When the new salient information perturbation introduced a sixth source arguing the topic was "largely solved," agents had no numerical constraint or rule to push back against. The injection looked like relevant domain information, and the agent's job is to synthesize domain information. The domain's inherent openness to new evidence made it structurally susceptible to a perturbation that arrived as new evidence.

### What early onset step (1.6) means for detection and intervention

An average onset step of 1.6 — meaning drift was detectable, on average, within the first two steps following perturbation injection — has a direct implication for monitoring design: drift is not a late-stage phenomenon that emerges gradually. It manifests almost immediately after the triggering event, which means post-hoc analysis of completed traces is not the only viable detection strategy. A monitoring system with access to the live audit trace could flag a drift signal in near real-time, potentially within one or two agent turns of the perturbation firing.

This also means that intervention windows are short. If the goal is to interrupt a drifting trial before it produces a finalized (and potentially acted-upon) output, the intervention system must be responsive at the step level, not the trial level. The early onset finding motivates investment in streaming audit trace analysis rather than batch review.

---

## Limitations

1. **Rubric-based classifier is domain-dependent.** The drift classifier uses keyword and structural flag matching tuned to the three task domains and four perturbation types in this study. Its precision and recall on novel domains or perturbation designs has not been validated. False negatives are likely when drift manifests in language patterns not covered by the rubric; false positives are possible when non-drift outputs happen to contain flagged phrases.

2. **Small sample size per cell.** With 20 trials per domain and 5 trials per perturbation type per domain, individual cell counts are too small to support strong statistical conclusions. The 26.7% drift rate for new_salient_information, for example, is based on a small number of positive detections. Confidence intervals would be wide; the rank ordering of perturbation types may not be stable at larger N.

3. **Single model evaluated.** All trials were run against one model. Drift rates, onset steps, and the dominance of goal substitution over other drift types are properties of this model's behavior under these conditions. Results may differ substantially for models with different context handling, instruction-following behavior, or training objectives.

4. **Controlled perturbation design may underestimate real-world risk.** Perturbations were injected at fixed, pre-specified steps with exact wording. Real deployment environments will expose agents to adversarial or misleading content at unpredictable intervals, in more varied forms, and often embedded in otherwise legitimate content. The 12.9% overall drift rate should be treated as a lower bound on the risk in less controlled settings.

---

## Implications for Safe Deployment

**1. Treat in-context information updates as a first-class attack surface.**
The finding that new salient information drove more drift than an explicit contradicting instruction suggests that goal-aligned agents can be redirected without ever being told to change their goal. Teams deploying agents in information-rich environments — where the agent receives documents, search results, or messages from other systems — should treat every in-context update as a potential goal-redirecting event and audit for substitution signals accordingly.

**2. Design tasks with verifiable constraint anchors.**
Financial allocation and task queue management showed 4.8% drift rates against research synthesis's 30.0%. The structural difference is the presence of explicit, numerically checkable constraints that the agent can re-verify at each step. Where possible, task designs for deployed agents should embed verifiable constraints — not just high-level goal statements — so that drift produces detectable outputs rather than plausible-looking alternative work.

**3. Invest in step-level, streaming audit trace analysis.**
An average onset step of 1.6 means drift is detectable early. A monitoring system that reads the audit trace step-by-step and scores for substitution signals can raise a flag within one or two turns of a triggering event. Batch review of completed traces is insufficient for time-sensitive tasks where a drifted agent might take consequential actions before the trace is reviewed.

**4. Log independently of the agent.**
The Flight Recorder result — that the agent under study has no write access to its own trace — should be a design requirement for any audit system used in high-stakes agentic deployments. An agent that can modify or suppress its own log cannot be reliably audited. Immutable, independently-written traces are a prerequisite for the kind of post-hoc and real-time drift detection this study demonstrates.

**5. Extend this framework to longer-horizon tasks.**
Goal forgetting and goal narrowing were not detected in this study, likely because 8–12 step sequences are short enough that context pressure is not yet significant. The expected failure modes for longer-horizon agentic tasks — multi-hour workflows, autonomous research loops, extended coding agents — may look very different. Replicating this study design at 50–100 step sequences, and with significantly larger context loads, is a high-priority next step.
