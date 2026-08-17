import unittest

from app.web.spaces_routes import spaces_page


class WorkgroupUiTests(unittest.TestCase):
    def test_legacy_spaces_url_returns_to_the_lin_shell(self):
        response = spaces_page()
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/?view=workgroup")


if __name__ == "__main__":
    unittest.main()
