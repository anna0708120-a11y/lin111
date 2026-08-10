"""Phase 8 attachment contract tests. No Storage, database, or model calls."""
from __future__ import annotations

import unittest

from app.attachments import (
    AttachmentValidationError,
    MAX_FILE_BYTES,
    build_attachment,
    normalize_filename,
    public_attachment,
    validate_upload,
)


class AttachmentContractTests(unittest.TestCase):
    def test_image_contract_uses_private_object_key(self):
        attachment = build_attachment("../photo.png", "image/png", b"png-bytes", owner_type="chat")
        self.assertEqual(attachment["kind"], "image")
        self.assertEqual(attachment["filename"], "photo.png")
        self.assertTrue(attachment["object_key"].startswith("chat/"))
        self.assertTrue(attachment["object_key"].endswith(".png"))
        self.assertNotIn("url", attachment)

    def test_document_contract_is_shared_with_agent(self):
        attachment = build_attachment("brief.pdf", "application/pdf", b"pdf", owner_type="agent")
        self.assertEqual(attachment["kind"], "file")
        self.assertEqual(attachment["owner_type"], "agent")
        self.assertEqual(attachment["mime_type"], "application/pdf")

    def test_rejects_unknown_type_empty_and_oversized_content(self):
        with self.assertRaisesRegex(AttachmentValidationError, "unsupported_mime_type"):
            validate_upload("malware.exe", "application/octet-stream", b"x")
        with self.assertRaisesRegex(AttachmentValidationError, "empty_file"):
            validate_upload("note.txt", "text/plain", b"")
        with self.assertRaisesRegex(AttachmentValidationError, "file_too_large"):
            validate_upload("note.txt", "text/plain", b"x" * (MAX_FILE_BYTES + 1))

    def test_public_contract_does_not_expose_object_key(self):
        attachment = build_attachment("note.txt", "text/plain", b"hello")
        attachment["url"] = "https://signed.example/file"
        public = public_attachment(attachment)
        self.assertNotIn("object_key", public)
        self.assertEqual(public["filename"], "note.txt")
        self.assertEqual(public["url"], "https://signed.example/file")

    def test_filename_cannot_escape_object_key(self):
        self.assertEqual(normalize_filename("../../"), "upload")


if __name__ == "__main__":
    unittest.main()
