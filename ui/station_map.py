"""Small verified-location map component with an honest unavailable state."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.investigation_service import verified_station_location


def render_station_map(root, station_id="VILD0"):
    location = verified_station_location(root, station_id)
    st.subheader("Station location")
    if not location["available"]:
        st.info("Station coordinates unavailable.")
        if location.get("reported_location"):
            st.caption(f"Reported station locality: {location['reported_location']}. It is not used as a map coordinate.")
        st.caption(location["reason"])
        return
    point = pd.DataFrame([{"latitude": location["latitude"], "longitude": location["longitude"]}])
    st.map(point, latitude="latitude", longitude="longitude", size=180, zoom=9)
    st.caption(f"Verified station marker: {location['station_id']} · {location['latitude']:.5f}, {location['longitude']:.5f}")
