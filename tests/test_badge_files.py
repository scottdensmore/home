"""Synthetic checker regressions; no badge app is imported or executed."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_badge_files as checker


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def tiny_png():
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return checker.PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"\0\0\0\0")) + chunk(b"IEND", b"")


class BadgeFilesTests(unittest.TestCase):
    def test_parse_does_not_execute_device_or_filesystem_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "must-not-exist"
            source = f"import machine\nopen({str(marker)!r}, 'w').write('bad')\nrun(update)"
            checker.parse_source(source)
            self.assertFalse(marker.exists())

    def test_python_syntax_failure_is_not_ignored(self):
        with self.assertRaises(SyntaxError):
            checker.parse_source("def broken(:\n")

    def test_current_nested_fstring_grammar_is_accepted(self):
        checker.parse_source('text = f"{state["current"]}ml"')

    def test_empty_templates_accept_locale_fields(self):
        source = "\n".join(f'{name} = ""' for name in checker.CREDENTIAL_FIELDS)
        checker.check_template(checker.parse_source(source + '\nREGION = "GB"\nTIMEZONE = 0'))

    def test_credentials_and_missing_fields_are_rejected_without_values(self):
        source = "\n".join(f'{name} = ""' for name in checker.CREDENTIAL_FIELDS)
        source = source.replace('GITHUB_TOKEN = ""', 'GITHUB_TOKEN = "SYNTHETIC_SECRET"')
        with self.assertRaises(checker.InvalidAsset) as caught:
            checker.check_template(checker.parse_source(source))
        self.assertNotIn("SYNTHETIC_SECRET", str(caught.exception))
        with self.assertRaises(checker.InvalidAsset):
            checker.check_template(checker.parse_source('WIFI_SSID = ""'))

    def test_valid_png_container(self):
        checker.check_png(tiny_png())

    def test_corrupt_and_truncated_png_containers_fail(self):
        valid = tiny_png()
        corrupt = bytearray(valid)
        corrupt[29] ^= 1
        for data in (b"not-png", valid[:-1], bytes(corrupt), valid + b"extra"):
            with self.subTest(length=len(data)):
                with self.assertRaises(checker.InvalidAsset):
                    checker.check_png(data)

    def test_empty_export_trees_are_not_a_false_success(self):
        with tempfile.TemporaryDirectory() as directory:
            _, errors = checker.validate(Path(directory))
            self.assertEqual(len(errors), 4)


if __name__ == "__main__":
    unittest.main()
