"""White-background, parity-gated figures. All coordinates derive from outputs."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve
from sklearn.calibration import calibration_curve
from .config import OUT

SOURCE='Source: Project Horizon synthetic data (PostgreSQL; Wolfram/Python parity validated)'
COLOR=['#225777','#45948c','#dd9951','#8a729c']
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white','axes.prop_cycle':plt.cycler(color=COLOR),'savefig.dpi':160})

def finish(fig, ax, name: str, title: str, xlabel: str, ylabel: str) -> None:
    ax.set(title=title,xlabel=xlabel,ylabel=ylabel)
    fig.text(.02,.012,SOURCE,fontsize=7,color='#53646c')
    fig.tight_layout(rect=(0,.045,1,1))
    fig.savefig(OUT/'figures/python'/f'{name}.png')
    plt.close(fig)

def generate(engine='wolfram',dual=True) -> None:
    global SOURCE
    if dual: assert json.loads((OUT/'parity/status.json').read_text())['status']=='PASS'
    else: SOURCE=f'Source: Project Horizon synthetic PostgreSQL facts; {engine} analysis; cross-language parity SKIPPED'
    daily=pd.read_csv(OUT/'tables/daily_kpis.csv');curve=pd.read_csv(OUT/'tables/retention_curve.csv')
    breakdown=pd.read_csv(OUT/'tables/retention_breakdown.csv');funnel=pd.read_csv(OUT/'tables/funnel.csv')
    predictions=pd.read_csv(OUT/f'models/{engine}_predictions.csv');coefficients=pd.read_csv(OUT/('tables/python_logistic_coefficients.csv' if engine=='python' else 'tables/logistic_coefficients.csv'))
    fig,ax=plt.subplots(figsize=(10,4));ax.axis('off')
    nodes=[(.5,.9,'Game growth & retention'),(.17,.55,'Acquisition: new users'),(.50,.55,'Activation: core loop'),(.83,.55,'Retention: D1 / D7 / D30'),(.17,.15,'Source quality: market / channel'),(.5,.15,'Friction: progression / crash'),(.83,.15,'DAU = new + retained + returned')]
    for x,y,text in nodes:ax.text(x,y,text,ha='center',va='center',bbox=dict(boxstyle='round,pad=.6',fc='#edf4f7',ec='#8eabbc'))
    for i in [1,2,3]:ax.annotate('',xy=nodes[i][:2],xytext=nodes[0][:2],arrowprops=dict(arrowstyle='->',color='#8eabbc'))
    for i in [4,5,6]:ax.annotate('',xy=nodes[i][:2],xytext=nodes[i-3][:2],arrowprops=dict(arrowstyle='->',color='#8eabbc'))
    finish(fig,ax,'01_metric_tree','Growth metric framework','', '')
    fig,ax=plt.subplots(figsize=(10,4));ax.stackplot(np.arange(len(daily)),*[daily[k] for k in ['new_active','retained','returned']],labels=['New active','Retained (<7-day gap)','Returned (7+ day gap)'],alpha=.9);ax.legend(loc='upper left');finish(fig,ax,'02_dau_composition','Daily active user composition','Simulation day','Active users (users)')
    fig,ax=plt.subplots(figsize=(9,4));ax.plot(curve.d,curve.rate);ax.fill_between(curve.d,curve.ci_low,curve.ci_high,alpha=.2);finish(fig,ax,'03_retention_curve','Mature-cohort exact-day retention (95% Wilson CI)','Relative day since registration','Retention (fraction)')
    weekly=pd.read_csv(OUT/'tables/weekly_retention.csv').pivot(index='week',columns='d',values='rate')
    fig,ax=plt.subplots(figsize=(7,5));image=ax.imshow(weekly.to_numpy(),aspect='auto',vmin=0,vmax=1,cmap='Blues');ax.set_xticks(range(3),['D1','D7','D30']);ax.set_yticks(range(0,len(weekly),2),weekly.index[::2]);fig.colorbar(image,ax=ax,label='Retention (fraction)');finish(fig,ax,'04_cohort_heatmap','Weekly cohorts; blank cells are immature','Retention horizon','Registration week')
    for dim,name in [('channel','05_retention_channel'),('device','06_retention_device')]:
        f=breakdown.loc[(breakdown.dimension==dim)&(breakdown.d==7)].sort_values('rate')
        fig,ax=plt.subplots(figsize=(9,4));ax.barh(f.category,f.rate,xerr=[f.rate-f.ci_low,f.ci_high-f.rate],color=COLOR[0],capsize=3);finish(fig,ax,name,'D7 retention by '+dim+' (95% Wilson CI)','Retention (fraction)',dim.title())
    f=funnel.loc[funnel.dimension.eq('overall')&funnel.stage_type.eq('core')]
    fig,ax=plt.subplots(figsize=(9,4));ax.barh(f.name,f.n,color=COLOR[0]);ax.invert_yaxis();finish(fig,ax,'07_funnel','Core D0-D7 progression, mature D7 users','Players passing cumulative step (users)','Funnel step')
    f=funnel.loc[funnel.dimension.eq('device')&funnel.stage_type.eq('core')]
    fig,ax=plt.subplots(figsize=(10,4))
    for device,g in f.groupby('category'):ax.plot(g.step,g.n/g.iloc[0].n,marker='o',label=device)
    ax.set_xticks(range(1,7),['Reg','Start','Tutorial','Core','Ch2','Ch3']);ax.legend();finish(fig,ax,'08_funnel_device','Early funnel by device','Cumulative D0-D7 step','Share of registered players (fraction)')
    f=funnel.loc[funnel.dimension.eq('overall')&funnel.stage_type.eq('core')&funnel.step.gt(1)]
    fig,ax=plt.subplots(figsize=(10,4));ax.barh(f.name,f.dropoff,color=COLOR[2]);ax.invert_yaxis();finish(fig,ax,'09_progression_dropoff','Conditional losses between early funnel steps','Loss versus preceding step (fraction)','Destination step')
    for kind,name in [('roc','10_roc'),('pr','11_pr')]:
        fig,ax=plt.subplots(figsize=(8,4))
        for model in ['logistic','nonlinear']:
            if kind=='roc': xx,yy,_=roc_curve(predictions.churn_30,predictions[model])
            else: yy,xx,_=precision_recall_curve(predictions.churn_30,predictions[model])
            ax.plot(xx,yy,label=engine.title()+' '+model)
        ax.legend();finish(fig,ax,name,'Temporal test '+('ROC curve' if kind=='roc' else 'precision-recall curve'),'False positive rate (fraction)' if kind=='roc' else 'Recall (fraction)','True positive rate (fraction)' if kind=='roc' else 'Precision (fraction)')
    fig,ax=plt.subplots(figsize=(8,4));ax.plot([0,1],[0,1],ls='--',color='gray',label='Perfect calibration')
    for model in ['logistic','nonlinear']:
        observed,predicted=calibration_curve(predictions.churn_30,predictions[model],n_bins=10,strategy='quantile');ax.plot(predicted,observed,marker='o',label=model)
    ax.legend();finish(fig,ax,'12_calibration','Temporal test calibration','Mean predicted churn probability','Observed D22-D30 churn rate')
    f=coefficients.assign(magnitude=coefficients.coefficient.abs()).nlargest(10,'magnitude').sort_values('coefficient')
    fig,ax=plt.subplots(figsize=(10,5));ax.barh(f.feature,f.coefficient,color=[COLOR[2] if x>0 else COLOR[0] for x in f.coefficient]);ax.axvline(0,color='gray',lw=.7);finish(fig,ax,'13_churn_signals','Logistic predictive signals; no causal interpretation','Log odds per training standard deviation','Observable D0-D7 predictor')
    f=predictions.sort_values('logistic',ascending=False).copy();f['decile']=np.minimum(np.arange(len(f))*10//len(f)+1,10);lift=f.groupby('decile').churn_30.mean()/f.churn_30.mean();lift.to_csv(OUT/'tables/risk_decile_lift.csv')
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(lift.index,lift.values);ax.axhline(1,color='gray',ls='--');finish(fig,ax,'14_risk_decile_lift','Logistic risk deciles on temporal test','Risk decile (1 = highest risk)','Churn concentration / base rate (x)')
    f=pd.read_csv(OUT/('tables/python_segments.csv' if engine=='python' or dual else 'tables/segments.csv'))
    fig,ax=plt.subplots(figsize=(10,4));ax.barh(f.segment,f.n);finish(fig,ax,'15_segments','Exclusive operations snapshot segments','Players (users)','Operations segment')
    f=pd.read_csv(OUT/'tables/reactivation_device.csv')
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(f.device,f['mean']);finish(fig,ax,'16_reactivation','Patch2 return among 14-day silent users','Device','Returned within 7 calendar days (fraction)')
    fig,ax=plt.subplots(figsize=(10,4));ax.axis('off')
    for i,(title,pop,metric) in enumerate([('A: progression','First Level12 boss attempt','Chapter3 clear within3 days'),('B: D7 high risk','Top 10% predicted churn risk','Exact-day D30 retention'),('C: returning users','Silent users at observed return','Post-return 7-day active days')]):
        y=.85-i*.32
        for x,label in [(.16,title),(.50,pop),(.85,metric)]:ax.text(x,y,label,ha='center',va='center',fontsize=9,bbox=dict(boxstyle='round,pad=.6',fc='#edf4f7',ec='#8eabbc'))
        for x in [.31,.68]:ax.annotate('',xy=(x+.035,y),xytext=(x-.04,y),arrowprops=dict(arrowstyle='->'))
    finish(fig,ax,'17_experiments','Proposed randomized experiments; no intervention was executed','','')
