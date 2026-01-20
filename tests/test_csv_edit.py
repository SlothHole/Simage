from simage.ui.csv_edit import amend_records_csv


def test_amend_records_csv_updates_and_adds(tmp_path):
    csv_path = tmp_path / "records.csv"
    csv_path.write_text(
        "file_name,prompt\nimg1.png,old\nimg2.png,keep\n",
        encoding="utf-8",
    )

    updates = [
        {"file_name": "img1.png", "prompt": "new"},
        {"file_name": "img3.png", "prompt": "added"},
    ]
    amend_records_csv(str(csv_path), updates)

    backup_path = tmp_path / "records.csv.bak"
    assert backup_path.exists()

    updated = csv_path.read_text(encoding="utf-8")
    assert "img1.png,new" in updated
    assert "img3.png,added" in updated
