# Multimodal Video Understanding Engine

Backend MVP for turning uploaded videos into timestamped video memory:
transcripts, keyframes, scene data, timeline events, and question-answerable evidence.

The repository is ready through M7 from the Software Engineering Specification.
M7 is delivery readiness and verification infrastructure for the backend MVP. It
does not add a user interface.

## Current Backend Scope

- Upload and status endpoints
- Audio extraction, keyframe extraction, and scene detection
- Transcription and keyframe visual summaries through provider adapters
- Scene/window timeline events with evidence links
- Question answering over stored timeline, transcript, frame, and scene evidence
- SQLite persistence for video metadata and analysis outputs
- Tests using fakes without real provider calls

## Requirements

- Python 3.11 or newer
- FFmpeg installed locally for real video analysis
- Provider API key for real transcription, frame summaries, and answer generation
- Local filesystem access for `data/uploads`, `data/audio`, `data/frames`, and SQLite

Automated tests do not require FFmpeg, provider keys, or external API calls.

## Setup From Scratch

```bash
cd "Multimodal Video Understanding Engine"
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` before running real analysis. Leave `.env` local; it is ignored by Git.

## Model Provider Configuration

The analysis pipeline can use either OpenAI or Gemini for transcription and frame
summaries. Set one default provider in `.env`:

```env
MODEL_PROVIDER="gemini"
GEMINI_API_KEY=""
GEMINI_MODEL="gemini-3.5-flash"
```

Or split providers by modality. This keeps Gemini on frame summaries while trying
multiple transcription providers in order:

```env
MODEL_PROVIDER="gemini"
TRANSCRIPTION_PROVIDER_ORDER="gemini,openai"
FRAME_ANALYSIS_PROVIDER="gemini"
GEMINI_API_KEY=""
OPENAI_API_KEY=""
```

Or keep the default OpenAI setup:

```env
MODEL_PROVIDER="openai"
OPENAI_API_KEY=""
TRANSCRIPTION_MODEL="whisper-1"
VISION_MODEL="gpt-4.1-mini"
```

## Run The API

```bash
uvicorn app.main:app --reload
```

Then open:

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

If port 8000 is busy, run with another port:

```bash
uvicorn app.main:app --reload --port 8001
```

## Manual Acceptance Checklist

Use a short `.mp4` or `.mov` video for local verification.

- [ ] Start the API server and open Swagger UI.
- [ ] `POST /videos/upload` with a short video and save the returned `video_id`.
- [ ] `GET /videos/{video_id}/status` returns `uploaded`.
- [ ] `POST /videos/{video_id}/analyze` returns `analyzed` with transcript, keyframe, scene, and timeline counts.
- [ ] `GET /videos/{video_id}/timeline` returns ordered timestamped events.
- [ ] Timeline events include evidence references to transcript, frame, or scene records.
- [ ] `POST /videos/{video_id}/ask` with a non-empty question returns an answer and timestamped evidence.
- [ ] Repeat `POST /videos/{video_id}/ask` and confirm the video remains analyzed without rerunning upload or preprocessing.

Example ask request:

```json
{
  "question": "What happened at the start?"
}
```

## Known Limitations

- No React or custom web UI is included yet; Swagger UI is the local product interface for the backend.
- No authentication, user accounts, roles, or multi-tenant isolation.
- No background queue; analysis runs synchronously in the request process.
- No ranking, embeddings, vector search, or deep mode. `/ask` uses stored evidence only.
- No production storage layer; SQLite and local `data/` folders are for local MVP use.
- No production deployment hardening such as HTTPS termination, cloud object storage, or worker scaling.

## Troubleshooting

Port 8000 already in use:

```bash
uvicorn app.main:app --reload --port 8001
```

FFmpeg missing:

```bash
ffmpeg -version
brew install ffmpeg
```

On Linux, install FFmpeg through your distribution package manager.

Provider key missing:

- Check `MODEL_PROVIDER`, `TRANSCRIPTION_PROVIDER_ORDER`, and `FRAME_ANALYSIS_PROVIDER`.
- Set the matching `OPENAI_API_KEY` or `GEMINI_API_KEY` in local `.env`.
- Restart Uvicorn after changing `.env`.
- If analysis failed earlier, check `GET /videos/{video_id}/status` for the safe failure state.

SQLite or local data reset:

- Runtime data lives under `data/uploads`, `data/audio`, `data/frames`, and `data/*.sqlite3`.
- Stop the server before manually clearing local runtime files.
- Keep the `.gitkeep` files so the runtime folders stay present in Git.

## Run Checks

```bash
ruff check app tests
pytest
```

## Development Workflow

This repository uses a pull-request workflow for changes to `main`.

- Work on feature branches.
- Open a pull request for every change.
- Run local checks before opening or merging a pull request.
- Keep `.env`, local databases, uploaded media, extracted audio, and frames out of Git.

## Project Layout

```text
app/
  api/             FastAPI routers
  adapters/        FFmpeg, OpenCV, scene detection, and provider wrappers
  db/              SQLAlchemy ORM models
  domain/          Status values, timeline data, and controlled application errors
  repositories/    Persistence access layer
  services/        Application workflow services
data/
  uploads/         Uploaded videos
  audio/           Extracted audio files
  frames/          Extracted keyframes
docs/              Software engineering specification and diagrams
tests/             Automated tests
```

## Milestone Plan

- M1: Project scaffold
- M2: Upload and metadata
- M3: Media preprocessing
- M4: Transcription and visual summaries
- M5: Scene/window timeline builder
- M6: Ask video
- M7: Delivery readiness and verification
