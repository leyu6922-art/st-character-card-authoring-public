import json
from pathlib import Path

import pytest

from scripts.export_public import export_tree


ROOT = Path(__file__).resolve().parents[1]


def write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manifest_kind": "public-export",
                "source_scope": {
                    "include": ["SKILL.md", "README.md", "LICENSE", "scripts/**", "references/**"],
                    "exclude": ["build/**", "**/*.env", ".env*", "**/*.bak"],
                    "manual_review": ["references/cases/**"],
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def write_review_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manifest_kind": "public-review",
                "reviews": [
                    {"path": "references/cases/example.md", "status": "approved_public"},
                    {"path": "references/cases/private.md", "status": "rejected_private"},
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_export_tree_uses_allowlist_and_excludes_private_scopes(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    (source / "scripts").mkdir(parents=True)
    (source / "references/cases").mkdir(parents=True)
    (source / "build").mkdir()
    (source / "SKILL.md").write_text("public skill", encoding="utf-8")
    (source / "scripts/tool.py").write_text("print('ok')", encoding="utf-8")
    (source / "references/cases/private.md").write_text("review", encoding="utf-8")
    (source / "build/private.md").write_text("build", encoding="utf-8")
    (source / ".env").write_text("PRIVATE=1", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    result = export_tree(source, destination, manifest, run_audit=False)

    assert result["errors"] == []
    assert (destination / "SKILL.md").is_file()
    assert (destination / "scripts/tool.py").is_file()
    assert not (destination / "build/private.md").exists()
    assert not (destination / ".env").exists()
    assert not (destination / "references/cases/private.md").exists()
    assert "references/cases/private.md" in result["manual_review"]


def test_export_tree_can_include_manual_review_only_explicitly(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    (source / "references/cases").mkdir(parents=True)
    (source / "references/cases/example.md").write_text("review", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    review_manifest = tmp_path / "review-manifest.json"
    write_manifest(manifest)
    write_review_manifest(review_manifest)

    result = export_tree(
        source,
        destination,
        manifest,
        review_manifest=review_manifest,
        run_audit=False,
    )

    assert result["errors"] == []
    assert (destination / "references/cases/example.md").is_file()
    assert result["manual_review"] == []
    assert result["approved_public"] == ["references/cases/example.md"]


def test_export_tree_rejects_bulk_manual_review_override(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    with pytest.raises(ValueError, match="review manifest"):
        export_tree(source, tmp_path / "public", manifest, include_manual_review=True, run_audit=False)


def test_export_tree_rejects_nonempty_destination(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    source.mkdir()
    destination.mkdir()
    (destination / "stale.txt").write_text("stale", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    with pytest.raises(ValueError, match="non-empty"):
        export_tree(source, destination, manifest, run_audit=False)


def test_export_tree_rejects_source_inside_destination(tmp_path):
    destination = tmp_path / "public"
    source = destination / "source"
    source.mkdir(parents=True)
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    with pytest.raises(ValueError, match="inside source|inside destination"):
        export_tree(source, destination, manifest, run_audit=False)


def test_export_tree_rejects_manifest_path_traversal(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "manifest_kind": "public-export",
        "source_scope": {"include": ["../outside/**"], "exclude": [], "manual_review": []},
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="path pattern"):
        export_tree(source, tmp_path / "public", manifest, run_audit=False)


def test_export_tree_rejects_binary_file(tmp_path):
    source = tmp_path / "source"
    (source / "scripts").mkdir(parents=True)
    (source / "scripts/blob.bin").write_bytes(b"header" + bytes([0]) + b"secret")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    result = export_tree(source, tmp_path / "public", manifest, run_audit=False)

    assert any("BINARY_REJECTED" in item for item in result["errors"])


def test_export_tree_rejects_symlink(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    target = source / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = source / "SKILL.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows runner")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    result = export_tree(source, tmp_path / "public", manifest, run_audit=False)

    assert any("SYMLINK_REJECTED" in item for item in result["errors"])


def test_export_supports_explicit_public_overrides(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("private README", encoding="utf-8")
    (source / "release/core").mkdir(parents=True)
    (source / "release/core/README.md").write_text("sanitized README", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "manifest_kind": "public-export",
        "source_scope": {"include": ["README.md"], "exclude": [], "manual_review": []},
        "overrides": {"README.md": "release/core/README.md"},
    }), encoding="utf-8")

    result = export_tree(source, tmp_path / "public", manifest, run_audit=False)

    assert result["errors"] == []
    assert result["copied"] == ["README.md"]
    assert (tmp_path / "public/README.md").read_text(encoding="utf-8") == "sanitized README"


def test_export_ignores_git_metadata_outside_allowlist(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / ".git").mkdir()
    (source / ".git/config").write_text("private git metadata", encoding="utf-8")
    (source / "SKILL.md").write_text("public", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    result = export_tree(source, tmp_path / "public", manifest, dry_run=True, run_audit=False)

    assert result["errors"] == []
    assert result["copied"] == ["SKILL.md"]


def test_export_result_records_release_trace_metadata(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    source.mkdir()
    (source / "SKILL.md").write_text("public skill\n", encoding="utf-8")
    (source / "README.md").write_text("public readme\n", encoding="utf-8")
    (source / "LICENSE").write_text("license\n", encoding="utf-8")
    (source / "skill-manifest.json").write_text("{}\n", encoding="utf-8")
    (source / "public-export-manifest.json").write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    result = export_tree(source, destination, manifest, run_audit=False)

    trace = result["release_trace"]
    assert trace["source_commit"] is None
    assert len(trace["export_manifest_sha256"]) == 64
    assert len(trace["skill_manifest_sha256"]) == 64
    assert trace["exported_files"] == len(result["copied"])
    assert trace["manual_review_unresolved"] == len(result["manual_review"])
    assert trace["export_timestamp_utc"].endswith("Z")


def test_export_tree_dry_run_does_not_write_destination(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    source.mkdir()
    (source / "SKILL.md").write_text("public", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    result = export_tree(source, destination, manifest, dry_run=True, run_audit=False)

    assert result["errors"] == []
    assert result["copied"] == ["SKILL.md"]
    assert not destination.exists()


def test_export_requires_the_declared_provenance_manifest_to_be_exported(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    source.mkdir()
    (source / "SKILL.md").write_text("public skill\n", encoding="utf-8")
    (source / "workflow-provenance-manifest.json").write_text(json.dumps({
        "manifest_kind": "provenance", "files": {}
    }), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "manifest_kind": "public-export",
        "provenance_manifest": "workflow-provenance-manifest.json",
        "source_scope": {"include": ["SKILL.md"], "exclude": [], "manual_review": []},
    }), encoding="utf-8")

    result = export_tree(source, destination, manifest, run_audit=False)

    assert any("PROVENANCE_NOT_EXPORTED" in item for item in result["errors"])
    assert not destination.exists()


def test_root_workflow_contract_uses_a_distinct_provenance_manifest():
    export_manifest = json.loads((ROOT / "public-export-manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((ROOT / "workflow-provenance-manifest.json").read_text(encoding="utf-8"))
    assert export_manifest["manifest_kind"] == "public-export"
    assert export_manifest["provenance_manifest"] == "workflow-provenance-manifest.json"
    assert export_manifest["current_blockers"] == []
    assert export_manifest["known_boundaries"]
    assert provenance["release_line"] == "v0.1.0"
    assert provenance["product_kind"] == "opinionated_personal_workflow"
    assert "release/public-core/provenance-manifest.json" not in export_manifest["provenance_manifest"]
    assert export_manifest["artifact_release_line"] == export_manifest["release_line"]
    assert export_manifest["strict_core_release_line"] == "v0.1.0-public-readiness-core-rc2"


def test_export_tree_rejects_destination_inside_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest)

    with pytest.raises(ValueError, match="inside source"):
        export_tree(source, source / "public", manifest, run_audit=False)
