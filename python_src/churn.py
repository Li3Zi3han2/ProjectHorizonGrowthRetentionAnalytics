"""Independent feature computation, temporal evaluation, and sklearn models."""
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, precision_recall_fscore_support, confusion_matrix
from sklearn.inspection import permutation_importance
from .config import OUT, START, END, CONFIG
from .database import query, save_json

NUMERIC = ['sessions_d0_7','active_days_d0_7','total_minutes_d0_7','avg_session_minutes','tutorial_completed','core_loop_unlocked','chapter_reached_d7','boss_attempts_d0_7','boss_failure_rate_d0_7','social_interactions_d0_7','activity_participation_d0_7','crash_rate_d0_7','fps_quality','first_purchase_flag_d0_7','spend_d0_7','registration_week']
CATEGORIES = {'market':['CN','DE','JP','KR','US'], 'channel':['creator','cross_promo','organic','referral','store_feature','video_ads'], 'device':['Android','PC','iOS']}

def features(raw: dict) -> pd.DataFrame:
    """Build from raw facts; all predictors end at relative D7, label starts D22."""
    u = raw['users'].loc[raw['users'].register_date.le(pd.Timestamp(END)-pd.Timedelta(days=30))].copy()
    s = raw['sessions'].join(u.register_date.rename('registered'), on='user_id')
    s['relative_day'] = (s.session_date-s.registered).dt.days
    early = s.loc[s.relative_day.between(0,7)]
    f = early.groupby('user_id').agg(sessions_d0_7=('session_date','size'),active_days_d0_7=('session_date','nunique'),total_minutes_d0_7=('session_minutes','sum'),avg_session_minutes=('session_minutes','mean'),crash_rate_d0_7=('crash_flag','mean'),fps_quality=('fps_quality_bucket','mean'),max_feature_day=('relative_day','max'))
    p = query("SELECT p.user_id,chapter,tutorial_completed,core_loop_unlocked,boss_attempts,boss_failures FROM horizon.progression p JOIN horizon.users u USING(user_id) WHERE p.event_date-u.register_date BETWEEN 0 AND 7 AND u.register_date<=DATE '2026-05-30'")
    pp = p.groupby('user_id').agg(chapter_reached_d7=('chapter','max'),tutorial_completed=('tutorial_completed','max'),core_loop_unlocked=('core_loop_unlocked','max'),boss_attempts_d0_7=('boss_attempts','sum'),failures=('boss_failures','sum'))
    pp['boss_failure_rate_d0_7'] = (pp.failures/pp.boss_attempts_d0_7.replace(0,np.nan)).fillna(0)
    f = f.join(pp.drop(columns='failures'))
    e = query("SELECT e.user_id,event_type FROM horizon.gameplay_events e JOIN horizon.users u USING(user_id) WHERE e.event_time::date-u.register_date BETWEEN 0 AND 7 AND u.register_date<=DATE '2026-05-30' AND event_type IN('social_interaction','activity_enter')")
    for event, name in [('social_interaction','social_interactions_d0_7'),('activity_enter','activity_participation_d0_7')]:
        f[name] = e.loc[e.event_type.eq(event)].groupby('user_id').size().reindex(f.index,fill_value=0)
    m = query("SELECT m.user_id,amount_usd::float8 amount FROM horizon.monetization m JOIN horizon.users u USING(user_id) WHERE m.transaction_date-u.register_date BETWEEN 0 AND 7 AND u.register_date<=DATE '2026-05-30'")
    f['spend_d0_7'] = m.groupby('user_id').amount.sum().reindex(f.index,fill_value=0)
    f['first_purchase_flag_d0_7'] = f.index.isin(m.user_id).astype(int)
    f = f.join(u.rename(columns={'acquisition_channel':'channel'}))
    f['registration_day'] = (f.register_date-pd.Timestamp(START)).dt.days
    f['registration_week'] = f.registration_day//7
    active_target = s.loc[s.relative_day.between(22,30),'user_id'].unique()
    f['churn_30'] = (~f.index.isin(active_target)).astype(int)
    f.sort_index(inplace=True)
    f.to_csv(OUT / 'tables/python_features.csv')
    return f

def design(f: pd.DataFrame) -> pd.DataFrame:
    x = f[NUMERIC].astype(float).copy()
    for key, levels in CATEGORIES.items():
        for level in levels[1:]:
            x[f'{key}={level}'] = f[key].eq(level).astype(float)
    return x

def evaluate(y, p, threshold: float = .5) -> dict:
    top = np.lexsort((np.arange(len(p)), -p))[:int(np.ceil(len(p)/10))]
    precision, recall, f1, _ = precision_recall_fscore_support(y,p>=threshold,average='binary',zero_division=0)
    return dict(roc_auc=float(roc_auc_score(y,p)),pr_auc=float(average_precision_score(y,p)),brier=float(brier_score_loss(y,p)),precision=float(precision),recall=float(recall),f1=float(f1),confusion_matrix=confusion_matrix(y,p>=threshold).tolist(),threshold=threshold,lift_at_10pct=float(np.mean(y[top])/np.mean(y)),capture_at_10pct=float(np.sum(y[top])/np.sum(y)))

def calculate(raw: dict, metrics: dict) -> dict:
    f = features(raw)
    x = design(f)
    y = f.churn_30.to_numpy()
    train, val, test = f.registration_day.le(89), f.registration_day.between(90,119), f.registration_day.gt(119)
    scaler = StandardScaler().fit(x.loc[train])
    # Wolfram uses sample standard deviation, so match ddof=1 explicitly.
    scaler.scale_ = x.loc[train].std(ddof=1).replace(0,1).to_numpy()
    z = scaler.transform(x)
    logistic = LogisticRegression(C=10000.,solver='lbfgs',tol=1e-10,max_iter=1000).fit(z[train],y[train])
    ids = np.flatnonzero(train)[:CONFIG['nonlinear_training_cap']]
    nonlinear = HistGradientBoostingClassifier(max_iter=80,max_depth=4,max_leaf_nodes=16,min_samples_leaf=30,l2_regularization=0,random_state=CONFIG['seed'],early_stopping=False).fit(x.iloc[ids],y[ids])
    lp = logistic.predict_proba(z[test])[:,1]
    bp = nonlinear.predict_proba(x.loc[test])[:,1]
    result = dict(logistic=evaluate(y[test],lp),nonlinear=evaluate(y[test],bp),train_n=int(train.sum()),validation_n=int(val.sum()),test_n=int(test.sum()),nonlinear_train_n=len(ids),feature_names=list(x.columns))
    predictions = pd.DataFrame(dict(user_id=f.index[test],churn_30=y[test],logistic=lp,nonlinear=bp))
    predictions.to_csv(OUT / 'models/python_predictions.csv',index=False)
    pd.DataFrame(dict(feature=x.columns,coefficient=logistic.coef_[0],odds_ratio_per_sd=np.exp(logistic.coef_[0]))).to_csv(OUT / 'tables/python_logistic_coefficients.csv',index=False)
    # Validation-only permutation importance; test remains an untouched evaluation.
    vi = np.flatnonzero(val)[:5000]
    imp = permutation_importance(nonlinear,x.iloc[vi],y[vi],n_repeats=3,random_state=CONFIG['seed'],scoring='roc_auc')
    pd.DataFrame(dict(feature=x.columns,importance=imp.importances_mean,std=imp.importances_std)).sort_values('importance',ascending=False).to_csv(OUT / 'tables/permutation_importance.csv',index=False)
    save_json(OUT / 'models/python_evaluation.json', result)
    joblib.dump(dict(logistic=logistic,nonlinear=nonlinear,scaler=scaler,features=list(x.columns)),OUT / 'models/python_models.joblib')
    metrics.update({'churn/sample':len(f),'churn/positive':int(y.sum()),'churn/train':int(train.sum()),'churn/validation':int(val.sum()),'churn/test':int(test.sum())})
    # D7 intervention candidates; threshold and ranking are decided before target observations.
    all_p = logistic.predict_proba(z)[:,1]
    pd.DataFrame(dict(user_id=f.index,risk=all_p,registration_day=f.registration_day)).to_csv(OUT / 'tables/d7_risk_scores.csv',index=False)
    return result
