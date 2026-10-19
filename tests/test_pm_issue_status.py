import unittest

from app.models.pm.issue import (
    ISSUE_STATUS_ORDER,
    IssueCreate,
    IssuePatch,
    canonical_issue_status,
)


class IssueStatusCompatibilityTests(unittest.TestCase):
    def test_legacy_implemented_input_is_saved_as_done(self):
        self.assertEqual(IssueCreate(title="완료 업무", status="IMPLEMENTED").status, "DONE")
        self.assertEqual(IssuePatch(status="IMPLEMENTED").status, "DONE")

    def test_legacy_records_share_the_done_column(self):
        self.assertEqual(canonical_issue_status("IMPLEMENTED"), "DONE")
        self.assertEqual(ISSUE_STATUS_ORDER, ["BACKLOG", "TODO", "IN_PROGRESS", "DONE"])


if __name__ == "__main__":
    unittest.main()
