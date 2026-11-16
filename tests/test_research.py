import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from weather_research.features import add_segments, engineer_features
from weather_research.preprocessing import chronological_split, prepare_train_test
from weather_research.models import default_model_configs, fit_predict_configurations, stability_summary
from weather_research.temporal import build_episodes, episode_gap_sensitivity
from weather_research.faults import inject_fault, evaluate_injection, inject_fault_with_feature_recompute
from weather_research.quality import physical_quality_flags
from weather_research.spatial import spatial_evidence, compare_spatial_values
from weather_research.evidence import classify_evidence
from weather_research.experiments import (paired_permutation_bootstrap, matched_episode_values,
                                          block_length_sensitivity)
from weather_research.audit import phase01_integrity_audit


def sample_frame(n=18):
    idx = pd.date_range("2025-01-01", periods=n, freq="h", tz="Asia/Kolkata")
    return pd.DataFrame({"temp": np.arange(n, dtype=float), "dwpt": np.arange(n)-5,
                         "rhum": np.repeat(50.0,n), "prcp": np.zeros(n),
                         "wspd": np.repeat(4.0,n), "pres": np.repeat(1000.0,n)}, index=idx)


class TestFeatureEngineering(unittest.TestCase):
    def test_grouped_diff_and_shifted_six_observation_mean(self):
        frame=sample_frame(10); frame["segment_id"]=0
        out=engineer_features(frame)
        self.assertTrue(pd.isna(out.iloc[0]["temp_change_row"]))
        self.assertTrue(pd.isna(out.iloc[5]["temp_rolling_mean_6obs"]))
        self.assertEqual(out.iloc[6]["temp_rolling_mean_6obs"],2.5)
        self.assertEqual(out.iloc[6]["temp_deviation_6obs"],3.5)
        self.assertEqual(out.iloc[6]["temp_change_1h"],1.0)
        pd.testing.assert_frame_equal(frame, sample_frame(10).assign(segment_id=0))

    def test_segment_boundary_and_irregular_gap_mask_strict_hour_change(self):
        frame=sample_frame(9); frame.loc[frame.index[5]:,"segment_id"]=1
        frame=frame.drop(frame.index[7])
        out=engineer_features(frame)
        self.assertTrue(pd.isna(out.iloc[5]["temp_change_row"]))
        self.assertTrue(pd.isna(out.iloc[7]["temp_change_1h"]))

    def test_missing_segment_ids_follow_dropna_groupby(self):
        frame=sample_frame(9); frame["segment_id"]=0; frame.iloc[3,frame.columns.get_loc("segment_id")]=np.nan
        out=engineer_features(frame)
        self.assertTrue(out.iloc[3]["temp_change_row"] != out.iloc[3]["temp_change_row"])
        self.assertTrue(out.iloc[3]["temp_rolling_mean_6obs"] != out.iloc[3]["temp_rolling_mean_6obs"])

    def test_segments_from_timestamp_gaps(self):
        frame=sample_frame(8).drop(sample_frame(8).index[4])
        out=add_segments(frame)
        self.assertNotEqual(out.iloc[3].segment_id,out.iloc[4].segment_id)


class TestPreprocessing(unittest.TestCase):
    def test_chronological_split_and_train_only_median(self):
        frame=sample_frame(10); frame.loc[frame.index[1],"prcp"]=np.nan
        frame.loc[frame.index[8],"prcp"]=10000.0
        train,test=chronological_split(frame,frame.index[6])
        xtr,xte,meta=prepare_train_test(train,test,["prcp"])
        self.assertEqual(meta["medians"]["prcp"],0.0)
        self.assertEqual(xtr.iloc[1,0],0.0)
        self.assertEqual(xte.loc[frame.index[8],"prcp"],10000.0)
        self.assertFalse(set(train.index)&set(test.index))

    def test_no_raw_mutation_and_overlap_rejected(self):
        frame=sample_frame(8); original=frame.copy(deep=True)
        train,test=chronological_split(frame,frame.index[4])
        prepare_train_test(train,test,["temp"])
        pd.testing.assert_frame_equal(frame,original)
        with self.assertRaises(ValueError): prepare_train_test(frame.iloc[:5],frame.iloc[4:],["temp"])

    def test_phase01_audit_feature_split_and_train_only_precipitation(self):
        model=sample_frame(20); model["segment_id"]=0
        model["temp_change_1h"]=model.groupby("segment_id").temp.diff()
        model["temp_rolling_mean_6h"]=model.groupby("segment_id").temp.transform(
            lambda s:s.shift(1).rolling(6,min_periods=6).mean())
        model["temp_deviation_6h"]=model.temp-model.temp_rolling_mean_6h
        model.iloc[8,model.columns.get_loc("prcp")]=np.nan
        model.iloc[14,model.columns.get_loc("prcp")]=np.nan
        features=["temp","dwpt","rhum","prcp","wspd","pres",
                  "temp_change_1h","temp_rolling_mean_6h","temp_deviation_6h"]
        prepared=model.dropna(subset=["temp_change_1h","temp_rolling_mean_6h","temp_deviation_6h"])[features].copy()
        cutoff=model.index[12]
        tr=prepared.loc[prepared.index<cutoff].copy(); te=prepared.loc[prepared.index>=cutoff].copy()
        median=model.loc[model.index.intersection(tr.index),"prcp"].median()
        prepared["prcp"]=prepared.prcp.fillna(median); tr["prcp"]=tr.prcp.fillna(median); te["prcp"]=te.prcp.fillna(median)
        report=phase01_integrity_audit(model,prepared,tr,te,split_boundary=cutoff)
        self.assertTrue(report["phase01_passed"])
        self.assertEqual(len(report["precipitation_retained_timestamps"]),2)
        self.assertTrue(report["precipitation_imputation"].matches_training_median.all())
        self.assertTrue(report["split_report"].passed.all())
        self.assertEqual(len(report["excluded_model_rows_and_reasons"]),6)
        self.assertEqual(len(report["physical_summary"]),6)

    def test_phase01_audit_detects_corrupted_feature(self):
        model=sample_frame(18); model["segment_id"]=0
        model["temp_change_1h"]=model.groupby("segment_id").temp.diff()
        model["temp_rolling_mean_6h"]=model.groupby("segment_id").temp.transform(
            lambda s:s.shift(1).rolling(6,min_periods=6).mean())
        model["temp_deviation_6h"]=model.temp-model.temp_rolling_mean_6h
        model.iloc[8,model.columns.get_loc("temp_deviation_6h")]+=0.5
        features=["temp","dwpt","rhum","prcp","wspd","pres",
                  "temp_change_1h","temp_rolling_mean_6h","temp_deviation_6h"]
        prepared=model.dropna(subset=list(features[6:]))[features]
        cutoff=model.index[10]
        tr=prepared.loc[prepared.index<cutoff].copy(); te=prepared.loc[prepared.index>=cutoff].copy()
        report=phase01_integrity_audit(model,prepared,tr,te,split_boundary=cutoff)
        self.assertFalse(report["phase01_passed"])
        self.assertGreater(report["feature_report"].mismatch_count.sum(),0)


class TestModelAndTemporal(unittest.TestCase):
    def test_model_predictions_timestamp_aligned_and_stability(self):
        frame=sample_frame(60); train=frame.iloc[:45]; test=frame.iloc[45:]
        configs=[{"family":"IsolationForest","name":"IF","parameter":"contamination","value":0.05,"random_seed":7},
                 {"family":"LocalOutlierFactor","name":"LOF","parameter":"n_neighbors","value":5,"random_seed":7},
                 {"family":"OneClassSVM","name":"SVM","parameter":"nu","value":0.05,"random_seed":7}]
        from sklearn.preprocessing import StandardScaler
        scaler=StandardScaler().fit(train)
        tr_s=pd.DataFrame(scaler.transform(train),index=train.index,columns=train.columns)
        te_s=pd.DataFrame(scaler.transform(test),index=test.index,columns=test.columns)
        pred=fit_predict_configurations(train,test,tr_s,te_s,configs,n_estimators=10)
        self.assertEqual(len(pred),len(test)*3)
        summary,jac=stability_summary(pred)
        self.assertEqual(len(summary),len(test)); self.assertEqual(jac.shape,(3,3))
        self.assertEqual(len(default_model_configs()),12)

    def test_missing_configuration_timestamp_cannot_become_normal_vote(self):
        index=pd.date_range("2025-01-01",periods=2,freq="h",tz="Asia/Kolkata")
        pred=pd.DataFrame({"configuration":["IF","IF","LOF","LOF","SVM"],
                           "family":["IsolationForest"]*2+["LocalOutlierFactor"]*2+["OneClassSVM"],
                           "is_candidate":[False]*5},index=[index[0],index[1],index[0],index[1],index[0]])
        with self.assertRaisesRegex(ValueError,"exact same test timestamps"):
            stability_summary(pred)

    def test_episode_gap_segment_and_singletons(self):
        idx=pd.date_range("2025-01-01",periods=5,freq="h",tz="Asia/Kolkata")
        seg=pd.Series([0,0,1,1,1],index=idx)
        out=build_episodes([idx[0],idx[1],idx[2],idx[4]],seg,"1h")
        self.assertEqual(out.observations.tolist(),[2,1,1])
        sens=episode_gap_sensitivity([idx[0],idx[2]],None,("1h","2h","3h"))
        self.assertEqual(sens.groupby("gap_threshold").episode_id.nunique().tolist(),[2,1,1])


class TestFaultAndEvidence(unittest.TestCase):
    def test_fault_labels_heldout_bounds_and_copy(self):
        frame=sample_frame(10); original=frame.copy(deep=True)
        changed,labels,registry=inject_fault(frame,"temp",frame.index[7],kind="spike",magnitude=4,
                                              calibration_end=frame.index[6])
        self.assertTrue(labels.loc[frame.index[7]])
        self.assertEqual(changed.loc[frame.index[7],"temp"],frame.loc[frame.index[7],"temp"]+4)
        self.assertEqual(len(registry),1); pd.testing.assert_frame_equal(frame,original)
        with self.assertRaises(ValueError): inject_fault(frame,"temp",frame.index[3],calibration_end=frame.index[6])
        with self.assertRaises(ValueError): inject_fault(frame,"temp",frame.index[7],magnitude=1000,
                                                        calibration_end=frame.index[6])
        with self.assertRaises(ValueError): inject_fault(frame,"temp",frame.index[7],frame.index[8],
            kind="spike",calibration_end=frame.index[6])

    def test_temporal_fault_types_and_exact_labels(self):
        frame=sample_frame(10)
        for kind in ("positive_offset","negative_offset","drift","stuck",
                     "repeated_spikes","dropout","noise_burst"):
            changed,labels,registry=inject_fault(frame,"temp",frame.index[7],frame.index[9],
                kind=kind,magnitude=1.0,random_seed=13,calibration_end=frame.index[6],
                repetition_interval=2)
            expected=2 if kind=="repeated_spikes" else 3
            self.assertEqual(int(labels.sum()),expected,kind)
            if kind=="repeated_spikes":
                self.assertEqual(labels.iloc[7:10].tolist(),[True,False,True],kind)
            else:
                self.assertTrue(labels.iloc[7:10].all(),kind)
            self.assertEqual(len(registry),3,kind)
            if kind=="dropout": self.assertTrue(changed.iloc[7:10].temp.isna().all())

    def test_repeated_spike_registry_preserves_interval_and_exact_changed_timestamps(self):
        frame=sample_frame(12)
        changed,labels,registry=inject_fault(frame,"temp",frame.index[7],frame.index[10],
            kind="repeated_spikes",magnitude=2.0,repetition_interval=2,
            calibration_end=frame.index[6])
        expected=[frame.index[7],frame.index[9]]
        self.assertEqual(labels[labels].index.tolist(),expected)
        self.assertEqual(registry.timestamp.tolist(),frame.index[7:11].tolist())
        self.assertEqual(registry.injection_interval_start.unique().tolist(),[frame.index[7]])
        self.assertEqual(registry.injection_interval_end.unique().tolist(),[frame.index[10]])
        self.assertEqual(json.loads(registry.injected_timestamps_json.iloc[0]),[str(t) for t in expected])
        self.assertEqual(registry.value_modified.tolist(),[True,False,True,False])
        self.assertEqual(changed.loc[frame.index[8],"temp"],frame.loc[frame.index[8],"temp"])
        pred=pd.Series(False,index=frame.index)
        pred.loc[expected]=True
        metrics=evaluate_injection(pred,labels)
        self.assertEqual((metrics["tp"],metrics["fp"],metrics["fn"]),(2,0,0))
        frame.loc[frame.index[9],"temp"]=np.nan
        _,missing_labels,missing_registry=inject_fault(frame,"temp",frame.index[7],frame.index[10],
            kind="repeated_spikes",magnitude=2.0,repetition_interval=2,
            calibration_end=frame.index[6])
        self.assertEqual(missing_labels[missing_labels].index.tolist(),[frame.index[7]])
        self.assertEqual(json.loads(missing_registry.injected_timestamps_json.iloc[0]),[str(frame.index[7])])

    def test_missing_physical_observations_flag_all_six_weather_variables(self):
        frame=sample_frame(6)
        variables=("temp","dwpt","rhum","prcp","wspd","pres")
        for row,variable in enumerate(variables):
            frame.iloc[row,frame.columns.get_loc(variable)]=np.nan
        flags=physical_quality_flags(frame)
        for row,variable in enumerate(variables):
            record=flags[(flags.row_position==row)&(flags.variable==variable)].iloc[0]
            self.assertTrue(record.missing,variable)
            self.assertFalse(record.nonnumeric,variable)
            self.assertFalse(record.infinite,variable)
            self.assertFalse(record.below_screening_range,variable)
            self.assertFalse(record.above_screening_range,variable)
            self.assertTrue(record.screening_flag,variable)
            self.assertFalse(record.cross_variable_inconsistency,variable)

    def test_temporal_fault_cannot_bridge_gap_or_segment_boundary(self):
        frame=sample_frame(10); frame["segment_id"]=0
        gap_frame=frame.drop(frame.index[8])
        with self.assertRaisesRegex(ValueError,"missing/irregular timestamp gap"):
            inject_fault(gap_frame,"temp",frame.index[7],frame.index[9],kind="drift",
                         magnitude=2,calibration_end=frame.index[6])
        frame.loc[frame.index[8]:,"segment_id"]=1
        with self.assertRaisesRegex(ValueError,"segment boundary"):
            inject_fault(frame,"temp",frame.index[7],frame.index[8],kind="drift",
                         magnitude=2,calibration_end=frame.index[6])

    def test_sensor_stuck_fault_is_constant_from_last_good_reading(self):
        frame=sample_frame(9)
        changed,labels,_=inject_fault(frame,"temp",frame.index[7],frame.index[8],kind="stuck",
                                      calibration_end=frame.index[6])
        self.assertEqual(changed.iloc[7].temp,frame.iloc[6].temp)
        self.assertEqual(changed.iloc[7].temp,changed.iloc[8].temp)

    def test_injected_value_does_not_enter_its_own_shifted_reference(self):
        frame=sample_frame(12); frame["segment_id"]=0
        _,_,_,clean_features,faulted_features=inject_fault_with_feature_recompute(
            frame,"temp",frame.index[8],kind="spike",magnitude=5,calibration_end=frame.index[7])
        self.assertEqual(faulted_features.loc[frame.index[8],"temp_rolling_mean_6obs"],
                         clean_features.loc[frame.index[8],"temp_rolling_mean_6obs"])
        pd.testing.assert_frame_equal(faulted_features.loc[:frame.index[7]],clean_features.loc[:frame.index[7]])

    def test_injection_evaluation_rejects_missing_model_outputs(self):
        idx=sample_frame(3).index
        pred=pd.Series([False,np.nan,True],index=idx)
        labels=pd.Series([False,True,True],index=idx)
        with self.assertRaisesRegex(ValueError,"missing predictions"):
            evaluate_injection(pred,labels)

    def test_physical_flags_are_timestamped_screening_flags(self):
        frame=sample_frame(3); frame.iloc[1,frame.columns.get_loc("rhum")]=120
        frame.iloc[2,frame.columns.get_loc("dwpt")]=10
        flags=physical_quality_flags(frame)
        row=flags[(flags.timestamp==frame.index[1])&(flags.variable=="rhum")].iloc[0]
        self.assertTrue(row.above_screening_range); self.assertIn("not station calibration",row.rule_type)
        inconsistency=flags[(flags.timestamp==frame.index[2])&
                            (flags.variable=="dwpt_vs_temp")].iloc[0]
        self.assertTrue(inconsistency.cross_variable_inconsistency)
        self.assertTrue(inconsistency.screening_flag)

    def test_spatial_unavailability_and_exact_value_comparison(self):
        frame=sample_frame(3); empty=pd.DataFrame(columns=["temp"],index=pd.DatetimeIndex([],tz="Asia/Kolkata"))
        table=spatial_evidence([frame.index[0]],{"empty":empty,"live":frame},"temp")
        self.assertIn("NO_OBSERVED_DATA",set(table.availability))
        comp=compare_spatial_values(pd.Series([frame.iloc[0].temp],index=[frame.index[0]]),table,0.1)
        self.assertIn("UNAVAILABLE",set(comp.comparison))
        self.assertIn("SUPPORTS_WITHIN_DECLARED_TOLERANCE",set(comp.comparison))

    def test_spatial_before_after_internal_gap_and_variable_missing(self):
        frame=sample_frame(3)
        sparse=frame.drop(frame.index[1]).copy(); sparse["temp"]=sparse["temp"].astype(float)
        sparse.loc[frame.index[2],"temp"]=np.nan
        table=spatial_evidence([frame.index[0]-pd.Timedelta(hours=1),frame.index[1],
                                frame.index[2],frame.index[-1]+pd.Timedelta(hours=1)],
                               {"sparse":sparse},"temp")
        self.assertEqual(table.availability.tolist(),["BEFORE_OBSERVATION_PERIOD",
            "INTERNAL_TIMESTAMP_GAP","VARIABLE_UNAVAILABLE","AFTER_OBSERVATION_PERIOD"])

    def test_integrated_framework_abstains_on_missing_or_conflicting_evidence(self):
        evidence=pd.DataFrame({"spatial_status":["UNAVAILABLE","CONFLICTING","SUPPORTED"],
                               "supporting_stations":[0,0,2],"conflicting_stations":[0,1,0],
                               "hard_physical_violation":[False,True,False],
                               "model_stable":[True,True,True],
                               "temporal_coherent":[True,True,True]})
        out=classify_evidence(evidence)
        self.assertEqual(out.outcome.tolist(),["UNCERTAIN_INSUFFICIENT_EVIDENCE",
            "STATION_SPECIFIC_SUSPICIOUS_OBSERVATION","REGIONALLY_SUPPORTED_UNUSUAL_EVENT"])
        incomplete=evidence.iloc[[1]].drop(columns="temporal_coherent")
        self.assertEqual(classify_evidence(incomplete).iloc[0].outcome,
                         "UNCERTAIN_INSUFFICIENT_EVIDENCE")
        self.assertEqual(classify_evidence(pd.DataFrame(index=[0])).iloc[0].outcome,
                         "UNCERTAIN_INSUFFICIENT_EVIDENCE")

    def test_episode_level_paired_inference_reports_same_mean_estimand(self):
        pairs=pd.DataFrame({"difference_mean":[1.0,2.0,0.0,-1.0]})
        result=paired_permutation_bootstrap(pairs,n_permutations=200,n_bootstrap=200,random_seed=9)
        self.assertEqual(result["estimand"],"mean paired episode difference")
        self.assertEqual(result["n_episodes"],4)
        self.assertEqual(result["mean_difference"],0.5)

    def test_matched_control_inference_reproducible_seed(self):
        from weather_research.experiments import paired_permutation_bootstrap
        pairs=pd.DataFrame({"difference_mean":[0.5,1.0,1.5,2.0]})
        a=paired_permutation_bootstrap(pairs,n_permutations=300,n_bootstrap=300,random_seed=4)
        b=paired_permutation_bootstrap(pairs,n_permutations=300,n_bootstrap=300,random_seed=4)
        self.assertEqual(a,b)

    def test_matched_controls_are_post_candidate_and_non_overlapping(self):
        idx=pd.date_range("2025-01-01",periods=24*5,freq="h",tz="Asia/Kolkata")
        frame=pd.DataFrame({"temp":np.arange(len(idx),dtype=float)},index=idx)
        candidates=idx[4:6]
        episodes=pd.DataFrame([{"start":idx[4],"end":idx[5],"observations":2}])
        pairs=matched_episode_values(frame,episodes,"temp",candidates,max_controls=2)
        self.assertEqual(len(pairs),2)
        self.assertTrue((pairs.control_start>=idx[4]).all())
        control_windows=[set(pd.date_range(ts,periods=2,freq="h")) for ts in pairs.control_start]
        self.assertFalse(control_windows[0]&control_windows[1])
        self.assertFalse(control_windows[0]&set(candidates))

    def test_block_length_sensitivity_is_reported(self):
        pairs=pd.DataFrame({"episode_start":pd.date_range("2025-01-01",periods=5,freq="D"),
                            "difference_mean":[1.,2.,0.,-1.,3.]})
        out=block_length_sensitivity(pairs,block_lengths=(1,2,3),n_permutations=100,
                                     n_bootstrap=100,random_seed=1)
        self.assertEqual(out.block_length_episodes.tolist(),[1,2,3])
        self.assertEqual(out.mean_difference.nunique(),1)


class TestNotebookStructure(unittest.TestCase):
    def test_master_and_archive_are_valid_notebook_documents(self):
        for name in ("Weather_Station_Anomaly_Detection_Master.ipynb",
                     "Weather_Station_Anomaly_Detection_Exploratory_Archive.ipynb"):
            doc=json.loads((ROOT/name).read_text(encoding="utf-8"))
            self.assertEqual(doc["nbformat"],4)
            self.assertTrue(all(c["cell_type"] in ("code","markdown") for c in doc["cells"]))
            self.assertTrue(all(isinstance(c["source"],list) for c in doc["cells"]))

    def test_master_ids_are_unique_and_archive_ids_follow_declared_nbformat(self):
        for name in ("Weather_Station_Anomaly_Detection_Master.ipynb",
                     "Weather_Station_Anomaly_Detection_Exploratory_Archive.ipynb"):
            doc=json.loads((ROOT/name).read_text(encoding="utf-8"))
            cells=doc["cells"]
            if name.endswith("Master.ipynb") or doc["nbformat_minor"] >= 5:
                ids=[cell.get("id") for cell in cells]
                self.assertTrue(all(isinstance(cell_id,str) and 1<=len(cell_id)<=64 for cell_id in ids))
                self.assertEqual(len(ids),len(set(ids)))

    def test_every_section_has_explicit_implementation_status(self):
        doc=json.loads((ROOT/"Weather_Station_Anomaly_Detection_Master.ipynb").read_text(encoding="utf-8"))
        markdown_cells=["".join(c["source"]) for c in doc["cells"] if c["cell_type"]=="markdown"]
        for section in range(17):
            cell=next((text for text in markdown_cells if f"Section {section:02d}" in text),None)
            self.assertIsNotNone(cell,f"Section {section:02d} heading missing")
            self.assertIn("**Second-pass status:**",cell,f"Section {section:02d} status missing")
        markdown="\n".join(markdown_cells)
        self.assertIn("Section implementation status (second-pass audit)",markdown)

    def test_setup_cell_imports_package_from_non_project_working_directory(self):
        doc=json.loads((ROOT/"Weather_Station_Anomaly_Detection_Master.ipynb").read_text(encoding="utf-8"))
        setup="".join(doc["cells"][2]["source"])
        env=os.environ.copy(); env["WEATHER_RESEARCH_ROOT"]=str(ROOT)
        with tempfile.TemporaryDirectory() as other_cwd:
            proc=subprocess.run([sys.executable,"-B","-c",setup],cwd=other_cwd,env=env,
                                capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)


if __name__ == "__main__":
    unittest.main()
