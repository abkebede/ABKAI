# ABK AI (ABK_PAI) — Public Demonstration Release

**ABK AI / ABK_PAI** is a physics-focused AI-assisted teaching and learning environment developed by **Abebe Kebede**. This public repository is a **curated demonstration release** derived from ABK_PAI Volume 100; it is intentionally not the complete private development archive.

## V100 capabilities represented here

- Canonical-problem Physics Tutor with structured, line-by-line feedback
- Teacher-assigned independent homework
- Teacher grading, correction, and written feedback returned to students
- Student portfolio access to grades and teacher feedback
- Domain, Problem Family, Learning Mode, and reasoning-component selections
- Context preservation for active Tutor problems
- Prompt and equation tools
- Help interface for Tutor, Assignments, Prompt Library, Equation Library, and grades

## Public-release scope

This repository exposes representative application source code and documentation so that the scholarly digital contribution can be inspected. The full ABK_PAI development package contains additional private/internal materials that are **not distributed here**, including historical versions, source books, large training/problem banks, development dictionaries, internal manifests, classroom databases, and other development records.

## Software

The V100 application uses Python with FastAPI and Uvicorn. The active V100 application entry point is:

`backend.main_v100:app`

The original Windows launcher is retained as `START_ABK_PAI_V100_BROWSER.bat` for provenance. A local database may be created by the software at runtime; no private classroom database is included in this public release.

## Installation

Create a Python environment and install:

```bash
pip install -r requirements.txt
```

Then run from the repository root:

```bash
uvicorn backend.main_v100:app --host 127.0.0.1 --port 8200
```

Open:

`http://127.0.0.1:8200/v100/student-home`

## Citation

If you use or discuss this repository in scholarly work, please cite the repository and **Abebe Kebede** as the developer/author. ORCID: 0000-0002-0500-9966.

## Repository status

This is a curated public research/education software release. It should not be interpreted as a release of the complete ABK_PAI knowledge base, training resources, or development archive.

## License

No software license is asserted in this curated package. A license should be selected deliberately before permitting reuse or redistribution beyond normal GitHub viewing and citation.
