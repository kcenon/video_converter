#!/usr/bin/env python3
"""Generate architecture diagrams using pyreverse and pydeps.

This script automates the generation of:
- Class diagrams using pyreverse (pylint)
- Package diagrams using pyreverse
- Dependency graphs using pydeps

Usage:
    python scripts/generate_diagrams.py [--output-dir DIR]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a shell command and handle errors."""
    print(f"  {description}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout:
            print(f"    {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"    Error: Command not found: {cmd[0]}")
        return False


def generate_pyreverse_diagrams(output_dir: Path, project_name: str) -> bool:
    """Generate class and package diagrams using pyreverse."""
    print("\n[1/3] Generating pyreverse diagrams...")

    # Generate SVG diagrams (more portable than PNG)
    cmd = [
        "pyreverse",
        "-o", "svg",
        "-p", project_name,
        "--output-directory", str(output_dir),
        "src/video_converter",
    ]

    success = run_command(cmd, "Creating class and package diagrams")

    if success:
        # Rename output files for clarity
        classes_file = output_dir / f"classes_{project_name}.svg"
        packages_file = output_dir / f"packages_{project_name}.svg"

        if classes_file.exists():
            print(f"    Created: {classes_file}")
        if packages_file.exists():
            print(f"    Created: {packages_file}")

    return success


def generate_pydeps_diagram(output_dir: Path) -> bool:
    """Generate dependency graph using pydeps."""
    print("\n[2/3] Generating pydeps dependency graph...")

    output_file = output_dir / "dependencies.svg"
    cmd = [
        "pydeps",
        "src/video_converter",
        "--max-bacon=3",
        "--cluster",
        "--no-show",
        "-o", str(output_file),
    ]

    success = run_command(cmd, "Creating dependency graph")

    if success and output_file.exists():
        print(f"    Created: {output_file}")

    return success


def generate_core_diagram(output_dir: Path) -> bool:
    """Generate focused diagram for core module."""
    print("\n[3/3] Generating core module diagram...")

    output_file = output_dir / "core_dependencies.svg"
    cmd = [
        "pydeps",
        "src/video_converter/core",
        "--max-bacon=2",
        "--cluster",
        "--no-show",
        "-o", str(output_file),
    ]

    success = run_command(cmd, "Creating core module diagram")

    if success and output_file.exists():
        print(f"    Created: {output_file}")

    return success


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate architecture diagrams for video_converter"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/architecture/generated"),
        help="Output directory for diagrams (default: docs/architecture/generated)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Architecture Diagram Generator")
    print("=" * 60)

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {args.output_dir}")

    # Track success
    results = []

    # Generate diagrams
    results.append(generate_pyreverse_diagrams(args.output_dir, "video_converter"))
    results.append(generate_pydeps_diagram(args.output_dir))
    results.append(generate_core_diagram(args.output_dir))

    # Summary
    print("\n" + "=" * 60)
    success_count = sum(results)
    total_count = len(results)
    print(f"Completed: {success_count}/{total_count} diagram generators succeeded")

    if all(results):
        print("\nAll diagrams generated successfully!")
        return 0
    else:
        print("\nSome diagrams failed to generate. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
