"""Tests for incremental skill auto-detection."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from maestro_rag.engine import MaestroEngine, Config, Chunker, SkillFingerprint


@pytest.fixture
def tmp_skills(tmp_path):
    """Create a temporary skill directory structure."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Create skill_a
    skill_a = skills_dir / "skill_a"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text(
        "---\nname: skill_a\ndescription: Test skill A\ndomains:\n  - testing\n---\n\n# Skill A\n\nContent for skill A."
    )

    # Create skill_b
    skill_b = skills_dir / "skill_b"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text(
        "---\nname: skill_b\ndescription: Test skill B\ndomains:\n  - coding\n---\n\n# Skill B\n\nContent for skill B."
    )

    return skills_dir


def test_discover_skills_finds_all(tmp_skills):
    config = Config()
    config.skill_paths = [tmp_skills]
    config.vectordb_path = tmp_skills.parent / "vectordb"

    with patch("maestro_rag.engine.MaestroEngine._init_db"):
        engine = MaestroEngine(config)
        skills = engine._discover_skills()

    names = {s.name for s in skills}
    assert "skill_a" in names
    assert "skill_b" in names


def test_incremental_detects_new_skill(tmp_skills):
    config = Config()
    config.skill_paths = [tmp_skills]
    config.vectordb_path = tmp_skills.parent / "vectordb"

    with patch("maestro_rag.engine.MaestroEngine._init_db"):
        engine = MaestroEngine(config)
        # Simulate that skill_a is already indexed
        engine._fingerprints["skill_a"] = SkillFingerprint(
            name="skill_a",
            description="Test skill A",
            domains=["testing"],
            chunk_count=1,
        )
        engine._indexed = True

        # Mock the storage methods
        engine._collection = MagicMock()
        engine._collection.count.return_value = 10
        engine._collection.get.return_value = {
            "ids": ["id1"],
            "documents": ["doc1"],
        }
        engine._store_chunks = MagicMock()
        engine._embed_fingerprints = MagicMock()
        engine._save_index_meta = MagicMock()
        engine._refresh_skill_index_files = MagicMock()

        result = engine._incremental_index_new_skills()

    assert result is not None
    assert "skill_b" in result["new_skills"]
    assert result["new_chunks"] > 0
    engine._store_chunks.assert_called_once()
    engine._refresh_skill_index_files.assert_called_once()


def test_incremental_returns_none_when_no_new(tmp_skills):
    config = Config()
    config.skill_paths = [tmp_skills]
    config.vectordb_path = tmp_skills.parent / "vectordb"

    with patch("maestro_rag.engine.MaestroEngine._init_db"):
        engine = MaestroEngine(config)
        # All skills already indexed
        engine._fingerprints["skill_a"] = SkillFingerprint(
            name="skill_a", description="A", domains=["testing"], chunk_count=1
        )
        engine._fingerprints["skill_b"] = SkillFingerprint(
            name="skill_b", description="B", domains=["coding"], chunk_count=1
        )
        engine._indexed = True

        result = engine._incremental_index_new_skills()

    assert result is None


def test_chunker_produces_chunks(tmp_skills):
    chunker = Chunker(max_tokens=400)
    skill_md = tmp_skills / "skill_a" / "SKILL.md"
    chunks = chunker.chunk_file(skill_md, "skill_a", ["testing"])
    assert len(chunks) > 0
    assert all(c.skill == "skill_a" for c in chunks)


def test_extract_domains(tmp_skills):
    config = Config()
    config.skill_paths = [tmp_skills]
    config.vectordb_path = tmp_skills.parent / "vectordb"

    with patch("maestro_rag.engine.MaestroEngine._init_db"):
        engine = MaestroEngine(config)
        domains = engine._extract_domains(tmp_skills / "skill_a")

    assert domains == ["testing"]


def test_extract_description(tmp_skills):
    config = Config()
    config.skill_paths = [tmp_skills]
    config.vectordb_path = tmp_skills.parent / "vectordb"

    with patch("maestro_rag.engine.MaestroEngine._init_db"):
        engine = MaestroEngine(config)
        desc = engine._extract_description(tmp_skills / "skill_a")

    assert desc == "Test skill A"
