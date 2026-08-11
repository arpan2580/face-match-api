# Face Match Profile API

A Flask-based backend service for creating user profiles with a selfie image and later
identifying users by matching a new image (single-person or group) against stored face
embeddings.

This project is designed as a **reusable face-matching module** rather than a standalone
product — it's intended to be plugged into other applications that need selfie-based
verification, such as attendance systems (individual or group/classroom selfie attendance),
event check-ins, or similar identity-confirmation flows. Authentication, business logic, and
production-grade configuration are expected to be handled by the consuming application, not
by this module (see [Security Notes](#security-notes) below).

### Related Projects

A companion Flutter mobile app that consumes these four endpoints and demonstrates the matching flow end-to-end is planned to be published separately. 

*(Link to be added once that repository is uploaded.)*

## Overview

This service exposes four REST endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/create-profile` | POST | Registers a new user with name, email, phone, and a profile image. Compresses and stores the image, generates a face embedding, and saves everything to SQLite. |
| `/find-image` | POST | Accepts a single selfie image and returns the best-matching stored profile, if similarity ≥ 0.6. |
| `/find-group-image` | POST | Accepts a group photo, detects all faces, and returns every stored profile that matches any detected face (similarity ≥ 0.6). |
| `/get-profile` | POST | Looks up a stored profile by `image_name` and returns name, email, and phone. |

## Tech Stack

- **Framework:** Flask 2.2.5
- **Database:** SQLite via SQLAlchemy (`Flask-SQLAlchemy` 3.0.5)
- **Image handling:** Pillow 9.5.0 (compression), OpenCV (`opencv-python-headless` 4.10.0.84)
- **Face detection / embeddings:** `insightface` 0.7.3, running on `onnxruntime` 1.18.1
- **Server:** Gunicorn 21.2.0 (see `Dockerfile`)
- **Containerization:** Docker (multi-stage build)

## Project Structure

```
.
├── app.py             # Flask application and route definitions
├── config.py          # App configuration (DB URI, etc.)
├── models.py          # SQLAlchemy models (UserProfile, etc.)
├── models/            # insightface model to be stored here (run insightface locally and copy the buffalo_l model directory here)
├── profile_images/    # stored compressed profile images
├── requirements.txt   # Python dependencies
└── Dockerfile
```

## API Reference

### `POST /create-profile`

**Request:** `multipart/form-data`

| Field | Type | Required |
|---|---|---|
| `name` | string | Yes |
| `email` | string | Yes |
| `phone` | string | Yes |
| `image` | file | Yes |

**Response (200 — match found):**
```json
{
  "message": "Profile created successfully",
  "image_name": "<image_name>",
  "status": 200
}
```

### `POST /find-image`

**Request:** `multipart/form-data` with a single `image` file (a selfie of one person).

**Response (200 — match found):**
```json
{
  "message": "Profile image matched",
  "matched_image": "<image_name>",
  "status": 200
}
```

**Response (400 — no match):**
```json
{
  "message": "Profile image not found",
  "status": 400
}
```

### `POST /find-group-image`

**Request:** `multipart/form-data` with a single `image` file containing multiple faces.

**Response (200):**
```json
{
  "matches": [
    { "name": "...", "email": "...", "image_name": "..." }
  ],
  "status": 200
}
```

### `POST /get-profile`

**Request:** JSON or form body with `image_name`.

**Response (200):**
```json
{
  "name": "...",
  "email": "...",
  "phone": "...",
  "status": 200
}
```

**Response (400 — not found):**
```json
{
  "message": "User not found",
  "status": 400
}
```

## Setup

### Prerequisites

- Python 3.10 or above
- pip
- Docker (optional, for containerized runs)

### Local Development

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Docker

```bash
docker build -t face-recognition-api .
docker run -p 5000:5000 -v $(pwd)/data:/app face-recognition-api
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `SQLALCHEMY_DATABASE_URI` | SQLite DB path | `sqlite:////app/users.db` (hardcoded — see note above) |


## Security Notes

- **No authentication by design.** This module intentionally does not implement auth — it's
  meant to be embedded into other applications (attendance systems, check-in apps, etc.) that
  handle their own authentication/authorization layer around these endpoints. If you deploy this
  service standalone or expose it directly to the internet without a consuming application in
  front of it, anyone who can reach `/get-profile` or `/find-image` could query stored personal
  data (name, email, phone) or attempt face matches — make sure a gateway, reverse proxy, or the
  wrapping application enforces auth before these endpoints are reachable.
- **Note:** `config.py` currently hardcodes `SQLALCHEMY_DATABASE_URI = "sqlite:////app/users.db"`.
  This is intentional for this demo/reference project — the path targets the containerized filesystem for local testing.
  **If you adopt this project for a real application, replace this with your actual database configuration** (e.g., PostgreSQL/MySQL)
  connection string, ideally sourced from an environment variable rather than hardcoded before using it in production.
- The similarity threshold (`0.6`) is hardcoded in two places (`/find-image` and
  `/find-group-image`). You may want to centralize it as a config value so it's tuned in one
  place.

## Model Setup

This repository does **not** include the `insightface` `.onnx` model weight files — they must
be downloaded and placed manually before the app will run correctly. If the expected model
files aren't present in the `models/` directory, face detection/embedding calls will likely
fail or error out.

1. **Install dependencies locally** (outside Docker, so the download step below works):
   ```bash
   pip install -r requirements.txt
   ```

2. **Trigger the default model download.** Run a short Python snippet that initializes
   `insightface`'s `FaceAnalysis` the same way `app.py` does so it downloads to its default cache location — commonly `~/.insightface/models/<model_name>/` on Linux/macOS.
   Example:
   ```python
   from insightface.app import FaceAnalysis
   app = FaceAnalysis(name="buffalo_l")
   app.prepare(ctx_id=0)
   ```

3. **Copy the downloaded model folder into this project's `models/` directory.** For example:
   ```bash
   cp -r ~/.insightface/models/buffalo_l ./models/
   ```

4. **Rebuild/run the Docker image** so the `COPY models ./models` step in the `Dockerfile`
   picks up the files you just placed there:
   ```bash
   docker build -t face-recognition-api .
   ```

If anyone cloning this repo runs into a "model not found" style error, this is almost certainly
the cause — point them to this section.

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for
details.

## CI/CD

This project can be wired up for automated builds and deployment using GitHub Actions —
no changes to the existing `Dockerfile` or application code are required. The general flow:

1. On every push to the main branch, a workflow builds the Docker image from the existing
   `Dockerfile`.
2. The image is pushed to **GitHub Container Registry (GHCR)**, tagged (e.g. `:latest` or by
   commit SHA).
3. A deploy step connects to an EC2 instance over SSH and runs `docker pull` + restarts the
   container with the new image.

