import os
import shutil
import stat
import subprocess

import pytest

from gitignore_generator.generator import GitignoreGenerator


def test_list_templates():
    """Test listing available templates."""
    gen = GitignoreGenerator()
    templates = gen.list_templates()
    assert "python" in templates
    assert "node" in templates
    assert "java" in templates


def test_generate_single_template():
    """Test generating single template."""
    gen = GitignoreGenerator()
    content = gen.generate(["python"])
    assert "__pycache__" in content
    assert "# --- PYTHON ---" in content


def test_generate_multiple_templates():
    """Test generating multiple templates."""
    gen = GitignoreGenerator()
    content = gen.generate(["python", "node", "macos"])
    assert "__pycache__" in content
    assert "node_modules" in content
    assert ".DS_Store" in content


def test_unknown_template():
    """Test that unknown template raises error."""
    gen = GitignoreGenerator()
    with pytest.raises(ValueError):
        gen.generate(["unknown_language"])


def test_generate_to_file(tmp_path):
    """Test generating to file."""
    gen = GitignoreGenerator()
    output = tmp_path / ".gitignore"
    gen.generate_to_file(["python"], str(output))
    assert output.exists()
    assert "__pycache__" in output.read_text()


@pytest.mark.parametrize("original", [b"", b"# custom\r\nprivate-secrets/\r\n", b"\xff\xfe"])
def test_generate_to_file_preserves_existing_bytes(tmp_path, original):
    output = tmp_path / ".gitignore"
    output.write_bytes(original)
    with pytest.raises(FileExistsError):
        GitignoreGenerator().generate_to_file(["python"], output)
    assert output.read_bytes() == original


def test_generate_to_file_explicit_overwrite(tmp_path):
    output = tmp_path / ".gitignore"
    output.write_text("private-secrets/\n")
    gen = GitignoreGenerator()
    assert gen.generate_to_file(["python"], output, overwrite=True) == output
    assert output.read_text() == gen.generate(["python"])


@pytest.mark.parametrize("overwrite", [False, True])
def test_invalid_template_preserves_existing_file(tmp_path, overwrite):
    output = tmp_path / ".gitignore"
    output.write_bytes(b"private-secrets/\r\n")
    with pytest.raises(ValueError, match="Unknown template: unknown"):
        GitignoreGenerator().generate_to_file(["python", "unknown"], output, overwrite=overwrite)
    assert output.read_bytes() == b"private-secrets/\r\n"


def test_invalid_template_does_not_create_file(tmp_path):
    output = tmp_path / ".gitignore"
    with pytest.raises(ValueError):
        GitignoreGenerator().generate_to_file(["unknown"], output)
    assert not output.exists()


def test_default_output_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert GitignoreGenerator().generate_to_file(["python"]) == ".gitignore"
    assert (tmp_path / ".gitignore").exists()


@pytest.mark.parametrize("target_exists", [False, True])
def test_default_write_rejects_symlink(tmp_path, target_exists):
    target = tmp_path / "target"
    if target_exists:
        target.write_bytes(b"private-secrets/\n")
    output = tmp_path / ".gitignore"
    try:
        output.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable on this platform")
    with pytest.raises(FileExistsError):
        GitignoreGenerator().generate_to_file(["python"], output)
    assert output.is_symlink()
    if target_exists:
        assert target.read_bytes() == b"private-secrets/\n"
    else:
        assert not target.exists()


def test_exclusive_creation_prevents_check_write_race(tmp_path, monkeypatch):
    import builtins

    output = tmp_path / ".gitignore"
    real_open = builtins.open

    def create_competing_file(path, mode, **kwargs):
        with real_open(output, "wb") as f:
            f.write(b"another-process/\n")
        return real_open(path, mode, **kwargs)

    monkeypatch.setattr(builtins, "open", create_competing_file)
    with pytest.raises(FileExistsError):
        GitignoreGenerator().generate_to_file(["python"], output)
    assert output.read_bytes() == b"another-process/\n"


def test_explicit_overwrite_follows_symlink(tmp_path):
    target = tmp_path / "target"
    target.write_text("private-secrets/\n")
    output = tmp_path / ".gitignore"
    try:
        output.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable on this platform")
    gen = GitignoreGenerator()
    gen.generate_to_file(["python"], output, overwrite=True)
    assert output.is_symlink()
    assert target.read_text() == gen.generate(["python"])


def test_explicit_overwrite_can_create_new_file(tmp_path):
    output = tmp_path / ".gitignore"
    gen = GitignoreGenerator()
    gen.generate_to_file(["python"], output, overwrite=True)
    assert output.read_text() == gen.generate(["python"])


def test_existing_symlink_is_rejected_before_open(tmp_path, monkeypatch):
    import builtins

    from gitignore_generator import generator

    output = tmp_path / ".gitignore"
    monkeypatch.setattr(generator.os.path, "islink", lambda path: True)

    def unexpected_open(*args, **kwargs):
        pytest.fail("Existing symlink must not be opened, even in exclusive mode")

    monkeypatch.setattr(builtins, "open", unexpected_open)
    with pytest.raises(FileExistsError):
        GitignoreGenerator().generate_to_file(["python"], output)
    assert not output.exists()


def _git_env():
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    return env


def _git_ignores(repo, relative_path):
    completed = subprocess.run(
        ["git", "-c", "core.excludesFile=", "check-ignore", "-q", "--", relative_path],
        cwd=repo,
        env=_git_env(),
        capture_output=True,
    )
    assert completed.returncode in (0, 1), completed.stderr
    return completed.returncode == 0


def _init_git_repo(path):
    path.mkdir()
    subprocess.run(
        ["git", "init", "-q"],
        cwd=path,
        env=_git_env(),
        check=True,
        capture_output=True,
    )


def _fail_writes(monkeypatch, mode_marker, partial=False):
    import builtins

    real_open = builtins.open

    def factory(path, mode="r", *args, **kwargs):
        handle = real_open(path, mode, *args, **kwargs)
        if mode_marker in str(mode):
            real_write = handle.write
            state = {"failed": False}

            def flaky(data):
                if not state["failed"]:
                    state["failed"] = True
                    if partial:
                        real_write(data[:100])
                    raise OSError("disk full")
                return real_write(data)

            handle.write = flaky
        return handle

    monkeypatch.setattr(builtins, "open", factory)


def test_single_name_is_not_split_into_characters():
    gen = GitignoreGenerator()
    assert gen.generate("python") == gen.generate(["python"])


def test_duplicate_templates_are_emitted_once():
    gen = GitignoreGenerator()
    assert gen.generate(["python", "node", "python"]) == gen.generate(["python", "node"])
    assert gen.generate(["python", "node", "python"]).count("# --- PYTHON ---") == 1


def test_empty_selection_is_rejected_without_creating_a_file(tmp_path):
    output = tmp_path / ".gitignore"
    output.write_bytes(b"keep-me\n")
    with pytest.raises(ValueError, match="At least one template is required"):
        GitignoreGenerator().generate_to_file([], output, overwrite=True)
    assert output.read_bytes() == b"keep-me\n"


@pytest.mark.parametrize("value", [None, b"python", ["python", 1]])
def test_template_input_must_be_names(value):
    with pytest.raises(TypeError):
        GitignoreGenerator().generate(value)


def test_tuple_of_names_preserves_order():
    gen = GitignoreGenerator()
    content = gen.generate(("rust", "go", "linux"))
    assert content.index("# --- RUST ---") < content.index("# --- GO ---")
    assert content.index("# --- GO ---") < content.index("# --- LINUX ---")
    assert content.endswith("\n")
    assert not content.endswith("\n\n")


def test_every_template_renders_its_header():
    gen = GitignoreGenerator()
    names = gen.list_templates()
    rendered = gen.generate(names)
    for name in names:
        assert f"# --- {name.upper()} ---" in rendered


def test_output_bytes_are_utf8_with_lf_newlines(tmp_path):
    output = tmp_path / ".gitignore"
    gen = GitignoreGenerator()
    gen.generate_to_file(["python", "windows"], output)
    data = output.read_bytes()
    assert b"\r" not in data
    assert data == gen.generate(["python", "windows"]).encode("utf-8")

    output.write_bytes(b"custom\r\n")
    gen.generate_to_file(["python"], output, overwrite=True)
    replaced = output.read_bytes()
    assert b"\r" not in replaced
    assert replaced == gen.generate(["python"]).encode("utf-8")


def test_overwrite_keeps_the_same_file_and_permissions(tmp_path):
    output = tmp_path / ".gitignore"
    output.write_bytes(b"x" * 5000)
    output.chmod(0o640)
    before = output.stat()
    gen = GitignoreGenerator()
    gen.generate_to_file(["linux"], output, overwrite=True)
    after = output.stat()
    assert output.read_bytes() == gen.generate(["linux"]).encode("utf-8")
    assert stat.S_IMODE(after.st_mode) == stat.S_IMODE(before.st_mode)
    if os.name == "posix":
        assert after.st_ino == before.st_ino


def test_failed_overwrite_preserves_original_bytes(tmp_path, monkeypatch):
    output = tmp_path / ".gitignore"
    original = b"private-secrets/\n"
    output.write_bytes(original)
    _fail_writes(monkeypatch, "+", partial=False)
    with pytest.raises(OSError, match="disk full"):
        GitignoreGenerator().generate_to_file(["python"], output, overwrite=True)
    assert output.read_bytes() == original


def test_partial_overwrite_restores_original_bytes(tmp_path, monkeypatch):
    output = tmp_path / ".gitignore"
    original = b"private-secrets/\n"
    output.write_bytes(original)
    _fail_writes(monkeypatch, "+", partial=True)
    with pytest.raises(OSError, match="disk full"):
        GitignoreGenerator().generate_to_file(["python"], output, overwrite=True)
    assert output.read_bytes() == original


def test_failed_create_does_not_leave_a_partial_file(tmp_path, monkeypatch):
    output = tmp_path / ".gitignore"
    _fail_writes(monkeypatch, "x", partial=True)
    with pytest.raises(OSError, match="disk full"):
        GitignoreGenerator().generate_to_file(["python"], output)
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_overwrite_dangling_symlink_creates_the_relative_target(tmp_path, monkeypatch):
    link = tmp_path / ".gitignore"
    try:
        link.symlink_to("nested")
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable on this platform")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    gen = GitignoreGenerator()
    gen.generate_to_file(["python"], link, overwrite=True)
    assert link.is_symlink()
    assert not (elsewhere / "nested").exists()
    assert (tmp_path / "nested").read_bytes() == gen.generate(["python"]).encode("utf-8")


def test_python_template_ignores_dot_venv(tmp_path):
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / ".gitignore").write_bytes(GitignoreGenerator().generate(["python"]).encode("utf-8"))
    assert _git_ignores(repo, ".venv/pyvenv.cfg")
    assert _git_ignores(repo, "venv/bin/python")
    assert not _git_ignores(repo, "src/app.py")


@pytest.mark.parametrize("order", [["java", "vscode"], ["vscode", "java"]])
def test_java_template_does_not_block_vscode_exceptions(tmp_path, order):
    assert ".vscode/" not in GitignoreGenerator().generate(["java"]).splitlines()
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / ".gitignore").write_bytes(GitignoreGenerator().generate(order).encode("utf-8"))
    assert not _git_ignores(repo, ".vscode/settings.json")
    assert not _git_ignores(repo, ".vscode/launch.json")
    assert _git_ignores(repo, ".vscode/other.txt")
    assert _git_ignores(repo, "target/classes/App.class")


def test_append_creates_missing_file(tmp_path):
    output = tmp_path / ".gitignore"
    gen = GitignoreGenerator()
    assert gen.append_to_file("python", output) == ["python"]
    assert output.read_bytes() == gen.generate(["python"]).encode("utf-8")


def test_append_preserves_custom_rules_and_is_idempotent(tmp_path):
    output = tmp_path / ".gitignore"
    original = b"# custom\r\nprivate-secrets/\r\n"
    output.write_bytes(original)
    gen = GitignoreGenerator()
    added = gen.append_to_file(["python", "python", "macos"], output)
    assert added == ["python", "macos"]
    expected = original + b"\n" + gen.generate(["python", "macos"]).encode("utf-8")
    assert output.read_bytes() == expected

    assert gen.append_to_file(["python", "macos"], output) == []
    assert output.read_bytes() == expected


def test_append_adds_only_missing_sections(tmp_path):
    output = tmp_path / ".gitignore"
    gen = GitignoreGenerator()
    original = gen.generate(["python"]).encode("utf-8") + b"# custom\nsecret/\n"
    output.write_bytes(original)
    assert gen.append_to_file(["python", "node"], output) == ["node"]
    assert output.read_bytes() == original + b"\n" + gen.generate(["node"]).encode("utf-8")


def test_append_without_trailing_newline(tmp_path):
    output = tmp_path / ".gitignore"
    output.write_bytes(b"private-secrets/")
    gen = GitignoreGenerator()
    gen.append_to_file(["linux"], output)
    assert output.read_bytes() == b"private-secrets/\n\n" + gen.generate(["linux"]).encode("utf-8")


def test_append_rejects_symlink_and_binary_input(tmp_path):
    gen = GitignoreGenerator()
    target = tmp_path / "target"
    target.write_bytes(b"private-secrets/\n")
    link = tmp_path / ".gitignore"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable on this platform")
    with pytest.raises(FileExistsError):
        gen.append_to_file(["python"], link)
    assert target.read_bytes() == b"private-secrets/\n"

    binary = tmp_path / "binary.gitignore"
    binary.write_bytes(b"\xff\xfe")
    with pytest.raises(ValueError, match="not valid UTF-8"):
        gen.append_to_file(["python"], binary)
    assert binary.read_bytes() == b"\xff\xfe"


def test_append_failure_preserves_original_bytes(tmp_path, monkeypatch):
    output = tmp_path / ".gitignore"
    original = b"# custom\r\nprivate-secrets/\r\n"
    output.write_bytes(original)
    _fail_writes(monkeypatch, "+", partial=True)
    with pytest.raises(OSError, match="disk full"):
        GitignoreGenerator().append_to_file(["python"], output)
    assert output.read_bytes() == original


def test_append_unknown_template_does_not_touch_output(tmp_path):
    output = tmp_path / ".gitignore"
    output.write_bytes(b"keep-me\n")
    with pytest.raises(ValueError, match="Unknown template: nope"):
        GitignoreGenerator().append_to_file(["python", "nope"], output)
    assert output.read_bytes() == b"keep-me\n"
