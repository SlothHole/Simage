import sqlite3

from simage.core.resources import (
    as_float,
    classify_urn,
    dedupe_resources,
    ensure_resources_table,
    extract_from_extra_airs,
    extract_from_extra_metadata,
    extract_from_nodes,
    get_inputs,
    iter_node_dicts,
    normalize_class_type,
)

def test_as_float_valid():
    assert as_float('1.23') == 1.23
    assert as_float(2) == 2.0
    assert as_float(None) is None
    assert as_float('not_a_float') is None

def test_classify_urn():
    assert classify_urn('urn:air:sdxl:checkpoint:civitai:foo') == 'checkpoint'
    assert classify_urn('urn:air:sdxl:lora:civitai:foo') == 'lora'
    assert classify_urn('urn:air:sdxl:embedding:civitai:foo') == 'embedding'
    assert classify_urn('urn:air:sdxl:vae:civitai:foo') == 'vae'
    assert classify_urn('urn:air:sdxl:upscaler:civitai:foo') == 'upscaler'
    assert classify_urn('urn:air:sdxl:controlnet:civitai:foo') == 'controlnet'
    assert classify_urn('urn:air:sdxl:other:civitai:foo') is None


def test_iter_node_dicts_and_normalizers():
    workflow = {
        "nodes": [
            {"id": 1, "class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
            {"id": 2, "type": "LoraLoader", "inputs": {"lora_name": "style.safetensors"}},
        ],
        "prompt": {"3": {"class_type": "VAELoader", "inputs": {"vae_name": "vae.safetensors"}}},
    }
    ids = [nid for nid, _node in iter_node_dicts(workflow)]
    assert set(ids) == {"1", "2", "3"}

    node = {"type": "Foo", "inputs": {"a": 1}}
    assert normalize_class_type(node) == "Foo"
    assert get_inputs(node) == {"a": 1}


def test_extract_from_nodes():
    workflow = {
        "nodes": [
            {"id": 1, "class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
            {"id": 2, "class_type": "LoraLoader", "inputs": {"lora_name": "style.safetensors", "strength_model": "0.7"}},
            {"id": 3, "class_type": "UpscaleModelLoader", "inputs": {"model_name": "upscaler.pth"}},
            {"id": 4, "class_type": "ControlNetLoader", "inputs": {"control_net_name": "control.safetensors", "strength": 0.5}},
            {"id": 5, "class_type": "VAELoader", "inputs": {"vae_name": "vae.safetensors"}},
            {"id": 6, "class_type": "EmbeddingLoader", "inputs": {"embedding_name": "emb.pt"}},
        ]
    }
    items = extract_from_nodes(workflow)
    kinds = {it["kind"] for it in items}
    assert {"checkpoint", "lora", "upscaler", "controlnet", "vae", "embedding"} <= kinds


def test_extract_from_extra_fallbacks():
    workflow = {"extra": {"airs": ["urn:air:sdxl:checkpoint:civitai:foo", "urn:air:sdxl:lora:civitai:bar"]}}
    items = extract_from_extra_airs(workflow)
    kinds = {it["kind"] for it in items}
    assert kinds == {"checkpoint", "lora"}

    workflow = {"extraMetadata": '{"resources": [{"modelVersionId": 123, "strength": 0.6}]}'}
    items = extract_from_extra_metadata(workflow)
    assert items[0]["kind"] == "resource_ref"
    assert items[0]["name"] == "modelVersionId:123"


def test_dedupe_resources_merges_weight_and_extra():
    items = [
        {"kind": "lora", "name": "style", "weight": None, "extra": {"a": 1}},
        {"kind": "lora", "name": "style", "weight": 0.5, "extra": {"b": 2}},
    ]
    deduped = dedupe_resources(items)
    assert len(deduped) == 1
    assert deduped[0]["weight"] == 0.5
    assert deduped[0]["extra"]["a"] == 1
    assert deduped[0]["extra"]["b"] == 2


def test_ensure_resources_table_creates_table():
    with sqlite3.connect(":memory:") as conn:
        ensure_resources_table(conn)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='resources'"
        ).fetchone()
        assert row is not None
