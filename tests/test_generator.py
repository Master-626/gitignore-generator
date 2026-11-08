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
