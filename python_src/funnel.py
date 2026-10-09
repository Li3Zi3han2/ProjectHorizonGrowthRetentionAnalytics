"""Sequential D0-D7 events, independently reduced to user flags."""
import numpy as np
import pandas as pd
from .config import END, OUT
from .database import query
from .retention import wilson

def calculate(raw: dict, metrics: dict) -> pd.DataFrame:
    u = raw['users'].loc[raw['users'].register_date.le(pd.Timestamp(END)-pd.Timedelta(days=7))].copy()
    events = query("SELECT e.user_id,event_type,event_value FROM horizon.gameplay_events e JOIN horizon.users u USING(user_id) WHERE e.event_time::date-u.register_date BETWEEN 0 AND 7 AND u.register_date<=DATE '2026-06-22'")
    flags = pd.DataFrame(index=u.index)
    flags['Register'] = True
    for name in ['tutorial_start','tutorial_complete','core_loop_unlock','chapter_2','chapter_3','activity_enter','social_interaction']:
        mask = events.event_type.eq('chapter_complete') & events.event_value.ge(int(name[-1])) if name.startswith('chapter_') else events.event_type.eq(name)
        flags[name] = flags.index.isin(events.loc[mask, 'user_id'])
    metrics['activation_rate'] = float(flags.core_loop_unlock.mean())
    cumulative = flags.astype(int).cumprod(axis=1)
    # Optional adoption has the same Chapter 3 denominator, not a forced branch chain.
    for name in ['activity_enter','social_interaction']:
        cumulative[name] = cumulative.chapter_3 * flags[name]
    records = []
    groups = [('overall', 'all', cumulative)]
    for dim, col in [('device','device'),('market','market'),('channel','acquisition_channel')]:
        groups += [(dim, cat, cumulative.loc[group.index]) for cat, group in u.groupby(col)]
    for dim, cat, group in groups:
        previous = len(group)
        for step, name in enumerate(group.columns, 1):
            stage_type = 'core' if step<=6 else 'optional'
            if stage_type=='optional': previous=int(group.chapter_3.sum())
            n = int(group[name].sum())
            lo, hi = wilson(n, max(previous, 1))
            records.append(dict(dimension=dim, category=cat, step=step, name=name, stage_type=stage_type, denominator=previous, n=n, conversion=n/max(previous,1), dropoff=1-n/max(previous,1), ci_low=lo, ci_high=hi))
            metrics[f'funnel/{dim}/{cat}/{name}'] = n
            previous = n
    result = pd.DataFrame(records)
    result.to_csv(OUT / 'tables/python_funnel.csv', index=False)
    # Early engagement groups use sessions only and are descriptive, never causal.
    early = raw['sessions'].join(raw['users']['register_date'], on='user_id')
    early = early.loc[(early.session_date-early.register_date).dt.days.between(0,7)].groupby('user_id').session_date.nunique()
    group = np.where(early.reindex(u.index).ge(4),'4+ early active days','1-3 early active days')
    behavior = cumulative.assign(behavior=group).groupby('behavior').mean().T
    behavior.to_csv(OUT / 'tables/funnel_early_behavior.csv')
    return result
