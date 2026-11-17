# Methodology

> All data is SIMULATED. Results are not real-world performance.

## Formal Problem Statement

**Fixed-charge budgeted asset selection:**

Given a set of assets I, corridors C, budget B:
- Binary decision: x_i ∈ {0,1} (repair asset i), y_c ∈ {0,1} (open corridor c)
- Objective: maximise Σ b_i x_i where b_i = risk_i × criticality_i
- Constraints:
  - Σ w_i x_i + Σ M_c y_c ≤ B  (budget)
  - x_i ≤ y_{c(i)}  for all i  (corridor must be open to repair asset)
  - Optional: Σ_{i∈ward w} (w_i x_i + M_{c(i)} y_{c(i)}) ≥ min_share × B/|W|  (equity)

## Cost Model

- **Uncoordinated**: cost(i) = work_cost_i + mobilisation_cost_{c(i)}  (each asset pays full mobilisation)
- **Coordinated**: cost(plan) = Σ work_cost_i + Σ_{c opened} mobilisation_cost_c  (mobilisation paid once per corridor)
- **Reactive repair**: cost = 1.5 × work_cost + mobilisation_cost  (emergency premium, always uncoordinated)

## Evaluation Protocol

- **Time-based splits**: train months 0–23, calibration 24–29, test 30–35 (no shuffling, no leakage)
- **Calibration**: isotonic regression on calibration months, evaluated on test months
- **Simulation**: 12 months from month 36, 10–30 seeds, common random numbers across strategies
- **Paired comparisons**: differences computed within each seed, CI from seed distribution
- **Metrics**: failures, criticality-weighted failures, planned/emergency/total spend, re-dig events, vehicle-hours disrupted

## Key Assumptions

1. Corridor frailty and vintage age create within-corridor risk correlation (documented in `ml/city.py`)
2. Mobilisation cost is paid once per corridor visit regardless of number of assets
3. Reactive repairs always incur a separate mobilisation (no coordination possible for emergencies)
4. Budget carryover is allowed month-to-month within the simulation year
5. IsolationForest contamination=0.10 is set a priori as an alert budget, not tuned on labels
