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
    descriptions = {
        "python": "Python projects",
        "node": "Node.js / JavaScript projects",
        "java": "Java projects",
        "vscode": "VS Code editor settings",
        "jetbrains": "JetBrains IDE (IntelliJ, PyCharm)",
        "macos": "macOS system files",
        "linux": "Linux system files",
        "windows": "Windows system files",
        "go": "Go projects",
        "rust": "Rust projects",
    }
    assert set(descriptions) == set(GitignoreGenerator().list_templates())
    for template, description in descriptions.items():
        assert template in result.output
        assert description in result.output


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


def test_generate_help_lists_write_options():
    result = CliRunner().invoke(main, ["generate", "--help"])
    assert result.exit_code == 0, result.output
    for option in ("--output", "--force", "--append"):
        assert option in result.output


def test_duplicate_template_arguments_are_written_once(tmp_path):
    output = tmp_path / ".gitignore"
    result = CliRunner().invoke(main, ["generate", "python", "python", "-o", str(output)])
    assert result.exit_code == 0, result.output
    assert output.read_text().count("# --- PYTHON ---") == 1


def test_append_keeps_custom_rules(tmp_path):
    output = tmp_path / ".gitignore"
    original = b"# custom\r\nprivate-secrets/\r\n"
    output.write_bytes(original)
    result = CliRunner().invoke(main, ["generate", "python", "macos", "-o", str(output), "--append"])
    assert result.exit_code == 0, result.output
    data = output.read_bytes()
    assert data.startswith(original)
    assert b"private-secrets/" in data
    assert b"# --- PYTHON ---" in data
    assert b"# --- MACOS ---" in data
    assert "Updated .gitignore" in result.output
    assert "Generated .gitignore" not in result.output

    again = CliRunner().invoke(main, ["generate", "python", "-o", str(output), "--append"])
    assert again.exit_code == 0, again.output
    assert output.read_bytes() == data
    assert "No changes" in again.output


def test_append_creates_when_missing(tmp_path):
    output = tmp_path / ".gitignore"
    result = CliRunner().invoke(main, ["generate", "go", "-o", str(output), "--append"])
    assert result.exit_code == 0, result.output
    assert output.read_text() == GitignoreGenerator().generate(["go"])
    assert "Generated .gitignore" in result.output


def test_append_and_force_cannot_be_combined(tmp_path):
    output = tmp_path / ".gitignore"
    output.write_text("keep\n")
    result = CliRunner().invoke(
        main, ["generate", "python", "-o", str(output), "--append", "--force"]
    )
    assert result.exit_code == 2
    assert "cannot be used together" in result.output
    assert output.read_text() == "keep\n"


def test_append_refuses_symlink(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"private-secrets/\n")
    output = tmp_path / ".gitignore"
    try:
        output.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable on this platform")
    result = CliRunner().invoke(main, ["generate", "python", "-o", str(output), "--append"])
    assert result.exit_code == 1
    assert "symbolic link" in result.output
    assert target.read_bytes() == b"private-secrets/\n"
    assert output.is_symlink()


def test_append_unknown_template_keeps_existing_bytes(tmp_path):
    output = tmp_path / ".gitignore"
    original = b"# custom\r\nprivate-secrets/\r\n"
    output.write_bytes(original)
    result = CliRunner().invoke(main, ["generate", "python", "nope", "-o", str(output), "--append"])
    assert result.exit_code == 1
    assert "Unknown template: nope" in result.output
    assert output.read_bytes() == original
    assert "Updated .gitignore" not in result.output
