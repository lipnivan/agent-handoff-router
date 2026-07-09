from __future__ import annotations

from typing import Any


def _parse_scalar(value: str) -> Any:
    text = value.strip()
    if text == "":
        return ""
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if text.lower() == "null":
        return None
    if text.isdigit():
        return int(text)
    return text


def loads(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            if current_list_key is None:
                raise ValueError("list item without a key")
            data[current_list_key].append(_parse_scalar(line[4:]))
            continue
        if ":" not in line:
            raise ValueError(f"invalid line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = _parse_scalar(value)
            current_list_key = None
    return data


def dumps(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"
