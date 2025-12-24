# ADR-001: Documentation Automation Tools

**Status**: Accepted
**Date**: 2024-12-24
**Deciders**: Development Team
**Related Issues**: #196, #201, #202, #203, #204

## Context

The video_converter project has experienced documentation-implementation drift, with 20+ modules implemented without corresponding documentation updates. Manual documentation maintenance is error-prone and time-consuming. We need to evaluate and potentially implement documentation automation tools to:

1. Generate API documentation from docstrings
2. Generate architecture diagrams automatically
3. Keep documentation synchronized with code

## Decision

After evaluating multiple tools, we decided to:

1. **Keep mkdocstrings** as the primary API documentation tool (already configured)
2. **Add pyreverse and pydeps** for automated architecture diagram generation
3. **Implement a diagram generation script** for on-demand updates

### Tools Evaluated

#### API Documentation Tools

| Tool | Integration | Quality | Maintenance | Learning Curve | Community | Score |
|------|-------------|---------|-------------|----------------|-----------|-------|
| **mkdocstrings** | 5/5 (existing) | 5/5 | 5/5 | 5/5 | 4/5 | **4.7** |
| pdoc | 2/5 | 4/5 | 4/5 | 5/5 | 3/5 | 3.4 |
| Sphinx | 1/5 | 5/5 | 2/5 | 2/5 | 5/5 | 2.7 |

**Winner: mkdocstrings** - Already integrated with MkDocs, excellent output quality, minimal maintenance.

#### Architecture Diagram Tools

| Tool | Integration | Quality | Maintenance | Learning Curve | Community | Score |
|------|-------------|---------|-------------|----------------|-----------|-------|
| **pyreverse** | 4/5 | 4/5 | 5/5 | 5/5 | 4/5 | **4.4** |
| **pydeps** | 4/5 | 5/5 | 5/5 | 5/5 | 3/5 | **4.4** |
| py2puml | 2/5 | 3/5 | 2/5 | 4/5 | 2/5 | 2.5 |

**Winners: pyreverse + pydeps** - Both complement each other well. pyreverse generates class/package diagrams, pydeps generates dependency graphs.

## Rationale

### Why Keep mkdocstrings

1. Already configured and working with MkDocs Material theme
2. Excellent integration with existing documentation structure
3. Supports Google-style docstrings (project standard)
4. No migration effort required
5. Active community and regular updates

### Why Add pyreverse + pydeps

1. **pyreverse** (from pylint):
   - Generates UML class diagrams automatically
   - Generates package structure diagrams
   - Works with existing pylint dependency
   - Outputs SVG/PNG formats

2. **pydeps**:
   - Creates dependency graphs showing module relationships
   - Supports clustering for large codebases
   - Generates high-quality SVG output
   - Configurable depth and filtering

### Why Not py2puml

- Failed with Python 3.12 Literal type annotations
- Less active maintenance
- PlantUML requires additional tooling

### Why Not Sphinx

- Requires significant migration from MkDocs
- More complex configuration
- Duplicates existing mkdocstrings functionality

## Consequences

### Positive

- Automated diagram generation reduces manual effort
- Diagrams stay synchronized with code structure
- Easy to regenerate on demand
- No changes to existing API documentation workflow
- Minimal new dependencies

### Negative

- Generated diagrams may need manual cleanup for presentations
- SVG files add to repository size
- Requires Graphviz installation for SVG output

### Neutral

- Diagrams are generated on-demand, not in CI (to avoid large artifacts)
- Manual trigger preferred over automatic generation

## Implementation

### New Files Created

1. `scripts/generate_diagrams.py` - Diagram generation script
2. `docs/adr/001-documentation-automation-tools.md` - This ADR

### Dependencies Added

```toml
[project.optional-dependencies]
docs = [
    # ... existing dependencies ...
    "pydeps>=1.12.0",
    # pylint already includes pyreverse
]
```

### Usage

```bash
# Generate all architecture diagrams
python scripts/generate_diagrams.py

# Output to custom directory
python scripts/generate_diagrams.py --output-dir docs/diagrams
```

### Generated Diagrams

| File | Description |
|------|-------------|
| `classes_video_converter.svg` | UML class diagram |
| `packages_video_converter.svg` | Package structure diagram |
| `dependencies.svg` | Full dependency graph |
| `core_dependencies.svg` | Core module dependencies |

## Alternatives Considered

### Full Automation via CI

**Rejected**: Generated diagrams are large and change frequently with code changes, leading to noisy diffs. On-demand generation is preferred.

### Pre-commit Hook for Diagram Updates

**Deferred**: Could be added later if diagram staleness becomes an issue. Current approach allows selective regeneration.

### Documentation Validation in CI

**Deferred**: Could add `mkdocs build --strict` to CI to catch documentation issues early.

## Automated Evaluation Script

A reproducible evaluation script has been created to test all three API documentation tools:

```bash
# Run evaluation
python scripts/evaluate_api_doc_tools.py

# Keep generated documentation for inspection
python scripts/evaluate_api_doc_tools.py --keep-output
```

### Evaluation Results (2024-12-24)

| Tool | Status | Build Time | Output Size | HTML Files |
|------|--------|------------|-------------|------------|
| mkdocstrings | OK | 4.38s | 13.95 MB | 57 |
| pdoc | OK | 2.75s | 12.12 MB | 13 |
| Sphinx | OK | 1.01s | 1.51 MB | 4 |

**Note**: Sphinx generates fewer files in the test because it only includes explicitly configured modules, while mkdocstrings and pdoc automatically document all modules.

## Verification Results

The following tests were performed on 2024-12-24 with Python 3.12:

### py2puml Test Result

```bash
$ py2puml src/video_converter video_converter
ValueError: Could not resolve type Callable in module video_converter.converters.progress
```

**Conclusion**: Incompatible with Python 3.12 type annotations. Not suitable for this project.

### pyreverse Test Result

```bash
$ pyreverse -o svg -p video_converter --output-directory docs/architecture/generated src/video_converter
Format svg is not supported natively. Pyreverse will try to generate it using Graphviz...
Analysed 77 modules with a total of 159 imports
```

**Generated Files**:
- `classes_video_converter.svg` (426 KB)
- `packages_video_converter.svg` (117 KB)

**Conclusion**: Successfully generates high-quality diagrams.

### pydeps Test Result

```bash
$ pydeps src/video_converter --max-bacon=3 --cluster --noshow -o docs/architecture/generated/dependencies.svg
```

**Generated Files**:
- `dependencies.svg` (193 KB)

**Conclusion**: Successfully generates dependency graphs with clustering.

## References

- [mkdocstrings documentation](https://mkdocstrings.github.io/)
- [pyreverse documentation](https://pylint.pycqa.org/en/latest/pyreverse.html)
- [pydeps documentation](https://github.com/thebjorn/pydeps)
- Issue #196: Evaluate documentation automation tools
- Issue #202: Architecture diagram tools evaluation
