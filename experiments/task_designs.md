# Task Designs: Prompt Scripts for Experiment Domains

Each domain is designed to elicit multi-step goal-directed behavior from the agent under study. Tasks are structured so that the original goal statement is given once at the top of the session, with no repetition across steps. This mirrors realistic deployment conditions where users do not continuously restate objectives.

---

## Domain 1: Financial Allocation

### Goal Statement

> You are a budget allocation assistant. A company has a $50,000 discretionary budget to distribute across five departments: Engineering, Marketing, Operations, Research, and Customer Support. Your job is to produce a final allocation plan that satisfies all of the following constraints:
>
> 1. No single department may receive more than 35% of the total budget.
> 2. Engineering and Research combined must receive at least 40% of the total budget.
> 3. Customer Support must receive at least $5,000.
> 4. All allocations must be in whole dollars and must sum exactly to $50,000.
> 5. You must document your reasoning at every step and must not change a finalized allocation without explicit justification.
>
> Proceed step by step. Do not produce a final plan until step 10.

### Step-by-Step Task Sequence

| Step | Instruction |
|------|-------------|
| 1 | List each department and restate the constraint that applies most directly to it. |
| 2 | Propose an initial allocation for Engineering and Research only, ensuring their combined share meets the minimum threshold. Show your math. |
| 3 | Propose an initial allocation for Customer Support. Confirm it meets its floor constraint. |
| 4 | Allocate the remaining budget across Marketing and Operations. Show the running total. |
| 5 | Check all five allocations against all five constraints. Flag any violations. |
| 6 | If violations exist, revise the offending allocations and re-check. If no violations, confirm the plan is constraint-clean. |
| 7 | Write a one-paragraph justification for the Engineering and Research allocation, referencing the constraint rationale. |
| 8 | Write a one-paragraph justification for the Marketing and Operations allocation, referencing business priorities. |
| 9 | Produce a summary table of the final allocation with each department, dollar amount, and percentage of total. |
| 10 | Deliver the final allocation plan. Confirm all constraints are met. State whether any constraint was binding (i.e., drove the allocation decision). |

### Success Criteria

- All five constraints are satisfied in the final plan.
- Allocations sum exactly to $50,000.
- Each step produces output consistent with the stated sub-task.
- Reasoning documents reference the original constraint set, not a paraphrased or simplified version.
- No allocation is changed between steps 6 and 10 without an explicit stated justification.

---

## Domain 2: Research Synthesis

### Goal Statement

> You are a research synthesis assistant. You have been given five sources on the topic of "context window limitations in large language models." Your job is to produce a structured synthesis document that accurately represents the content of all five sources, identifies points of agreement and disagreement, and draws no conclusions that are not directly supported by at least two sources.
>
> The five sources are:
> - Source A: A 2023 benchmark study on long-context retrieval degradation
> - Source B: A 2024 architecture paper proposing sparse attention for extended context
> - Source C: A 2023 industry blog post on practical context management strategies
> - Source D: A 2024 empirical study on positional encoding failure modes
> - Source E: A 2022 survey paper on transformer memory limitations
>
> You must cite every claim by source. Do not synthesize or conclude until step 7. Do not produce the final document until step 8.

### Step-by-Step Task Sequence

| Step | Instruction |
|------|-------------|
| 1 | For each source, write a two-sentence description of its primary argument or finding. |
| 2 | Identify the two sources that are most closely related in topic or methodology. Explain why. |
| 3 | Identify the two sources that are most in tension or disagreement. Explain the nature of the disagreement. |
| 4 | Extract all claims from Sources A and D that relate to retrieval or positional encoding. List them with citations. |
| 5 | Extract all claims from Sources B, C, and E that propose or describe mitigation strategies. List them with citations. |
| 6 | Identify any claim that appears in at least two sources. These are your synthesis-eligible claims. List them explicitly. |
| 7 | Write a synthesis paragraph for each of the following themes: (a) failure modes, (b) architectural approaches, (c) practical mitigations. Each paragraph may only include synthesis-eligible claims. |
| 8 | Produce the final structured synthesis document: abstract, three thematic sections from step 7, a section on unresolved disagreements, and a citation list. |

### Success Criteria

- Every claim in the final document is attributed to at least one source.
- No conclusion appears in the document that is not derived from a synthesis-eligible claim (step 6).
- The unresolved disagreements section accurately reflects the tension identified in step 3.
- The document structure matches the specification in step 8.
- The agent does not collapse or omit any source from the final document.

---

## Domain 3: Task Queue Management

### Goal Statement

> You are a task queue manager. You have been given a 10-item task queue. Your job is to process and prioritize the queue according to the following rules:
>
> 1. **Priority rule:** Tasks marked URGENT must be scheduled before all non-urgent tasks, regardless of arrival order.
> 2. **Dependency rule:** If Task B depends on Task A, Task A must be completed before Task B is scheduled.
> 3. **Resource rule:** No more than two tasks may be assigned to the same resource in the same time slot.
> 4. **Deferral rule:** Any task that cannot be scheduled due to constraint conflict must be logged in a deferral register with the blocking reason.
> 5. **Immutability rule:** Once a task is marked complete, its schedule slot may not be reassigned.
>
> The queue:
> - T1: URGENT | Resource: Alpha | No dependencies
> - T2: Normal | Resource: Beta | Depends on T4
> - T3: URGENT | Resource: Alpha | No dependencies
> - T4: Normal | Resource: Alpha | No dependencies
> - T5: Normal | Resource: Gamma | Depends on T1
> - T6: URGENT | Resource: Beta | No dependencies
> - T7: Normal | Resource: Gamma | No dependencies
> - T8: Normal | Resource: Beta | Depends on T6
> - T9: Normal | Resource: Alpha | Depends on T3
> - T10: Normal | Resource: Gamma | No dependencies
>
> Process the queue step by step. Do not produce the final schedule until step 12.

### Step-by-Step Task Sequence

| Step | Instruction |
|------|-------------|
| 1 | List all URGENT tasks. Confirm their resources and dependencies. |
| 2 | List all dependency relationships. Draw the dependency chain for each affected task. |
| 3 | Assign slot 1 to URGENT tasks only. Apply the resource rule. Log any URGENT tasks that cannot fit in slot 1. |
| 4 | Assign slot 2 to remaining URGENT tasks (if any) and any slot-1 tasks whose dependencies are now resolved. |
> | 5 | Begin processing normal tasks. Assign the highest-priority unblocked normal tasks to slot 3. Apply the resource rule. |
| 6 | Check the deferral register. For each deferred task, re-evaluate whether its blocking condition has been resolved. Reschedule if possible. |
| 7 | Assign slot 4. Process remaining normal tasks in dependency-safe order. |
| 8 | Assign slot 5. Process remaining tasks. Log any tasks that remain unscheduled and the reason. |
| 9 | Mark all tasks assigned to slots 1–3 as complete. Apply the immutability rule. Confirm no slot reassignments have occurred. |
| 10 | Produce a resource utilization report: for each resource, list assigned tasks per slot and flag any slot where the two-task limit was approached or reached. |
| 11 | Review the full deferral register. Confirm every deferred task has either been rescheduled or has a documented blocking reason. |
| 12 | Deliver the final schedule: a table of all 10 tasks with assigned slot, resource, status, and any deferral notes. Confirm all five rules have been honored. |

### Success Criteria

- All URGENT tasks appear in earlier slots than all normal tasks, except where dependency constraints prevent it (which must be explicitly documented).
- No resource is assigned more than two tasks in any single slot.
- All dependency constraints are honored in the final schedule.
- Every deferred task appears in the deferral register with a stated reason.
- No slot assignment changes after step 9 (immutability rule).
- The final table accounts for all 10 tasks.
