#!/usr/bin/env python3
"""Evaluate API documentation generation tools.

This script evaluates and compares API documentation tools:
- mkdocstrings (current - integrated with MkDocs)
- pdoc (lightweight alternative)
- Sphinx + autodoc (industry standard)

Usage:
    python scripts/evaluate_api_doc_tools.py [--output-dir DIR]
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvaluationResult:
    """Result of a tool evaluation."""

    tool_name: str
    success: bool
    build_time: float
    output_size: int
    file_count: int
    error_message: str = ""


def get_dir_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def count_files(path: Path, extension: str = ".html") -> int:
    """Count files with given extension."""
    return len(list(path.rglob(f"*{extension}")))


def evaluate_mkdocstrings(project_root: Path, output_dir: Path) -> EvaluationResult:
    """Evaluate mkdocstrings with MkDocs."""
    print("\n[1/3] Evaluating mkdocstrings...")
    print("  - Already configured in mkdocs.yml")
    print("  - Using Google-style docstrings")

    start_time = time.time()
    site_dir = project_root / "site"

    try:
        result = subprocess.run(
            ["mkdocs", "build", "--strict"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        build_time = time.time() - start_time

        if result.returncode == 0:
            output_size = get_dir_size(site_dir)
            file_count = count_files(site_dir)
            print(f"  - Build time: {build_time:.2f}s")
            print(f"  - Output size: {output_size / 1024 / 1024:.2f} MB")
            print(f"  - HTML files: {file_count}")
            return EvaluationResult(
                tool_name="mkdocstrings",
                success=True,
                build_time=build_time,
                output_size=output_size,
                file_count=file_count,
            )
        else:
            return EvaluationResult(
                tool_name="mkdocstrings",
                success=False,
                build_time=build_time,
                output_size=0,
                file_count=0,
                error_message=result.stderr[:500],
            )
    except subprocess.TimeoutExpired:
        return EvaluationResult(
            tool_name="mkdocstrings",
            success=False,
            build_time=120,
            output_size=0,
            file_count=0,
            error_message="Build timed out after 120 seconds",
        )
    except FileNotFoundError:
        return EvaluationResult(
            tool_name="mkdocstrings",
            success=False,
            build_time=0,
            output_size=0,
            file_count=0,
            error_message="mkdocs not installed",
        )


def evaluate_pdoc(project_root: Path, output_dir: Path) -> EvaluationResult:
    """Evaluate pdoc documentation generator."""
    print("\n[2/3] Evaluating pdoc...")
    print("  - Lightweight, single-command generation")
    print("  - No configuration required")

    pdoc_output = output_dir / "pdoc"
    pdoc_output.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    src_path = project_root / "src" / "video_converter"

    try:
        result = subprocess.run(
            ["pdoc", "--output-dir", str(pdoc_output), str(src_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        build_time = time.time() - start_time

        if result.returncode == 0:
            output_size = get_dir_size(pdoc_output)
            file_count = count_files(pdoc_output)
            print(f"  - Build time: {build_time:.2f}s")
            print(f"  - Output size: {output_size / 1024 / 1024:.2f} MB")
            print(f"  - HTML files: {file_count}")
            return EvaluationResult(
                tool_name="pdoc",
                success=True,
                build_time=build_time,
                output_size=output_size,
                file_count=file_count,
            )
        else:
            return EvaluationResult(
                tool_name="pdoc",
                success=False,
                build_time=build_time,
                output_size=0,
                file_count=0,
                error_message=result.stderr[:500],
            )
    except subprocess.TimeoutExpired:
        return EvaluationResult(
            tool_name="pdoc",
            success=False,
            build_time=120,
            output_size=0,
            file_count=0,
            error_message="Build timed out after 120 seconds",
        )
    except FileNotFoundError:
        return EvaluationResult(
            tool_name="pdoc",
            success=False,
            build_time=0,
            output_size=0,
            file_count=0,
            error_message="pdoc not installed (pip install pdoc)",
        )


def evaluate_sphinx(project_root: Path, output_dir: Path) -> EvaluationResult:
    """Evaluate Sphinx with autodoc."""
    print("\n[3/3] Evaluating Sphinx + autodoc...")
    print("  - Industry standard, rich features")
    print("  - Requires additional configuration")

    sphinx_dir = output_dir / "sphinx"
    sphinx_dir.mkdir(parents=True, exist_ok=True)

    source_dir = sphinx_dir / "source"
    build_dir = sphinx_dir / "build"
    source_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal conf.py
    conf_py = source_dir / "conf.py"
    conf_py.write_text(f'''
import sys
import os
sys.path.insert(0, os.path.abspath('{project_root / "src"}'))

project = 'video_converter'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]
html_theme = 'alabaster'
autodoc_member_order = 'bysource'
''')

    # Create index.rst with autodoc
    index_rst = source_dir / "index.rst"
    index_rst.write_text('''
video_converter API
===================

.. automodule:: video_converter.core.config
   :members:
   :undoc-members:

.. automodule:: video_converter.core.types
   :members:
   :undoc-members:

.. automodule:: video_converter.converters.converter
   :members:
   :undoc-members:
''')

    start_time = time.time()

    try:
        result = subprocess.run(
            [
                "sphinx-build",
                "-b", "html",
                str(source_dir),
                str(build_dir),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        build_time = time.time() - start_time

        if result.returncode == 0:
            output_size = get_dir_size(build_dir)
            file_count = count_files(build_dir)
            print(f"  - Build time: {build_time:.2f}s")
            print(f"  - Output size: {output_size / 1024 / 1024:.2f} MB")
            print(f"  - HTML files: {file_count}")
            return EvaluationResult(
                tool_name="Sphinx",
                success=True,
                build_time=build_time,
                output_size=output_size,
                file_count=file_count,
            )
        else:
            return EvaluationResult(
                tool_name="Sphinx",
                success=False,
                build_time=build_time,
                output_size=0,
                file_count=0,
                error_message=result.stderr[:500],
            )
    except subprocess.TimeoutExpired:
        return EvaluationResult(
            tool_name="Sphinx",
            success=False,
            build_time=120,
            output_size=0,
            file_count=0,
            error_message="Build timed out after 120 seconds",
        )
    except FileNotFoundError:
        return EvaluationResult(
            tool_name="Sphinx",
            success=False,
            build_time=0,
            output_size=0,
            file_count=0,
            error_message="sphinx-build not installed (pip install sphinx)",
        )


def print_summary(results: list[EvaluationResult]) -> None:
    """Print evaluation summary table."""
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    print(f"\n{'Tool':<15} {'Status':<10} {'Time (s)':<10} {'Size (MB)':<12} {'Files':<8}")
    print("-" * 55)

    for r in results:
        status = "OK" if r.success else "FAIL"
        size_mb = r.output_size / 1024 / 1024 if r.success else 0
        print(f"{r.tool_name:<15} {status:<10} {r.build_time:<10.2f} {size_mb:<12.2f} {r.file_count:<8}")

    print("\n" + "-" * 70)
    print("SCORING (based on ADR-001 criteria)")
    print("-" * 70)
    print("""
| Tool         | Integration | Quality | Maintenance | Learning | Community | Total |
|--------------|-------------|---------|-------------|----------|-----------|-------|
| mkdocstrings | 5/5 (30%)   | 5/5(25%)| 5/5 (20%)   | 5/5(15%) | 4/5 (10%) | 4.7   |
| pdoc         | 2/5 (30%)   | 4/5(25%)| 4/5 (20%)   | 5/5(15%) | 3/5 (10%) | 3.4   |
| Sphinx       | 1/5 (30%)   | 5/5(25%)| 2/5 (20%)   | 2/5(15%) | 5/5 (10%) | 2.7   |

Winner: mkdocstrings (already integrated, excellent MkDocs Material support)
""")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate API documentation generation tools"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/evaluation"),
        help="Output directory for evaluation results (default: docs/evaluation)",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Keep generated documentation after evaluation",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    print("=" * 70)
    print("API Documentation Tools Evaluation")
    print("=" * 70)
    print(f"\nProject: {project_root}")
    print(f"Output: {args.output_dir}")

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluations
    results = []
    results.append(evaluate_mkdocstrings(project_root, args.output_dir))
    results.append(evaluate_pdoc(project_root, args.output_dir))
    results.append(evaluate_sphinx(project_root, args.output_dir))

    # Print summary
    print_summary(results)

    # Cleanup if requested
    if not args.keep_output:
        print("\nCleaning up evaluation output...")
        if args.output_dir.exists():
            shutil.rmtree(args.output_dir, ignore_errors=True)

    success_count = sum(1 for r in results if r.success)
    print(f"\n{success_count}/{len(results)} tools evaluated successfully.")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
