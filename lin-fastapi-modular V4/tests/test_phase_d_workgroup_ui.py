import unittest

from app.web.spaces_routes import SPACES_EMBED_HTML


class WorkgroupUiTests(unittest.TestCase):
    def test_legacy_spaces_url_returns_to_the_lin_shell(self):
        from app.web.spaces_routes import spaces_page

        response = spaces_page()
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/?view=workgroup")

    def test_dwell_embed_has_six_cards_and_keeps_diary_and_settings_routes(self):
        self.assertEqual(SPACES_EMBED_HTML.count("grid.appendChild(rot(card("), 6)
        self.assertIn("parent.location.assign('/?view=diary')", SPACES_EMBED_HTML)
        self.assertIn("parent.location.assign('/agent-settings')", SPACES_EMBED_HTML)

    def test_dwell_group_card_signals_the_shell_workgroup_panel(self):
        self.assertIn("parentAction('workgroup-chat')", SPACES_EMBED_HTML)


if __name__ == "__main__":
    unittest.main()
