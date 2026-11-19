from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'final_report'/'ieee_figures'; OUT.mkdir(parents=True,exist_ok=True)
BLUE='#22577A'; TEAL='#38A3A5'; GOLD='#F4A261'; RED='#C44E52'; GRAY='#667085'; LIGHT='#EEF3F7'; DARK='#1F2937'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'figure.facecolor':'white','axes.facecolor':'white','axes.edgecolor':'#AAB4BE','axes.linewidth':0.7,'savefig.facecolor':'white'})

def save(fig,name):
 fig.savefig(OUT/name,dpi=320,bbox_inches='tight',pad_inches=0.06); plt.close(fig)

def box(ax,xy,w,h,title,body,color=BLUE,fs=7):
 x,y=xy; p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.02',facecolor='white',edgecolor=color,linewidth=1.2)
 ax.add_patch(p); ax.text(x+w/2,y+h*.70,title,ha='center',va='center',weight='bold',color=color,fontsize=fs)
 ax.text(x+w/2,y+h*.36,body,ha='center',va='center',color=DARK,fontsize=fs-0.5,wrap=True)

def arrow(ax,a,b,color=GRAY): ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=8,color=color,linewidth=0.9))

# Fig. 1: implementation-aware system architecture (schematic, based on saved code and evidence modules)
fig,ax=plt.subplots(figsize=(7.0,3.4)); ax.set(xlim=(0,1),ylim=(0,1)); ax.axis('off')
box(ax,(.02,.68),.20,.22,'Processed series','weather variables\n+ timestamps',BLUE)
box(ax,(.28,.68),.20,.22,'Feature pipeline','history features\n+ month sin/cos',BLUE)
box(ax,(.55,.68),.19,.22,'E1 candidate screen','IF • LOF • OCSVM\n12 configurations',TEAL)
box(ax,(.80,.68),.18,.22,'Candidate events','unlabeled review\nset',TEAL)
arrow(ax,(.22,.79),(.28,.79)); arrow(ax,(.48,.79),(.55,.79)); arrow(ax,(.74,.79),(.80,.79))
box(ax,(.16,.34),.19,.20,'E2 temporal','history-relative\nstatus',GOLD)
box(ax,(.405,.34),.19,.20,'E3 spatial','source-eligible\ncontext only',RED)
box(ax,(.65,.34),.19,.20,'E4 physical','broad plausibility\nscreens',GOLD)
for x in (.255,.50,.745): arrow(ax,(.89,.68),(x+.095,.55),GRAY)
box(ax,(.31,.05),.38,.18,'Evidence ledger and policy','provenance • comparability • conflicts • missingness',BLUE)
for x in (.255,.50,.745): arrow(ax,(x+.095,.34),(.50,.23),GRAY)
ax.text(.50,.285,'E3 remains outside classifier voting',ha='center',va='center',fontsize=7,color=RED,weight='bold')
ax.text(.50,.005,'Interpretation is uncertain when independent evidence is insufficient; anomaly ≠ fault.',ha='center',va='bottom',fontsize=7,color=DARK)
ax.set_title('WeatherGuard AI: evidence flow and validation boundary',loc='left',weight='bold',color=DARK)
save(fig,'fig01_system_architecture.png')

# Fig. 2: evidence framework
fig,ax=plt.subplots(figsize=(7.0,3.2)); ax.axis('off'); ax.set(xlim=(0,1),ylim=(0,1))
items=[('E1  Model stability','12 configurations across IF, LOF, OCSVM','Candidate agreement; not probability',BLUE),('E2  Temporal consistency','History-relative checks, real-time/retrospective','Departure status; not a fault label',GOLD),('E3  Spatial evidence','Time/variable/source matched station records','DESCRIPTIVE_ONLY; no classifier vote',RED),('E4  Physical plausibility','Missingness, broad bounds, cross-variable checks','Screening flag; not sensor diagnosis',TEAL)]
for (title,desc,limit,col),(x,y) in zip(items,[(.03,.55),(.52,.55),(.03,.15),(.52,.15)]):
 box(ax,(x,y),.44,.30,title,desc+'\n'+limit,col,fs=8)
ax.set_title('Four evidence dimensions and their interpretation limits',loc='left',weight='bold',color=DARK)
save(fig,'fig02_e1_e4_framework.png')

# Fig. 3: processed dataset distribution and missingness
m=pd.read_csv(ROOT/'verified_phase01/model_df.csv',parse_dates=['time'])
fig,(a,b)=plt.subplots(2,1,figsize=(7.0,3.7),gridspec_kw={'height_ratios':[2.1,1.15]})
monthly=m.set_index('time').resample('MS').size(); a.bar(monthly.index,monthly.values,width=24,color=BLUE,edgecolor='white',linewidth=.2)
a.axvline(pd.Timestamp('2025-03-21',tz='Asia/Kolkata'),color=RED,ls='--',lw=1,label='Held-out period begins (after 7-day gap)')
a.set_ylabel('Processed rows / month'); a.xaxis.set_major_locator(mdates.MonthLocator(interval=6)); a.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m')); a.tick_params(axis='x',rotation=25); a.legend(frameon=False,fontsize=7,loc='upper left'); a.grid(axis='y',alpha=.2)
miss=m.drop(columns='time').isna().sum().sort_values(ascending=False); b.bar(miss.index,miss.values,color=[GOLD if v else TEAL for v in miss.values]); b.set_ylabel('Missing cells'); b.tick_params(axis='x',rotation=25); b.grid(axis='y',alpha=.2)
fig.tight_layout(); save(fig,'fig03_dataset_coverage_missingness.png')

# Fig. 4: station record locations and source-level row coverage
z=pd.read_csv(ROOT/'outputs/phase06_controlled_e3_validation/station_zone_assignment.csv')
valid=z[z.latitude.notna()].copy(); valid=valid[valid.station_id.isin(['VILD0','42099','42101'])]
fig,(a,b)=plt.subplots(1,2,figsize=(7.0,3.4),gridspec_kw={'width_ratios':[1.0,1.45]})
for _,r in valid.iterrows():
 col=RED if r.station_id=='VILD0' else (TEAL if r.station_id=='42099' else BLUE)
 a.scatter(r.longitude,r.latitude,s=48 if r.station_id=='VILD0' else 34,marker='*' if r.station_id=='VILD0' else 'o',color=col,zorder=3)
 dx,dy=(.015,.008) if r.station_id!='VILD0' else (.01,-.014)
 label=f"{r.station_id}" if r.station_id=='VILD0' else f"{r.station_id} | {r.zone} | {r.distance_from_VILD0_km:.1f} km"
 a.annotate(label,(r.longitude+dx,r.latitude+dy),fontsize=6.5,color=DARK)
a.set_xlabel('Longitude (°E)'); a.set_ylabel('Latitude (°N)'); a.grid(alpha=.2); a.set_title('Station-record coordinates',loc='left')
a.text(.02,.02,'Reference points; exact sensor sites unverified',transform=a.transAxes,fontsize=6,color=GRAY)
files={'42099':ROOT/'outputs/phase04_provenance_aware_collection/raw_station_data/42099_hourly_source_level.csv','42101':ROOT/'outputs/phase04_provenance_aware_collection/raw_station_data/42101_hourly_source_level.csv','VILD0':ROOT/'outputs/phase06_controlled_e3_validation/raw_station_data/VILD0_hourly_source_level.csv'}
series=[]
for sid,p in files.items():
 d=pd.read_csv(p,parse_dates=['time']); d['month']=d.time.dt.tz_convert('UTC').dt.tz_localize(None).dt.to_period('M').dt.to_timestamp(); d['station']=sid
 series.append(d.groupby(['month','station']).size().rename('rows'))
cover=pd.concat(series).rename('rows').reset_index()
for sid,color in [('42099',TEAL),('42101',BLUE),('VILD0',RED)]:
 d=cover[cover.station==sid]; b.plot(d.month,d.rows,marker='o',ms=2.5,lw=1,color=color,label=sid)
b.set_ylabel('Source-level rows / month'); b.set_xlabel('UTC month'); b.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); b.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m')); b.tick_params(axis='x',rotation=30); b.grid(alpha=.2); b.legend(frameon=False,ncol=3,fontsize=6,loc='upper left'); b.set_title('Observed source-record coverage',loc='left')
fig.tight_layout(); save(fig,'fig04_station_distribution_coverage.png')

# Fig. 5: family comparison is candidate output prevalence, not performance
fam=pd.read_csv(ROOT/'research_results/e1_family_comparison.csv')
fig,ax=plt.subplots(figsize=(7.0,2.8)); y=np.arange(len(fam)); h=.34
ax.barh(y-h/2,fam.any_config_count,height=h,color=BLUE,label='At least one of four configurations')
ax.barh(y+h/2,fam.all_four_count,height=h,color=TEAL,label='All four configurations')
ax.set_yticks(y,fam.family.str.replace('LocalOutlierFactor','LOF').str.replace('OneClassSVM','One-Class SVM')); ax.invert_yaxis(); ax.set_xlabel('Unique held-out timestamps flagged'); ax.grid(axis='x',alpha=.2); ax.legend(frameon=False,fontsize=7,loc='lower right')
ax.set_title('Saved candidate counts by detector family (8,415 held-out timestamps)',loc='left',weight='bold')
for i,r in fam.iterrows(): ax.text(r.any_config_count+8,i-h/2,str(int(r.any_config_count)),va='center',fontsize=7); ax.text(r.all_four_count+8,i+h/2,str(int(r.all_four_count)),va='center',fontsize=7)
fig.tight_layout(); save(fig,'fig05_model_family_candidate_counts.png')

# Fig. 6: E1 threshold sensitivity and E2 screen sensitivity
th=pd.read_csv(ROOT/'research_results/e1_threshold_sensitivity.csv'); e=pd.read_csv(ROOT/'research_results/e2_candidate_sensitivity.csv')
fig,(a,b)=plt.subplots(1,2,figsize=(7.0,3.2),gridspec_kw={'width_ratios':[.82,1.5]})
a.bar(th.threshold,th.timestamps,color=BLUE); a.set_ylabel('Candidate timestamps'); a.set_xlabel('E1 consensus threshold'); a.grid(axis='y',alpha=.2)
for x,yv in zip(th.threshold,th.timestamps): a.text(x,yv+9,str(int(yv)),ha='center',fontsize=6.5)
# E2 SUPPORTING fraction per evaluated candidate; each cell is one setting, not truth rate.
sub=e.groupby(['mode','window_hours','robust_z_threshold','status']).size().unstack(fill_value=0)
frac=[]
for mode in ['real_time','retrospective']:
 for win in sorted(e.window_hours.unique()):
  for cut in sorted(e.robust_z_threshold.unique()):
   row=sub.loc[(mode,win,cut)] if (mode,win,cut) in sub.index else pd.Series(dtype=float)
   denom=float(row.sum()); val=(row.get('SUPPORTING',0)/denom*100) if denom else np.nan
   frac.append({'mode':mode,'window':win,'cutoff':cut,'support_pct':val,'unavailable':int(row.get('UNAVAILABLE',0))})
fd=pd.DataFrame(frac)
for mode,color,marker in [('real_time',TEAL,'o'),('retrospective',GOLD,'s')]:
 for cut,ls in [(2.5,'-'),(3.5,'--'),(4.5,':')]:
  d=fd[(fd['mode']==mode)&(fd['cutoff']==cut)].sort_values('window'); b.plot(d.window,d.support_pct,marker=marker,ms=3,lw=1,ls=ls,color=color,label=f'{mode.replace("_"," ")}, z={cut}')
b.set_xticks(sorted(e.window_hours.unique())); b.set_xlabel('History window (hours)'); b.set_ylabel('SUPPORTING evaluations (%)'); b.grid(alpha=.2); b.legend(frameon=False,fontsize=5.8,ncol=2,loc='upper right'); b.set_title('E2 sensitivity on 123 selected candidates',loc='left')
fig.tight_layout(); save(fig,'fig06_e1_e2_sensitivity.png')

# Fig. 7: monthly saved 8/12 candidate counts (not true anomaly/fault prevalence)
c=pd.read_csv(ROOT/'phase03_model_revalidation/candidate_observations_8of12.csv',parse_dates=['timestamp'])
c['month']=c.timestamp.dt.tz_convert('Asia/Kolkata').dt.tz_localize(None).dt.to_period('M').dt.to_timestamp()
cs=c.groupby('month').size().sort_index()
fig,ax=plt.subplots(figsize=(7.0,2.8)); ax.bar(cs.index,cs.values,width=21,color=TEAL)
ax.set_ylabel('8/12 candidate timestamps'); ax.set_xlabel('Month (Asia/Kolkata)'); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y')); ax.grid(axis='y',alpha=.2); ax.set_title('Monthly distribution of saved E1 consensus candidates',loc='left',weight='bold')
for x,yv in zip(cs.index,cs.values): ax.text(x,yv+.6,str(int(yv)),ha='center',fontsize=6)
fig.tight_layout(); save(fig,'fig07_monthly_candidate_distribution.png')

# Fig. 8: exact source-pair valid-pair coverage; every pair fails independent-lineage eligibility.
v=pd.read_csv(ROOT/'outputs/phase06_controlled_e3_validation/variable_comparison_results.csv')
v=v[(v.comparison_scope=='ALL_SERIES')&(v.tolerance_minutes==0)].copy()
v['pair']=v.station_primary.astype(str)+' '+v.source_primary.astype(str)+' → '+v.station_neighbor.astype(str)+' '+v.source_neighbor.astype(str)
vars_=['temp','dwpt','rhum','wspd','wdir','pres','prcp']; pairs=list(dict.fromkeys(v.pair))
mat=np.zeros((len(pairs),len(vars_)),float)
for i,pair in enumerate(pairs):
 for j,var in enumerate(vars_):
  q=v[(v.pair==pair)&(v.variable==var)]
  if len(q): mat[i,j]=float(q.iloc[0].valid_pairs or 0)
fig,ax=plt.subplots(figsize=(7.0,3.5)); im=ax.imshow(mat,aspect='auto',cmap='Blues',vmin=0)
ax.set_xticks(range(len(vars_)),['Temp.','Dew point','RH','Wind sp.','Wind dir.','Pressure','Precip.'])
ax.set_yticks(range(len(pairs)),[p.replace(' → ',' / ') for p in pairs],fontsize=6)
for i in range(mat.shape[0]):
 for j in range(mat.shape[1]):
  n=int(mat[i,j]); ax.text(j,i,str(n) if n else '–',ha='center',va='center',fontsize=6,color='white' if n>mat.max()*.52 else DARK)
ax.set_title('Exact UTC variable-valid pairs by source stratum',loc='left',weight='bold'); ax.tick_params(length=0); fig.colorbar(im,ax=ax,label='Valid paired rows',fraction=.03,pad=.02)
fig.tight_layout(); save(fig,'fig08_e3_pair_coverage_heatmap.png')

# Fig. 9: corrected synthetic E1 and E4 direct-screen responses
bdata=pd.read_csv(ROOT/'research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/synthetic_baseline_response_summary.csv')
sc=bdata[bdata.baseline.isin(['E1_consensus','E4_direct_variable_screen'])].copy()
sc['scenario']=sc.experiment_id.str.replace('TEMP_','',regex=False).str.replace('_',' ').str.title()
order=['DEWPOINT_TEMP_INCONSISTENCY','TEMP_GRADUAL_DRIFT','TEMP_INTERMITTENT_NOISE','TEMP_MISSING_BLOCK','TEMP_PERSISTENT_OFFSET','TEMP_POINT_DROP','TEMP_POINT_SPIKE','TEMP_STUCK_SENSOR']
labels=['Dew-point inconsistency','Gradual drift','Intermittent noise','Missing block','Persistent offset','Point drop','Point spike','Stuck sensor']
fig,ax=plt.subplots(figsize=(7.0,3.9)); y=np.arange(len(order)); h=.34
for base,setting,offset,col,name in [('E1_consensus','8/12',-h/2,BLUE,'E1 consensus ≥8/12'),('E4_direct_variable_screen','existing broad rule',h/2,GOLD,'E4 broad direct screen')]:
 d=sc[(sc.baseline==base)&(sc.setting==setting)].set_index('experiment_id'); vals=[float(d.loc[o,'mean_context_response_fraction'])*100 if o in d.index else 0 for o in order]
 ax.barh(y+offset,vals,height=h,color=col,label=name)
 for yi,xv in zip(y+offset,vals): ax.text(xv+1,yi,f'{xv:.1f}%',va='center',fontsize=6)
ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_xlim(0,115); ax.set_xlabel('Mean synthetic-label response across five contexts (%)'); ax.grid(axis='x',alpha=.2); ax.legend(frameon=False,fontsize=7,loc='lower right'); ax.set_title('Corrected synthetic response by scenario (not field accuracy)',loc='left',weight='bold')
fig.tight_layout(); save(fig,'fig09_synthetic_e1_e4_response.png')

# Fig. 10: Phase 09/11 evidence and adjudication status
fig,(a,b)=plt.subplots(1,2,figsize=(7.0,2.8),gridspec_kw={'width_ratios':[1.4,1]})
labels=['Candidate events','Provisional archive links','Provider-ID confirmed','Independently adjudicated']; vals=[8,2,0,0]
cols=[BLUE,GOLD,RED,RED]; y=np.arange(4); a.barh(y,vals,color=cols,height=.55); a.set_yticks(y,labels,fontsize=7); a.invert_yaxis(); a.set_xlim(0,9); a.set_xlabel('Events'); a.grid(axis='x',alpha=.2)
for yi,xv in zip(y,vals): a.text(xv+.12,yi,str(xv),va='center',fontsize=7)
a.set_title('Candidate evidence linkage',loc='left')
b.bar(['Archive\nMETAR rows'],[31],color=TEAL,width=.48); b.set_ylabel('Raw text rows'); b.text(0,32,'31 across 5 queried dates',ha='center',fontsize=6.5); b.set_ylim(0,36); b.grid(axis='y',alpha=.2); b.set_title('Archive retrieval',loc='left')
fig.tight_layout(); save(fig,'fig10_event_reference_status.png')

print('Generated',len(list(OUT.glob('fig*.png'))),'figures in',OUT)
