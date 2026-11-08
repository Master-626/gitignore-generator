# Gitignore Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Developer Tool](https://img.shields.io/badge/developer-tool-orange.svg)]()

Generate .gitignore files for different programming languages and frameworks from the command line.

## 🌟 Features

- 🐍 **Python** - Generate .gitignore for Python projects
- 📦 **Node.js** - Generate for Node.js / JavaScript projects
- ☕ **Java** - Generate for Java projects
- 🦀 **Rust** - Generate for Rust projects
- 🐹 **Go** - Generate for Go projects
- 🖥️ **OS Files** - Include macOS, Linux, Windows system files
- 🎨 **IDE Files** - Include VS Code, JetBrains IDE settings
- 🐍 **Python API** - Use as a library in your code

## 📦 Installation

```bash
git clone https://github.com/Master-626/gitignore-generator.git
cd gitignore-generator
pip install .
```

## 🚀 Usage

### List Available Templates
```bash
gitignore list
```

### Generate .gitignore
```bash
# Python project
gitignore generate python

# Node.js + macOS + VS Code
gitignore generate node macos vscode

# Python project with OS and IDE files
gitignore generate python macos jetbrains

# Custom output path
gitignore generate python node -o myproject/.gitignore

# Explicitly replace an existing file (discards its current rules)
gitignore generate python --force
```

Existing output paths are protected by default, including empty files and
symlinks. Review or back up your custom rules before using `--force`, which
replaces rather than merges the file. The output directory must already exist.
With `--force`, a symbolic link is followed and its target is overwritten.
Invalid templates and file errors produce a nonzero exit status.

## 🐍 Python API

```python
from gitignore_generator import GitignoreGenerator

gen = GitignoreGenerator()

# List templates
print(gen.list_templates())

# Generate content
content = gen.generate(["python", "node", "macos"])

# Generate to file
gen.generate_to_file(["python"], ".gitignore")

# Only when replacing the existing rules is intentional
gen.generate_to_file(["python"], ".gitignore", overwrite=True)
```

`generate_to_file` raises `FileExistsError` if the output already exists unless
`overwrite=True` is passed. Unknown templates raise `ValueError` before the
output file is opened, even when overwrite is enabled.
Like `--force`, `overwrite=True` follows symbolic links.

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest
```

## 📄 License

MIT License
