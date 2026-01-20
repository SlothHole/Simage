import json
import sqlite3
from pathlib import Path

from simage.core.resolve import (
    ensure_table,
    import_manual_map,
    iter_dicts_deep,
    merge_extra_json,
    norm_kind,
    pick_sha256,
    rewrite_resources,
    upsert_mv,
)
from simage.utils.paths import repo_relative

def test_norm_kind_variants():
    assert norm_kind('checkpoint') == 'checkpoint'
    assert norm_kind('model') == 'checkpoint'
    assert norm_kind('ckpt') == 'checkpoint'
    assert norm_kind('lora') == 'lora'
    assert norm_kind('locon') == 'lora'
    assert norm_kind('lycoris') == 'lora'
    assert norm_kind('embedding') == 'embedding'
    assert norm_kind('textualinversion') == 'embedding'
    assert norm_kind('vae') == 'vae'
    assert norm_kind('controlnet') == 'controlnet'
    assert norm_kind('upscaler') == 'upscaler'
    assert norm_kind('unknown') is None
    assert norm_kind(None) is None


def test_pick_sha256_variants():
    sha = "a" * 64
    assert pick_sha256({"sha256": sha}) == sha
    assert pick_sha256({"hashes": {"SHA256": sha}}) == sha
    assert pick_sha256({"hash": sha}) == sha
    assert pick_sha256({"hash": "short"}) is None


def test_merge_extra_json_collisions():
    merged = merge_extra_json(json.dumps({"a": 1, "b": "x"}), {"b": "y", "c": 2})
    obj = json.loads(merged)
    assert obj["a"] == 1
    assert obj["c"] == 2
    assert obj["b"] in (["x", "y"], ["y", "x"])


def test_iter_dicts_deep():
    data = {"a": {"b": 1}, "c": [{"d": 2}, 3]}
    dicts = list(iter_dicts_deep(data))
    assert any(d.get("b") == 1 for d in dicts)
    assert any(d.get("d") == 2 for d in dicts)


def test_import_manual_map_json(tmp_path: Path):
    map_path = tmp_path / "map.json"
    map_path.write_text(
        json.dumps([{"modelVersionId": 123, "kind": "checkpoint", "name": "foo", "sha256": "b" * 64}]),
        encoding="utf-8",
    )

    with sqlite3.connect(":memory:") as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        rel = str(repo_relative(map_path))
        imported = import_manual_map(conn, rel)
        assert imported == 1
        row = conn.execute("SELECT model_version_id, kind, name FROM civitai_model_versions").fetchone()
        assert row["model_version_id"] == 123
        assert row["kind"] == "checkpoint"
        assert row["name"] == "foo"


def test_rewrite_resources_rewrites_rows():
    with sqlite3.connect(":memory:") as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        conn.execute(
            """
            CREATE TABLE resources (
                image_id TEXT,
                kind TEXT,
                name TEXT,
                hash TEXT,
                extra_json TEXT,
                weight REAL
            )
            """
        )
        conn.execute(
            "INSERT INTO resources(image_id, kind, name, hash, extra_json, weight) VALUES(?,?,?,?,?,?)",
            ("img1", "resource_ref", "modelVersionId:123", None, None, 1.0),
        )
        upsert_mv(conn, 123, "checkpoint", "foo", "urn:civitai:model:1:version:123", "c" * 64, {"src": "test"})
        scanned, rewritten = rewrite_resources(conn)
        row = conn.execute("SELECT kind, name, hash, extra_json FROM resources").fetchone()

        assert scanned == 1
        assert rewritten == 1
        assert row["kind"] == "checkpoint"
        assert row["name"] == "urn:civitai:model:1:version:123"
        assert row["hash"] == "c" * 64
        assert "resource_ref" in json.loads(row["extra_json"])
