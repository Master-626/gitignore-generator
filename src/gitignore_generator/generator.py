"""
Core .gitignore generation logic.

``venv/`` does not match ``.venv/``, the directory created by
``python -m venv .venv``. The Java template must not exclude ``.vscode/``:
Git cannot re-include a file when a parent directory is excluded, so that
rule would disable the VS Code template's exceptions.
"""

import errno
import os
from typing import Dict, List, Sequence, Tuple, Union

TEMPLATES: Dict[str, str] = {
    "python": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.venv/
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
""",

    "node": """# Node.js
node_modules/
npm-debug.log
yarn-error.log
.env
.env.local
.next/
out/
dist/
""",

    "java": """# Java
*.class
# Package Files
*.jar
*.war
*.ear
*.zip
*.tar.gz
*.rar
# IDE
.idea/
*.iml
# Maven
target/
""",

    "vscode": """# VS Code
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json
""",

    "jetbrains": """# JetBrains IDE
.idea/
*.iws
*.iml
*.ipr
out/
""",

    "macos": """# macOS
.DS_Store
.AppleDouble
.LSOverride
Icon
._*
""",

    "linux": """# Linux
*~
.fuse_hidden*
.directory
.Trash-*
.nfs*
""",

    "windows": """# Windows
Thumbs.db
Thumbs.db:encryptable
ehthumbs.db
ehthumbs_vista.db
*.stackdump
[Dd]esktop.ini
$RECYCLE.BIN/
""",

    "go": """# Go
# Binaries for programs and plugins
*.exe
*.exe~
*.dll
*.so
*.dylib
# Test binary, built with `go test -c`
*.test
# Output of the go coverage tool
*.out
# Go workspace file
go.work
""",

    "rust": """# Rust
debug/
target/
**/*.rs.bk
Cargo.lock
""",
}

TemplateInput = Union[str, Sequence[str]]


def _normalize_templates(templates: TemplateInput) -> List[str]:
    """Return unique known template names in selection order.

    A bare string is one template name. It must not be iterated character by
    character. Repeated names are ignored after the first occurrence.
    """
    if templates is None or isinstance(templates, (bytes, bytearray)):
        raise TypeError("templates must be a sequence of template names")
    if isinstance(templates, str):
        names: List[object] = [templates]
    else:
        try:
            names = list(templates)
        except TypeError as exc:
            raise TypeError("templates must be a sequence of template names") from exc

    selected: List[str] = []
    seen = set()
    for name in names:
        if not isinstance(name, str):
            raise TypeError(
                f"template names must be strings, got {type(name).__name__}"
            )
        if name not in TEMPLATES:
            raise ValueError(f"Unknown template: {name}")
        if name in seen:
            continue
        seen.add(name)
        selected.append(name)
    if not selected:
        raise ValueError("At least one template is required")
    return selected


def _render(selected: Sequence[str]) -> str:
    sections = []
    for template_name in selected:
        content = TEMPLATES[template_name].strip()
        sections.append(f"# --- {template_name.upper()} ---\n{content}")
    return "\n\n".join(sections) + "\n"


def _marker(template_name: str) -> str:
    return f"# --- {template_name.upper()} ---"


def _write_all(handle, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = handle.write(remaining)
        if not written:
            raise OSError(errno.EIO, "Could not write .gitignore output")
        remaining = remaining[written:]


def _exclusive_write(path: str, payload: bytes) -> None:
    """Create ``path`` exclusively. A failed write removes the partial file."""
    created = False
    try:
        handle = open(path, "xb")
        created = True
        with handle:
            _write_all(handle, payload)
    except BaseException:
        if created:
            try:
                os.unlink(path)
            except OSError:
                pass
        raise


def _overwrite_in_place(path: str, payload: bytes) -> None:
    """Replace existing bytes without truncating before the write succeeds.

    Mode ``w`` discards the old file first. If that write then fails, the
    previous rules are already gone. This updates the same file and puts the
    previous bytes back when publishing fails.
    """
    with open(path, "rb") as current:
        original = current.read()
    handle = open(path, "r+b")
    try:
        _write_all(handle, payload)
        handle.truncate(len(payload))
        handle.flush()
    except BaseException:
        try:
            handle.seek(0)
            _write_all(handle, original)
            handle.truncate(len(original))
            handle.flush()
        except OSError:
            pass
        raise
    finally:
        handle.close()


def _publish_overwrite(path: str, payload: bytes) -> None:
    """Write ``payload`` over ``path``, following symlinks like ``open`` does."""
    if os.path.exists(path):
        _overwrite_in_place(path, payload)
        return
    if os.path.islink(path):
        # A dangling link has no file to update. Create the target itself.
        # Opening the link in exclusive mode can follow it on Windows.
        _exclusive_write(os.path.realpath(path), payload)
        return
    _exclusive_write(path, payload)


def _merge_payload(path: str, existing: bytes, selected: Sequence[str]) -> Tuple[bytes, List[str]]:
    try:
        text = existing.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Output is not valid UTF-8: {path}") from exc

    present = {line.strip() for line in text.splitlines()}
    missing = [name for name in selected if _marker(name) not in present]
    if not missing:
        return existing, []

    addition = _render(missing).encode("utf-8")
    if not existing or existing.endswith(b"\n\n"):
        separator = b""
    elif existing.endswith(b"\n"):
        separator = b"\n"
    else:
        separator = b"\n\n"
    return existing + separator + addition, missing


class GitignoreGenerator:
    """Generate .gitignore files for different languages and tools."""

    def list_templates(self) -> List[str]:
        """List all available templates."""
        return list(TEMPLATES.keys())

    def generate(self, templates: TemplateInput) -> str:
        """Generate .gitignore content from selected templates.

        ``templates`` may be one template name or a sequence of names.
        Output is UTF-8 text with LF line endings. Template names are
        validated before any content is returned.
        """
        return _render(_normalize_templates(templates))

    def generate_to_file(
        self,
        templates: TemplateInput,
        output_path: str = ".gitignore",
        *,
        overwrite: bool = False,
    ):
        """Write a .gitignore, refusing existing paths unless overwrite is true.

        Templates are validated before opening the output. Exclusive creation
        protects existing files from competing writes. Symlinks are checked
        separately because Windows may follow dangling links even in x mode.
        Files are written as UTF-8 with LF newlines. An existing file is
        updated in place so a failed write can restore the previous bytes.
        With overwrite, a symlink is followed and its target is updated.
        """
        payload = self.generate(templates).encode("utf-8")
        path = os.fspath(output_path)
        if overwrite:
            _publish_overwrite(path, payload)
        else:
            if os.path.islink(path):
                raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), path)
            _exclusive_write(path, payload)
        return output_path

    def append_to_file(
        self,
        templates: TemplateInput,
        output_path: str = ".gitignore",
    ) -> List[str]:
        """Add template sections that are not already in the output file.

        Existing rules are preserved, including rules outside generated
        sections. A missing file is created. Symbolic links are rejected.
        Sections are detected by their ``# --- NAME ---`` header. Returns
        the canonical template names that were added, in selection order.
        """
        selected = _normalize_templates(templates)
        path = os.fspath(output_path)
        if os.path.islink(path):
            raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), path)
        if not os.path.exists(path):
            try:
                _exclusive_write(path, _render(selected).encode("utf-8"))
            except FileExistsError:
                if os.path.islink(path):
                    raise
            else:
                return selected

        with open(path, "rb") as handle:
            existing = handle.read()
        updated, missing = _merge_payload(path, existing, selected)
        if not missing:
            return []
        _overwrite_in_place(path, updated)
        return missing
