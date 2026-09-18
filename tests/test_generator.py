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
    assert "# PYTHON" in content


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
