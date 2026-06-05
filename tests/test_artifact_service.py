"""Artifact service workspace registration."""

from src.agents_tg.services.artifact_service import ArtifactService


def test_register_workspace_file(tmp_path):
    svc = ArtifactService()
    f = tmp_path / "note.txt"
    f.write_text("hi", encoding="utf-8")
    ok = svc.register_workspace_file("a1", f, workspace_root=tmp_path)
    assert ok is True
    assert svc.get_path("a1") == f.resolve()
