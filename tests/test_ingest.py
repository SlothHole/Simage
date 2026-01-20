import json
import os
import sqlite3
from pathlib import Path

from simage.core.ingest import (
    utc_now_iso,
    stable_id_for_path,
    sha256_file,
    is_probably_json,
    safe_json_loads,
    first_present,
    clean_ws,
    parse_ksampler_widgets,
    extract_comfyui_params,
    extract_comfyui_prompts,
    enforce_pos_neg_separation,
    split_tokens_top_level,
    parse_weighted_token,
    tokenize_prompt,
    normalize_sampler,
    normalize_scheduler,
    postprocess_prompts_and_params,
    extract_candidate_blobs,
    extract_keyed_fields,
    parse_a1111_parameters,
    parse_comfyui_embedded_json,
    merge_missing_values,
    normalize_key,
    record_key,
    init_db,
    upsert_record,
    load_jsonl,
    write_csv,
    normalize_record,
    merge_record_lists,
    compute_csv_columns,
)
from simage.utils.paths import REPO_ROOT

def test_utc_now_iso_format():
    result = utc_now_iso()
    assert result.endswith('Z')
    assert 'T' in result

def test_stable_id_for_path_consistency():
    path = 'test_image.png'
    id1 = stable_id_for_path(path)
    id2 = stable_id_for_path(path)
    assert id1 == id2
    assert isinstance(id1, str)

def test_sha256_file(tmp_path):
    tmp_file = tmp_path / "hash.bin"
    tmp_file.write_bytes(b"testdata")
    hash_val = sha256_file(os.fspath(tmp_file))
    assert isinstance(hash_val, str)

def test_is_probably_json():
    assert is_probably_json('{"a":1}')
    assert is_probably_json('[1,2,3]')
    assert not is_probably_json('not json')

def test_safe_json_loads():
    assert safe_json_loads('{"a":1}') == {"a":1}
    assert safe_json_loads('invalid') is None

def test_first_present():
    d = {"a": 1, "b": None}
    assert first_present(d, ["b", "a"]) == 1
    assert first_present(d, ["c"]) is None

def test_clean_ws():
    s = 'a   b\n\n\n\nc'
    cleaned = clean_ws(s)
    assert '\n\n' in cleaned
    assert cleaned.startswith('a')

def test_parse_ksampler_widgets_extracts_params():
    values = [True, 1081302725092220, "randomize", 21, 4, "euler_cfg_pp", "simple", 0]
    out = parse_ksampler_widgets(values)
    assert out["seed"] == 1081302725092220
    assert out["steps"] == 21
    assert out["cfg_scale"] == 4.0
    assert out["sampler"] == "euler_cfg_pp"
    assert out["scheduler"] == "simple"

def test_extract_comfyui_params_from_widgets():
    workflow = {
        "nodes": [
            {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model.safetensors"},
            },
            {
                "class_type": "KSamplerAdvanced",
                "widgets_values": [True, 123456789, "randomize", 20, 7, "euler", "simple"],
            },
        ]
    }
    out = extract_comfyui_params(workflow)
    assert out["model"] == "model.safetensors"
    assert out["seed"] == 123456789
    assert out["steps"] == 20
    assert out["cfg_scale"] == 7.0
    assert out["sampler"] == "euler"
    assert out["scheduler"] == "simple"

def test_extract_comfyui_prompts_from_nodes():
    workflow = {
        "nodes": [
            {"type": "Prompt (LoraManager)", "widgets_values": ["pos text"]},
            {"type": "CLIPTextEncode", "title": "CLIP Text Encode (Negative Prompt)", "widgets_values": ["neg text"]},
        ]
    }
    pos, neg = extract_comfyui_prompts(workflow)
    assert pos == "pos text"
    assert neg == "neg text"

def test_merge_record_lists_preserves_old_values():
    old_records = [
        {"source_file": "Input/a.png", "prompt": "old", "steps": "30"},
        {"source_file": "Input/missing.png", "prompt": "keep"},
    ]
    new_records = [
        {"source_file": "Input/a.png", "prompt": "", "steps": None},
        {"source_file": "Input/b.png", "prompt": "new"},
    ]
    merged = merge_record_lists([dict(r) for r in new_records], old_records)
    merged_map = {r.get("source_file"): r for r in merged}
    assert merged_map["Input/a.png"]["prompt"] == "old"
    assert merged_map["Input/a.png"]["steps"] == "30"
    assert "Input/missing.png" in merged_map
    assert merged_map["Input/missing.png"]["prompt"] == "keep"

def test_compute_csv_columns_includes_extras():
    records = [{"file_name": "a.png", "extra_field": "x"}]
    cols = compute_csv_columns(records)
    assert "extra_field" in cols


def test_enforce_pos_neg_separation_splits_and_cleans():
    pos = "A cat. Negative prompt: blurry Steps: 30, Sampler: Euler"
    new_pos, new_neg = enforce_pos_neg_separation(pos, None)
    assert new_pos == "A cat."
    assert new_neg == "blurry"


def test_split_tokens_top_level_respects_brackets():
    toks = split_tokens_top_level("a,(b,c),d BREAK e")
    assert toks == ["a", "(b,c)", "d", "e"]


def test_parse_weighted_token_variants():
    assert parse_weighted_token("(cat:1.2)") == ("cat", 1.2)
    assert parse_weighted_token("<lora:style:0.5>") == ("lora:style", 0.5)
    assert parse_weighted_token("dog") == ("dog", 1.0)


def test_tokenize_prompt_dedupes_and_weights():
    toks = tokenize_prompt("cat, dog, cat, (bird:1.2), <lora:style:0.5>")
    norms = {t["t_norm"] for t in toks}
    assert "cat" in norms
    assert "dog" in norms
    assert "bird" in norms
    assert "lora:style" in norms


def test_normalize_sampler_scheduler():
    assert normalize_sampler("Euler A") == "euler_a"
    assert normalize_scheduler("SGM Uniform") == "sgm_uniform"


def test_postprocess_prompts_and_params_populates_kv():
    rec = {
        "prompt": "a cat",
        "negative_prompt": "blurry",
        "sampler": "Euler A",
        "scheduler": "Karras",
        "steps": 20,
        "cfg_scale": 7.5,
        "seed": 123,
        "width": 512,
        "height": 512,
        "kv": {},
    }
    postprocess_prompts_and_params(rec)
    kv = rec["kv"]
    assert kv["prompt_text"] == "a cat"
    assert kv["neg_prompt_text"] == "blurry"
    assert kv["sampler_norm"] == "euler_a"
    assert kv["scheduler_norm"] == "karras"
    assert kv["steps_norm"] == 20
    assert kv["cfg_scale_norm"] == 7.5
    assert kv["seed_norm"] == 123
    assert kv["size_norm"] == "512x512"


def test_extract_candidate_blobs_picks_keys_and_markers():
    exif_obj = {
        "PNG:Parameters": "Steps: 20",
        "Other": "seed: 42 " + ("x" * 40),
    }
    blobs = extract_candidate_blobs(exif_obj)
    keys = {k for k, _v in blobs}
    assert "PNG:Parameters" in keys
    assert "Other" in keys


def test_extract_keyed_fields_prefers_prompt_keys():
    exif_obj = {
        "PNG:Prompt": "pos text",
        "PNG:NegativePrompt": "neg text",
    }
    out = extract_keyed_fields(exif_obj)
    assert out["prompt"] == "pos text"
    assert out["negative_prompt"] == "neg text"


def test_extract_keyed_fields_skips_camera_model():
    exif_obj = {"EXIF:Model": "Canon EOS"}
    out = extract_keyed_fields(exif_obj)
    assert "model" not in out


def test_parse_a1111_parameters_extracts_fields():
    text = (
        "Prompt text. Negative prompt: bad "
        "Steps: 30, Sampler: Euler a, CFG scale: 7, Seed: 42, Size: 512x512, Model: foo"
    )
    parsed = parse_a1111_parameters(text)
    assert parsed["prompt"] == "Prompt text."
    assert parsed["negative_prompt"] == "bad"
    assert parsed["steps"] == 30
    assert parsed["cfg_scale"] == 7.0
    assert parsed["seed"] == 42
    assert parsed["width"] == 512
    assert parsed["height"] == 512
    assert parsed["sampler"] == "Euler a"
    assert parsed["model"] == "foo"


def test_parse_comfyui_embedded_json_extracts_prompt_and_params():
    blob = {
        "nodes": [
            {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
            {
                "class_type": "KSampler",
                "inputs": {"seed": 123, "steps": 20, "cfg": 7, "sampler_name": "euler", "scheduler": "karras"},
            },
        ],
        "meta": {"positive": "good", "negative": "bad"},
    }
    rec = parse_comfyui_embedded_json(blob)
    assert rec is not None
    assert rec["prompt"] == "good"
    assert rec["negative_prompt"] == "bad"
    assert rec["model"] == "model.safetensors"
    assert rec["seed"] == 123
    assert rec["steps"] == 20


def test_merge_missing_values_and_record_key():
    target = {"source_file": "Input\\Foo.png", "meta": {"a": None}}
    source = {"meta": {"a": 1, "b": 2}}
    merge_missing_values(target, source)
    assert target["meta"]["a"] == 1
    assert target["meta"]["b"] == 2

    assert normalize_key("Input\\Foo.png") == "input/foo.png"
    assert record_key(target) == "input/foo.png"


def test_load_jsonl_skips_invalid(tmp_path: Path):
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": 1}\nnot json\n{"b": 2}\n', encoding="utf-8")
    records = load_jsonl(os.fspath(path))
    assert records == [{"a": 1}, {"b": 2}]


def test_write_csv_outputs_header_and_rows(tmp_path: Path):
    csv_path = tmp_path / "records.csv"
    records = [{"file_name": "a.png", "prompt": "cat"}, {"file_name": "b.png", "prompt": "dog"}]
    write_csv(os.fspath(csv_path), records, columns=["file_name", "prompt"])
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "file_name,prompt"
    assert "a.png,cat" in lines[1]


def test_init_db_and_upsert_record(tmp_path: Path):
    db_path = tmp_path / "images.db"
    schema_path = REPO_ROOT / "simage" / "data" / "schema.sql"
    init_db(os.fspath(db_path), os.fspath(schema_path))

    rec = {
        "id": "img1",
        "source_file": "Input/img1.png",
        "file_name": "img1.png",
        "ext": "png",
        "width": 64,
        "height": 64,
        "created_utc": None,
        "imported_utc": "2020-01-01T00:00:00Z",
        "sha256": None,
        "format_hint": "a1111_like",
        "raw_text_preview": "preview",
        "kv": {"steps": 20, "prompt": "cat", "meta": {"a": 1}},
    }

    with sqlite3.connect(db_path) as conn:
        upsert_record(conn, rec)
        row = conn.execute("SELECT file_name FROM images WHERE id='img1'").fetchone()
        assert row[0] == "img1.png"
        kv_rows = conn.execute("SELECT k, v, v_num, v_json FROM kv WHERE image_id='img1'").fetchall()
        kv_map = {r[0]: r for r in kv_rows}
        assert "steps" in kv_map
        assert kv_map["steps"][2] == 20.0
        assert kv_map["meta"][3] == '{"a": 1}'


def test_normalize_record_extracts_prompt(tmp_path: Path):
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"fake")
    text = "A cat. Negative prompt: blurry Steps: 10, Sampler: Euler a, CFG scale: 7, Seed: 1, Size: 64x64"
    exif_obj = {"SourceFile": os.fspath(img_path), "PNG:Parameters": text}
    rec = normalize_record(exif_obj)
    assert rec["file_name"] == "test.png"
    assert rec["prompt"] == "A cat."
    assert rec["negative_prompt"] == "blurry"


def test_normalize_record_prefers_workflow_prompt(tmp_path: Path):
    img_path = tmp_path / "test2.png"
    img_path.write_bytes(b"fake")
    workflow = {
        "nodes": [
            {"type": "Prompt (LoraManager)", "widgets_values": ["workflow prompt"]},
        ]
    }
    exif_obj = {
        "SourceFile": os.fspath(img_path),
        "PNG:Parameters": "A1111 prompt. Steps: 10",
        "PNG:Workflow": json.dumps(workflow),
    }
    rec = normalize_record(exif_obj)
    assert rec["prompt"] == "workflow prompt"
