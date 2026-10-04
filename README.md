# AI-Driven Welding Inspection & Quality Reporting Framework

A complete local academic MVP based on the supplied project presentation. It demonstrates an image collection → preprocessing → AI analysis → defect detection → PDF quality report workflow for crack, porosity, incomplete fusion, and no-defect outcomes.

> This is a demonstration prototype. The included samples are synthetic and the fallback detector is a deterministic computer-vision heuristic. It is not trained or validated for industrial inspection and must not be represented as achieving the presentation's stated accuracy claims. Use certified human inspection for real weld decisions.

## Features

- Demo login (`admin` / `admin123`) and responsive industrial dashboard.
- Upload JPG/JPEG/PNG (up to 10 MB) or run four bundled sample images.
- OpenCV preprocessing with blur, normalization, edge analysis, and a visual ROI overlay.
- SQLite inspection history with result view, report download, and record deletion.
- Formatted PDF report with images, result, pipeline, timestamp, report ID, page number, and disclaimer.
- Modular optional ONNX Runtime model adapter; missing weights automatically use prototype fallback inference.

## Architecture

React + Vite UI → FastAPI API → OpenCV inference pipeline → SQLite local database → ReportLab PDF service. Everything runs locally; the fallback does not require a GPU or network access after dependencies are installed.

## Technology stack

Python, FastAPI, OpenCV, NumPy, SQLite, ReportLab, React, Vite, lucide-react.

## Folder structure

```text
backend/
  main.py, database.py
  ml/{detector.py,preprocessing.py,model.py}
  services/reports.py
  sample_images/ bundled synthetic examples (generated if missing)
  uploads/ generated annotated and source images
  generated_reports/ generated PDFs
frontend/src/ React application and responsive styles
start.bat, start.sh
```

## Installation and running

Requirements: Python 3.12 and Node.js 18+ (npm). Internet is needed only for the initial package installation. Python 3.12 is recommended because it has broad support for the pinned computer-vision wheels.

### Windows

Run `start.bat` from a Python 3.12 installation. It creates a backend virtual environment, installs backend packages, installs frontend packages if needed, starts FastAPI in a second terminal, and runs Vite.

### Linux / macOS

Run `chmod +x start.sh && ./start.sh` with `python3.12` installed. The script installs dependencies and runs the API and UI together.

### Manual setup

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). API docs are at [http://localhost:8000/docs](http://localhost:8000/docs); health check at `/api/health`.

Demo login: **admin** / **admin123**.

## How to perform an inspection

1. Sign in with the demo credentials.
2. Open **New Inspection** and choose a sample image or upload a local weld photo.
3. Select **Analyze weld**. Review the verdict, confidence, and annotated region.
4. Choose **Download PDF report**, or open History to revisit, download, or delete records.

## How AI detection works

`backend/ml/detector.py` first asks the optional model adapter for a prediction. The adapter loads ONNX weights only when a compatible model path and ONNX Runtime are available. The MVP does not ship trained weights. It therefore uses a labeled deterministic route for included demonstration samples and a simple image-processing heuristic for uploaded images. The heuristic output is marked `Prototype AI Analysis` in the interface and is not validated. Confidence values communicate the demo result only and are not calibrated probabilities.

Preprocessing converts to grayscale, applies Gaussian denoising and intensity normalization, then computes Canny edges. The overlay highlights a centerline inspection region derived from image dimensions and edge distribution; it does not establish certified defect localization.

## How PDF reports work

The report is generated locally with ReportLab when the download endpoint is called. It contains source and annotated images, inspection metadata, defect result, pipeline, technology, disclaimer, report identifier, and page number.

## API endpoints

- `POST /api/auth/login`
- `POST /api/inspection/analyze` (multipart `image`, or `sample_name`)
- `GET /api/inspection/history`
- `GET /api/inspection/{id}` and `DELETE /api/inspection/{id}`
- `GET /api/inspection/{id}/image` and `/annotated`
- `POST /api/report/{id}` and `GET /api/report/{id}/download`
- `GET /api/dashboard/stats`, `GET /api/samples`, `GET /api/health`

## Troubleshooting

- **Port already in use:** stop the other process or change the API port in `start.bat`/`start.sh` and `API` in `frontend/src/main.jsx`.
- **Python package install fails:** use Python 3.10–3.12 and recreate `backend/.venv`.
- **UI says backend unavailable:** ensure the API terminal reports startup on port 8000.
- **Image rejected:** use an actual JPG/JPEG/PNG under 10 MB.
- **Browser CORS error:** use the frontend URL at `localhost:5173` or `127.0.0.1:5173`.
- **Generated data reset:** stop the API, remove `backend/weld_inspections.db`, and clear generated files under `backend/uploads` and `backend/generated_reports`.

## Limitations and future scope

No trained model weights or labeled industrial dataset are included. The sample images are synthetic teaching visuals. The demo heuristic is not suitable for manufacturing decisions. Future work could add a properly trained and independently validated detector, annotated real datasets, model-specific localization, role-based access, and deployment to an edge device or production service.

## How to demonstrate this project in 3 minutes

1. Sign in with `admin` / `admin123` and show dashboard totals.
2. Start an inspection and select **Crack** or **Porosity** from sample images.
3. Explain the highlighted prototype ROI and PASS/FAIL result.
4. Download and open the generated PDF report.
5. Show the inspection in History and the other samples, including the good-weld PASS case.

## Production build

Run `cd frontend && npm run build` to generate a minified React bundle in `frontend/dist`. Vite serves the local development experience; the production bundle is built with its bundled esbuild engine. API requests use same-origin `/api`, proxied to FastAPI locally and routed to the backend service on Vercel.

## Vercel deployment

The root `vercel.json` configures Vercel Services with the Vite frontend and FastAPI backend. The browser uses same-origin `/api` requests, and Vercel routes those requests to FastAPI. Connect this repository to Vercel and deploy with the Services feature enabled (currently documented by Vercel as beta). The backend uses `/tmp` for uploads, generated reports, and SQLite when running on Vercel. Those files are temporary and can be isolated per serverless instance; cloud inspection history is therefore not durable. Use a managed database and object storage before relying on deployed history or uploaded files.
