import unittest
from unittest.mock import patch

from app.life.event_normalizer import normalize_screentime, normalize_weather
from app.life.runtime import ingest_context, list_events, reset_memory_runtime
from app.web import routes


class EvidenceRefreshTests(unittest.TestCase):
    def setUp(self):
        reset_memory_runtime()

    def test_weather_normalizes_to_dedupable_life_evidence(self):
        first = normalize_weather({"temperature": 22, "weather_code": 1, "observed_at": "2026-08-11T10:00:00Z"})
        second = normalize_weather({"temperature": 22, "weather_code": 1, "observed_at": "2026-08-11T10:00:00Z"})
        self.assertEqual(first[0].event_type, "weather.observed")
        self.assertEqual(first[0].dedupe_key, second[0].dedupe_key)

    @patch("app.context.weather.db.load_context")
    def test_cached_weather_keeps_its_original_observation_time(self, load_context):
        from app.context.weather import get_weather
        load_context.return_value = {"updated_at": "2026-08-11T10:00:00Z", "payload": {"temperature": 22}}
        with patch("app.context.weather.config.WEATHER_CACHE_MINUTES", 999999):
            self.assertEqual(get_weather()["observed_at"], "2026-08-11T10:00:00Z")

    def test_screentime_rejects_negative_and_invalid_total(self):
        from app.web.routes import ScreenTimePayload
        for value in (-1, 1441, "not-a-number"):
            with self.assertRaises(Exception):
                ScreenTimePayload(total_minutes=value, date="2026-08-11", timestamp="2026-08-11T10:00:00Z")

    def test_screentime_preserves_timestamp_as_event_time(self):
        event = normalize_screentime({"total_minutes": 20, "date": "2026-08-11", "timestamp": "2026-08-11T10:00:00Z"})[0]
        self.assertEqual(event.occurred_at, "2026-08-11T10:00:00Z")

    def test_weather_ingest_is_idempotent(self):
        payload = {"temperature": 22, "weather_code": 1, "observed_at": "2026-08-11T10:00:00Z"}
        self.assertTrue(ingest_context("weather", payload)[0]["inserted"])
        self.assertFalse(ingest_context("weather", payload)[0]["inserted"])
        self.assertEqual(len([event for event in list_events() if event["event_type"] == "weather.observed"]), 1)

    def test_screentime_ingest_is_idempotent(self):
        payload = {"total_minutes": 20, "date": "2026-08-11", "timestamp": "2026-08-11T10:00:00Z"}
        self.assertTrue(ingest_context("screentime", payload)[0]["inserted"])
        self.assertEqual(ingest_context("screentime", payload), [])

    @patch("app.context.provider.get_context")
    def test_context_refresh_only_uses_server_owned_weather_and_calendar(self, get_context):
        routes._refresh_last_at = None
        get_context.return_value = {"weather": {"temperature": 22}}
        result = routes._refresh_context_sources()
        self.assertEqual(result["status"], "refreshed")
        self.assertEqual(result["sources"], ["weather"])
        get_context.assert_called_once_with(need=["mac", "weather", "calendar"])

    @patch("app.context.provider.get_context")
    def test_context_refresh_uses_server_side_cooldown(self, get_context):
        routes._refresh_last_at = None
        routes._refresh_context_sources()
        result = routes._refresh_context_sources()
        self.assertEqual(result["status"], "cooldown")
        self.assertEqual(get_context.call_count, 1)


if __name__ == "__main__":
    unittest.main()
