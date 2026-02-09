"""Design scanner — detect CSS frameworks, UI files, and component structure."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DesignProfile:
    """Profile of a scanned project's UI/frontend setup."""
    root: str
    name: str
    has_css_framework: bool = False
    css_framework: str = ""
    has_tailwind: bool = False
    has_react: bool = False
    has_vue: bool = False
    has_angular: bool = False
    has_components: bool = False
    component_files: list[str] = field(default_factory=list)
    existing_pages: list[str] = field(default_factory=list)
    html_files: list[str] = field(default_factory=list)
    css_files: list[str] = field(default_factory=list)
    js_files: list[str] = field(default_factory=list)
    file_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "has_css_framework": self.has_css_framework,
            "css_framework": self.css_framework,
            "has_tailwind": self.has_tailwind,
            "has_react": self.has_react,
            "has_vue": self.has_vue,
            "has_angular": self.has_angular,
            "has_components": self.has_components,
            "component_count": len(self.component_files),
            "page_count": len(self.existing_pages),
            "html_files": len(self.html_files),
            "css_files": len(self.css_files),
            "js_files": len(self.js_files),
            "file_count": self.file_count,
        }


SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "target", ".tox", ".mypy_cache",
}

UI_EXTENSIONS = {".html", ".css", ".scss", ".sass", ".less", ".jsx", ".tsx", ".vue", ".svelte"}
COMPONENT_DIR_NAMES = {"components", "component", "ui", "atoms", "molecules", "organisms", "widgets"}


def scan_project(root: str) -> DesignProfile:
    """Scan a project directory for UI/frontend structure."""
    root_path = Path(root).resolve()
    profile = DesignProfile(root=str(root_path), name=root_path.name)

    if not root_path.is_dir():
        raise FileNotFoundError(f"Not a directory: {root}")

    file_count = 0

    for path in root_path.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue

        file_count += 1
        rel = str(path.relative_to(root_path))
        ext = path.suffix.lower()

        # Track UI files
        if ext == ".html":
            profile.html_files.append(rel)
        elif ext in (".css", ".scss", ".sass", ".less"):
            profile.css_files.append(rel)
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            profile.js_files.append(rel)

        # Detect component directories
        if any(part.lower() in COMPONENT_DIR_NAMES for part in path.parts):
            if ext in UI_EXTENSIONS:
                profile.has_components = True
                profile.component_files.append(rel)

        # Detect pages
        if "pages" in path.parts or "views" in path.parts or "screens" in path.parts:
            if ext in UI_EXTENSIONS:
                profile.existing_pages.append(rel)

    profile.file_count = file_count

    # Detect CSS frameworks from config files and dependencies
    _detect_css_framework(root_path, profile)

    # Detect JS frameworks
    _detect_js_framework(root_path, profile)

    return profile


def _detect_css_framework(root: Path, profile: DesignProfile) -> None:
    """Detect CSS frameworks from config files and package.json."""
    # Tailwind
    tailwind_configs = ["tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs"]
    for cfg in tailwind_configs:
        if (root / cfg).exists():
            profile.has_tailwind = True
            profile.has_css_framework = True
            profile.css_framework = "tailwind"
            return

    # Check package.json for CSS frameworks
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            dep_names = " ".join(all_deps.keys()).lower()

            if "tailwindcss" in dep_names:
                profile.has_tailwind = True
                profile.has_css_framework = True
                profile.css_framework = "tailwind"
            elif "bootstrap" in dep_names:
                profile.has_css_framework = True
                profile.css_framework = "bootstrap"
            elif "@mui/material" in dep_names or "@material-ui" in dep_names:
                profile.has_css_framework = True
                profile.css_framework = "material-ui"
            elif "bulma" in dep_names:
                profile.has_css_framework = True
                profile.css_framework = "bulma"
        except (json.JSONDecodeError, KeyError):
            pass

    # Check for CDN references in HTML files
    for html_file in profile.html_files[:5]:
        try:
            content = (root / html_file).read_text(errors="replace").lower()
            if "tailwindcss" in content or "tailwind" in content:
                profile.has_tailwind = True
                profile.has_css_framework = True
                profile.css_framework = "tailwind"
            elif "bootstrap" in content:
                profile.has_css_framework = True
                profile.css_framework = "bootstrap"
        except OSError:
            pass


def _detect_js_framework(root: Path, profile: DesignProfile) -> None:
    """Detect JS frameworks from package.json."""
    pkg = root / "package.json"
    if not pkg.exists():
        return

    try:
        data = json.loads(pkg.read_text())
        all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        dep_names = set(all_deps.keys())

        if "react" in dep_names or "react-dom" in dep_names:
            profile.has_react = True
        if "vue" in dep_names:
            profile.has_vue = True
        if "@angular/core" in dep_names:
            profile.has_angular = True
    except (json.JSONDecodeError, KeyError):
        pass
