# Multimodal Video Understanding Engine

Backend-centered MVP for turning uploaded videos into timestamped video memory:
transcripts, keyframes, scene data, timeline events, and question-answerable evidence.

This repository currently contains the M1 project scaffold from the Software Engineering Specification.

## Current Milestone

M1: Project scaffold

- FastAPI application entry point
- Central settings module
- Layered package structure
- Runtime data folders
- Base schemas, domain errors, and status model
- SQLAlchemy model scaffold
- Starter tests

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
GEMINI_MODEL="gemini-2.5-flash-lite"
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
  adapters/        FFmpeg, OpenCV, scene detection, and AI API wrappers
  db/              SQLAlchemy ORM models
  domain/          Status values and controlled application errors
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
- M5: Timeline builder
- M6: Ask video
- M7: Verification and release
