import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.docling_extractor import DocumentExtractionError, extract_chunks, extract_chunks_with_audit


class FirstPassExtractionTests(unittest.TestCase):
    def test_incomplete_text_is_returned_without_starting_docling(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "sample.pdf"
            pdf_path.touch()
            chunks = [("Teks penting yang sudah terbaca", 1)]
            audit = {
                "status": "INCOMPLETE",
                "important_text_total": 2,
                "important_text_missing": 1,
                "coverage_percent": 50.0,
                "missing_texts": [{"page": 1, "text": "Bagian lain"}],
                "total_pages": 1,
            }
            metadata = {}
            with patch("utils.docling_extractor.extract_chunks", return_value=chunks) as extract, patch(
                "utils.docling_extractor.audit_chunks", return_value=audit
            ):
                result = extract_chunks_with_audit(
                    str(pdf_path), extraction_mode="auto", extraction_metadata=metadata
                )

            self.assertEqual(result, chunks)
            self.assertEqual(extract.call_count, 1)
            self.assertEqual(extract.call_args.kwargs["extraction_mode"], "auto")
            self.assertEqual(metadata["status"], "INCOMPLETE")
            self.assertEqual(metadata["attempts"], 1)

    def test_auto_mode_does_not_start_ocr_when_text_layer_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "scan.pdf"
            pdf_path.touch()
            with patch("utils.docling_extractor._inspect_pdf", return_value=(1, True, True)), patch(
                "utils.docling_extractor._extract_text_layer_chunks", return_value=None
            ), patch("utils.docling_extractor._get_converter") as converter:
                with self.assertRaises(DocumentExtractionError):
                    extract_chunks(str(pdf_path), extraction_mode="auto")
            converter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
