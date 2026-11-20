"""Refresh policy for the Home dashboard's historical playback fragment."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from ui import home_dashboard


class TestHomeRenderPolicy(unittest.TestCase):
    def _assert_fragment_interval(self, playing: bool, expected_interval: float | None) -> None:
        state = Mock()
        state.get.return_value = playing
        data = {"sentinel": "saved-project-data"}
        fragment_body = Mock()

        with patch.object(home_dashboard.st, "session_state", state), patch.object(
            home_dashboard.st, "fragment"
        ) as fragment:
            fragment.return_value.return_value = fragment_body
            home_dashboard.render_home_dashboard(data, "project-root")

        fragment.assert_called_once_with(run_every=expected_interval)
        fragment_body.assert_called_once_with(data, "project-root")

    def test_idle_dashboard_does_not_schedule_periodic_rerenders(self):
        self._assert_fragment_interval(playing=False, expected_interval=None)

    def test_playing_timeline_schedules_its_frame_updates(self):
        self._assert_fragment_interval(playing=True, expected_interval=0.8)


if __name__ == "__main__":
    unittest.main()
