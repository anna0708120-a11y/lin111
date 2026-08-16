import unittest

from app.web.spaces_routes import SPACES_HTML, WORKGROUP_HTML, _group_url


class WorkgroupUiTests(unittest.TestCase):
    def test_dwell_group_card_enters_the_original_workgroup_page(self):
        self.assertEqual(_group_url(), "/workgroup")
        self.assertIn("location.assign('__GROUP_URL__')", SPACES_HTML)

    def test_workgroup_page_uses_the_existing_message_api(self):
        for marker in ('id="workgroupMembers"', 'id="workgroupMessages"', 'id="workgroupComposer"', "fetch('/workgroup/messages')", "method:'POST'", 'Gemma preprocessing'):
            self.assertIn(marker, WORKGROUP_HTML)

    def test_workgroup_polling_preserves_a_user_scrolled_position(self):
        self.assertIn('const followNewMessages=', WORKGROUP_HTML)
        self.assertIn('if(followNewMessages)', WORKGROUP_HTML)


if __name__ == "__main__":
    unittest.main()
