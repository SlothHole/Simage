import sqlite3
from pathlib import Path
from types import SimpleNamespace

from simage.core.wildcards import (
    apply_filters,
    connect,
    ensure_out_dir,
    export_kv,
    export_prompts,
    export_resources,
    export_sql,
    export_tokens,
    table_exists,
    write_lines,
)
from simage.utils.paths import repo_relative

def test_table_exists(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER)")
    assert table_exists(conn, "test")
    assert not table_exists(conn, "missing")
    conn.close()

def test_apply_filters():
    items = [("foo", 10), ("bar", 5), ("baz", 20)]
    # min_count
    filtered = apply_filters(items, None, None, 10, None)
    assert filtered == [("foo", 10), ("baz", 20)]
    # max_count
    filtered = apply_filters(items, None, None, 0, 10)
    assert filtered == [("foo", 10), ("bar", 5)]
    # include_re
    import re
    filtered = apply_filters(items, re.compile("ba"), None, 0, None)
    assert filtered == [("bar", 5), ("baz", 20)]
    # exclude_re
    filtered = apply_filters(items, None, re.compile("ba"), 0, None)
    assert filtered == [("foo", 10)]


def test_write_lines_creates_output(tmp_path: Path):
    out_path = tmp_path / "out" / "lines.txt"
    ensure_out_dir(str(out_path))
    count = write_lines(str(out_path), ["a", "", "b", "  ", "c"])
    assert count == 3
    assert out_path.read_text(encoding="utf-8").splitlines() == ["a", "b", "c"]


def _create_wildcards_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE tokens (t TEXT, t_norm TEXT, side TEXT)")
        conn.execute("CREATE TABLE kv (image_id TEXT, k TEXT, v TEXT, v_num REAL, v_json TEXT)")
        conn.execute("CREATE TABLE resources (kind TEXT, name TEXT, weight REAL)")
        conn.executemany(
            "INSERT INTO tokens (t, t_norm, side) VALUES (?,?,?)",
            [("Cat", "cat", "pos"), ("Dog", "dog", "pos"), ("Noise", "noise", "neg")],
        )
        conn.executemany(
            "INSERT INTO kv (image_id, k, v, v_num, v_json) VALUES (?,?,?,?,?)",
            [
                ("img1", "prompt_text", "a cat", None, None),
                ("img2", "prompt_text", "a dog", None, None),
                ("img1", "steps_norm", "30", 30.0, None),
            ],
        )
        conn.executemany(
            "INSERT INTO resources (kind, name, weight) VALUES (?,?,?)",
            [("lora", "style_a", 0.7), ("lora", "style_b", 1.0)],
        )
        conn.commit()


def test_export_functions(tmp_path: Path):
    db_path = tmp_path / "wildcards.db"
    _create_wildcards_db(db_path)

    rel_db = str(repo_relative(db_path))

    tokens_out = tmp_path / "tokens.txt"
    export_tokens(
        SimpleNamespace(
            db=rel_db,
            out=str(repo_relative(tokens_out)),
            side="pos",
            field="t_norm",
            min_count=1,
            max_count=None,
            include=None,
            exclude=None,
            sort="alpha",
            limit=None,
            with_count=False,
        )
    )
    assert tokens_out.read_text(encoding="utf-8").splitlines() == ["cat", "dog"]

    prompts_out = tmp_path / "prompts.txt"
    export_prompts(
        SimpleNamespace(
            db=rel_db,
            out=str(repo_relative(prompts_out)),
            which="pos",
            min_count=1,
            max_count=None,
            include=None,
            exclude=None,
            sort="count_desc",
            limit=None,
            with_count=False,
        )
    )
    assert "a cat" in prompts_out.read_text(encoding="utf-8")

    kv_out = tmp_path / "steps.txt"
    export_kv(
        SimpleNamespace(
            db=rel_db,
            out=str(repo_relative(kv_out)),
            key="steps_norm",
            column="v_num",
            min_count=1,
            max_count=None,
            include=None,
            exclude=None,
            sort="count_desc",
            limit=None,
            with_count=False,
        )
    )
    assert kv_out.read_text(encoding="utf-8").strip() == "30.0"

    res_out = tmp_path / "resources.txt"
    export_resources(
        SimpleNamespace(
            db=rel_db,
            out=str(repo_relative(res_out)),
            kind="lora",
            with_weight=False,
            min_count=1,
            max_count=None,
            include=None,
            exclude=None,
            sort="alpha",
            limit=None,
            with_count=False,
        )
    )
    assert res_out.read_text(encoding="utf-8").splitlines() == ["style_a", "style_b"]

    sql_out = tmp_path / "sql.txt"
    export_sql(
        SimpleNamespace(
            db=rel_db,
            out=str(repo_relative(sql_out)),
            sql="SELECT name FROM resources ORDER BY name",
        )
    )
    assert sql_out.read_text(encoding="utf-8").splitlines() == ["style_a", "style_b"]
