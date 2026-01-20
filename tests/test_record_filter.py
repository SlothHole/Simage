from simage.ui.record_filter import filter_by_tags, filter_records, load_records


def test_load_and_filter_records(tmp_path):
    csv_path = tmp_path / "records.csv"
    csv_path.write_text(
        "file_name,prompt\nimg1.png,a cat with hat\nimg2.png,a dog\n",
        encoding="utf-8",
    )

    records = load_records(str(csv_path))
    assert len(records) == 2

    filtered = filter_records(records, "cat")
    assert len(filtered) == 1
    assert filtered[0]["file_name"] == "img1.png"

    tagged = filter_by_tags(records, ["cat", "hat"])
    assert len(tagged) == 1
    assert tagged[0]["file_name"] == "img1.png"
