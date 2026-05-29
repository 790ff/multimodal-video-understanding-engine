# Multimodal Video Understanding Engine

Local product app and backend MVP for turning uploaded videos into timestamped
video memory: transcripts, keyframes, scene data, timeline events, and
question-answerable evidence.

The backend was ready through M7 from the Software Engineering Specification.
M8 adds the first React/Vite product web app on top of the existing FastAPI
backend.

## Current Product Scope

- React/Vite local web app for upload, status, analysis, timeline, and ask
- Upload and status endpoints
- Audio extraction, keyframe extraction, and scene detection
- Transcription and keyframe visual summaries through provider adapters
- Scene/window timeline events with evidence links
- Question answering over stored timeline, transcript, frame, and scene evidence
- SQLite persistence for video metadata and analysis outputs
- Tests using fakes without real provider calls

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer
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
cd frontend
npm install
cp .env.example .env.local
```

Edit `.env` before running real analysis. Edit `frontend/.env.local` if the API
uses a non-default port. Leave both local env files untracked.

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

## Run Locally

```bash
uvicorn app.main:app --reload
```

Then open:

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

In another terminal:

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open the product app at http://127.0.0.1:5173.

If port 8000 is busy, run with another port:

```bash
uvicorn app.main:app --reload --port 8001
```

Then set `VITE_API_BASE_URL="http://127.0.0.1:8001"` in
`frontend/.env.local` and restart Vite.

## Manual Acceptance Checklist

Use a short `.mp4` or `.mov` video for local verification.

- [ ] Start the API server and product web app.
- [ ] Upload a short video from the web app.
- [ ] Confirm status changes to `uploaded`.
- [ ] Run analysis and confirm the result reaches `analyzed`.
- [ ] Confirm timeline events render in timestamp order.
- [ ] Timeline events include evidence references to transcript, frame, or scene records.
- [ ] Ask a non-empty question and confirm the answer includes timestamped evidence.
- [ ] Repeat the ask request and confirm the video remains analyzed without rerunning upload or preprocessing.

Example ask request:

```json
{
  "question": "What happened at the start?"
}
```

## Known Limitations

- No authentication, user accounts, roles, or multi-tenant isolation.
- No background queue; analysis runs synchronously in the request process.
- No ranking, embeddings, vector search, or deep mode. `/ask` uses stored evidence only.
- No production storage layer; SQLite and local `data/` folders are for local MVP use.
- No production deployment hardening such as HTTPS termination, cloud object storage, or worker scaling.
- Timeline frame evidence displays local frame references; serving extracted frames in-browser is deferred.

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
cd frontend
npm run check
npm run lint
npm test
npm run build
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
frontend/
  src/api/         Frontend API client and response types
  src/components/  Product UI components
  src/hooks/       Local workflow state
  src/views/       Product workspace views
  src/styles/      Application CSS
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
- M8: Product web app foundation
