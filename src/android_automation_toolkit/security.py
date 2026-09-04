from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from xml.etree import ElementTree


SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(account|authorization|credential|email|password|passwd|pwd|secret|token|username)"
)


class SecretRedactor:
    def __init__(self, *secrets: str) -> None:
        self._secrets = tuple(sorted({value for value in secrets if value}, key=len, reverse=True))

    def text(self, value: object) -> str:
        result = str(value)
        for secret in self._secrets:
            result = result.replace(secret, "[REDACTED]")
        return re.sub(
            r"(?i)\b(ACCOUNT|AUTHORIZATION|EMAIL|PASSWORD|PASSWD|PWD|SECRET|TOKEN|USERNAME)\s*[=:]\s*([^\s,;]+)",
            r"\1=[REDACTED]",
            result,
        )

    def object(self, value: Any, key: str = "") -> Any:
        if key and SENSITIVE_KEY_PATTERN.search(key):
            return "[REDACTED]"
        if isinstance(value, Mapping):
            return {str(k): self.object(v, str(k)) for k, v in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [self.object(item) for item in value]
        if isinstance(value, str):
            return self.text(value)
        return value

    def xml(self, xml_text: str) -> str:
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            return self.text(xml_text)
        for node in root.iter():
            if node.text:
                node.text = self.text(node.text)
            for name, value in tuple(node.attrib.items()):
                node.attrib[name] = self.text(value)
        return ElementTree.tostring(root, encoding="unicode")
