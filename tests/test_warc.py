# -*- coding: utf-8 -*-
"""
Tests for the WARC exporter in :mod:`wparc.wpapi.warc.writer`.
"""
import gzip
import json

import pytest

from wparc.wpapi.warc import writer


def _write_jsonl(tmp_path, name, rows):
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    path = data_dir / name
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


class TestExportWarc:
    def test_writes_gzipped_warc(self, tmp_path):
        _write_jsonl(
            tmp_path,
            "wp_v2_posts.jsonl",
            [
                {"id": 1, "title": {"rendered": "Hello"}},
                {"id": 2, "title": {"rendered": "World"}},
            ],
        )
        result = writer.export_warc(str(tmp_path))
        assert result["records"] == 2

        out_path = result["output_path"]
        assert out_path.endswith(".warc.gz")

        # Decompress and inspect.
        with gzip.open(out_path, "rt", encoding="utf-8") as f:
            text = f.read()
        # ``gzip.open`` in text mode normalises line endings to ``\n``;
        # the underlying bytes still contain ``\r\n`` separators.
        assert text.startswith("WARC/1.0")
        # The first record must be a warcinfo block.
        assert "WARC-Type: warcinfo" in text
        # Each row produces a response record.
        assert text.count("WARC-Type: response") == 2
        # The slug-derived target URI is preserved.
        assert "wp_v2_posts.jsonl#1" in text
        assert "wp_v2_posts.jsonl#2" in text

    def test_uncompressed_warc(self, tmp_path):
        _write_jsonl(tmp_path, "wp_v2_posts.jsonl", [{"id": 1}])
        result = writer.export_warc(str(tmp_path), output_filename="dump.warc", compress=False)
        assert result["output_path"].endswith(".warc")
        with open(result["output_path"], "r", encoding="utf-8") as f:
            text = f.read()
        assert "WARC-Type: response" in text

    def test_missing_data_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            writer.export_warc(str(tmp_path))

    def test_record_id_includes_source(self, tmp_path):
        _write_jsonl(tmp_path, "wp_v2_posts.jsonl", [{"id": 42}])
        result = writer.export_warc(str(tmp_path))
        with gzip.open(result["output_path"], "rt", encoding="utf-8") as f:
            text = f.read()
        assert "<wparc:wp_v2_posts.jsonl:42>" in text

    def test_skips_malformed_lines(self, tmp_path, caplog):
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "wp_v2_posts.jsonl").write_text(
            '{"id": 1}\nnot a valid json line\n{"id": 2}\n',
            encoding="utf-8",
        )
        with caplog.at_level("WARNING"):
            result = writer.export_warc(str(tmp_path))
        # Only the two valid records count.
        assert result["records"] == 2

    def test_non_dict_scalar_record(self, tmp_path):
        # Some endpoints can return scalar JSON; the exporter must wrap them.
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "scalar.jsonl").write_text('42\n"hello"\n', encoding="utf-8")
        result = writer.export_warc(str(tmp_path))
        assert result["records"] == 2


class TestCLIIntegration:
    def test_warc_command_runs(self, tmp_path):
        from typer.testing import CliRunner

        from wparc.core import app

        _write_jsonl(tmp_path, "wp_v2_posts.jsonl", [{"id": 1}])
        runner = CliRunner()
        result = runner.invoke(app, ["warc", str(tmp_path)])
        assert result.exit_code == 0
        assert "WARC archive written" in result.output

    def test_warc_command_no_data_dir(self, tmp_path):
        from typer.testing import CliRunner

        from wparc.core import app

        runner = CliRunner()
        result = runner.invoke(app, ["warc", str(tmp_path)])
        assert result.exit_code == 1
