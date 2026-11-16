"""Matched-window inference helpers using episode-level paired units."""
from __future__ import annotations

import numpy as np
import pandas as pd


def matched_episode_values(frame: pd.DataFrame, episodes: pd.DataFrame, variable: str,
                           candidate_times, max_controls=1, eligible_control_start=None):
    """Match controls by month, start hour and episode observation count.

    Candidate event windows and selected controls cannot overlap; controls must
    have exact hourly timestamps and complete values for the requested variable.
    Results are descriptive matched pairs, not causal estimates.
    """
    candidates=set(pd.DatetimeIndex(candidate_times)); reserved=set(candidates)
    if not candidates: raise ValueError("candidate_times cannot be empty")
    control_start=pd.Timestamp(eligible_control_start) if eligible_control_start is not None else min(candidates)
    if max_controls < 1: raise ValueError("max_controls must be positive")
    if not isinstance(frame.index,pd.DatetimeIndex) or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("matching frame needs a unique, sorted DatetimeIndex")
    for _, event in episodes.iterrows():
        reserved.update(frame.index[(frame.index >= pd.Timestamp(event["start"])) &
                                    (frame.index <= pd.Timestamp(event["end"]))])
    rows=[]
    if variable not in frame:
        raise KeyError(variable)
    for _,ep in episodes.iterrows():
        count=int(ep["observations"]); start=pd.Timestamp(ep["start"]); end=pd.Timestamp(ep["end"])
        event_idx=frame.index[(frame.index>=start)&(frame.index<=end)&frame.index.isin(candidates)]
        if len(event_idx)==0: continue
        if len(event_idx)!=count or (event_idx.to_series().diff().dropna()!=pd.Timedelta(hours=1)).any():
            continue
        event_mean=pd.to_numeric(frame.loc[event_idx,variable],errors="coerce").mean()
        if not np.isfinite(event_mean): continue
        chosen=0
        for i in range(0,max(0,len(frame)-count+1)):
            ix=frame.index[i:i+count]
            if len(ix)!=count or (ix.to_series().diff().dropna()!=pd.Timedelta(hours=1)).any(): continue
            cstart=ix[0]
            if cstart < control_start: continue
            if cstart.month!=start.month or cstart.hour!=start.hour or cstart.minute!=start.minute: continue
            if any(t in reserved for t in ix): continue
            vals=pd.to_numeric(frame.loc[ix,variable],errors="coerce")
            if vals.isna().any(): continue
            rows.append({"episode_start":start,"control_start":cstart,"month":start.month,
                         "hour":start.hour,"duration_observations":count,
                         "candidate_mean":event_mean,"control_mean":vals.mean(),
                         "difference_mean":event_mean-vals.mean()})
            reserved.update(ix); chosen+=1
            if chosen>=max_controls: break
    return pd.DataFrame(rows)


def paired_permutation_bootstrap(pairs: pd.DataFrame, difference_col="difference_mean",
                                n_permutations=10000, n_bootstrap=5000, random_seed=42,
                                block_length=2):
    """Block sign-flip test and circular moving-block bootstrap for mean difference.

    Rows must be chronologically ordered by episode. Block length is a declared
    dependence assumption and should be sensitivity-tested; it is not estimated here.
    """
    if "episode_start" in pairs and not pd.to_datetime(pairs["episode_start"]).is_monotonic_increasing:
        raise ValueError("matched episode pairs must be chronological")
    d=pd.to_numeric(pairs[difference_col],errors="coerce")
    if d.isna().any() or not np.isfinite(d.to_numpy(dtype=float)).all():
        raise ValueError("matched differences must be complete and finite")
    d=d.to_numpy(float)
    if len(d)<2: raise ValueError("at least two matched episodes are required")
    if block_length < 1: raise ValueError("block_length must be positive")
    if n_permutations < 1 or n_bootstrap < 1: raise ValueError("resampling counts must be positive")
    rng=np.random.default_rng(random_seed); observed=float(d.mean())
    blocks=[d[i:i+block_length] for i in range(0,len(d),block_length)]
    perm=np.empty(n_permutations)
    for r in range(n_permutations):
        signs=rng.choice([-1.0,1.0],size=len(blocks))
        perm[r]=np.concatenate([sign*b for sign,b in zip(signs,blocks)]).mean()
    p=(1+int(np.sum(np.abs(perm)>=abs(observed))))/(n_permutations+1)
    boot=np.empty(n_bootstrap)
    for r in range(n_bootstrap):
        chosen=[]
        while len(chosen)<len(d):
            start=int(rng.integers(0,len(d)))
            chosen.extend(d[(start+j)%len(d)] for j in range(block_length))
        boot[r]=np.asarray(chosen[:len(d)]).mean()
    low,high=np.quantile(boot,[0.025,0.975])
    return {"null_hypothesis":"mean paired episode difference equals zero",
            "alternative_hypothesis":"mean paired episode difference differs from zero",
            "estimand":"mean paired episode difference","n_episodes":len(d),
            "mean_difference":observed,"permutation_p_value_two_sided":float(p),
            "bootstrap_95pct_ci_mean_difference":(float(low),float(high)),
            "sampling_unit":"chronologically ordered matched episode pairs in circular blocks",
            "block_length_episodes":int(block_length),
            "assumption":"block length should be sensitivity-tested; residual dependence beyond blocks may remain",
            "random_seed":random_seed}


def block_length_sensitivity(pairs: pd.DataFrame, block_lengths=(1,2,3,4), **kwargs):
    """Run the declared paired estimand across candidate dependence block lengths."""
    outputs=[]
    for length in block_lengths:
        result=paired_permutation_bootstrap(pairs,block_length=int(length),**kwargs)
        outputs.append({"block_length_episodes":int(length),
                        "mean_difference":result["mean_difference"],
                        "permutation_p_value_two_sided":result["permutation_p_value_two_sided"],
                        "ci_low":result["bootstrap_95pct_ci_mean_difference"][0],
                        "ci_high":result["bootstrap_95pct_ci_mean_difference"][1]})
    return pd.DataFrame(outputs)
