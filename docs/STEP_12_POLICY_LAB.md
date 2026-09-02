# Step 12: Recovery Policy Lab & What-If Economic Simulator

## 1. Overview & Core Philosophy

**RecoverAI Policy Lab** is an interactive financial simulation environment and What-If analysis engine that enables fintech leaders and operators to simulate, stress-test, and compare recovery strategies under configurable macroeconomic cost regimes.

### Core Fintech Invariant:
> **"RecoverAI is not an LLM that controls payments. It is a bounded financial agent operating inside deterministic financial safety rails."**

---

## 2. 3-Way Strategy Architecture

The simulator tests three distinct recovery paradigms across identical pseudo-randomly generated synthetic payment populations:

| Strategy | Description | Safety Rails | Accounting Integrity |
| :--- | :--- | :--- | :--- |
| **Naive Baseline** | Industry-standard aggressive retry logic. Assumes webhook failures = lost revenue. | ❌ None | Books unverified phantom claims, double-charges late-auths, retries hard declines. |
| **RecoverAI Core** | Full multi-layer agentic safety loop with FinancialStateEngine, RecoveryFirewall, and RecoveryVerifier. | ✅ Complete | Zero double-charges, zero unearned claims, exact ₹0.00 accounting conservation. |
| **Custom Policy** | Merchant-tailored channel preferences, retry thresholds, high-value escalations, and min ENV constraints. | ✅ Guaranteed via Non-Bypassable Firewall | Zero safety violations, customized unit economics. |

---

## 3. Mathematical Foundations

### Transparent Expected Net Value Calculation
$$\text{ENV}(\text{action}) = P(\text{recovery} \mid \text{context}, \text{action}) \times \text{Amount} - \text{Cost}(\text{action}) - \text{Expected Risk Loss}$$

Where:
- $\text{Cost}(\text{action})$ includes gateway retry fees, dynamic payment link generation, and communication dispatch costs.
- $\text{Expected Risk Loss}$ includes card scheme penalty surcharges and double-charge dispute exposure.
- **Action Selection**: Selects $\arg\max_{\text{permitted actions}} \text{ENV}(\text{action})$ subject to $\text{ENV} > \text{min\_expected\_net\_value}$.

### Accounting Conservation Law
$$\text{Total Volume} = \text{Recovered} + \text{Withheld} + \text{Pending} + \text{Escalated} + \text{Outstanding}$$
$$\text{Accounting Imbalance} = |\text{Total Volume} - \sum \text{Buckets}| \equiv \text{₹}0.00$$

---

## 4. Analytical Capabilities

### 1. One-Parameter Sensitivity Sweeps (`SensitivityAnalyzer`)
Varies key parameters across defined test points while keeping the synthetic population and other cost variables strictly fixed:
- `retry_cost` (₹0.50 to ₹25.00)
- `chargeback_cost` (₹50 to ₹2,500)
- `scheme_penalty` (₹0 to ₹500)
- `recovery_probability_multiplier` (0.20x to 2.00x)
- `max_retries` (0 to 5)

### 2. Break-Even Discovery (`BreakEvenAnalyzer`)
Scans parameter space using bisection and linear interpolation to discover the exact threshold where $\text{RecoverAI Net Value} = \text{Naive Net Value}$. If RecoverAI strictly dominates the baseline across the entire domain, the analyzer returns `break_even_found = False` with a mathematical proof of dominance.

### 3. Multi-Seed Monte Carlo Validation (`MonteCarloSimulator`)
Simulates $N$ independent populations ($N \in \{10, 50, 100\}$) across sequential random seeds ($\text{seed}_0, \text{seed}_0 + 1, \dots$). Computes:
- Mean and Median Value Lift %
- Standard Deviation
- 95% Confidence Interval $[\mu - 1.96\sigma/\sqrt{N}, \mu + 1.96\sigma/\sqrt{N}]$
- Global verification of the ₹0.00 accounting conservation invariant.

---

## 5. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/policy-lab/run` | Executes 3-way comparative simulation on synthetic population. |
| `POST` | `/api/policy-lab/sensitivity` | Executes one-parameter sensitivity analysis sweep. |
| `POST` | `/api/policy-lab/break-even` | Discovers deterministic economic break-even crossover points. |
| `POST` | `/api/policy-lab/monte-carlo` | Executes multi-seed stochastic Monte Carlo simulation. |
| `GET` | `/api/policy-lab/latest` | Retrieves the latest Policy Lab simulation run. |
| `GET` | `/api/policy-lab/{run_id}` | Retrieves a cached run by its unique `run_id`. |

---

## 6. Command Center UI

The React/Vite Command Center includes:
- **Interactive Controls**: Sliders for unit costs, probability multiplier, risk appetite, and custom policy rules.
- **Winner Highlighting**: Visual cards for Naive, RecoverAI, and Custom Policy with dynamic badges for Top Legitimate Value.
- **Audit Table**: Full side-by-side breakdown of Real Cash, Phantom Claims, Dispute Losses, and Net Value.
- **"Why Did This Strategy Win?"**: Automated rule-based explanations proving why the winning strategy created optimal economic value.
- **Sensitivity & Monte Carlo Visualizers**: Interactive tables and confidence interval indicators.
