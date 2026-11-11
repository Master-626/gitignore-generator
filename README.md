# Gitignore Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/Master-626/gitignore-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/Master-626/gitignore-generator/actions/workflows/ci.yml)

## 中文摘要

`gitignore-generator` 是一个小巧的命令行工具，用来按编程语言、操作系统和编辑器模板生成 `.gitignore`。

```bash
pip install .
gitignore list
gitignore generate python macos vscode
gitignore generate python --append   # 保留已有规则，只补上缺失模板
pip install -e ".[dev]" && ruff check src tests && pytest
```

已有输出默认不会覆盖。`--force` 会替换整个文件；`--append` 会保留你自己的规则。写入使用 UTF-8 和 LF 换行。Java 模板不会忽略整个 `.vscode/` 目录，因此可以和 `vscode` 模板一起用。下文是完整英文说明。

## Purpose

Generate a `.gitignore` from built-in templates instead of copying boilerplate by hand. Templates cover Python, Node.js, Java, Go, and Rust, plus macOS, Linux, Windows, VS Code, and JetBrains. The same generator is available as a command-line tool and as a Python library.

## Installation

Python 3.8 or newer is required.

```bash
git clone https://github.com/Master-626/gitignore-generator.git
cd gitignore-generator
pip install .
```

Install the development tools (pytest and ruff) with:

```bash
pip install -e ".[dev]"
```

The `gitignore` command is registered as a console script.

## Usage

### List templates

```bash
gitignore list
```

### Generate a file

```bash
# Python project
gitignore generate python

# Node.js, macOS, and VS Code
gitignore generate node macos vscode

# Python with operating-system and IDE rules
gitignore generate python macos jetbrains

# Custom output path. The directory must already exist.
gitignore generate python node -o myproject/.gitignore

# Replace an existing file, including a file that only contains local rules.
gitignore generate python --force
```

Repeated template names are written once. A template name must match the id shown by `gitignore list`.

Existing output paths are protected by default, including empty files and symbolic links. `--force` replaces the file contents. When the output is a symbolic link, `--force` follows the link and updates its target; it does not replace the link itself. A failed write does not leave a newly created file empty, and it restores the previous contents of an existing file.

Output is UTF-8 with LF newlines on every platform.

### Append to an existing file

```bash
# Keep custom rules and add any selected templates that are not already present.
gitignore generate macos vscode --append

# Safe to run again: templates already in the file are left untouched.
gitignore generate python macos --append -o myproject/.gitignore
```

`--append` and `--force` cannot be used together. Append detects a template by its generated header, such as `# --- PYTHON ---`, and refuses to follow a symbolic link. Rules outside those headers are kept. If the file does not exist yet, it is created.

### Options

| Command | Option | Description |
| --- | --- | --- |
| `generate` | `templates` | One or more template ids. Required. |
| `generate` | `-o`, `--output PATH` | Output path. Default: `.gitignore`. |
| `generate` | `--force` | Replace an existing file instead of refusing it. |
| `generate` | `--append` | Add missing template sections and keep current rules. |
| `list` | | Print every template id and a short description. |
| | `--help` | Show command help. |
| | `--version` | Show the installed version. |

Unknown templates and filesystem errors exit with status 1. Conflicting options and missing arguments exit with status 2.

## Python API

```python
from gitignore_generator import GitignoreGenerator

gen = GitignoreGenerator()

print(gen.list_templates())

content = gen.generate(["python", "node", "macos"])
# A single name is accepted. Passing "python" does not iterate characters.
content = gen.generate("python")

gen.generate_to_file(["python"], ".gitignore")

# Only when replacing the existing rules is intentional.
gen.generate_to_file(["python"], ".gitignore", overwrite=True)

# Returns the template names that were actually added.
added = gen.append_to_file(["macos", "vscode"], ".gitignore")
```

`generate_to_file` raises `FileExistsError` if the output already exists unless `overwrite=True` is passed. Unknown templates raise `ValueError` before the output file is opened, even when overwrite or append is requested. An empty selection raises `ValueError`. `append_to_file` raises `ValueError` when the existing file is not valid UTF-8, and `FileExistsError` when the path is a symbolic link.

## Testing

```bash
pip install -e ".[dev]"
ruff check src tests
pytest
```

GitHub Actions runs both ruff and pytest on Python 3.8 through 3.13 (3.8 on Ubuntu 22.04), and also runs the suite on Windows and macOS.

## License

MIT License
