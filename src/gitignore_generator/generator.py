"""
Core .gitignore generation logic.
"""

from typing import Dict, List


TEMPLATES: Dict[str, str] = {
    "python": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
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
.vscode/
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


class GitignoreGenerator:
    """Generate .gitignore files for different languages and tools."""

    def list_templates(self) -> List[str]:
        """List all available templates."""
        return list(TEMPLATES.keys())

    def generate(self, templates: List[str]) -> str:
        """Generate .gitignore content from selected templates."""
        sections = []

        for template_name in templates:
            if template_name not in TEMPLATES:
                raise ValueError(f"Unknown template: {template_name}")

            content = TEMPLATES[template_name].strip()
            sections.append(f"# --- {template_name.upper()} ---\n{content}")

        return "\n\n".join(sections) + "\n"

    def generate_to_file(self, templates: List[str], output_path: str = ".gitignore"):
        """Generate .gitignore file."""
        content = self.generate(templates)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path
