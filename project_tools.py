"""T+ project scaffolding and installation diagnostics.

No third-party code is downloaded or executed by these helpers.
"""
from __future__ import annotations
from pathlib import Path
import re
import shutil
import sys
import tomllib


class ProjectError(Exception):
    pass


def create_project(path: str) -> Path:
    root = Path(path).expanduser().absolute()
    name = root.name
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,63}", name):
        raise ProjectError("Project name must use letters, digits, '_' or '-'")
    if root.exists():
        raise ProjectError(f"Project already exists: {root}. Existing files were not changed.")
    if not root.parent.is_dir():
        raise ProjectError(f"Parent folder not found: {root.parent}")
    if root.parent.is_symlink():
        raise ProjectError("Choose a real parent directory, not a symlink")
    root.mkdir()
    try:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "teka.toml").write_text(
            '[project]\n'
            f'name = "{name}"\n'
            'version = "0.1.0"\n\n'
            '[build]\n'
            'entry = "src/main.teka"\n',
            encoding="utf-8",
        )
        (root / ".editorconfig").write_text(
            'root = true\n\n[*.teka]\nindent_style = tab\n'
            'indent_size = 4\ntab_width = 4\n',
            encoding="utf-8",
        )
        (root / "src" / "main.teka").write_text(
            "# First program in T+\n"
            f"print('hello from {name}!')\n", encoding="utf-8",
        )
        (root / "tests" / "test_main.teka").write_text(
            "print('T+ test program runs')\n", encoding="utf-8",
        )
        (root / "README.md").write_text(
            f"# {name}\n\n"
            "A T+ project.\n\n"
            "Run with: teka run\n"
            "Compile with: teka build --release\n"
            "Or open the folder in IntelliJ IDEA and run src/main.teka.\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(root)
        raise
    return root


def project_entry(directory: Path) -> Path | None:
    manifest = directory / "teka.toml"
    if not manifest.is_file():
        return None
    try:
        config = tomllib.loads(manifest.read_text(encoding="utf-8"))
        name = config["project"]["name"]
        path = config["build"]["entry"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ProjectError(f"Invalid teka.toml: {exc}") from exc
    if not isinstance(name, str) or not isinstance(path, str):
        raise ProjectError("Project name and entry must be strings")
    entry = (directory / path).resolve()
    if not entry.is_relative_to(directory.resolve()):
        raise ProjectError("The project entry must stay inside the project folder")
    if entry.suffix != ".teka" or not entry.is_file():
        raise ProjectError(f"Entry does not exist or is not .teka: {entry}")
    return entry


def doctor(installed_root: Path) -> dict:
    compiler = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
    include = next(
        (p for p in [Path("/opt/homebrew/include/raylib.h"),
                     Path("/usr/local/include/raylib.h")] if p.exists()), None
    )
    idea_plugins = Path.home() / "Library" / "Application Support" / "JetBrains"
    plugin_versions = []
    if idea_plugins.exists():
        for plugin in idea_plugins.glob("IntelliJIdea*/plugins/TekaLang-IntelliJ/lib/*.jar"):
            plugin_versions.append(str(plugin))
    return {
        "python": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 11),
        "cpp_compiler": compiler,
        "cpp_available": bool(compiler),
        "raylib_headers": str(include) if include else None,
        "graphics_available": bool(include),
        "intellij_plugin": sorted(plugin_versions),
        "root": str(installed_root),
        "stdlib": ["math", "random"],
        "status": "ready" if sys.version_info >= (3, 11) and compiler else "incomplete",
    }