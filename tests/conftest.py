# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures.
"""
import os
import tempfile
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_media_file(temp_dir):
    """Create a sample media JSONL file."""
    media_dir = os.path.join(temp_dir, "data")
    os.makedirs(media_dir, exist_ok=True)
    media_file = os.path.join(media_dir, "wp_v2_media.jsonl")

    with open(media_file, "w", encoding="utf8") as f:
        f.write('{"source_url": "http://example.com/file1.jpg", "id": 1}\n')
        f.write('{"source_url": "http://example.com/file2.jpg", "id": 2}\n')
        f.write('{"source_url": "http://example.com/file3.jpg", "id": 3}\n')

    return media_file, temp_dir
