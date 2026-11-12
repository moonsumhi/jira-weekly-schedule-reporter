import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.routers.attachments import pptx_preview


class PptxPreviewTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.routers.attachments.subprocess.run")
    @patch("app.routers.attachments._resolve_safe_path")
    async def test_converts_presentation_with_isolated_libreoffice_profile(
        self, resolve_safe_path, run
    ):
        with tempfile.TemporaryDirectory() as source_dir:
            source = Path(source_dir) / "presentation.pptx"
            source.write_bytes(b"pptx")
            resolve_safe_path.return_value = source

            def convert(args, **_kwargs):
                output_dir = Path(args[args.index("--outdir") + 1])
                (output_dir / "presentation.pdf").write_bytes(b"%PDF-1.7")
                return SimpleNamespace(returncode=0, stderr="", stdout="")

            run.side_effect = convert
            response = await pptx_preview("pm/presentation.pptx")

        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.body, b"%PDF-1.7")
        command = run.call_args.args[0]
        self.assertTrue(any(arg.startswith("-env:UserInstallation=file:") for arg in command))


if __name__ == "__main__":
    unittest.main()
