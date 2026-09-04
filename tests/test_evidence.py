from android_automation_toolkit.evidence import create_evidence_directory


def test_evidence_folder_is_compact_but_unique(tmp_path) -> None:
    run_id = "12345678-1234-5678-1234-567812345678"
    directory = create_evidence_directory(tmp_path, run_id)
    assert directory.name.endswith("_12345678")
    assert len(directory.name) <= 20
