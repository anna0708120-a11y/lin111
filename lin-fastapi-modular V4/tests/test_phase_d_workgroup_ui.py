import unittest
from unittest.mock import patch

from app.web.frontend import HTML_CONTENT


class WorkgroupUiTests(unittest.TestCase):
    def test_internal_workgroup_is_a_separate_visible_page(self):
        for marker in ('id="tb-workgroup"', 'id="pg-workgroup"', 'Anna · Gemma · Lin', 'id="workgroupMembers"', 'id="workgroupMessages"', 'id="workgroupComposer"', 'initWorkgroup()'):
            self.assertIn(marker, HTML_CONTENT)

    def test_workgroup_keeps_gemma_process_display_separate(self):
        self.assertIn('Gemma preprocessing', HTML_CONTENT)
        self.assertIn("m.member==='gemma'", HTML_CONTENT)
        self.assertIn("fetch(AU+'/workgroup/messages')", HTML_CONTENT)
        self.assertIn('await loadWorkgroup()', HTML_CONTENT)
        self.assertNotIn('127.0.0.1:8787', HTML_CONTENT)


if __name__ == "__main__":
    unittest.main()
