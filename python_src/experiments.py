"""Independent eligibility and power plans; none are measured treatment effects."""
import math
import pandas as pd
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize
from .config import OUT
from .database import query, save_json

def plan(summary: dict, engine='wolfram') -> list[dict]:
    gate=pd.read_csv(OUT/('tables/python_gate_eligibility.csv' if engine=='python' else 'tables/gate_eligibility.csv'))
    base_a=float(gate.completed_within3.mean())
    pred=pd.read_csv(OUT/f'models/{engine}_predictions.csv').sort_values('logistic',ascending=False)
    risky=pred.head(math.ceil(len(pred)/10))
    n=query("SELECT count(DISTINCT s.user_id) FROM horizon.sessions s JOIN horizon.users u USING(user_id) WHERE s.session_date=u.register_date+30 AND s.user_id=ANY(%s)",(risky.user_id.astype(int).tolist(),)).iloc[0,0]
    base_b=float(n/len(risky))
    sd=query("WITH eligible AS(SELECT u.user_id FROM horizon.users u WHERE u.register_date<DATE '2026-04-17' AND NOT EXISTS(SELECT 1 FROM horizon.sessions s WHERE s.user_id=u.user_id AND s.session_date BETWEEN DATE '2026-04-17' AND DATE '2026-04-30')), r AS(SELECT e.user_id,min(session_date) rd FROM eligible e JOIN horizon.sessions s USING(user_id) WHERE session_date BETWEEN DATE '2026-05-01' AND DATE '2026-05-07' GROUP BY e.user_id), p AS(SELECT r.user_id,count(DISTINCT session_date) n FROM r JOIN horizon.sessions s ON s.user_id=r.user_id AND s.session_date BETWEEN rd AND rd+6 GROUP BY r.user_id) SELECT stddev_samp(n)::float8 sd FROM p").iloc[0,0]
    binary_n=lambda p,d:math.ceil(NormalIndPower().solve_power(abs(proportion_effectsize(p,min(.999,p+d))),power=.8,alpha=.05,ratio=1))
    plans=[dict(experiment='A',population='First Level 12 boss attempt; user 1:1 randomization at exposure',primary='Chapter 3 completion within 3 days of first Level 12 attempt',eligible_n=len(gate),completed_n=int(gate.completed_within3.sum()),baseline=base_a,mde=.025,per_arm=binary_n(base_a,.025),treatment='关卡难度、资源或引导优化',guardrails='Mature D7/D14 retention, crashes, playtime, spend, downstream progression'),dict(experiment='B',population='Top decile risk ranked at D7',primary='Exact-day D30 retention',eligible_n=len(risky),baseline=base_b,mde=.03,per_arm=binary_n(base_b,.03),treatment='个性化任务提示与资源扶持',guardrails='Crashes, spend, opt-out; D22-D30 activity secondary'),dict(experiment='C',population='14-day silent users randomized at observed return',primary='Post-return D0-D6 active days',eligible_n=summary['reactivation_count'],baseline=summary['post_return_active_days'],mde=.3,per_arm=math.ceil(TTestIndPower().solve_power(.3/float(sd),power=.8,alpha=.05,ratio=1)),treatment='个性化回流内容导航',guardrails='Crashes, disengagement, spend')]
    pd.DataFrame(plans).to_csv(OUT/'tables/experiment_design.csv',index=False)
    save_json(OUT/'metrics/power_analysis.json',dict(alpha=.05,power=.8,two_sided=True,experiments=plans,assumptions='User 1:1 allocation, fixed horizon, no peeking; planning MDEs, no executed experiment. A followup includes exposure date through +3 calendar days, complete-window eligibility independent of clearing. D7/D14 retention secondary requires complete registration-relative maturity; gate-relative windows can be separately prespecified. B exact D30 differs from D22-D30 activity. C counts distinct active dates.'))
    return plans
