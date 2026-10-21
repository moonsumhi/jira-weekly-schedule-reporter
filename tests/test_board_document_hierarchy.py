import unittest
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId
from fastapi import HTTPException

from app.models.board import PostCreate
from app.routers.boards import _validate_post_parent, patch_post


class FakePosts:
    def __init__(self, documents):
        self.documents = documents

    async def find_one(self, query):
        document = self.documents.get(str(query["_id"]))
        return document if document and document["board_id"] == query["board_id"] else None

    async def find_one_and_update(self, query, update, return_document):
        document = await self.find_one(query)
        if not document or document.get("version") != query.get("version"):
            return None
        document.update(update["$set"])
        document["version"] += update["$inc"]["version"]
        return document


class FakeUsers:
    def __init__(self, user_id):
        self.user_id = user_id

    async def find_one(self, query):
        return {"full_name": "새 책임자", "email": "owner@example.com"} if str(query["_id"]) == self.user_id else None


class FakeHistories:
    def __init__(self):
        self.records = []

    async def insert_one(self, record):
        self.records.append(record)

    async def update_one(self, query, update, upsert=False):
        record = next((
            item for item in self.records
            if item.get("post_id") == query.get("post_id") and item.get("version") == query.get("version")
        ), None)
        if record is None and upsert:
            record = dict(update.get("$setOnInsert", {}))
            self.records.append(record)
        if record is not None:
            record.update(update.get("$setOnInsert", {}))
            record.update(update.get("$set", {}))


class DocumentHierarchyTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_descendant_as_parent(self):
        root_id, child_id = str(ObjectId()), str(ObjectId())
        posts = FakePosts({
            root_id: {"_id": ObjectId(root_id), "board_id": "board", "parent_id": None},
            child_id: {"_id": ObjectId(child_id), "board_id": "board", "parent_id": root_id},
        })

        with self.assertRaises(HTTPException) as error:
            await _validate_post_parent(posts, "board", child_id, root_id)

        self.assertEqual(error.exception.status_code, 400)

    async def test_admin_can_transfer_responsibility_without_rewriting_author(self):
        post_id, old_owner, new_owner = str(ObjectId()), str(ObjectId()), str(ObjectId())
        document = {
            "_id": ObjectId(post_id), "board_id": "board", "title": "운영 문서", "part": "",
            "category": "", "content": "본문", "attachments": [], "parent_id": None,
            "author_id": old_owner, "author_name": "퇴사한 작성자", "owner_id": old_owner,
            "owner_name": "퇴사한 작성자", "editor_ids": [], "version": 1,
        }
        posts, histories = FakePosts({post_id: document}), FakeHistories()
        payload = PostCreate(title="운영 문서", content="본문", owner_id=new_owner)
        admin = SimpleNamespace(id=str(ObjectId()), full_name="관리자", email="admin@example.com", is_admin=True)

        with patch("app.routers.boards.MongoClientManager.get_board_posts_collection", return_value=posts), \
             patch("app.routers.boards.MongoClientManager.get_users_collection", return_value=FakeUsers(new_owner)), \
             patch("app.routers.boards.MongoClientManager.get_board_post_histories_collection", return_value=histories):
            result = await patch_post("board", post_id, payload, admin)

        self.assertEqual(result.author_name, "퇴사한 작성자")
        self.assertEqual(result.owner_name, "새 책임자")
        self.assertEqual(result.version, 2)
        current_history = next(record for record in histories.records if record.get("version") == 2)
        self.assertEqual(current_history["diff"][0]["field"], "문서 책임자")

    async def test_designated_editor_cannot_transfer_responsibility(self):
        post_id, owner_id, editor_id, new_owner = (str(ObjectId()) for _ in range(4))
        posts = FakePosts({post_id: {
            "_id": ObjectId(post_id), "board_id": "board", "author_id": owner_id,
            "owner_id": owner_id, "editor_ids": [editor_id], "version": 1,
        }})
        payload = PostCreate(title="운영 문서", content="수정 본문", editor_ids=[editor_id], owner_id=new_owner)
        editor = SimpleNamespace(id=editor_id, full_name="편집자", email="editor@example.com", is_admin=False)

        with patch("app.routers.boards.MongoClientManager.get_board_posts_collection", return_value=posts):
            with self.assertRaises(HTTPException) as error:
                await patch_post("board", post_id, payload, editor)

        self.assertEqual(error.exception.status_code, 403)

    async def test_rejects_parent_from_other_board(self):
        parent_id = str(ObjectId())
        posts = FakePosts({parent_id: {
            "_id": ObjectId(parent_id), "board_id": "another-board", "parent_id": None,
        }})

        with self.assertRaises(HTTPException) as error:
            await _validate_post_parent(posts, "board", parent_id)

        self.assertEqual(error.exception.status_code, 400)

    async def test_returns_parent_category_for_child(self):
        parent_id = str(ObjectId())
        posts = FakePosts({parent_id: {
            "_id": ObjectId(parent_id), "board_id": "board", "parent_id": None,
            "category": "운영 가이드",
        }})

        category = await _validate_post_parent(posts, "board", parent_id)

        self.assertEqual(category, "운영 가이드")


if __name__ == "__main__":
    unittest.main()
