"""Read-only Phase 01 Pipeline B audit, retained outside notebook globals."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .quality import physical_quality_flags
from .quality import DEFAULT_SCREENING_BOUNDS
from .validation import BASE_VARIABLES

HISTORICAL_FEATURES = ("temp_change_1h", "temp_rolling_mean_6h", "temp_deviation_6h")


def recompute_historical_features(model_df: pd.DataFrame, segment_col="segment_id") -> pd.DataFrame:
    """Exactly reconstruct source Cell 53's row-based diff and shifted six-row mean."""
    required={segment_col,"temp",*HISTORICAL_FEATURES}
    missing=required-set(model_df.columns)
    if missing: raise KeyError(f"historical model_df missing columns: {sorted(missing)}")
    if not isinstance(model_df.index,pd.DatetimeIndex): raise TypeError("DatetimeIndex required")
    if model_df.index.has_duplicates: raise ValueError("duplicate raw timestamps")
    out=pd.DataFrame(index=model_df.index)
    grouped=model_df.groupby(segment_col,sort=False,dropna=True)["temp"]
    out["temp_change_1h"]=grouped.diff()
    out["temp_rolling_mean_6h"]=grouped.transform(
        lambda s:s.shift(1).rolling(window=6,min_periods=6).mean())
    out["temp_deviation_6h"]=model_df["temp"]-out["temp_rolling_mean_6h"]
    return out


def _compare_features(actual, expected, tolerance):
    rows=[]
    for col in expected:
        a=pd.to_numeric(actual[col],errors="coerce").to_numpy(dtype=float)
        e=pd.to_numeric(expected[col],errors="coerce").to_numpy(dtype=float)
        if len(a)!=len(e): raise ValueError("feature comparison row count mismatch")
        missing_a=np.isnan(a); missing_e=np.isnan(e)
        common=~missing_a & ~missing_e
        delta=np.abs(a[common]-e[common])
        bad_missing=missing_a!=missing_e
        mismatch=int(bad_missing.sum()+np.sum(delta>tolerance))
        rows.append({"feature":col,"mismatch_count":mismatch,
                     "missingness_mismatch_count":int(bad_missing.sum()),
                     "max_absolute_difference":float(delta.max()) if len(delta) else 0.0,
                     "passed":mismatch==0})
    return pd.DataFrame(rows)


def phase01_integrity_audit(model_df: pd.DataFrame, x_multi: pd.DataFrame,
                            x_train: pd.DataFrame, x_test: pd.DataFrame,
                            split_boundary="2025-03-21 17:30:00+05:30",
                            segment_col="segment_id", tolerance=1e-8):
    """Reconcile historical features, indexes, imputation and raw quality without mutation.

    Inputs are explicit copies/references; all returned objects are new. This verifies
    computational parity against historical formulas but does not certify weather truth.
    """
    required={segment_col,"temp","prcp",*HISTORICAL_FEATURES,*BASE_VARIABLES}
    missing=required-set(model_df.columns)
    if missing: raise KeyError(f"model_df missing required columns: {sorted(missing)}")
    duplicates=[]
    for name,frame in (("model_df",model_df),("X_multi",x_multi),
                       ("X_train",x_train),("X_test",x_test)):
        if not isinstance(frame.index,pd.DatetimeIndex): raise TypeError(f"{name} needs DatetimeIndex")
        if frame.index.has_duplicates:
            counts=frame.index[frame.index.duplicated(keep=False)].value_counts()
            duplicates.extend({"frame":name,"timestamp":ts,"duplicate_rows":int(count)}
                              for ts,count in counts.items())
        if not frame.index.is_monotonic_increasing: raise ValueError(f"{name} timestamps are unsorted")
    expected_features=recompute_historical_features(model_df,segment_col)
    feature_report=_compare_features(model_df.loc[:,HISTORICAL_FEATURES],expected_features,tolerance)
    segment_reports=[]
    segment_values=model_df[segment_col]
    for segment_value in segment_values.drop_duplicates().tolist():
        positions=np.flatnonzero(segment_values.isna().to_numpy()) if pd.isna(segment_value) else np.flatnonzero(segment_values.eq(segment_value).fillna(False).to_numpy())
        part=_compare_features(model_df.iloc[positions][list(HISTORICAL_FEATURES)],
                               expected_features.iloc[positions],tolerance)
        part["segment_id"]=segment_value
        segment_reports.append(part)
    segment_feature_report=pd.concat(segment_reports,ignore_index=True) if segment_reports else pd.DataFrame()
    ready_mask=model_df[list(HISTORICAL_FEATURES)].notna().all(axis=1)
    expected_index=model_df.index[ready_mask]
    actual_index=x_multi.index
    index_report=pd.DataFrame([
        {"check":"expected feature-ready index equals X_multi index",
         "expected_rows":len(expected_index),"actual_rows":len(actual_index),
         "missing_from_X_multi":len(expected_index.difference(actual_index)),
         "unexpected_in_X_multi":len(actual_index.difference(expected_index)),
         "passed":expected_index.equals(actual_index)}])
    actual_membership=pd.Series(model_df.index.isin(actual_index),index=model_df.index)
    excluded_positions=np.flatnonzero(~actual_membership.to_numpy())
    exclusion_rows=[]
    for pos in excluded_positions:
        row=model_df.iloc[pos]
        missing_features=[col for col in HISTORICAL_FEATURES if pd.isna(row[col])]
        exclusion_rows.append({"timestamp":model_df.index[pos],"row_position":pos,
                               "reason":"missing engineered feature(s): "+", ".join(missing_features)
                               if missing_features else "not present in X_multi despite feature-ready values"})
    exclusions=pd.DataFrame(exclusion_rows,columns=["timestamp","row_position","reason"])
    missing_segments=pd.DataFrame({"timestamp":model_df.index[model_df[segment_col].isna()]})
    boundary=pd.Timestamp(split_boundary)
    if model_df.index.tz is not None and boundary.tzinfo is None:
        boundary=boundary.tz_localize(str(model_df.index.tz))
    elif model_df.index.tz is None and boundary.tzinfo is not None:
        boundary=boundary.tz_localize(None)
    expected_train=expected_index[expected_index<boundary]
    expected_test=expected_index[expected_index>=boundary]
    split_report=pd.DataFrame([
        {"check":"train index equals chronological membership","expected_rows":len(expected_train),
         "actual_rows":len(x_train),"missing":len(expected_train.difference(x_train.index)),
         "unexpected":len(x_train.index.difference(expected_train)),
         "passed":expected_train.equals(x_train.index)},
        {"check":"test index equals chronological membership","expected_rows":len(expected_test),
         "actual_rows":len(x_test),"missing":len(expected_test.difference(x_test.index)),
         "unexpected":len(x_test.index.difference(expected_test)),
         "passed":expected_test.equals(x_test.index)},
        {"check":"train/test disjoint","expected_rows":0,"actual_rows":len(x_train.index.intersection(x_test.index)),
         "missing":0,"unexpected":0,"passed":x_train.index.intersection(x_test.index).empty},
    ])
    raw_missing=model_df.index[model_df["prcp"].isna()]
    retained=raw_missing[raw_missing.isin(x_multi.index)]
    excluded=raw_missing[~raw_missing.isin(x_multi.index)]
    train_raw=model_df.loc[model_df.index.intersection(expected_train),"prcp"]
    median=float(train_raw.median()) if train_raw.notna().any() else np.nan
    matrix_columns=[c for c in list(BASE_VARIABLES)+list(HISTORICAL_FEATURES) if c in x_multi.columns]
    missing_matrix_columns=sorted((set(BASE_VARIABLES)|set(HISTORICAL_FEATURES))-set(matrix_columns))
    expected_positions=np.flatnonzero(ready_mask.to_numpy())
    expected_matrix=model_df.iloc[expected_positions][matrix_columns].copy()
    if "prcp" in expected_matrix:
        expected_matrix["prcp"]=expected_matrix["prcp"].fillna(median)
    model_matrix_report=_compare_features(x_multi.loc[:,matrix_columns],expected_matrix,tolerance)
    split_value_rows=[]
    for label,part,expected_idx in (("train",x_train,expected_train),("test",x_test,expected_test)):
        aligned=(not model_df.index.has_duplicates and not x_multi.index.has_duplicates
                 and part.index.equals(expected_idx) and expected_idx.isin(x_multi.index).all())
        if aligned:
            reference=x_multi.loc[expected_idx,matrix_columns]
            comparison=_compare_features(part.loc[:,matrix_columns],reference,tolerance)
            split_value_rows.append({"partition":label,"mismatch_count":int(comparison.mismatch_count.sum()),
                                     "passed":bool(comparison.passed.all())})
        else:
            split_value_rows.append({"partition":label,"mismatch_count":-1,"passed":False})
    split_value_report=pd.DataFrame(split_value_rows)
    imputation_rows=[]
    for ts in retained:
        frame_name="train" if ts in x_train.index else "test" if ts in x_test.index else "neither"
        target=x_train if frame_name=="train" else x_test if frame_name=="test" else None
        value=(target.loc[target.index==ts,"prcp"].iloc[0]
               if target is not None and "prcp" in target and (target.index==ts).any() else np.nan)
        imputation_rows.append({"timestamp":ts,"partition":frame_name,"training_median":median,
                                "imputed_value":value,"matches_training_median":bool(pd.notna(value) and np.isclose(value,median))})
    precipitation=pd.DataFrame(imputation_rows,columns=["timestamp","partition","training_median","imputed_value","matches_training_median"])
    physical_all=physical_quality_flags(model_df[list(BASE_VARIABLES)])
    summary_rows=[]
    for variable in BASE_VARIABLES:
        part=physical_all.loc[physical_all.variable.eq(variable)]
        summary_rows.append({"variable":variable,"missing_count":int(model_df[variable].isna().sum()),
                             "nonnumeric_count":int(part.nonnumeric.sum()),"infinite_count":int(part.infinite.sum()),
                             "below_bound_count":int(part.below_screening_range.sum()),
                             "above_bound_count":int(part.above_screening_range.sum()),
                             "screening_bounds":DEFAULT_SCREENING_BOUNDS[variable]})
    physical_summary=pd.DataFrame(summary_rows)
    physical=physical_all.loc[physical_all["screening_flag"]|
                              physical_all["cross_variable_inconsistency"]].reset_index(drop=True)
    autocorr=[]
    for variable in BASE_VARIABLES:
        if variable not in model_df: continue
        frame=model_df[[segment_col,variable]].copy()
        prev=frame.groupby(segment_col,dropna=True)[variable].shift(1)
        prev_time=pd.Series(model_df.index,index=model_df.index).groupby(model_df[segment_col],dropna=True).shift(1)
        adjacent=pd.Series(model_df.index,index=model_df.index).sub(prev_time).eq(pd.Timedelta(hours=1))
        pair=pd.DataFrame({"current":pd.to_numeric(frame[variable],errors="coerce"),"previous":pd.to_numeric(prev,errors="coerce")})
        pair=pair.loc[adjacent].dropna()
        variable_corr=(pair["current"].corr(pair["previous"])
                       if len(pair)>=2 and pair["current"].nunique()>1 and pair["previous"].nunique()>1 else np.nan)
        autocorr.append({"variable":variable,"adjacent_hour_pairs":len(pair),
                         "lag1_correlation":variable_corr,
                         "interpretation":"descriptive; temporal dependence, not iid inference"})
    monthly=model_df.assign(month=model_df.index.month).groupby("month")[list(BASE_VARIABLES)].agg(["count","mean","std"])
    gap=(x_test.index.min()-x_train.index.max()) if len(x_train) and len(x_test) else pd.NaT
    duplicate_report=pd.DataFrame(duplicates,columns=["frame","timestamp","duplicate_rows"])
    return {"feature_report":feature_report,"per_segment_feature_report":segment_feature_report,
            "duplicate_timestamp_report":duplicate_report,"missing_segment_timestamps":missing_segments,
            "excluded_model_rows_and_reasons":exclusions,"index_report":index_report,"split_report":split_report,
            "raw_precipitation_missing_timestamps":pd.DataFrame({"timestamp":raw_missing}),
            "precipitation_retained_timestamps":pd.DataFrame({"timestamp":retained}),
            "precipitation_excluded_timestamps":pd.DataFrame({"timestamp":excluded}),
            "precipitation_imputation":precipitation,"training_precipitation_median":median,
            "model_matrix_report":model_matrix_report,"missing_model_matrix_columns":missing_matrix_columns,
            "split_value_report":split_value_report,
            "physical_summary":physical_summary,"physical_flags":physical,
            "lag1_autocorrelation":pd.DataFrame(autocorr),
            "monthly_descriptive_summary":monthly,"train_end":x_train.index.max() if len(x_train) else pd.NaT,
            "test_start":x_test.index.min() if len(x_test) else pd.NaT,"train_test_time_gap":gap,
            "phase01_passed":bool(duplicate_report.empty and feature_report.passed.all() and index_report.passed.all() and
                                   split_report.passed.all() and model_matrix_report.passed.all() and
                                   not missing_matrix_columns and split_value_report.passed.all() and
                                   precipitation.get("matches_training_median",pd.Series(dtype=bool)).all())}
