# -*- coding: utf-8 -*-
"""
Tests for the SQLite index builder in
:mod:`wparc.wpapi.index.sqlite_index`.
"""
import json
import sqlite3

import pytest

from wparc.wpapi.index import sqlite_index


def _write_jsonl(tmp_path, name, rows):
    """Write a JSONL file with the given rows. Returns its absolute path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    path = data_dir / name
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


class TestBuildIndex:
    def test_indexes_jsonl_files(self, tmp_path):
        _write_jsonl(
            tmp_path,
            "wp_v2_posts.jsonl",
            [
                {"id": 1, "title": {"rendered": "Hello"}, "slug": "hello"},
                {"id": 2, "title": {"rendered": "World"}, "slug": "world"},
            ],
        )
        _write_jsonl(
            tmp_path,
            "wp_v2_pages.jsonl",
            [{"id": 100, "title": {"rendered": "About"}, "slug": "about"}],
        )

        result = sqlite_index.build_index(str(tmp_path))
        assert result["files"] == 2
        assert result["records"] == 3
        # The database must exist and contain the expected rows.
        conn = sqlite3.connect(result["db_path"])
        try:
            rows = conn.execute(
                "SELECT id, slug, source_file FROM records ORDER BY rowid"
            ).fetchall()
        finally:
            conn.close()
        assert rows == [
            ("100", "about", str(tmp_path / "data" / "wp_v2_pages.jsonl")),
            ("1", "hello", str(tmp_path / "data" / "wp_v2_posts.jsonl")),
            ("2", "world", str(tmp_path / "data" / "wp_v2_posts.jsonl")),
        ]

    def test_unwraps_rendered_field(self, tmp_path):
        """WP wraps strings like ``title`` in ``{"rendered": ...}``."""
        _write_jsonl(
            tmp_path,
            "wp_v2_posts.jsonl",
            [{"id": 1, "title": {"rendered": "Hello"}}],
        )
        result = sqlite_index.build_index(str(tmp_path))
        conn = sqlite3.connect(result["db_path"])
        try:
            title = conn.execute("SELECT title FROM records WHERE id = '1'").fetchone()[0]
        finally:
            conn.close()
        assert title == "Hello"

    def test_extras_preserves_unknown_keys(self, tmp_path):
        """Non-promoted keys survive in the ``extras`` JSON column."""
        _write_jsonl(
            tmp_path,
            "wp_v2_posts.jsonl",
            [
                {
                    "id": 1,
                    "title": {"rendered": "Hello"},
                    "custom_field": {"rendered": "x"},
                }
            ],
        )
        result = sqlite_index.build_index(str(tmp_path))
        conn = sqlite3.connect(result["db_path"])
        try:
            extras = json.loads(
                conn.execute("SELECT extras FROM records WHERE id = '1'").fetchone()[0]
            )
        finally:
            conn.close()
        assert extras == {"custom_field": {"rendered": "x"}}

    def test_skips_malformed_lines(self, tmp_path, caplog):
        _write_jsonl(
            tmp_path,
            "wp_v2_posts.jsonl",
            [
                {"id": 1, "title": "ok"},
                {"id": 2, "title": "also ok"},
            ],
        )
        # Append a malformed line directly.
        with open(tmp_path / "data" / "wp_v2_posts.jsonl", "a") as f:
            f.write("not a valid json line\n")
        with caplog.at_level("WARNING"):
            result = sqlite_index.build_index(str(tmp_path))
        assert result["records"] == 2

    def test_missing_data_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            sqlite_index.build_index(str(tmp_path))

    def test_no_jsonl_files_yields_empty_db(self, tmp_path):
        (tmp_path / "data").mkdir()
        result = sqlite_index.build_index(str(tmp_path))
        assert result["files"] == 0
        assert result["records"] == 0
        # The database is still created with the schema.
        conn = sqlite3.connect(result["db_path"])
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master " "WHERE type='table' AND name='records'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert count == 1


class TestCLIIntegration:
    """End-to-end: invoking ``wparc index`` against a dump directory."""

    def test_index_command_runs(self, tmp_path):
        from typer.testing import CliRunner

        from wparc.core import app

        _write_jsonl(
            tmp_path,
            "wp_v2_posts.jsonl",
            [{"id": 1, "title": {"rendered": "Hello"}}],
        )
        runner = CliRunner()
        result = runner.invoke(app, ["index", str(tmp_path)])
        assert result.exit_code == 0
        assert "SQLite index built" in result.output
        assert "1 records" in result.output

    def test_index_command_no_data_dir(self, tmp_path):
        from typer.testing import CliRunner

        from wparc.core import app

        runner = CliRunner()
        result = runner.invoke(app, ["index", str(tmp_path)])
        assert result.exit_code == 1
        assert "Data directory not found" in result.output
