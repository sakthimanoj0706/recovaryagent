import json
from policy_lab.models import EconomicEnvironment, BreakEvenRequest
from policy_lab.sensitivity import BreakEvenAnalyzer
from policy_lab.simulator import PolicyLabSimulator

req = BreakEvenRequest(
    parameter_name="retry_cost",
    search_min=50.0,
    search_max=100.0,
    env=EconomicEnvironment(payment_population=100, random_seed=42),
)

res = BreakEvenAnalyzer.find_break_even(req)
print(res.model_dump_json(indent=2))

for val in [50.0, 92.74, 100.0]:
    env_dict = req.env.model_dump()
    env_dict["retry_cost"] = val
    cloned_env = EconomicEnvironment(**env_dict)
    sim_res = PolicyLabSimulator.run_simulation(env=cloned_env)
    n_net = sim_res.comparison.naive.net_legitimate_value
    r_net = sim_res.comparison.recoverai.net_legitimate_value
    print(f"Cost {val}: Naive={n_net}, RecoverAI={r_net}, Diff={r_net - n_net}")
