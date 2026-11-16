"""Controlled held-out sensor-fault injection with exact synthetic labels."""
from __future__ import annotations

import numpy as np
import pandas as pd
import math
import json
from .features import engineer_features


def inject_fault(frame: pd.DataFrame, variable: str, start, end=None, kind="spike",
                 magnitude=1.0, random_seed=42, calibration_end=None,
                 physical_bounds=None, repetition_interval=3,
                 expected_interval="1h", segment_col="segment_id"):
    if variable not in frame:
        raise KeyError(variable)
    if (not isinstance(frame.index, pd.DatetimeIndex) or frame.index.has_duplicates
            or not frame.index.is_monotonic_increasing):
        raise ValueError("fault injection requires a unique, sorted DatetimeIndex")
    start=pd.Timestamp(start); end=pd.Timestamp(end if end is not None else start)
    if calibration_end is None:
        raise ValueError("calibration_end is required to isolate held-out fault injection")
    if start <= pd.Timestamp(calibration_end):
        raise ValueError("fault injections must be strictly after calibration_end")
    if start > end:
        raise ValueError("start must not follow end")
    mask=(frame.index>=start)&(frame.index<=end)
    if not mask.any():
        raise ValueError("fault interval has no held-out observations")
    out=frame.copy(deep=True)
    original=pd.to_numeric(out[variable],errors="coerce").copy()
    pos=np.flatnonzero(mask); values=original.iloc[pos].to_numpy(dtype=float)
    if len(pos)>1:
        selected_index=frame.index[pos]
        if (selected_index.to_series().diff().dropna()!=pd.Timedelta(expected_interval)).any():
            raise ValueError("temporal injection interval crosses a missing/irregular timestamp gap")
        if segment_col in frame and frame.iloc[pos][segment_col].nunique(dropna=False)!=1:
            raise ValueError("temporal injection interval crosses a segment boundary")
    rng=np.random.default_rng(random_seed)
    stuck_reference_value=np.nan
    stuck_reference_timestamp=None
    stuck_reference_source=None
    if kind in {"spike","point_positive_offset","point_negative_offset"} and len(pos)!=1:
        raise ValueError(f"{kind} must target exactly one timestamp")
    if kind=="spike": changed=values+float(magnitude)
    elif kind=="point_positive_offset": changed=np.array([values[0]+float(magnitude)])
    elif kind=="point_negative_offset": changed=np.array([values[0]-float(magnitude)])
    elif kind in {"positive_offset","step_positive"}: changed=values+float(magnitude)
    elif kind in {"negative_offset","step_negative"}: changed=values-float(magnitude)
    elif kind=="drift": changed=values+np.linspace(0,float(magnitude),len(values))
    elif kind=="stuck":
        first_position=int(pos[0])
        target_segment=frame.iloc[first_position][segment_col] if segment_col in frame else None
        candidate_positions=[]
        for prior_position in range(first_position-1,-1,-1):
            interval=frame.index[prior_position+1]-frame.index[prior_position]
            if interval != pd.Timedelta(expected_interval):
                break
            if segment_col in frame:
                candidate_segment=frame.iloc[prior_position][segment_col]
                same_segment=(pd.isna(candidate_segment) and pd.isna(target_segment)) or candidate_segment==target_segment
                if not same_segment:
                    break
            candidate_positions.append(prior_position)
        prior_positions=[p for p in candidate_positions if pd.notna(original.iloc[p])]
        if prior_positions:
            reference_position=prior_positions[0]
            stuck_value=float(original.iloc[reference_position])
            stuck_reference_timestamp=frame.index[reference_position]
            stuck_reference_source="last valid reading in the same contiguous segment"
        elif len(values) and np.isfinite(values[0]):
            stuck_value=float(values[0])
            stuck_reference_timestamp=frame.index[first_position]
            stuck_reference_source="first finite value inside injection interval; no prior same-segment reading"
        else:
            raise ValueError("stuck injection needs a finite reference from the same segment or first target value")
        stuck_reference_value=stuck_value
        changed=np.repeat(stuck_value,len(values))
    elif kind=="repeated_spikes":
        if repetition_interval < 1: raise ValueError("repetition_interval must be positive")
        changed=values.copy(); changed[::int(repetition_interval)]+=float(magnitude)
    elif kind=="dropout": changed=np.repeat(np.nan,len(values))
    elif kind=="noise_burst": changed=values+rng.normal(0,float(magnitude),len(values))
    else: raise ValueError(f"unknown fault kind: {kind}")
    if kind != "dropout":
        if physical_bounds is None:
            physical_bounds = {"temp":(-90,60),"dwpt":(-100,45),"rhum":(0,100),
                               "prcp":(0,1000),"wspd":(0,150),"pres":(800,1100)}
        if variable in physical_bounds:
            lo,hi=physical_bounds[variable]
            finite=np.isfinite(changed)
            if np.any((changed[finite]<lo)|(changed[finite]>hi)):
                raise ValueError("injection exceeds declared broad physical screening bounds")
    # Ground truth is timestamp-level: repeated-spike intervals contain both
    # modified and untouched observations. Other fault types preserve their
    # established interval labeling, including dropout even if already missing.
    affected=np.ones(len(pos),dtype=bool)
    if kind=="repeated_spikes":
        scheduled=np.zeros(len(pos),dtype=bool)
        scheduled[::int(repetition_interval)]=True
        unchanged=(changed == values) | (np.isnan(changed) & np.isnan(values))
        affected=scheduled & ~unchanged
    out.iloc[pos,out.columns.get_loc(variable)]=changed
    labels=pd.Series(False,index=frame.index,name="synthetic_fault_label")
    labels.iloc[pos[affected]]=True
    interval_start=start
    interval_end=end
    injected_timestamps=frame.index[pos[affected]].astype(str).tolist()
    registry=pd.DataFrame({"timestamp":frame.index[pos],"variable":variable,
                           "fault_kind":kind,"synthetic_fault_label":affected,
                           "value_modified":affected,
                           "injection_interval_start":interval_start,
                           "injection_interval_end":interval_end,
                           "injected_timestamps_json":json.dumps(injected_timestamps),
                           "random_seed":random_seed,"magnitude":magnitude,
                           "stuck_reference_value":stuck_reference_value,
                           "stuck_reference_timestamp":stuck_reference_timestamp,
                           "stuck_reference_source":stuck_reference_source,
                           "calibration_end":calibration_end,
                           "reference":"unaltered held-out raw value; training rows are not modified"})
    return out,labels,registry


def evaluate_injection(predicted: pd.Series, labels: pd.Series):
    """Pointwise metrics for synthetic labels only, with Wilson intervals for rates."""
    if not predicted.index.equals(labels.index):
        raise ValueError("predictions and injection labels must share exact timestamp index")
    if predicted.isna().any() or labels.isna().any():
        raise ValueError("missing predictions/labels must be resolved explicitly, never counted as normal")
    if not predicted.isin([True,False,0,1]).all() or not labels.isin([True,False,0,1]).all():
        raise ValueError("predictions and synthetic labels must be boolean/0-1 values")
    y=labels.fillna(False).astype(bool).to_numpy(); p=predicted.fillna(False).astype(bool).to_numpy()
    tp=int((y&p).sum()); fp=int((~y&p).sum()); fn=int((y&~p).sum()); tn=int((~y&~p).sum())
    def wilson(success,total,z=1.959963984540054):
        if total==0:return (float("nan"),float("nan"))
        phat=success/total; den=1+z*z/total
        center=(phat+z*z/(2*total))/den
        half=z*math.sqrt(phat*(1-phat)/total+z*z/(4*total*total))/den
        return (center-half,center+half)
    recall=tp/(tp+fn) if tp+fn else float("nan")
    fpr=fp/(fp+tn) if fp+tn else float("nan")
    return {"sampling_unit":"timestamp; dependence must be considered for temporal faults",
            "tp":tp,"fp":fp,"fn":fn,"tn":tn,"synthetic_point_recall":recall,
            "recall_wilson_95pct_ci":wilson(tp,tp+fn),"clean_false_positive_rate":fpr,
            "false_positive_rate_wilson_95pct_ci":wilson(fp,fp+tn)}


def inject_fault_with_feature_recompute(frame: pd.DataFrame, variable: str, start, end=None,
                                        kind="spike", magnitude=1.0, random_seed=42,
                                        calibration_end=None, segment_col="segment_id", **kwargs):
    """Inject into a copy and recompute clean/faulted features with the canonical function.

    The shifted rolling feature at the fault timestamp uses only preceding observations,
    so the injected value cannot enter its own reference. Earlier injected values can
    affect later causal windows, as would happen in a real sensor stream.
    """
    clean_features=engineer_features(frame,segment_col=segment_col)
    injected,labels,registry=inject_fault(frame,variable,start,end,kind,magnitude,
        random_seed,calibration_end,**kwargs)
    faulted_features=engineer_features(injected,segment_col=segment_col)
    return injected,labels,registry,clean_features,faulted_features
