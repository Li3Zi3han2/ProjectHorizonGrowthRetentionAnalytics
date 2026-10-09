"""Complete shared table contract and PDF rendering from current engine results."""
import json
import re
import shutil
import os
from html import escape
import pandas as pd
from .config import OUT, ARTIFACT_ROOT, ROOT, START, END
from .database import query, save_json


def python_tables(raw, metrics):
    for source,target in [('python_daily_kpis','daily_kpis'),('python_retention_curve','retention_curve'),('python_retention_breakdown','retention_breakdown'),('python_funnel','funnel'),('python_segments','segments'),('python_logistic_coefficients','logistic_coefficients'),('python_data_quality','data_quality_summary'),('python_gate_eligibility','gate_eligibility')]:
        shutil.copy2(OUT/f'tables/{source}.csv',OUT/f'tables/{target}.csv')
    funnel=pd.read_csv(OUT/'tables/funnel.csv')
    for kind,name in [('core','core_funnel'),('optional','optional_adoption')]:
        funnel.loc[funnel.stage_type.eq(kind)].to_csv(OUT/f'tables/{name}.csv',index=False)
    query("SELECT level,sum(boss_attempts) attempts,sum(boss_failures) failures,count(DISTINCT p.user_id) users,sum(boss_failures)::float8/NULLIF(sum(boss_attempts),0) failure_rate FROM horizon.progression p JOIN horizon.users u USING(user_id) WHERE p.event_date BETWEEN u.register_date AND u.register_date+7 AND u.register_date+7<=DATE '2026-06-29' AND boss_attempts>0 GROUP BY level ORDER BY level").to_csv(OUT/'tables/progression_diagnosis.csv',index=False)
    users=raw['users'].copy();users['week']=(users.register_date-pd.Timestamp(START)).dt.days//7
    active=raw['sessions'][['user_id','session_date']].drop_duplicates();records=[]
    for d in [1,7,30]:
        mature=users.loc[users.register_date.le(pd.Timestamp(END)-pd.Timedelta(days=d))].copy()
        kept=active.loc[(active.session_date-active.user_id.map(users.register_date)).dt.days.eq(d),'user_id']
        mature['retained']=mature.index.isin(kept)
        for week,g in mature.groupby('week'):records.append(dict(week=week,d=d,eligible=len(g),rate=float(g.retained.mean())))
    pd.DataFrame(records).to_csv(OUT/'tables/weekly_retention.csv',index=False)
    wall=pd.read_csv(OUT/'tables/progression_diagnosis.csv').set_index('level').loc[12]
    em=json.loads((OUT/'models/python_evaluation.json').read_text())
    values={k:metrics[k] for k in ['users','payer_conversion','arpu','arppu']}
    values.update({f'd{d}_retention':metrics[f'retention/d{d}'] for d in [1,7,30]})
    values.update({f'{device.lower()}_d7_retention':metrics[f'retention/device/{device}/d7'] for device in ['Android','PC','iOS']})
    values.update({k:metrics[f'session_diagnostics/{k}'] for k in ['sessions','active_user_days','sessions_per_active_day','multi_session_day_fraction']})
    device_rates=[metrics[f'retention/device/{d}/d7'] for d in ['Android','PC','iOS']]
    values.update(chapter2_to_chapter3_conversion=float(funnel.loc[funnel.dimension.eq('overall')&funnel.name.eq('chapter_3'),'conversion'].iloc[0]),level12_boss_failure_rate=float(wall.failure_rate),device_max_gap=max(device_rates)-min(device_rates),reactivation_eligible=metrics['reactivation/eligible'],reactivation_rate=metrics['return_rate'],logistic_auc=em['logistic']['roc_auc'],nonlinear_auc=em['nonlinear']['roc_auc'],lift_at_10pct=em['logistic']['lift_at_10pct'])
    bands={'sessions_per_active_day':(1.2,1.6),'d1_retention':(.3,.5),'d7_retention':(.12,.3),'d30_retention':(.05,.18),'payer_conversion':(.02,.10),'chapter2_to_chapter3_conversion':(.55,.75),'level12_boss_failure_rate':(.55,.80),'device_max_gap':(.02,.08)}
    diagnostics=[dict(metric=k,value=v,target_band_low=bands.get(k,(None,None))[0],target_band_high=bands.get(k,(None,None))[1],status=('WITHIN_DESIGN_BAND' if bands[k][0]<=v<=bands[k][1] else 'REVIEW_SOFT_BAND') if k in bands else 'OBSERVED',band_type='synthetic design guardrail; not industry benchmark') for k,v in values.items()]
    save_json(OUT/'validation/synthetic_calibration.json',dict(values=values,diagnostics=diagnostics,guardrail_note='Original soft design bands; not calibrated to published numbers.'))
    pd.DataFrame(diagnostics).to_csv(OUT/'validation/synthetic_calibration.csv',index=False)


def assets(engine):
    import matplotlib.pyplot as plt
    from .visualization import finish
    wall=pd.read_csv(OUT/'tables/progression_diagnosis.csv')
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(wall.level.astype(str),wall.failure_rate);ax.set_ylim(0,1)
    finish(fig,ax,'18_level12_friction','Early boss failures / attempts','Level','Failure fraction')
    dest=ARTIFACT_ROOT/'portfolio/assets';dest.mkdir(parents=True,exist_ok=True)
    names={'03_retention_curve':'01_retention_curve','04_cohort_heatmap':'02_cohort_heatmap','06_retention_device':'03_device_d7','07_funnel':'04_core_funnel','18_level12_friction':'05_level12_friction','12_calibration':'06_model_calibration','13_churn_signals':'07_logistic_coefficients','14_risk_decile_lift':'08_risk_decile','15_segments':'09_segments','16_reactivation':'10_reactivation','02_dau_composition':'11_dau_composition'}
    for source,target in names.items():shutil.copy2(OUT/f'figures/python/{source}.png',dest/f'{target}.png')
    # Static repository QR is not an analysis cache.
    shutil.copy2(ROOT/'portfolio/assets/github_qr.png',dest/'github_qr.png')


def pdf():
    if os.environ.get('HORIZON_PDF_MODE')=='manual':
        path=ARTIFACT_ROOT/'portfolio/Project_Horizon_Portfolio.md'
        import hashlib
        save_json(OUT/'validation/pdf_render_request.json',dict(status='PENDING_USER_RENDER',markdown_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),markdown='portfolio/Project_Horizon_Portfolio.md'))
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    font_path=os.environ.get('HORIZON_PDF_FONT')
    if not font_path and os.environ.get('WINDIR'):
        from pathlib import Path
        candidate=Path(os.environ['WINDIR'])/'Fonts/simsun.ttc'
        if candidate.is_file():font_path=str(candidate)
    if font_path:
        pdfmetrics.registerFont(TTFont('HorizonCJK',font_path,subfontIndex=0));font='HorizonCJK'
    else:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));font='STSong-Light'
    body=ParagraphStyle('Body',fontName=font,fontSize=10,leading=16,spaceAfter=6,wordWrap='CJK')
    heading=ParagraphStyle('Heading',parent=body,fontSize=14,leading=20,spaceBefore=12,spaceAfter=8,keepWithNext=True)
    small=ParagraphStyle('Small',parent=body,fontSize=8,leading=12)
    path=ARTIFACT_ROOT/'portfolio/Project_Horizon_Portfolio.md'
    text=path.read_text(encoding='utf8');text=text[text.index('# Project Horizon'):]
    story=[];lines=text.splitlines();i=0
    def clean(line):
        line=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',line)
        return escape(line.replace('**','').replace('`','').lstrip('> ').replace('–','-').replace('—','-'))
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line.startswith('```'):
            while i<len(lines) and not lines[i].startswith('```'):i+=1
            i+=1;continue
        image=re.match(r'!\[[^\]]*\]\(([^)]+)\)',line)
        if image:
            from PIL import Image as PILImage
            image_path=path.parent/image[1]
            with PILImage.open(image_path) as im:w,h=im.size
            width=480;story.extend([Image(str(image_path),width=width,height=width*h/w),Spacer(1,8)]);continue
        if line.startswith('[!['):
            nested=re.search(r'!\[[^\]]*\]\(([^)]+)\)',line)
            if nested:story.append(Image(str(path.parent/nested[1]),width=80,height=80,hAlign='LEFT'))
            continue
        if line.startswith('|'):
            rows=[line]
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
            data=[[Paragraph(clean(cell.strip()),small) for cell in row.strip('|').split('|')] for row in rows if not re.fullmatch(r'[|:\-\s]+',row)]
            table=Table(data,colWidths=[480/len(data[0])]*len(data[0]),repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf4f7')),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#a0b6c0')),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,8)]);continue
        story.append(Paragraph(clean(line.lstrip('# ')),heading if line.startswith('#') else body))
    def footer(canvas,doc):
        canvas.setFont(font,8);canvas.drawString(42,25,'Project Horizon - synthetic data; see run report for validation scope');canvas.drawRightString(A4[0]-42,25,str(doc.page))
    SimpleDocTemplate(str(path.with_suffix('.pdf')),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=42,title='Project Horizon current-run portfolio').build(story,onFirstPage=footer,onLaterPages=footer)
