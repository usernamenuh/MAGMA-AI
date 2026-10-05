import unittest

from utils.stored_text_audit import compare_text_pages


class StoredTextAuditTests(unittest.TestCase):
    def test_identifies_present_partial_and_missing_lines(self):
        source = [(1, "Nama Pengguna Contoh\nPeriode Laporan 1–4 September 2026\nKalimat yang hilang")]
        chunks = [("Nama Pengguna Contoh Periode Laporan 14 September 2026", 1)]

        report = compare_text_pages(source, chunks)

        self.assertEqual(report["status"], "compared")
        self.assertEqual([line["status"] for line in report["lines"]], ["matched", "partial", "missing"])
        self.assertEqual(report["summary"]["matched"], 1)
        self.assertEqual(report["summary"]["partial"], 1)
        self.assertEqual(report["summary"]["missing"], 1)
        self.assertIn("4", report["lines"][1]["missing_words"])

    def test_chunk_overlap_does_not_hide_a_missing_line(self):
        source = [(1, "Satu dua tiga\nEmpat lima enam\nTujuh delapan sembilan")]
        chunks = [("Satu dua tiga Empat lima enam", 1), ("Empat lima enam", 1)]

        report = compare_text_pages(source, chunks)

        self.assertEqual(report["lines"][2]["status"], "missing")

    def test_empty_text_layer_is_unverifiable_not_missing(self):
        report = compare_text_pages([(1, "")], [("Hasil OCR", 1)])

        self.assertEqual(report["status"], "unverifiable")
        self.assertEqual(report["summary"]["total_lines"], 0)
        self.assertEqual(report["unreadable_pages"], [1])

    def test_mixed_pdf_reports_unreadable_page(self):
        report = compare_text_pages([(1, "Teks halaman satu"), (2, "")], [("Teks halaman satu", 1), ("Hasil OCR", 2)])

        self.assertEqual(report["status"], "compared")
        self.assertEqual(report["unreadable_pages"], [2])

    def test_same_text_on_another_page_does_not_count(self):
        report = compare_text_pages([(1, "Hanya bagian pertama"), (2, "Teks halaman kedua")], [("Teks halaman kedua", 1)])

        self.assertEqual([line["status"] for line in report["lines"]], ["missing", "missing"])


if __name__ == "__main__":
    unittest.main()
