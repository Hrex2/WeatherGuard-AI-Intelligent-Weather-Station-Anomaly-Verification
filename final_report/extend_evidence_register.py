from pathlib import Path
import hashlib
import pandas as pd

root=Path(__file__).resolve().parent.parent
register=root/'final_report/FINAL_EVIDENCE_REGISTER.csv'
df=pd.read_csv(register)
commit='07edecdad90c36b98c0e2ad789f4d5c07bed728e'

def sha(rel):
    h=hashlib.sha256()
    with (root/rel).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

rows=[]
def add(cid,section,claim,value,unit,source,filter_,status,limit):
    rows.append({'claim_id':cid,'report_section':section,'claim':claim,'numeric_value':value,
                 'unit':unit,'source_file':source,'source_commit':commit,'source_hash':sha(source),
                 'source_rows_or_filter':filter_,'verification_status':status,'interpretation_limit':limit})

phase='verified_phase01/model_df.csv'
manifest='verified_phase01/phase01_manifest.json'
data=pd.read_csv(root/phase)
add('D07','4.1','Predictor count after deterministic runtime month features',11,'predictors','services/model_service.py','FEATURE_ORDER; six base weather variables + three historical features + month_sin/month_cos','HASH_VERIFIED_HISTORICAL_ARTIFACT','Two month terms are constructed at runtime; this is the saved service protocol, not a raw stored matrix width.')
add('D08','4.1','Base meteorological variable count',6,'variables',phase,'temp, dwpt, rhum, prcp, wspd, pres','HASH_VERIFIED_HISTORICAL_ARTIFACT','Processed snapshot; original instrument/provider provenance is not reconstructed.')
add('D09','4.1','Historical engineered temperature feature count',3,'features',phase,'temp_change_1h, temp_rolling_mean_6h, temp_deviation_6h','HASH_VERIFIED_HISTORICAL_ARTIFACT','Feature parity does not establish raw-data truth.')
add('D10','4.1','Missing cells in processed model snapshot',int(data.isna().sum().sum()),'cells',phase,'all cells','HASH_VERIFIED_HISTORICAL_ARTIFACT','Aggregate missingness; not an operational sensor-fault count.')
add('D11','4.1','Missing precipitation cells in processed snapshot',int(data['prcp'].isna().sum()),'cells',phase,'column prcp; isna()','HASH_VERIFIED_HISTORICAL_ARTIFACT','Saved preprocessing imputes retained precipitation gaps with training median.')
add('D12','4.1','Processed snapshot time span','2021-01-05 19:30 to 2026-03-09 23:30','Asia/Kolkata timestamps',manifest,'datasets.model_df.start and datasets.model_df.end','HASH_VERIFIED_HISTORICAL_ARTIFACT','Recorded timestamps in a processed snapshot; source provenance is not independently reconstructed.')

configs=pd.read_csv(root/'phase03_model_revalidation/configuration_results.csv')
for i,(family,count) in enumerate(configs.groupby('family').configuration.nunique().items(),1):
    add(f'MF{i}','5.1,7.1',f'{family} configuration count',int(count),'configurations','phase03_model_revalidation/configuration_results.csv',f'family == {family}; distinct configuration','HASH_VERIFIED_HISTORICAL_ARTIFACT','Configurations share a saved test series and are not independent datasets.')
settings={
 'IsolationForest':'contamination = 0.01, 0.02, 0.03, 0.05',
 'LocalOutlierFactor':'n_neighbors = 10, 20, 30, 50',
 'OneClassSVM':'nu = 0.01, 0.02, 0.03, 0.05'}
for i,(family,value) in enumerate(settings.items(),1):
    add(f'MS{i}','5.1,14.1',f'{family} saved configuration values',value,'parameter settings','phase03_model_revalidation/configuration_results.csv',f'family == {family}','HASH_VERIFIED_HISTORICAL_ARTIFACT','Parameter settings do not establish independent model fitting or current model quality.')

thresholds=pd.read_csv(root/'research_results/e1_threshold_sensitivity.csv')
for i,row in thresholds.iterrows():
    add(f'E1P{i+1}','7.2',f"E1 threshold {row['timestamps']} candidate share of held-out timestamps",round(float(row.pct_of_test_timestamps),2),'percent of 8,415 timestamps','research_results/e1_threshold_sensitivity.csv',f"threshold == {row['timestamps']}; pct_of_test_timestamps",'HASH_VERIFIED_HISTORICAL_ARTIFACT','Percentage is descriptive candidate prevalence without independent reference labels.')

e2path='research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/e2_multicontext_fault_detail.csv'
e2=pd.read_csv(root/e2path)
missing_unavailable=int(((e2.condition=='synthetic_faulted')&(e2.experiment_id=='TEMP_MISSING_BLOCK')&(e2.status=='UNAVAILABLE')).sum())
assert missing_unavailable==270
add('E2M','7.3,7.6','Unavailable faulted E2 evaluations tied to missing-block injection',missing_unavailable,'setting-level evaluations',e2path,'condition == synthetic_faulted; experiment_id == TEMP_MISSING_BLOCK; status == UNAVAILABLE','HASH_VERIFIED_HISTORICAL_ARTIFACT','Unavailable reflects insufficient temporal history; it is not a negative or positive fault classification.')
for idx,(condition,status,count) in enumerate([
 ('clean_same_timestamp','NO_DETECTED_EVIDENCE',2168),('clean_same_timestamp','SUPPORTING',691),('clean_same_timestamp','CONFLICTING',21),
 ('synthetic_faulted','NO_DETECTED_EVIDENCE',1510),('synthetic_faulted','SUPPORTING',961),('synthetic_faulted','CONFLICTING',139),('synthetic_faulted','UNAVAILABLE',270),
 ('matched_unmodified_control','NO_DETECTED_EVIDENCE',792),('matched_unmodified_control','SUPPORTING',272),('matched_unmodified_control','CONFLICTING',16)],1):
    actual=int(((e2.condition==condition)&(e2.status==status)).sum())
    assert actual==count,(condition,status,actual,count)
    add(f'E2STAT{idx:02d}','7.3,7.6',f'E2 {condition}: {status}',actual,'setting-level screen evaluations',e2path,f'condition == {condition}; status == {status}','HASH_VERIFIED_HISTORICAL_ARTIFACT','Repeated settings are dependent; SUPPORTING means temporal departure, not a confirmed fault.')
add('E2CFG','5.2,6.3','E2 temporal screen settings','2 modes; windows 3, 6, 12; robust-z 2.5, 3.5, 4.5','settings','research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/synthetic_e2_setting_sensitivity.csv','all saved setting rows','HASH_VERIFIED_HISTORICAL_ARTIFACT','Setting-level comparisons repeat underlying timestamps and do not constitute independent episodes.')
add('P1A2','4.4','Station/provider identities reviewed in Phase 1A',5,'identities','research_results/phase1a_station_preflight/PHASE1A_STATION_PREFLIGHT_REPORT.md','Phase 1A station candidate inventory','PROVIDER_REPORTED_METADATA','Metadata review only; individual observation availability remained unchecked.')
add('P1C2','4.4','Requested METAR parameter count',5,'parameters','research_results/phase1c_metar_pilot/PHASE1C_PILOT_READINESS_REPORT.md','temp, rhum, wspd, wdir, pres','UNVERIFIED_OR_UNAVAILABLE','No observations were retrieved; listed parameters are a proposed retrieval specification.')
add('P1C3','4.4','Phase 1C observations retrieved',0,'rows','research_results/phase1c_metar_pilot/PHASE1C_PILOT_READINESS_REPORT.md','requested 2025-09 period; provider preflight refused before request','UNVERIFIED_OR_UNAVAILABLE','No empirical E3 comparison can be made from this pilot.')

manifest_path='research_results/fault_matrix_multicontext_46ae5d119d/campaign_manifest.json'
for i,(scenario,variable,description) in enumerate([
 ('TEMP_POINT_SPIKE','temp','+10 for one timestamp'),('TEMP_POINT_DROP','temp','-10 for one timestamp'),
 ('TEMP_PERSISTENT_OFFSET','temp','+5 across six observations'),('TEMP_STUCK_SENSOR','temp','constant across six observations'),
 ('TEMP_GRADUAL_DRIFT','temp','0 to +5 across six observations'),('TEMP_MISSING_BLOCK','temp','three missing observations'),
 ('TEMP_INTERMITTENT_NOISE','temp','noise standard deviation 2 across six observations'),
 ('DEWPOINT_TEMP_INCONSISTENCY','dwpt','+20 across three observations')],1):
    add(f'SYN{i:02d}','6.2,14.2',f'Synthetic scenario {scenario}',f'{variable}: {description}','injection definition',manifest_path,f'scenarios[experiment_id == {scenario}]','REPRODUCIBLE_SYNTHETIC_RESULT','Controlled perturbation definition only; not a real fault distribution.')

campaign_report='MULTICONTEXT_FAULT_MATRIX_REPORT.md'
for i,(scenario,value) in enumerate([
 ('TEMP_POINT_SPIKE','0.850 (0.667–1.000)'),('TEMP_POINT_DROP','0.800 (0.667–0.917)'),
 ('TEMP_PERSISTENT_OFFSET','0.231 (0.042–0.361)'),('TEMP_STUCK_SENSOR','0.081 (0.000–0.319)'),
 ('TEMP_GRADUAL_DRIFT','0.019 (0.000–0.056)'),('TEMP_MISSING_BLOCK','0.167 (0.000–0.333)'),
 ('TEMP_INTERMITTENT_NOISE','0.164 (0.000–0.292)'),('DEWPOINT_TEMP_INCONSISTENCY','0.717 (0.667–0.806)')],1):
    add(f'CFGSC{i:02d}','7.4',f'Earlier campaign configuration-by-injected-timestamp response for {scenario}',value,'mean (range) fraction','MULTICONTEXT_FAULT_MATRIX_REPORT.md',f'scenario summary table; experiment_id == {scenario}','REPRODUCIBLE_SYNTHETIC_RESULT','Different aggregation from corrected context-level E1 consensus means; not field performance or recall.')
for i,(scenario,family,value,filter_) in enumerate([
 ('TEMP_POINT_DROP','LOF and One-Class SVM','1.00 in every context','family scenario comparison'),
 ('TEMP_POINT_DROP','Isolation Forest','0.40 mean across contexts','family scenario comparison'),
 ('TEMP_POINT_SPIKE','LOF and One-Class SVM','1.00 mean across contexts','family scenario comparison'),
 ('TEMP_POINT_SPIKE','Isolation Forest','0.00–1.00 across contexts','family scenario comparison'),
 ('TEMP_MISSING_BLOCK','Isolation Forest','0.00 mean','family scenario comparison'),
 ('TEMP_MISSING_BLOCK','LOF','0.50 mean','family scenario comparison'),
 ('TEMP_MISSING_BLOCK','One-Class SVM','0.00 mean','family scenario comparison')],1):
    add(f'FAMSC{i:02d}','7.5',f'Campaign family response for {scenario} / {family}',value,'synthetic response fraction',campaign_report,filter_,'REPRODUCIBLE_SYNTHETIC_RESULT','Five preselected contexts and one shared local fit; not population performance.')

quality='src/weather_research/quality.py'
for i,(variable,bounds,unit) in enumerate([
 ('temp','-90 to 60','°C'),('dwpt','-100 to 45','°C'),('rhum','0 to 100','%'),
 ('prcp','0 to 1000','stored precipitation units'),('wspd','0 to 150','stored wind-speed units'),
 ('pres','800 to 1100','stored pressure units')],1):
    add(f'E4B{i}','5.1,7.7',f'E4 broad screening bounds for {variable}',bounds,unit,quality,f'DEFAULT_SCREENING_BOUNDS[{variable}]','HASH_VERIFIED_HISTORICAL_ARTIFACT','Broad implementation screening limits; not local climatological validation, sensor calibration, or hardware diagnosis.')

testing='TESTING_REPORT.md'
for cid,count,filter_ in [('T84',84,'Phase 0 checkpoint full-suite run'),('T31',31,'older package regression summary')]:
    add(cid,'8.3,14.4',f'Repository-documented test suite count ({filter_})',count,'passed; 0 failed; 0 skipped',testing,filter_,'SOFTWARE_TEST_RESULT','Software regression evidence only; not field validation or anomaly-detection accuracy.')

existing=set(df.claim_id.astype(str))
rows=[r for r in rows if r['claim_id'] not in existing]
df=pd.concat([df,pd.DataFrame(rows)],ignore_index=True)
# Normalize the E2 paired-row units introduced during the first audit.
df.loc[df.claim_id.eq('E2P'),'unit']='setting-level rows'
df.to_csv(register,index=False)
print(f'Added {len(rows)} evidence rows; total {len(df)}')
