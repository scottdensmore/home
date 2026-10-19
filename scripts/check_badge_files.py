"""Static badge filesystem checks; never import or execute app modules."""
import ast
import json
from pathlib import Path
import struct
import sys
import zlib

CREDENTIAL_FIELDS = ("WIFI_SSID", "WIFI_PASSWORD", "GITHUB_USERNAME", "GITHUB_TOKEN")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class InvalidAsset(ValueError):
    pass


def parse_source(data):
    return ast.parse(data, feature_version=(3, 12))


def check_template(tree):
    assignments = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in CREDENTIAL_FIELDS:
                    empty = isinstance(node.value, ast.Constant) and node.value.value == ""
                    if not empty:
                        raise InvalidAsset("credential template must contain empty literal values")
                    assignments[target.id] = True
    if set(assignments) != set(CREDENTIAL_FIELDS):
        raise InvalidAsset("credential template fields missing")


def check_png(data):
    if not data.startswith(PNG_SIGNATURE):
        raise InvalidAsset("invalid PNG signature")
    offset = len(PNG_SIGNATURE)
    chunks = 0
    image_data = False
    while offset < len(data):
        if len(data) - offset < 12:
            raise InvalidAsset("truncated PNG chunk")
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise InvalidAsset("truncated PNG payload")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        if zlib.crc32(kind + payload) != expected_crc:
            raise InvalidAsset("PNG checksum mismatch")
        if chunks == 0:
            if kind != b"IHDR" or length != 13:
                raise InvalidAsset("missing PNG header")
            width, height = struct.unpack_from(">II", payload)
            if not width or not height:
                raise InvalidAsset("invalid PNG dimensions")
        if kind == b"IDAT" and length:
            image_data = True
        if kind == b"IEND":
            if length != 0 or end != len(data) or not image_data:
                raise InvalidAsset("invalid PNG end or missing image data")
            return
        chunks += 1
        offset = end
    raise InvalidAsset("missing PNG end")


def validate(root):
    counts = {"Python": 0, "JSON": 0, "PNG": 0, "templates": 0}
    errors = []
    for directory in ("badge", "badge25"):
        folder = root / directory
        sources = sorted(folder.rglob("*.py"))
        if not sources:
            errors.append(f"{directory}: no Python sources found")
        for path in sources:
            counts["Python"] += 1
            try:
                tree = parse_source(path.read_bytes())
                if path == folder / "secrets.py":
                    check_template(tree)
                    counts["templates"] += 1
            except SyntaxError as error:
                errors.append(f"{path.relative_to(root)}: invalid Python syntax at line {error.lineno}")
            except InvalidAsset as error:
                errors.append(f"{path.relative_to(root)}: {error}")
            except (OSError, UnicodeError, ValueError):
                errors.append(f"{path.relative_to(root)}: unreadable Python source")
        if not (folder / "secrets.py").is_file():
            errors.append(f"{directory}: credential template missing")
        for path in sorted(folder.rglob("*.json")):
            counts["JSON"] += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError):
                errors.append(f"{path.relative_to(root)}: invalid JSON")
        for path in sorted(folder.rglob("*.png")):
            counts["PNG"] += 1
            try:
                check_png(path.read_bytes())
            except InvalidAsset as error:
                errors.append(f"{path.relative_to(root)}: {error}")
            except OSError:
                errors.append(f"{path.relative_to(root)}: unreadable PNG")
    return counts, errors


def main():
    if sys.version_info < (3, 12):
        print("The host syntax checker requires existing Python 3.12 or newer.")
        return 1
    root = Path(__file__).resolve().parents[1]
    counts, errors = validate(root)
    print("Static checks:", ", ".join(f"{key}={value}" for key, value in counts.items()))
    for error in errors:
        print(error)
    print(f"{len(errors)} errors. Badge execution and firmware API compatibility are not validated.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
