"""
CLI interface for gitignore-generator.
"""

import os

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
@click.option("--force", is_flag=True, help="Replace an existing output file.")
@click.option(
    "--append",
    is_flag=True,
    help="Add missing templates without discarding existing rules.",
)
def generate(templates, output, force, append):
    """Generate .gitignore file from templates."""
    if force and append:
        raise click.UsageError("--append and --force cannot be used together.")

    gen = GitignoreGenerator()
    try:
        if append:
            already_there = os.path.isfile(output) and not os.path.islink(output)
            added = gen.append_to_file(list(templates), output)
        else:
            already_there = False
            added = None
            gen.generate_to_file(list(templates), output, overwrite=force)
    except FileExistsError as exc:
        if append and os.path.islink(output):
            raise click.ClickException(
                f"Refusing to update symbolic link: {output}."
            ) from exc
        raise click.ClickException(
            f"Output already exists: {output}. Use --force to replace it."
        ) from exc
    except (ValueError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc

    if append and already_there and not added:
        console.print(f"No changes: {output}", markup=False)
        console.print("   Templates already present.", markup=False)
        return
    if append and already_there:
        console.print(f"Updated .gitignore: {output}", markup=False)
        console.print(f"   Added templates: {', '.join(added)}", markup=False)
        return

    console.print(f"✅ Generated .gitignore: {output}", markup=False)
    console.print(f"   Templates: {', '.join(templates)}", markup=False)


@main.command(name="list")
def list_templates():
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
