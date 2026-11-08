from pathlib import Path

import pytest
from click.testing import CliRunner

from gitignore_generator.cli import main
from gitignore_generator.generator import GitignoreGenerator


@pytest.mark.parametrize("args", [["--help"], ["--version"], ["generate", "--help"]])
def test_help_and_version(args):
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output


def test_list_templates():
    result = CliRunner().invoke(main, ["list"])
    assert result.exit_code == 0, result.output
    for template in GitignoreGenerator().list_templates():
        assert template in result.output


def test_generate_default_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["generate", "python"])
    assert result.exit_code == 0, result.output
    assert Path(".gitignore").read_text() == GitignoreGenerator().generate(["python"])
    assert "Generated .gitignore" in result.output


def test_generate_multiple_templates_custom_path(tmp_path):
    output = tmp_path / "[test].gitignore"
    result = CliRunner().invoke(main, ["generate", "node", "macos", "-o", str(output)])
    assert result.exit_code == 0, result.output
    assert output.read_text() == GitignoreGenerator().generate(["node", "macos"])
    assert "[test].gitignore" in result.output


@pytest.mark.parametrize("original", [b"", b"# custom rules\r\nprivate-secrets/\r\n"])
def test_generate_preserves_existing_file(tmp_path, original):
    output = tmp_path / ".gitignore"
    output.write_bytes(original)
    result = CliRunner().invoke(main, ["generate", "python", "-o", str(output)])
    assert result.exit_code == 1
    assert output.read_bytes() == original
    assert "--force" in result.output
    assert "Generated .gitignore" not in result.output


def test_generate_force_replaces_file(tmp_path):
    output = tmp_path / ".gitignore"
    output.write_text("private-secrets/\n")
    result = CliRunner().invoke(main, ["generate", "python", "-o", str(output), "--force"])
    assert result.exit_code == 0, result.output
    assert output.read_text() == GitignoreGenerator().generate(["python"])


@pytest.mark.parametrize("force", [False, True])
def test_unknown_template_does_not_change_existing_file(tmp_path, force):
    output = tmp_path / ".gitignore"
    output.write_bytes(b"private-secrets/\r\n")
    args = ["generate", "python", "unknown", "-o", str(output)]
    if force:
        args.append("--force")
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 1
    assert "Unknown template: unknown" in result.output
    assert output.read_bytes() == b"private-secrets/\r\n"
    assert "Generated .gitignore" not in result.output


def test_unknown_template_does_not_create_file(tmp_path):
    output = tmp_path / ".gitignore"
    result = CliRunner().invoke(main, ["generate", "unknown", "-o", str(output)])
    assert result.exit_code == 1
    assert not output.exists()


@pytest.mark.parametrize("destination", ["missing/.gitignore", "."])
def test_filesystem_errors_are_reported(tmp_path, destination):
    result = CliRunner().invoke(
        main, ["generate", "python", "-o", str(tmp_path / destination), "--force"]
    )
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Generated .gitignore" not in result.output
    assert "Traceback" not in result.output


def test_permission_errors_are_reported(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(GitignoreGenerator, "generate_to_file", denied)
    result = CliRunner().invoke(main, ["generate", "python", "-o", str(tmp_path / "out")])
    assert result.exit_code == 1
    assert "Permission denied" in result.output
    assert "Generated .gitignore" not in result.output


def test_missing_templates_is_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["generate"])
    assert result.exit_code == 2
    assert not Path(".gitignore").exists()
