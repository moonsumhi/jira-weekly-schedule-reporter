import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.services.delayed_digest_service import DelayedDigestService


class AsyncCursor:
    def __init__(self, documents):
        self.documents = documents

    async def __aiter__(self):
        for document in self.documents:
            yield document


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents
        self.query = None

    def find(self, query):
        self.query = query
        return AsyncCursor(self.documents)


class FakeDatabase(dict):
    def __getitem__(self, key):
        return super().__getitem__(key)


class DelayedDigestServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_and_legacy_implemented_issues_are_not_emailed_as_delayed(self):
        project_id = ObjectId()
        assignee_id = ObjectId()
        now = datetime.now(timezone.utc)
        overdue_due_date = now - timedelta(days=2)
        issue_collection = FakeCollection([
            {"status": "DONE", "due_date": overdue_due_date, "assignee_id": assignee_id},
            {"status": "IMPLEMENTED", "due_date": overdue_due_date, "assignee_id": assignee_id},
            {
                "status": "IN_PROGRESS",
                "due_date": overdue_due_date,
                "assignee_id": assignee_id,
                "project_id": project_id,
                "number": 3,
                "title": "진행 중 업무",
            },
        ])
        project_collection = FakeCollection([{"_id": project_id, "key": "OPS"}])
        database = FakeDatabase({MongoClientManager.SERVICE_REQUESTS: FakeCollection([])})

        with (
            patch.object(MongoClientManager, "get_db", return_value=database),
            patch.object(MongoClientManager, "get_pm_issues_collection", return_value=issue_collection),
            patch.object(MongoClientManager, "get_pm_projects_collection", return_value=project_collection),
        ):
            _, issue_by_assignee = await DelayedDigestService()._collect_delayed(now)

        self.assertEqual(
            issue_collection.query["status"]["$nin"],
            ["DONE", "IMPLEMENTED"],
        )
        self.assertEqual(
            issue_by_assignee,
            {
                str(assignee_id): [{
                    "key": "OPS-3",
                    "title": "진행 중 업무",
                    "days_late": 2,
                }]
            },
        )


if __name__ == "__main__":
    unittest.main()
