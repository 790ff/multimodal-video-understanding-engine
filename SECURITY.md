# Security

This MVP processes local media files and may use external AI APIs in later milestones.
Do not commit secrets, API keys, raw private videos, large generated media files, or local
database files.

## Sensitive Data

- Keep `.env` local.
- Store only placeholder values in `.env.example`.
- Runtime media under `data/uploads`, `data/audio`, and `data/frames` is ignored by Git.
- Runtime media folders are not served as public static routes in the local MVP.
- Uploads and extracted audio stay local. Frame evidence may use safe relative frame references, not private local filesystem paths.
- API errors should return controlled safe messages and must not expose provider keys, stack traces, `.env` paths, or private local paths.

## Local MVP Authentication

The local MVP does not include authentication, accounts, roles, or multi-tenant
isolation. Any hosted deployment or public media exposure must add authentication
and authorization before exposing uploads, audio, frames, transcripts, timelines,
answers, or evidence.

## Reporting

For now, report security issues directly to the repository owner in GitHub.
