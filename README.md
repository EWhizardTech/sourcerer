Here’s a polished, detailed **README.md** with clear structure, improved wording, and developer-friendly flow:

---

# 🚀 Sourcerer Backend

**One place to learn and grow**

This repository contains the backend services for Sourcerer. It supports both containerized execution (recommended) and local development workflows.

---

## 📦 Prerequisites

* Docker
* Docker Compose
* (Optional) GPU with proper drivers (for accelerated workloads)

---

## ⚙️ Usage

### 🖥️ Running with GPU (Development Machine)

Use this setup when working on a GPU-enabled machine.

#### 🔹 Build and run containers

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

#### 🔹 Run containers (after initial build)

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
```

---

### ☁️ Running without GPU (CI / Cloud / CPU)

If you’re on a CPU-only machine:

```powershell
docker compose up
```

---

## ⚡ Faster Builds Using Docker Hub Cache

To significantly reduce build times, a prebuilt base image is used.

### 🔹 First-time setup (new machine)

```bash
docker pull premdharshan/sourcerer-base:latest
```

### 🔹 Build and run with cache (~30 seconds)

```bash
docker compose up --build
```

---

### 🔄 Updating Base Image (When Dependencies Change)

If you modify:

* `pyproject.toml`
* `uv.lock`

Rebuild and push the base image:

```bash
docker build -f Dockerfile.base -t premdharshan/sourcerer-base:latest .
docker push premdharshan/sourcerer-base:latest
```

---

## 🧱 Local Development (Without Docker)

If you prefer running the backend locally:

### 🔹 Step 1: Start Infrastructure (Redis, etc.)

```bash
docker compose -f docker-compose.infra.yml up
```

---

### 🔹 Step 2: Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

---

### 🔹 Step 3: Run the Backend Server

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

or 

uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### Step 4: Run the Streamlit frontend app
```bash
uv run streamlit run frontend/app.py
```

---


## 📁 Project Structure (Optional Overview)

```
.
├── app/                # FastAPI application
├── tests/              # Test suite
├── docs/               # Documentation
├── frontend/           # Streamlit frontend
├── docker-compose.yml
├── docker-compose.gpu.yml
├── docker-compose.infra.yml
├── Dockerfile
├── Dockerfile.base
├── pyproject.toml
└── uv.lock
```

---

## 📝 Notes

* GPU mode requires compatible drivers (e.g., NVIDIA + CUDA).
* Use Docker Hub cache for faster builds in development.
* Rebuild the base image whenever dependencies change.
* Local mode is useful for debugging and rapid iteration.

---

## 🧪 Running Tests

```bash
pytest -s -v
```

```

Run a particular test file
```
pytest tests/test_parser_chunker.py -v
```

Run a particular test function
```
pytest tests/test_parser_chunker.py::test_docx_parser_and_chunker -v
```

---

## 💡 Tips

* Use `-s` with pytest to see print/debug output.
* Use GPU mode only when necessary to conserve resources.
* Keep your base image updated for optimal build performance.

---
