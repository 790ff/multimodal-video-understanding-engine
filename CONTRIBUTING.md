# Contributing

This project follows a pull-request workflow.

## Branching

- The protected default branch is `main`.
- Do not commit directly to `main`.
- Use short feature branches, for example `feature/upload-metadata` or `fix/status-errors`.
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
- Wait for CI before merging.
