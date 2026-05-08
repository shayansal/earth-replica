# Earth Replica Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first public repository foundation for Earth Replica, a Genesis-backed open source initiative for a progressive 4D live illustration and simulation of Earth.

**Architecture:** The initial repo defines a Python package with project metadata, a simulation-scope model, and a Genesis sandbox entrypoint. Documentation separates the public mission from near-term engineering boundaries so contributors can join without assuming the full planetary simulator already exists.

**Tech Stack:** Python 3.10+, pytest, Genesis (`genesis-world`) as the intended physics backend, GitHub Actions for CI.

---

### Task 1: Core Project Contract

**Files:**
- Create: `tests/test_project.py`
- Create: `src/earth_replica/__init__.py`
- Create: `src/earth_replica/project.py`

- [x] **Step 1: Write failing tests** for project name, mission text, dimensional framing, and early physics domains.
- [x] **Step 2: Run tests and verify they fail** because `earth_replica` is not implemented yet.
- [x] **Step 3: Implement minimal metadata module** with immutable dataclasses.
- [x] **Step 4: Run tests and verify they pass.**

### Task 2: Repository Foundation

**Files:**
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/physics-scope.md`
- Create: `examples/genesis_sandbox.py`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.github/workflows/ci.yml`
- Create: `LICENSE`

- [x] **Step 1: Add package and test configuration** in `pyproject.toml`.
- [x] **Step 2: Add public-facing README** with mission, scope, and contribution path.
- [x] **Step 3: Add architecture and physics-scope docs** that define progressive fidelity.
- [x] **Step 4: Add Genesis sandbox example** that imports Genesis lazily and explains installation.
- [x] **Step 5: Add MIT license, gitignore, and CI workflow.**

### Task 3: Publish

**Files:**
- Modify: local git metadata
- Remote: `shayansal/earth-replica`

- [x] **Step 1: Run local verification** with pytest.
- [x] **Step 2: Commit scaffold.**
- [x] **Step 3: Create public GitHub repo** with the approved description.
- [x] **Step 4: Push `main` to GitHub.**
