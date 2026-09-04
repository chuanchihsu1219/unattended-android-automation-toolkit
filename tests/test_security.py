from android_automation_toolkit.security import SecretRedactor


def test_redacts_literals_keys_and_xml() -> None:
    redactor = SecretRedactor("value-only-known-locally")
    text = redactor.text("PASSWORD=hunter2 value-only-known-locally")
    assert "hunter2" not in text
    assert "value-only-known-locally" not in text
    nested = redactor.object({"safe": "ok", "token": "different-value"})
    assert nested == {"safe": "ok", "token": "[REDACTED]"}
    xml = redactor.xml('<node text="value-only-known-locally" />')
    assert "value-only-known-locally" not in xml
