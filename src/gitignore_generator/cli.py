"""
CLI interface for gitignore-generator.
"""

import click
from rich.console import Console
from rich.table import Table

from .generator import GitignoreGenerator

console = Console()


@click.group()
@click.version_option()
def main():
    """Gitignore Generator - Generate .gitignore files for different languages."""
    pass


@main.command()
@click.argument("templates", nargs=-1, required=True)
@click.option("-o", "--output", default=".gitignore", help="Output file path")
def generate(templates, output):
    """Generate .gitignore file from templates."""
    gen = GitignoreGenerator()

    try:
        gen.generate_to_file(list(templates), output)
        console.print(f"✅ Generated .gitignore: {output}")
        console.print(f"   Templates: {', '.join(templates)}")
    except ValueError as e:
        console.print(f"❌ Error: {e}", err=True)


@main.command()
def list():
    """List available templates."""
    gen = GitignoreGenerator()
    templates = gen.list_templates()

    table = Table(title="Available Templates")
    table.add_column("Template", style="cyan")
    table.add_column("Description", style="green")

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

    for t in templates:
        table.add_row(t, descriptions.get(t, ""))

    console.print(table)


if __name__ == "__main__":
    main()
