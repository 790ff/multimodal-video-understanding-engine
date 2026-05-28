# Contributing

This project follows a pull-request workflow.

## Branching

- The default branch is `main`.
- Do not commit directly to `main`.
- Use short feature branches, for example `m2-upload-metadata` or `fix-status-errors`.
- Open a pull request for every change.

## Local Checks

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check app tests
pytest
```

## Pull Request Expectations

- Keep changes focused on one issue or milestone task.
- Include tests for behavior changes.
- Update documentation when setup, API behavior, or workflow changes.
- Run local lint and test checks before merging.
