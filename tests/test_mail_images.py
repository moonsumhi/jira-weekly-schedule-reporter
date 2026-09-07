import unittest
from unittest.mock import AsyncMock, patch

from app.utils import mail_notify


class MailImageTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_sr_events_replace_images_without_changing_saved_content(self):
        content = '작업 설명\n![사진](/api/uploads/photo(1).png "사진")\n후속 설명'
        doc = {"description": content, "requester_email": "test@example.com"}
        for event in ("reviewed", "assigned", "completed"):
            with self.subTest(event=event), patch.object(
                mail_notify, "_post_mail", new_callable=AsyncMock
            ) as send:
                await mail_notify.send_sr_notification(doc, event)
                description = send.call_args.args[2]["description"]
                self.assertEqual(description, f"작업 설명 / {mail_notify._IMAGE_NOTICE} / 후속 설명")
                self.assertEqual(doc["description"], content)

    def test_html_and_embedded_images(self):
        for content in ('<img src="/api/uploads/a.png" alt="a > b">',
                        '![사진](data:image/png;base64,AAAA)'):
            self.assertEqual(mail_notify._mail_description(content), mail_notify._IMAGE_NOTICE)

    def test_text_and_normal_links_preserved(self):
        content = '설명 [문서](https://example.com/doc)'
        self.assertEqual(mail_notify._mail_description(content), content)

    async def test_firewall_purpose(self):
        with patch.object(mail_notify, "_post_mail", new_callable=AsyncMock) as send:
            await mail_notify.send_sr_notification({
                "requester_email": "test@example.com", "request_type": "FIREWALL",
                "type_detail": {"purpose": "목적 ![사진](/api/uploads/a.png)"},
            }, "assigned")
            self.assertEqual(send.call_args.args[2]["description"], "목적 " + mail_notify._IMAGE_NOTICE)


if __name__ == "__main__":
    unittest.main()
