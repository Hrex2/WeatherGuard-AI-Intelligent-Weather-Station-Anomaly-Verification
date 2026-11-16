"""Explicit Meteostat observation-only retrieval; never runs on import."""
from __future__ import annotations

from datetime import datetime
import hashlib
import importlib.metadata
import pandas as pd


def fetch_observations(station_ids, start: datetime, end: datetime,
                       timezone="Asia/Kolkata"):
    """Fetch only when explicitly called, recording API branch and per-station status."""
    import meteostat as ms
    version=importlib.metadata.version("meteostat")
    frames={}; records=[]
    for station in station_ids:
        previous=None; branch=None
        try:
            hourly=getattr(ms,"Hourly",None)
            if hourly is not None:
                try:
                    obj=hourly(station,start,end,timezone=timezone,model=False)
                    branch="Hourly(model=False)"
                except TypeError:
                    previous=getattr(ms.config,"include_model_data",None)
                    if previous is None: raise RuntimeError("cannot verify model-data exclusion setting")
                    ms.config.include_model_data=False
                    try: obj=ms.hourly(station,start,end,timezone=timezone)
                    finally: ms.config.include_model_data=previous
                    branch="hourly with include_model_data=False (restored)"
            else:
                previous=getattr(ms.config,"include_model_data",None)
                if previous is None: raise RuntimeError("cannot verify model-data exclusion setting")
                ms.config.include_model_data=False
                try: obj=ms.hourly(station,start,end,timezone=timezone)
                finally: ms.config.include_model_data=previous
                branch="hourly with include_model_data=False (restored)"
            frame=obj.fetch()
            if not isinstance(frame,pd.DataFrame): raise TypeError("fetch did not return DataFrame")
            frames[station]=frame
            records.append({"station_id":station,"status":"SUCCESS_WITH_DATA" if len(frame) else "SUCCESS_NO_RECORDS",
                            "records":len(frame),"first":str(frame.index.min()) if len(frame) else None,
                            "last":str(frame.index.max()) if len(frame) else None,
                            "meteostat_version":version,"api_branch":branch,"error":None})
        except Exception as exc:
            if previous is not None: ms.config.include_model_data=previous
            frames[station]=pd.DataFrame()
            records.append({"station_id":station,"status":"FAILED","records":0,
                            "first":None,"last":None,"meteostat_version":version,
                            "api_branch":branch,"error":repr(exc)})
    return frames,pd.DataFrame(records)


def sha256_file(path):
    digest=hashlib.sha256()
    with open(path,"rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()
