from pathlib import Path
import hashlib, json
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'final_report'
FIG = OUT / 'figures'
FIG.mkdir(parents=True, exist_ok=True)
CAM = ROOT / 'research_results/fault_matrix_multicontext_46ae5d119d'
BASE = CAM / 'baseline_review_1'
E2 = CAM / 'e2_validation_review_1'

def read(path): return pd.read_csv(ROOT / path)
def sha(path):
    h=hashlib.sha256()
    with open(ROOT/path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

phase=pd.read_csv(ROOT/'verified_phase01/model_df.csv')
x=pd.read_csv(ROOT/'verified_phase01/X_multi.csv')
train=pd.read_csv(ROOT/'verified_phase01/X_train_multi.csv')
test=pd.read_csv(ROOT/'verified_phase01/X_test_multi.csv')
pred=pd.read_csv(ROOT/'phase03_model_revalidation/model_predictions.csv')
threshold=read('research_results/e1_threshold_sensitivity.csv')
family=read('research_results/e1_family_comparison.csv')
detail=pd.read_csv(E2/'e2_multicontext_fault_detail.csv')
paired=pd.read_csv(E2/'e2_multicontext_fault_paired.csv')
controls=pd.read_csv(E2/'e2_matched_controls.csv')
summary=pd.read_csv(BASE/'synthetic_baseline_response_summary.csv')
coverage=pd.read_csv(BASE/'evidence_coverage_ablation_summary.csv')
mismatch=pd.read_csv('research_results/prediction_mismatch_investigation.csv')

assert (len(phase),len(x),len(train),len(test),len(pred))==(44879,44849,36434,8415,100980)
assert len(detail)==6840 and len(paired)==2880 and len(controls)==10
assert len(mismatch)==42

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':12,'axes.labelsize':10,
                     'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
blue='#174A70'; teal='#218C8D'; orange='#E59B3A'; red='#B95252'; gray='#62707C'

def save(name):
    plt.tight_layout(); plt.savefig(FIG/name,dpi=200,bbox_inches='tight'); plt.close()

# E1 threshold sensitivity
plt.figure(figsize=(7.2,4.2)); plt.plot(threshold['timestamps'].astype(str),threshold['pct_of_test_timestamps'],marker='o',lw=2.5,color=blue)
for _,r in threshold.iterrows(): plt.annotate(f"{int(r.timestamps)} ({r.pct_of_test_timestamps:.2f}%)",(str(r.timestamps),r.pct_of_test_timestamps),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
plt.xlabel('Consensus threshold (of 12 configurations)'); plt.ylabel('Test timestamps selected (%)'); plt.title('E1 consensus threshold sensitivity'); plt.grid(axis='y',alpha=.25); save('fig04_e1_consensus_threshold.png')

# E1 family counts
plt.figure(figsize=(7.4,4.4)); labels=['Isolation Forest','Local Outlier Factor','One-Class SVM']; yy=range(len(family)); h=.34
plt.barh([i-h/2 for i in yy],family.any_config_count,label='Flagged by ≥1 configuration',color=teal,height=h)
plt.barh([i+h/2 for i in yy],family.all_four_count,label='Flagged by all 4 configurations',color=orange,height=h)
plt.yticks(list(yy),labels); plt.xlabel('Unique test timestamps (n = 8,415)'); plt.title('E1 model-family candidate counts'); plt.legend(frameon=False,loc='lower right'); plt.grid(axis='x',alpha=.2); save('fig05_e1_family_comparison.png')

# corrected E1 by scenario
s=summary[(summary.baseline=='E1_consensus') & (summary.setting=='8/12')].copy()
s=s.sort_values('mean_context_response_fraction')
plt.figure(figsize=(8.4,5.2)); y=range(len(s)); mean=s.mean_context_response_fraction*100; lo=mean-s.minimum_context_response_fraction*100; hi=s.maximum_context_response_fraction*100-mean
plt.barh(list(y),mean,color=blue,xerr=[lo,hi],capsize=3)
plt.yticks(list(y),[i.replace('TEMP_','').replace('DEWPOINT_','').replace('_',' ').title() for i in s.experiment_id]); plt.xlabel('Mean context response (%)'); plt.title('Synthetic response at E1 threshold 8/12'); plt.grid(axis='x',alpha=.2); save('fig06_synthetic_scenario_response.png')

# paired status
conditions=['clean_same_timestamp','synthetic_faulted']
status_order=['NO_DETECTED_EVIDENCE','SUPPORTING','CONFLICTING','UNAVAILABLE']
counts={c:detail[detail.condition.eq(c)].status.value_counts() for c in conditions}
plt.figure(figsize=(7.5,4.3)); bottoms=[0,0]
colors=[gray,teal,red,'#B9C2C9']
for st,col in zip(status_order,colors):
 vals=[int(counts[c].get(st,0)) for c in conditions]
 plt.bar(['Unmodified same-time rows\n(n=2,880)','Synthetic faulted rows\n(n=2,880)'],vals,bottom=bottoms,color=col,label=st.replace('_',' ').title())
 for i,v in enumerate(vals):
  if v>90: plt.text(i,bottoms[i]+v/2,f'{v:,}',ha='center',va='center',color='white' if col in [gray,teal,red] else '#26333D',fontsize=8)
 bottoms=[bottoms[i]+vals[i] for i in range(2)]
plt.ylabel('E2 screen evaluations'); plt.title('E2 status distribution by paired condition'); plt.legend(ncol=2,frameon=False,fontsize=8); save('fig07_e2_paired_status.png')

# E2 sensitivity aggregate supporting fraction by window and mode, all thresholds/scenarios pooled
e2=pd.read_csv(BASE/'synthetic_e2_setting_sensitivity.csv')
e2['available']=e2.screen_rows-e2.unavailable
e2['support_fraction']=e2.supporting/e2.available
agg=e2.groupby(['mode','window_hours'],as_index=False).apply(lambda g: pd.Series({'supporting_fraction':g.supporting.sum()/g.available.sum()}),include_groups=False).reset_index(drop=True)
plt.figure(figsize=(7.4,4.4))
for mode,color in [('real_time',blue),('retrospective',orange)]:
 q=agg[agg['mode'].eq(mode)].sort_values('window_hours'); plt.plot(q.window_hours,q.supporting_fraction*100,marker='o',lw=2,label=mode.replace('_',' ').title(),color=color)
plt.xlabel('Prior observation window (hours)'); plt.ylabel('SUPPORTING among available evaluations (%)'); plt.title('E2 temporal screen by mode and window'); plt.xticks([3,6,12]); plt.grid(alpha=.25); plt.legend(frameon=False); save('fig08_e2_setting_sensitivity.png')

# E4 comparison by direct screen and E1 threshold
e4=summary[summary.baseline.eq('E4_physical_screen')].copy()
e4=e4.sort_values('mean_context_response_fraction')
plt.figure(figsize=(8.3,4.8)); y=range(len(e4)); plt.barh(list(y),e4.mean_context_response_fraction*100,color=teal)
plt.yticks(list(y),[i.replace('TEMP_','').replace('DEWPOINT_','').replace('_',' ').title() for i in e4.experiment_id]); plt.xlabel('Synthetic injected timestamp units flagged (%)'); plt.title('E4 direct physical screen response'); plt.grid(axis='x',alpha=.2); save('fig09_e4_synthetic_screen.png')

# coverage ablation selection
cov=coverage.groupby('combination',as_index=False).agg(units=('units','max'),complete_units=('complete_units','min'),coverage_fraction=('coverage_fraction','min'))
cov=cov.sort_values('coverage_fraction')
plt.figure(figsize=(7.6,4.5)); plt.barh(range(len(cov)),cov.coverage_fraction*100,color=[red if v==0 else teal for v in cov.coverage_fraction]); plt.yticks(range(len(cov)),cov.combination.str.replace('_',' ')); plt.xlabel('Units with required evidence available (%)'); plt.title('Evidence coverage ablation (160 experimental units)'); plt.xlim(0,105); plt.grid(axis='x',alpha=.2)
for i,v in enumerate(cov.coverage_fraction*100): plt.text(v+1,i,f'{v:.1f}%',va='center',fontsize=8)
save('fig10_evidence_coverage.png')

# roadmap
fig,ax=plt.subplots(figsize=(8.5,4.1)); ax.axis('off')
steps=[('Completed prototype','E1 model stability\nE2 temporal screens\nE4 physical checks',blue),('Partly evaluated','Synthetic five-context study\nCoverage-only ablation',teal),('Blocked empirical evidence','E3 raw neighbouring stations\nIndependent Phase 2 labels',orange),('Required validation','Resolve station identity\nAcquire traceable observations\nAdjudicate event/fault labels',red)]
for i,(head,body,col) in enumerate(steps):
 x0=.03+i*.245
 ax.add_patch(plt.Rectangle((x0,.35),.21,.42,facecolor=col,alpha=.96,transform=ax.transAxes))
 ax.text(x0+.105,.68,head,ha='center',va='center',color='white',weight='bold',fontsize=9,transform=ax.transAxes,wrap=True)
 ax.text(x0+.105,.49,body,ha='center',va='center',color='white',fontsize=8,transform=ax.transAxes,wrap=True)
 if i<3: ax.annotate('',xy=(x0+.24,.56),xytext=(x0+.215,.56),xycoords=ax.transAxes,arrowprops={'arrowstyle':'->','color':gray,'lw':1.6})
plt.title('Validation roadmap from prototype to field evaluation',pad=12); save('fig11_research_validation_roadmap.png')

# architecture schematic
fig,ax=plt.subplots(figsize=(8.6,4.5)); ax.axis('off')
boxes=[(.04,.63,.25,.23,'Processed station time series','6 weather variables +\n3 historical features\n(+ 2 seasonal model terms)',blue),(.38,.76,.22,.16,'E1 Model stability','IF · LOF · One-Class SVM',teal),(.38,.52,.22,.16,'E2 Temporal consistency','windows · robust deviations',teal),(.38,.28,.22,.16,'E3 Spatial corroboration','planned; empirical series unavailable',orange),(.38,.04,.22,.16,'E4 Physical screening','missingness · bounds · consistency',teal),(.72,.52,.24,.22,'Evidence-aware interpretation','Regional event supported\nStation-specific suspicious\nUncertain / abstain',blue)]
for x0,y0,w,h,head,body,col in boxes:
 ax.add_patch(plt.Rectangle((x0,y0),w,h,facecolor=col,transform=ax.transAxes,alpha=.96))
 ax.text(x0+w/2,y0+h*.68,head,ha='center',va='center',color='white',weight='bold',fontsize=9,transform=ax.transAxes)
 ax.text(x0+w/2,y0+h*.28,body,ha='center',va='center',color='white',fontsize=7.5,transform=ax.transAxes)
for yy in [.84,.60,.36,.12]: ax.annotate('',xy=(.37,yy),xytext=(.30,.74),xycoords=ax.transAxes,arrowprops={'arrowstyle':'->','color':gray,'lw':1.2})
for yy in [.84,.60,.36,.12]: ax.annotate('',xy=(.71,.63),xytext=(.61,yy),xycoords=ax.transAxes,arrowprops={'arrowstyle':'->','color':gray,'lw':1.2})
plt.title('WeatherGuard AI evidence architecture (E3 pending)'); save('fig01_architecture.png')

# workflow
fig,ax=plt.subplots(figsize=(8,3.3)); ax.axis('off')
steps=[('Processed snapshot\n44,879 rows',blue),('Feature readiness\n44,849 rows',teal),('Chronological split\n36,434 / 8,415',blue),('12 model configurations\n3 families',teal),('Saved predictions\n100,980 records',blue)]
for i,(txt,col) in enumerate(steps):
 x0=.02+i*.196; ax.add_patch(plt.Rectangle((x0,.40),.17,.32,facecolor=col,transform=ax.transAxes)); ax.text(x0+.085,.56,txt,ha='center',va='center',color='white',fontsize=8,weight='bold',transform=ax.transAxes)
 if i<4: ax.annotate('',xy=(x0+.194,.56),xytext=(x0+.173,.56),xycoords=ax.transAxes,arrowprops={'arrowstyle':'->','color':gray})
plt.title('Historical processing and prediction workflow'); save('fig03_data_model_workflow.png')

# evidence register records: claim rows point to exact files and filters; source SHA recalculated.
records=[]
def add(cid,sec,claim,val,unit,path,filter_,status,limit):
    records.append({'claim_id':cid,'report_section':sec,'claim':claim,'numeric_value':val,'unit':unit,'source_file':path,'source_commit':'07edecdad90c36b98c0e2ad789f4d5c07bed728e','source_hash':sha(path) if (ROOT/path).is_file() else 'UNAVAILABLE','source_rows_or_filter':filter_,'verification_status':status,'interpretation_limit':limit})
P='verified_phase01/'
add('D01','3,6.1','Processed snapshot rows',44879,'rows',P+'model_df.csv','all rows','HASH_VERIFIED_HISTORICAL_ARTIFACT','Processed snapshot; raw source acquisition not independently reconstructed.')
add('D02','3,6.1','Feature-ready rows',44849,'rows',P+'X_multi.csv','all rows','HASH_VERIFIED_HISTORICAL_ARTIFACT','Nine stored base features; model service adds two cyclical month terms.')
add('D03','3,6.1','Training observations',36434,'rows',P+'X_train_multi.csv','chronological training partition','HASH_VERIFIED_HISTORICAL_ARTIFACT','No independent labels.')
add('D04','3,6.1','Testing observations',8415,'rows',P+'X_test_multi.csv','chronological test partition','HASH_VERIFIED_HISTORICAL_ARTIFACT','No independent labels.')
add('D05','3,6.1','Stored model features',9,'columns',P+'X_multi.csv','exclude time column','HASH_VERIFIED_HISTORICAL_ARTIFACT','Two cyclical month features are generated at model runtime.')
add('D06','3','Train-test temporal gap',7,'days',P+'phase01_manifest.json','train last 2025-03-14 23:30; test starts 2025-03-21 23:30 (+05:30)','HASH_VERIFIED_HISTORICAL_ARTIFACT','Gap does not establish independence.')
add('R01','6.2','Prediction grid records',100980,'records','phase03_model_revalidation/model_predictions.csv','all rows','HASH_VERIFIED_HISTORICAL_ARTIFACT','Saved historical predictions; parity discrepancy disclosed.')
add('R02','6.2','Prediction timestamps',8415,'timestamps','phase03_model_revalidation/model_predictions.csv','nunique(timestamp)','HASH_VERIFIED_HISTORICAL_ARTIFACT','One test timestamp can have multiple model configurations.')
add('R03','6.2','Model configurations',12,'configurations','phase03_model_revalidation/configuration_results.csv','all configured models','HASH_VERIFIED_HISTORICAL_ARTIFACT','Four settings per family.')
for i,r in threshold.iterrows(): add(f'E1T{i+1}','6.2',f"E1 threshold {r['timestamps']} selected timestamps",int(r.timestamps),'timestamps','research_results/e1_threshold_sensitivity.csv',f"threshold == {r['timestamps']}",'HASH_VERIFIED_HISTORICAL_ARTIFACT','Agreement is not calibrated probability, fault confidence, or accuracy.')
for i,r in family.iterrows(): add(f'E1F{i+1}','6.2',f"{r.family}: any/all-four candidate timestamps",f"{int(r.any_config_count)}/{int(r.all_four_count)}",'unique timestamps','research_results/e1_family_comparison.csv',f"family == {r.family}",'HASH_VERIFIED_HISTORICAL_ARTIFACT','Configurations reuse the same test series; not independent samples.')
for cid,name,col,flt in [('E2D','E2 screen evaluations',len(detail),'all reviewed rows'),('E2P','E2 paired comparisons',len(paired),'all reviewed rows'),('E2C','Matched controls',len(controls),'all control entries')]: add(cid,'6.3,6.6',name,col,'rows/controls','research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_multicontext_fault_detail.csv' if cid=='E2D' else ('research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_multicontext_fault_paired.csv' if cid=='E2P' else 'research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_matched_controls.csv'),flt,'HASH_VERIFIED_HISTORICAL_ARTIFACT','Synthetic comparisons; repeated setting rows are not independent events.')
records[-2]['claim']='E2 paired setting-level comparisons'
records[-2]['source_rows_or_filter']='all reviewed rows; 18 settings per underlying pair ID'
records[-2]['interpretation_limit']='2,880 rows represent 160 underlying pair IDs repeated across 18 settings; not independent events.'
add('E2U','6.3,6.6','Unique underlying E2 pair IDs',int(paired.pair_id.nunique()),'pair IDs','research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_multicontext_fault_paired.csv','nunique(pair_id)','HASH_VERIFIED_HISTORICAL_ARTIFACT','Each underlying matched unit is repeated across 18 settings.')
status_changed=int(paired.status_changed_by_injection.astype(str).str.lower().isin(['true','1']).sum())
add('E2S','6.6','Paired E2 status changed after injection',status_changed,'of 2880 setting-level comparisons','research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_multicontext_fault_paired.csv','status_changed_by_injection true','HASH_VERIFIED_HISTORICAL_ARTIFACT','Rows repeat 160 underlying pair IDs across 18 settings; status change does not identify fault truth.')
for i,(cid,condition,status,count,denom) in enumerate([('E2SUP1','synthetic_faulted','SUPPORTING',961,2610),('E2SUP2','clean_same_timestamp','SUPPORTING',691,2880),('E2SUP3','matched_unmodified_control','SUPPORTING',272,1080),('E2UN','synthetic_faulted','UNAVAILABLE',270,2880)]):
    path='research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_multicontext_fault_detail.csv' if condition!='matched_unmodified_control' else 'research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_multicontext_fault_summary.csv'
    add(cid,'6.3,6.6',f'{condition} {status} status',f'{count}/{denom}','screen evaluations',path,f'condition={condition}; status={status}; available denominator where applicable','HASH_VERIFIED_HISTORICAL_ARTIFACT','SUPPORTING means temporal departure, not confirmed fault; controls are not adjudicated clean.')
add('SM01','6.4','Selected synthetic contexts',5,'contexts','research_results/fault_matrix_multicontext_46ae5d119d/context_selection.csv','preselected contexts','REPRODUCIBLE_SYNTHETIC_RESULT','Not a random or representative sample of climate regimes.')
add('SM02','6.4','Fault scenarios',8,'scenarios','research_results/fault_matrix_multicontext_46ae5d119d/campaign_manifest.json','scenario registry','REPRODUCIBLE_SYNTHETIC_RESULT','Injected perturbations cover selected variables and patterns only.')
add('SM03','6.4','Context-scenario combinations',40,'combinations','research_results/fault_matrix_multicontext_46ae5d119d/campaign_manifest.json','5 contexts × 8 scenarios','REPRODUCIBLE_SYNTHETIC_RESULT','Not independent field events.')
add('SM04','6.4','Baseline experimental units',160,'units','research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/synthetic_baseline_response_detail.csv','unique context × scenario × injected timestamp','REPRODUCIBLE_SYNTHETIC_RESULT','Aggregation unit differs from config × label rows.')
for i,r in s.iterrows(): pass
# Per-scenario corrected 8/12 response summary
for j,(_,r) in enumerate(summary[(summary.baseline=='E1_consensus')&(summary.setting=='8/12')].iterrows(),1):
    add(f'SC{j:02d}','6.4,6.5',f"{r.experiment_id} corrected context response mean [min,max]",f"{100*r.mean_context_response_fraction:.1f}; {100*r.minimum_context_response_fraction:.1f}-{100*r.maximum_context_response_fraction:.1f}",'%','research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/synthetic_baseline_response_summary.csv',f"baseline=E1_consensus; setting=8/12; experiment_id={r.experiment_id}",'REPRODUCIBLE_SYNTHETIC_RESULT','Mean across five context response fractions; not field recall or accuracy.')
for i,r in e4.iterrows(): add(f'E4{i+1}','6.7','E4 synthetic direct screen response',f"{100*r.mean_context_response_fraction:.1f}; {100*r.minimum_context_response_fraction:.1f}-{100*r.maximum_context_response_fraction:.1f}",'%','research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/synthetic_baseline_response_summary.csv',f"baseline=E4_physical_screen; experiment_id={r.experiment_id}",'REPRODUCIBLE_SYNTHETIC_RESULT','Injected-label screening response; not hardware diagnosis.')
for i,r in cov.groupby('combination',as_index=False).agg(units=('units','max'), complete=('complete_units','min'),coverage=('coverage_fraction','min')).iterrows(): add(f'AB{i+1}','6.9','Evidence combination availability',f"{int(r.complete)}/{int(r.units)} ({r.coverage:.4f})",'units with evidence','research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/evidence_coverage_ablation_summary.csv',f"combination={r.combination}",'REPRODUCIBLE_SYNTHETIC_RESULT','Coverage only; no outcome-level utility or accuracy.')
add('PAR01','6.10','Prediction parity mismatches',len(mismatch),'of 100980 predictions','research_results/prediction_mismatch_investigation.csv','all rows; Isolation Forest family','UNVERIFIED_OR_UNAVAILABLE','Historical estimator/scaler state and fit provenance missing; saved labels retained.')
add('P1A','3.6,9','Neighbour candidates inspected',4,'candidate stations','research_results/phase1a_station_preflight/PHASE1A_STATION_PREFLIGHT_REPORT.md','Phase 1A inventory metadata review','PROVIDER_REPORTED_METADATA','Observation availability unchecked; no raw observations retrieved.')
add('P1B','3.6,9','Provider/parameter inventory records',179,'records','research_results/phase1b_station_identity/PHASE1B_READINESS_REPORT.md','Phase 1B metadata inventory','PROVIDER_REPORTED_METADATA','Metadata inventory does not establish populated common observation coverage.')
add('P1C','3.6,9','METAR adapter requested period',30,'days','research_results/phase1c_metar_pilot/PHASE1C_PILOT_READINESS_REPORT.md','2025-09-01 through 2025-09-30 proposal','UNVERIFIED_OR_UNAVAILABLE','No observation retrieval; required period unavailable through inspected adapter.')
add('T98','7','Latest repository-documented full test suite',98,'passed; 0 failed; 0 skipped','TESTING_REPORT.md','latest recorded full-suite run after Phase 1A, lines 168-169','SOFTWARE_TEST_RESULT','Software behavior in covered tests only; the 140-passed figure from the request was not corroborated in this checkpoint.')
reg=OUT/'FINAL_EVIDENCE_REGISTER.csv'; pd.DataFrame(records).to_csv(reg,index=False)

(OUT/'FINAL_RESULTS_SUMMARY.md').write_text('''# Final results summary\n\nThis summary is tied to the local Phase 1C source commit `07edecdad90c36b98c0e2ad789f4d5c07bed728e`. Evidence identities are recorded in `FINAL_EVIDENCE_REGISTER.csv`; hashes establish file identity, not scientific provenance.\n\n- **Processed snapshot:** 44,879 rows; 44,849 feature-ready rows. Train/test contain 36,434/8,415 rows with a seven-day temporal gap. The persisted feature matrix contains nine base columns; the model service derives two cyclical month terms at runtime.\n- **Prediction grid:** 100,980 configuration-time records across 12 configurations and 8,415 test timestamps. A later parity investigation lists 42 mismatches, all associated with Isolation Forest; cause remains unresolved.\n- **E1:** 4/12, 6/12, 8/12, 10/12 and 12/12 consensus thresholds select 432, 214, 123, 51 and 15 timestamps. These are candidate counts, not calibrated probabilities or accuracy.\n- **E2:** reviewed outputs contain 6,840 evaluations, 2,880 pairs and 10 matched controls. Status changed in 1,008 pairs; 270 injected missing-block cases became unavailable. Supporting statuses are temporal evidence only.\n- **Synthetic campaign:** five preselected contexts, eight scenarios, 40 context-scenario combinations and 160 corrected context × scenario × injected-timestamp units. At 8/12 E1, corrected mean response ranges by scenario from 0% to 100%, with pronounced between-context variation. These are not field recall estimates.\n- **E4:** direct physical-screen synthetic outcomes detect the injected missing blocks in the reviewed baseline comparison; other modeled injections receive no E4 response in that summary. Rules remain broad screening heuristics.\n- **Coverage ablation:** E1-only and E1+E4 cover 160/160 units; E1+E2 and E1+E2+E4 cover 145/160; E1+E3 and the full E1+E2+E3+E4 combination cover 0/160 because E3 evidence is unavailable. This measures coverage only.\n- **Field evidence:** Phase 1A–1C acquired provider metadata and inspected an adapter, but no real observation rows were retrieved and no empirical E3 comparison was completed.\n''',encoding='utf-8')

(OUT/'FINAL_RESEARCH_LIMITATIONS.md').write_text('''# Research limitations and next work\n\n## Evidence limits\n\n1. The analyzed weather series is a processed historical snapshot. Independent raw-data reconstruction, direct instrument provenance and row-level provider indicators are unavailable.\n2. Station identity remains unresolved for VILD0 and 42099. Candidate inventories do not prove populated, comparable hourly observations; 42105 is conditional and 42101 is an alternative.\n3. The inspected Meteostat METAR adapter did not cover the proposed September 2025 period: its historical horizon began on 16 November 2026 and the inspected Aviation Weather Center integration exposed a 24-hour window. The pilot did not retrieve observations.\n4. There are no independently adjudicated field fault labels or independently verified clean operational labels. No real-world precision, recall, false alarm rate, calibration or operational utility can be estimated.\n5. E3 spatial corroboration is not empirically evaluated. Missing neighboring evidence must remain unavailable, never interpreted as negative evidence.\n6. E2 `SUPPORTING` denotes a temporal departure under a selected screen setting. Matched controls are not adjudicated clean truth, and repeated screen settings are dependent.\n7. Synthetic injections cover eight selected patterns, five preselected contexts and particular variables/magnitudes. They do not establish coverage of field failure modes or representativeness of weather regimes.\n8. The corrected baseline contains 160 experimental units. Its evidence ablation measures availability only, not outcome correctness or decision value.\n9. Forty-two of 100,980 saved prediction cells differ in the Isolation Forest parity investigation. Missing historical estimator/scaler artifacts and fit provenance leave the cause unresolved; historical labels were retained.\n10. Historical model artifacts and scaler provenance are incomplete; the notebook includes exploratory legacy material, and full Colab verification is not demonstrated.\n11. The literature review is a focused narrative synthesis, not a systematic review or exhaustive search.\n12. Physical bounds are broad screening limits and cross-variable checks; they do not diagnose hardware or establish local climatological validity.\n\n## Next work, in order\n\n1. Resolve station identifiers and instrument/provider provenance.\n2. Identify and retrieve traceable historical observations with row-level source and quality metadata.\n3. Validate temporal alignment, missingness, units and common coverage before any spatial comparison.\n4. Independently adjudicate regional events, station faults and operationally acceptable readings.\n5. Evaluate E3 on matched, time-aligned observations and characterize spatial representativeness.\n6. Measure outcome-level utility for evidence combinations, including abstention, with uncertainty intervals and leakage controls.\n7. Conduct broader robustness analyses across stations, seasons, variables, scenarios and acquisition sources.\n8. Resolve or bound the Isolation Forest parity discrepancy and preserve estimator/scaler provenance.\n9. Reassess integrated interpretation only after the independent reference set is available.\n''',encoding='utf-8')

(OUT/'REPRODUCIBILITY_AND_ARTIFACT_REGISTER.md').write_text(f'''# Reproducibility and artifact register\n\n## Source checkpoint\n\n- Repository: local WeatherGuard AI checkout\n- Source branch: `codex/phase1c-controlled-metar-pilot`\n- Source commit: `07edecdad90c36b98c0e2ad789f4d5c07bed728e`\n- Report branch: `codex/one-day-research-report` (local only)\n- Source working tree was clean at report start. The report artifacts are derived from saved files and do not modify historical research outputs.\n\n## Reproduction boundary\n\nThe report recomputes row counts, group summaries, percentages, plots and artifact SHA-256 values from the saved CSV/JSON artifacts. It does not fit models, regenerate predictions, rerun fault campaigns, retrieve provider data or alter historical files. Run `python final_report/build_assets.py` from the repository root to regenerate the report evidence register, summary, limitations and figures. This utility is analysis/report tooling and does not reproduce model fitting.\n\n## Key source artifacts\n\n| Artifact group | Location | Integrity/interpretation |\n|---|---|---|\n| Phase 01 processed data | `verified_phase01/` | Historical manifest and hashes; processed data, no raw provenance reconstruction |\n| Phase 03 predictions | `phase03_model_revalidation/` | Saved prediction grid and integrity manifest; 42 parity mismatches remain unresolved |\n| E1 results | `research_results/e1_*.csv` | Saved candidate/stability summaries, no independent truth labels |\n| E2 reviewed outputs | `research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/` | Reviewed output manifest and status comparisons; synthetic screens |\n| Corrected synthetic baseline | `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/` | Manifest plus integrity sidecar; corrected aggregation and coverage-only ablation |\n| Station acquisition phases | `research_results/phase1a_station_preflight/`, `phase1b_station_identity/`, `phase1c_metar_pilot/` | Provider inventory/adapter inspection; no raw observation retrieval |\n\n## Verification performed\n\nCounts asserted during report asset generation: 44,879 processed rows; 44,849 feature-ready rows; 36,434 training rows; 8,415 test rows; 100,980 prediction rows; 6,840 E2 evaluations; 2,880 paired rows; 10 matched controls; 42 parity mismatch rows. Source file hashes and row filters are recorded claim-by-claim in `FINAL_EVIDENCE_REGISTER.csv`.\n\nA passing artifact hash confirms byte identity against the referenced saved artifact at report generation. It does not establish that the original experiment was scientifically valid, independently reproduced or correctly labeled.\n''',encoding='utf-8')
print(f'Wrote {len(records)} evidence rows and {len(list(FIG.glob("*.png")))} figures')
