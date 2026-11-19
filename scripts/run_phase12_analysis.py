"""Read-only Phase 12 analysis of saved E1-E4 evidence outputs."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src")]
from services.data_service import load_project_data,prediction_wide,sha256_file
from services import evidence_integration as integ
from services.ablation_service import apply_component_subset
from services.phase12_analysis import PHASE12_CONFIGURATIONS,binary_contingency,evidence_profile,timestamp_offset_minutes

def _json(v):
    if isinstance(v,(pd.Timestamp,datetime)): return v.isoformat()
    if isinstance(v,np.integer): return int(v)
    if isinstance(v,np.floating): return float(v) if np.isfinite(v) else None
    if isinstance(v,np.bool_): return bool(v)
    if pd.isna(v): return None
    return str(v)

def run(output_dir=None):
    rid=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out=Path(output_dir) if output_dir else ROOT/"research_results"/"phase12_evidence_contribution"/rid
    if not out.is_absolute(): out=ROOT/out
    if out.exists() and any(out.iterdir()): raise FileExistsError(f"Nonempty output directory: {out}")
    out.mkdir(parents=True,exist_ok=True)
    data,manifest,input_hashes=load_project_data(ROOT)
    observations,predictions=data["observations"],data["predictions"]
    timestamps=prediction_wide(predictions).index.sort_values()
    if len(timestamps)!=8415 or not timestamps.isin(observations.index).all(): raise ValueError("Expected exact saved held-out timestamps (n=8,415)")
    spatial,sources=integ.load_spatial_tables(ROOT)
    historical=[ROOT/"verified_phase01"/n for n in ("model_df.csv","X_train_multi.csv","X_test_multi.csv","phase01_manifest.json")]
    historical += [ROOT/"phase03_model_revalidation"/n for n in ("model_predictions.csv","stability_results_verified.csv","episode_profiles_1h.csv","configuration_results.csv","phase03_integrity_manifest.json","spatial_comparison_42099.csv","spatial_comparison_42101.csv")]
    historical=[p for p in historical if p.is_file()]
    before={str(p.relative_to(ROOT)):sha256_file(p) for p in historical}
    full,records,e3rows=[],[],[]
    for ts in timestamps:
        r=integ.run_integrated_assessment(ts,"VILD0",observations,predictions,data["stability"],data["episodes"],spatial,sources,"temp")
        full.append(r); base=r["baseline_prediction"]; c=r["components"]
        e1,e2,e3,e4=(c[k] for k in ("E1","E2","E3","E4")); d2=e2.get("details") or {}
        flags=e4.get("details") or []; viol=[f for f in flags if not f.get("missing") and f.get("screening_flag")]
        e3d=e3.get("details") or []
        for d in e3d:
            off=timestamp_offset_minutes(d.get("candidate_time"),d.get("station_time"))
            row={"timestamp":ts.isoformat(),"neighbor_station_id":d.get("neighbor_station_id"),
                 "e3_status":e3["execution_status"],"candidate_time":d.get("candidate_time"),
                 "station_time":d.get("station_time"),"offset_minutes":off,
                 "exact_timestamp_match":off==0 if off is not None else False,
                 "matched":bool(d.get("matched",False)),"station_identity_verified":False,
                 "independent_lineage_verified":False,"decision_eligible":False}
            for v in ("temp","dwpt","rhum","wspd","pres","prcp"):
                x=d.get(v+"_difference"); row[v+"_difference"]=None if pd.isna(x) else float(x)
                row[v+"_comparable"]=bool(pd.notna(x))
            e3rows.append(row)
        if not e3d: e3rows.append({"timestamp":ts.isoformat(),"neighbor_station_id":None,"e3_status":e3["execution_status"],"candidate_time":None,"station_time":None,"offset_minutes":None,"exact_timestamp_match":False,"matched":False,"station_identity_verified":False,"independent_lineage_verified":False,"decision_eligible":False})
        votes=int(e1.get("source",{}).get("votes",-1))
        records.append({"timestamp":ts.isoformat(),"baseline_votes":base.get("configuration_votes"),
            "baseline_configurations":base.get("configuration_count"),"baseline_candidate_8_of_12":bool(base.get("candidate_8_of_12")),
            "E1_votes":votes,"E1_status":e1["execution_status"],"E1_result":e1["evidence_result"],
            "E1_derived_from_baseline_votes":votes==base.get("configuration_votes"),
            "E2_status":e2["execution_status"],"E2_result":e2["evidence_result"],
            "E2_supporting":e2["evidence_result"]=="SUPPORTING_EVIDENCE","E2_robust_deviation":d2.get("robust_deviation"),
            "E2_prior_count":d2.get("prior_count"),"E2_sudden_change":d2.get("sudden_change"),"E2_stuck_pattern":d2.get("stuck_pattern"),
            "E4_status":e4["execution_status"],"E4_result":e4["evidence_result"],
            "E4_supporting":e4["evidence_result"]=="SUPPORTING_EVIDENCE",
            "E4_nonmissing_screening_flags":len(viol),"E4_missing_variable_values":sum(bool(f.get("missing")) for f in flags),
            "E3_status":e3["execution_status"],"E3_result":e3["evidence_result"],
            "E3_decision_eligible":e3["decision_eligible"],"E3_indexed_rows":len(e3d),
            "E2_support_agrees_with_baseline":bool(base.get("candidate_8_of_12"))==(e2["evidence_result"]=="SUPPORTING_EVIDENCE"),
            "E4_support_agrees_with_baseline":bool(base.get("candidate_8_of_12"))==(e4["evidence_result"]=="SUPPORTING_EVIDENCE")})
    frame=pd.DataFrame(records)
    for cid in ("E1","E2","E4"):
        frame[cid+"_supporting"]=frame[cid+"_result"].eq("SUPPORTING_EVIDENCE")
        frame[cid+"_available"]=frame[cid+"_status"].eq("AVAILABLE")
    npos=frame[["E1_supporting","E2_supporting","E4_supporting"]].sum(axis=1)
    frame["supporting_component_count"]=npos
    frame["unique_positive_component"]=""
    for cid in ("E1","E2","E4"): frame.loc[(npos==1)&frame[cid+"_supporting"],"unique_positive_component"]=cid
    frame["overlapping_positive_evidence"]=npos.ge(2); frame["no_positive_component_evidence"]=npos.eq(0)
    # Baseline-only, single screens, full E1/E2/E4, and E3 on/off context.
    configs={
      "P0":("Baseline only",()),"P1":("Baseline + E1",("E1",)),
      "P2":("Baseline + E2",("E2",)),"P3":("Baseline + E4",("E4",)),
      "P4":("Baseline + E1 + E2 + E4",("E1","E2","E4")),
      "P5":("Full E1-E4 with descriptive E3",("E1","E2","E3","E4")),
      "P6":("E1 + E2 + E4 without E3",("E1","E2","E4")),
      "L1":("Leave E1 out: E2 + E4",("E2","E4")),
      "L2":("Leave E2 out: E1 + E4",("E1","E4")),
      "L3":("Leave E4 out: E1 + E2",("E1","E2"))}
    sensitivity=[]; sensrows=[]; profile_map={}; explanation_map={}; category_map={}
    for key,(name,included) in configs.items():
        arr=[apply_component_subset(r,included,name) for r in full]
        cats=[x["integrated_assessment"]["category"] for x in arr]
        category_map[key]=cats
        profiles=[]; exps=[]
        for r in arr:
            st={k:r["components"][k]["execution_status"] for k in integ.COMPONENT_IDS}
            res={k:r["components"][k]["evidence_result"] for k in integ.COMPONENT_IDS}
            p=evidence_profile(st,res,included);profiles.append(p)
            exps.append("|".join(f"{k}:{r['components'][k]['execution_status']}:{r['components'][k]['evidence_result']}:{r['components'][k]['explanation']}" for k in included))
            sensrows.append({"configuration_id":key,"timestamp":r["timestamp"],"assessment":r["integrated_assessment"]["category"],"assessment_reason":r["integrated_assessment"]["reason"],**p})
        profile_map[key]=profiles; explanation_map[key]=exps
        cnt=Counter(cats)
        sensitivity.append({"configuration_id":key,"configuration":name,"included_components":"+".join(included) if included else "none",
            "observations":len(arr),
            "mean_available_components":np.mean([p["available_component_count"] for p in profiles]),
            "mean_supporting_components":np.mean([p["supporting_evidence_count"] for p in profiles]),
            "mean_contradictory_components":np.mean([p["contradictory_evidence_count"] for p in profiles]),
            "mean_missing_components":np.mean([p["missing_evidence_count"] for p in profiles]),
            **{z:cnt.get(z,0) for z in ("SUSPICIOUS","INSUFFICIENT_EVIDENCE","NORMAL","ANOMALOUS")}})
    refcats=category_map["P4"]; refprofiles=profile_map["P4"]; refexps=explanation_map["P4"]
    for row in sensitivity:
        key=row["configuration_id"]; cats=category_map[key]
        changes=sum(a!=b for a,b in zip(refcats,cats))
        row["assessment_changes_vs_P4"]=changes
        row["assessment_stability_pct_vs_P4"]=100*(len(cats)-changes)/len(cats)
        row["assessment_changes_vs_P0"]=sum(a!=b for a,b in zip(category_map["P0"],cats))
        row["evidence_profile_changes_vs_P4"]=sum(a!=b for a,b in zip(refprofiles,profile_map[key]))
        row["included_explanation_changes_vs_P4"]=sum(a!=b for a,b in zip(refexps,explanation_map[key]))
    sensitivity=pd.DataFrame(sensitivity); sensobs=pd.DataFrame(sensrows)
    overlap=[]
    for kind in ("supporting","available"):
        for i,a in enumerate(("E1","E2","E4")):
            for b in ("E1","E2","E4")[i+1:]:
                aa=frame[a+"_"+kind]; bb=frame[b+"_"+kind]
                overlap.append({"indicator_type":kind,"component_left":a,"component_right":b,**binary_contingency(aa,bb)})
    for cid in ("E1","E2","E4"):
        overlap.append({"indicator_type":"baseline_candidate","component_left":"BASELINE",
            "component_right":cid,**binary_contingency(frame.baseline_candidate_8_of_12,frame[cid+"_supporting"])})
    overlap=pd.DataFrame(overlap)
    dependency=pd.DataFrame({"timestamp":frame.timestamp,"baseline_votes":frame.baseline_votes,"E1_votes":frame.E1_votes,
        "baseline_candidate_8_of_12":frame.baseline_candidate_8_of_12,"E1_candidate_8_of_12":frame.E1_votes.ge(8),
        "vote_count_equal":frame.baseline_votes.eq(frame.E1_votes),"candidate_flag_equal":frame.baseline_candidate_8_of_12.eq(frame.E1_votes.ge(8)),
        "shared_input":"The same 12 saved configuration is_candidate labels",
        "shared_calculation":"Count positive labels and apply the existing 8-of-12 threshold",
        "independent_E1_input_identified":False,
        "interpretation":"Removing the E1 evidence record while preserving baseline votes cannot remove this shared signal."})
    coverage=[]
    for c in ("E1","E2","E3","E4"):
        status=frame[c+"_status"]; counts=status.value_counts().to_dict()
        positive=frame[c+"_result"].eq("SUPPORTING_EVIDENCE") if c!="E3" else pd.Series(False,index=frame.index)
        coverage.append({"component":c,"observations":len(frame),"available_n":counts.get("AVAILABLE",0),
            "descriptive_only_n":counts.get("DESCRIPTIVE_ONLY",0),
            "missing_n":sum(v for k,v in counts.items() if k in ("UNAVAILABLE","INSUFFICIENT_DATA","ERROR")),
            "not_applicable_n":counts.get("NOT_APPLICABLE",0),"coverage_pct":100*counts.get("AVAILABLE",0)/len(frame),
            "supporting_n":int(positive.sum()),"supporting_pct_all":100*float(positive.mean()),
            "no_detected_evidence_n":int(frame[c+"_result"].eq("NO_DETECTED_EVIDENCE").sum()),
            "missing_is_negative":False})
    coverage=pd.DataFrame(coverage)
    e3=pd.DataFrame(e3rows); valid=e3[e3.neighbor_station_id.notna()]
    offsets=pd.to_numeric(valid.offset_minutes,errors="coerce").dropna()
    e3pairs=[]
    for station,g in valid.groupby("neighbor_station_id"):
        for v in ("temp","dwpt","rhum","wspd","pres","prcp"):
            for alignment,mask in (("exact_timestamp",g.offset_minutes.eq(0)),
                                   ("nonzero_offset",g.offset_minutes.notna() & g.offset_minutes.ne(0)),
                                   ("offset_missing",g.offset_minutes.isna())):
                x=pd.to_numeric(g.loc[mask,v+"_difference"],errors="coerce").dropna()
                e3pairs.append({"neighbor_station_id":station,"variable":v,"alignment_class":alignment,
                    "comparison_rows":int(mask.sum()),"valid_difference_pairs":len(x),
                    "mean_neighbor_minus_primary":float(x.mean()) if len(x) else None,
                    "mean_absolute_difference":float(x.abs().mean()) if len(x) else None,
                    "rmse":float(np.sqrt(np.mean(x**2))) if len(x) else None,
                    "interpretation":"Descriptive only; time alignment and independent lineage are not established."})
    e3pairs=pd.DataFrame(e3pairs)
    dist=Counter(r["integrated_assessment"]["category"] for r in full)
    unique={c:int(frame.unique_positive_component.eq(c).sum()) for c in ("E1","E2","E4")}
    summary={"phase":12,"run_id":out.name,"observations":len(frame),"timestamp_start":str(timestamps.min()),"timestamp_end":str(timestamps.max()),
        "identical_timestamps":True,"timestamp_sha256":hashlib.sha256("\n".join(t.isoformat() for t in timestamps).encode()).hexdigest(),
        "input_sha256":input_hashes,"historical_artifacts_unchanged":before=={str(p.relative_to(ROOT)):sha256_file(p) for p in historical},
        "historical_artifact_sha256":before,
        "baseline_E1_dependency":{"identical_vote_counts":int(dependency.vote_count_equal.sum()),"identical_candidate_flags":int(dependency.candidate_flag_equal.sum()),
            "candidate_n":int(frame.baseline_candidate_8_of_12.sum()),"E1_supporting_n":int(frame.E1_supporting.sum()),"additional_independent_input_identified":False},
        "coverage":coverage.to_dict("records"),"unique_positive_indicators":unique,
        "E4_missing_values_total":int(frame.E4_missing_variable_values.sum()),
        "E4_observations_with_any_missing_variable":int(frame.E4_missing_variable_values.gt(0).sum()),
        "overlapping_positive_n_ge_2":int(frame.overlapping_positive_evidence.sum()),"no_positive_n":int(frame.no_positive_component_evidence.sum()),
        "overlap":overlap.to_dict("records"),"sensitivity":sensitivity.to_dict("records"),"assessment_distribution":dict(dist),
        "E3":{"observations_descriptive":int(frame.E3_status.eq("DESCRIPTIVE_ONLY").sum()),"observations_insufficient":int(frame.E3_status.eq("INSUFFICIENT_DATA").sum()),
            "indexed_rows":len(valid),"exact_timestamp_rows":int((offsets==0).sum()),"nonzero_offset_rows":int((offsets!=0).sum()),
            "missing_offset_rows":int(valid.offset_minutes.isna().sum()) if len(valid) else 0,
            "median_absolute_offset_minutes":float(offsets.abs().median()) if len(offsets) else None,
            "neighbor_ids":sorted(valid.neighbor_station_id.dropna().unique().tolist()),"decision_eligible":False,"independent_lineage_verified":False},
        "statistical_methods":{"contingency_agreement":"paired binary indicators on identical timestamps","jaccard":"positive overlap; undefined for empty union",
            "phi":"undefined for constant marginals; association is descriptive, not causal","accuracy_precision_recall_f1":"not computed; independent labels unavailable"},
        "limitations":["E1 reuses the same 12 saved prediction flags as baseline.","E2/E4 are exploratory screens on processed observations, not calibrated reliability estimates.","E3 candidate-time indexing does not prove synchronous independent corroboration.","Independent event/fault labels and verified station lineage remain unavailable; ANOMALY is not FAULT."]}
    if not summary["historical_artifacts_unchanged"]: raise RuntimeError("Historical research artifacts changed during analysis")
    frame.to_csv(out/"phase12_observation_level_results.csv",index=False)
    dependency.to_csv(out/"phase12_component_dependency.csv",index=False)
    overlap.to_csv(out/"phase12_component_overlap.csv",index=False)
    coverage.to_csv(out/"phase12_evidence_coverage.csv",index=False)
    sensobs.to_csv(out/"phase12_sensitivity_results.csv",index=False)
    e3.to_csv(out/"phase12_e3_descriptive_results.csv",index=False)
    e3pairs.to_csv(out/"phase12_e3_pairwise_measurements.csv",index=False)
    (out/"phase12_summary.json").write_text(json.dumps(summary,indent=2,default=_json)+"\n",encoding="utf-8")
    figures(out,coverage,overlap,frame,sensitivity,e3,summary)
    (out/"PHASE12_RESEARCH_REPORT.md").write_text(report(summary,coverage,overlap,sensitivity),encoding="utf-8")
    return out

def figures(out,cov,ov,obs,sens,e3,s):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.titleweight":"bold"})
    pal={"E1":"#176B87","E2":"#2A9D8F","E3":"#E9A23B","E4":"#7656A5"}
    fig,ax=plt.subplots(figsize=(8,4.6)); x=np.arange(4)
    ax.bar(x,cov.available_n,color=[pal[c] for c in cov.component],label="Available")
    ax.bar(x,cov.descriptive_only_n,bottom=cov.available_n,color=pal["E3"],label="Descriptive only")
    ax.bar(x,cov.missing_n,bottom=cov.available_n+cov.descriptive_only_n,color="#C5CDD5",label="Missing / insufficient")
    ax.set_xticks(x,cov.component);ax.set_ylabel("Observations (n)");ax.set_title("Evidence availability by component (n=8,415)")
    ax.legend(frameon=False,ncols=3);ax.grid(axis="y",alpha=.2);fig.tight_layout();fig.savefig(out/"fig01_evidence_coverage.png",dpi=180);plt.close(fig)
    order=("E1","E2","E4");m=np.full((3,3),np.nan)
    for i,a in enumerate(order):
        for j,b in enumerate(order):
            if i==j: m[i,j]=1 if obs[a+"_supporting"].any() else np.nan
            else:
                aa,bb=sorted((a,b),key=order.index);r=ov[(ov.indicator_type=="supporting")&(ov.component_left==aa)&(ov.component_right==bb)]
                m[i,j]=r.jaccard_positive.iloc[0] if len(r) else np.nan
    fig,ax=plt.subplots(figsize=(5.3,4.4));im=ax.imshow(np.ma.masked_invalid(m),vmin=0,vmax=1,cmap="Blues")
    ax.set_xticks(range(3),order);ax.set_yticks(range(3),order);ax.set_title("Jaccard overlap of supporting evidence (n=8,415)")
    for i in range(3):
        for j in range(3):ax.text(j,i,"undefined" if np.isnan(m[i,j]) else f"{m[i,j]:.3f}",ha="center",va="center")
    fig.colorbar(im,ax=ax,label="Jaccard similarity");fig.tight_layout();fig.savefig(out/"fig02_component_overlap.png",dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.7,4.5));ax.scatter(obs.baseline_votes,obs.E1_votes,s=8,alpha=.3,color=pal["E1"])
    ax.plot([-.5,12.5],[-.5,12.5],"--",color="#B23A48",label="Identity")
    ax.set(xlim=(-.5,12.5),ylim=(-.5,12.5),xlabel="Baseline candidate votes (of 12)",ylabel="E1 votes (of 12)",title="E1-baseline shared vote signal (n=8,415)")
    ax.legend(frameon=False);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/"fig03_e1_baseline_dependency.png",dpi=180);plt.close(fig)
    tab=pd.crosstab(obs.E2_supporting,obs.E4_supporting).reindex(index=[False,True],columns=[False,True],fill_value=0)
    fig,ax=plt.subplots(figsize=(5.6,4.4));im=ax.imshow(tab.values,cmap="Purples");ax.set_xticks([0,1],["No E4 support","E4 support"]);ax.set_yticks([0,1],["No E2 support","E2 support"])
    ax.set_title("E2-E4 support contingency (n=8,415)")
    for i in range(2):
        for j in range(2):ax.text(j,i,f"{tab.values[i,j]:,}",ha="center",va="center",fontsize=12)
    fig.colorbar(im,ax=ax,label="Observations");fig.tight_layout();fig.savefig(out/"fig04_e2_e4_agreement.png",dpi=180);plt.close(fig)
    xx=np.arange(len(sens));fig,ax=plt.subplots(figsize=(8,4.5))
    ax.bar(xx-.18,sens.mean_supporting_components,.36,label="Mean supporting",color="#2A9D8F")
    ax.bar(xx+.18,sens.mean_missing_components,.36,label="Mean missing included",color="#BAC3CC")
    ax.set_xticks(xx,sens.configuration_id);ax.set_ylabel("Components / observation");ax.set_title("Evidence profiles by configuration (n=8,415)")
    ax.legend(frameon=False);ax.grid(axis="y",alpha=.2);fig.tight_layout();fig.savefig(out/"fig05_evidence_profiles.png",dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.7,4.3));ax.bar(sens.configuration_id,sens.assessment_changes_vs_P0,color="#B23A48")
    ax.set_ylabel("Changed assessments (n)");ax.set_title("Assessment stability under existing rule (n=8,415)");ax.grid(axis="y",alpha=.2)
    fig.tight_layout();fig.savefig(out/"fig06_assessment_stability.png",dpi=180);plt.close(fig)
    offs=pd.to_numeric(e3.offset_minutes,errors="coerce").dropna();fig,ax=plt.subplots(figsize=(7.5,4.3))
    if len(offs):ax.hist(offs,bins=min(30,max(5,offs.nunique())),color=pal["E3"],edgecolor="white");ax.axvline(0,color="#333",ls="--",label="Exact match")
    else:ax.text(.5,.5,"No offsets",ha="center",transform=ax.transAxes)
    ax.set(xlabel="Neighbor timestamp minus candidate timestamp (minutes)",ylabel="Comparison rows (n)",title=f"E3 timestamp offsets (n={len(offs)}, exact={(offs==0).sum()})")
    ax.legend(frameon=False);ax.grid(axis="y",alpha=.2);fig.tight_layout();fig.savefig(out/"fig07_e3_timestamp_offsets.png",dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.5,4.3));x=np.arange(4)
    ax.bar(x,cov.missing_n,color="#AAB4C0",label="Missing / insufficient")
    ax.bar(x,cov.descriptive_only_n,bottom=cov.missing_n,color=pal["E3"],label="Descriptive only")
    ax.set_xticks(x,cov.component);ax.set_ylabel("Observations (n)");ax.set_title("Component missingness (n=8,415; not negative evidence)")
    ax.legend(frameon=False);ax.grid(axis="y",alpha=.2);fig.tight_layout();fig.savefig(out/"fig08_component_missingness.png",dpi=180);plt.close(fig)

def report(s,cov,ov,sens):
    dep=s["baseline_E1_dependency"];e=s["E3"]
    cv="\n".join(f"| {r.component} | {r.available_n} | {r.descriptive_only_n} | {r.missing_n} | {r.supporting_n} |" for _,r in cov.iterrows())
    pr=ov[ov.indicator_type.isin(["supporting","baseline_candidate"])]
    pv="\n".join(f"| {r.indicator_type} | {r.component_left} | {r.component_right} | {r.both_positive} | {r.left_only} | {r.right_only} | {r.agreement_pct if pd.notna(r.agreement_pct) else 'undefined'} | {r.jaccard_positive if pd.notna(r.jaccard_positive) else 'undefined'} | {r.phi if pd.notna(r.phi) else 'undefined'} |" for _,r in pr.iterrows())
    sv="\n".join(f"| {r.configuration_id} | {r.configuration} | {r.assessment_changes_vs_P0} | {r.assessment_changes_vs_P4} | {r.evidence_profile_changes_vs_P4} | {r.included_explanation_changes_vs_P4} | {r.mean_available_components:.3f} | {r.mean_supporting_components:.3f} | {r.mean_missing_components:.3f} |" for _,r in sens.iterrows())
    return f"""# Phase 12 — Evidence Contribution, Dependency and Sensitivity Analysis

Run: {s['run_id']}  
Observations: {s['observations']:,} identical held-out timestamps  
Period: {s['timestamp_start']} to {s['timestamp_end']}  
Scope: saved artifacts only; no model retraining, threshold tuning, or external data.

## Method

Loaded integrity-verified Phase 01 data and Phase 03 predictions, then ran the existing adapters on the exact saved timestamps. Ablations preserve baseline predictions and mask evidence only. E3 remained decision-ineligible. Historical input hashes were checked before and after; unchanged: {s['historical_artifacts_unchanged']}.

Paired binary contingency, agreement, Jaccard and phi summarize matched indicators. Jaccard is undefined when the positive union is empty; phi is undefined for constant marginals. These statistics describe association, not causation or independence. Accuracy, precision, recall and F1 are unavailable without independent adjudicated labels.

## Evidence coverage

| Component | Available | Descriptive only | Missing / insufficient | Supporting |
|---|---:|---:|---:|---:|
{cv}

![Evidence coverage](fig01_evidence_coverage.png)

## E1 dependency

Baseline and E1 vote counts were identical for {dep['identical_vote_counts']:,}/{s['observations']:,} observations; candidate flags matched for {dep['identical_candidate_flags']:,}/{s['observations']:,}. E1 summarizes the same 12 saved labels and same 8/12 screen. No additional independent input is identified. Removing its evidence record while preserving baseline necessarily retains that signal.

![E1 dependency](fig03_e1_baseline_dependency.png)

## E2 and E4

E2 exposes prior-history temporal screening; E4 exposes broad physical, missingness, and cross-variable screens. These can change evidence profiles and explanations without changing category. Both use processed primary-station data and are not independent calibrated reliability estimates.

E2 produced {int(cov.loc[cov.component=='E2','supporting_n'].iloc[0]):,} temporal support flags. E4 produced {int(cov.loc[cov.component=='E4','supporting_n'].iloc[0]):,} nonmissing screening flags. Its details recorded {s['E4_missing_values_total']:,} missing values in {s['E4_observations_with_any_missing_variable']:,} observations in this evaluated window.

| Indicator pair type | Left | Right | Both positive | Left only | Right only | Agreement % | Jaccard | Phi |
|---|---|---|---:|---:|---:|---:|---:|---:|
{pv}

![E2-E4 contingency](fig04_e2_e4_agreement.png)

![Evidence profiles](fig05_evidence_profiles.png)

## Sensitivity

| ID | Configuration | Category changes vs P0 | Category changes vs P4 | Profile changes vs P4 | Explanation changes vs P4 | Mean available | Mean supporting | Mean missing |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{sv}

![Assessment stability](fig06_assessment_stability.png)

Zero category changes follow from the current rule: category comes from the unchanged baseline candidate screen; E2/E4 do not vote and E3 cannot affect decisions. Category stability does not mean evidence-profile stability.

## E3 descriptive spatial context

E3 had descriptive comparisons for {e['observations_descriptive']:,} observations and insufficient evidence for {e['observations_insufficient']:,}. There were {e['indexed_rows']:,} candidate-indexed neighbor rows: {e['exact_timestamp_rows']:,} exact timestamps, {e['nonzero_offset_rows']:,} nonzero offsets, {e['missing_offset_rows']:,} missing offsets; median absolute offset {e['median_absolute_offset_minutes']} minutes. Neighbor IDs: {', '.join(e['neighbor_ids']) or 'none'}. Independent lineage verified: {e['independent_lineage_verified']}. Candidate indexing is not proof of alignment or independent corroboration.

![E3 offsets](fig07_e3_timestamp_offsets.png)

Variable-wise valid pair counts, mean differences, absolute differences, and RMSE are separated into exact timestamp, nonzero-offset, and missing-offset groups in phase12_e3_pairwise_measurements.csv. The reported difference units inherit the source fields; asynchronous comparisons remain descriptive.

## Research conclusions

1. E1 supplies no independently identified input beyond the saved baseline vote; its information is composition/explanation of the same signal.
2. E2 contributes temporal screening output, but its incremental predictive validity is untested.
3. E4 contributes broad physical screening and missingness information, not a fault/event diagnosis.
4. E2/E4 paired association is listed above; shared processed inputs mean independence is unsupported.
5. Zero decision changes are explained by baseline-only categorization and E3 decision-ineligibility.
6. The integration records components but the final category hides additive evidence profile. This analysis quantifies profiles without changing the engine.
7. E3 adds candidate-indexed descriptive comparisons only; no independent corroboration is validated.
8. Independent labels, station lineage and calibrated thresholds are missing, preventing predictive-performance claims.
9. Next: acquire provenance-verified independent station data, pre-register event adjudication, and evaluate incremental value on independent events/stations.

Limitations: E2/E4 are exploratory; E3 identity, lineage and timestamp alignment are unresolved. ANOMALY ≠ FAULT; missing evidence is not normal evidence.

Re-run using python scripts/run_phase12_analysis.py. Outputs: phase12_observation_level_results.csv, phase12_component_dependency.csv, phase12_component_overlap.csv, phase12_evidence_coverage.csv, phase12_sensitivity_results.csv, phase12_e3_descriptive_results.csv, phase12_e3_pairwise_measurements.csv, phase12_summary.json, and eight PNG figures in this timestamped output directory.
"""

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output-dir",type=Path,default=None)
    print(run(p.parse_args().output_dir))
