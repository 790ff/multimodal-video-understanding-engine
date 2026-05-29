# Multimodal Video Understanding Engine

Backend-centered MVP for turning uploaded videos into timestamped video memory:
transcripts, keyframes, scene data, timeline events, and question-answerable evidence.

This repository currently contains the backend pipeline through M6 from the Software Engineering Specification.

## Current Milestone

M6: Ask video

- Upload and status endpoints
- Audio extraction, keyframe extraction, and scene detection
- Transcription and keyframe visual summaries through provider adapters
- Scene/window timeline events with evidence links
- Question answering over stored timeline, transcript, and frame evidence
- SQLite persistence for video metadata and analysis outputs
- Tests using fakes without real provider calls

## Requirements

- Python 3.11 or newer
- FFmpeg installed locally before media preprocessing work begins
- Provider API key before transcription and vision analysis milestones

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Model Provider Configuration

The analysis pipeline can use either OpenAI or Gemini for transcription and frame summaries.
Set one provider for the full analysis pipeline in `.env`:

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

## Analyze A Video

1. Upload a video with `POST /videos/upload`.
2. Run `POST /videos/{video_id}/analyze`.
3. Read the generated timeline with `GET /videos/{video_id}/timeline`.
4. Ask a stored-evidence question with `POST /videos/{video_id}/ask`.

The analyze response includes counts for transcript segments, keyframes, scenes, and
timeline events. Timeline events include evidence references back to transcript
segments, keyframes, and scenes.

## Ask A Video Question

`POST /videos/{video_id}/ask` accepts:

```json
{
  "question": "What happened at the start?"
}
```

The response includes an `answer` and timestamped `evidence` references from the
stored timeline, transcript, and frame metadata. Empty questions return 400,
missing videos return 404, and videos that have not completed analysis return 409.
The ask endpoint does not rerun analysis, generate a new timeline, or prompt over
the full video file. M6 intentionally avoids ranking, embeddings, and vector
search so those can be added later without changing the API contract.

## Run Tests

```bash
pytest
```

## Development Workflow

This repository uses a pull-request workflow for changes to `main`.

- Work on feature branches.
- Open a pull request for every change.
- Run local checks before opening or merging a pull request.
- Runtime media, local databases, and secrets must stay out of Git.

Install development tools with:

```bash
pip install -r requirements-dev.txt
ruff check app tests
pytest
```

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
- M7: Verification and release
