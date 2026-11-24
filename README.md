<h1 align="center">🎙️ Speech to text Conversion for oral histories & interviews</h1>

<p align="center">
  <em>Preserving the legacy of World War II veterans through AI-powered transcription, translation, and summarization.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React.js-blue" alt="React">
  <img src="https://img.shields.io/badge/Backend-Python_Flask-green" alt="Flask">
  <img src="https://img.shields.io/badge/Database-PostgreSQL-336791" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/AI-Faster--Whisper_&_OpenVINO-lightgrey" alt="Whisper">
  <img src="https://img.shields.io/badge/Container-Docker-2496ED" alt="Docker">
</p>

---

## 📖 Overview

**Motivation:**
Personal testimonies of soldiers from World War II are an invaluable historical source. However, many are in old formats, spoken in various languages, and remain inaccessible to the general public. In the digital age, preserving this heritage and making it accessible to diverse audiences is of immense importance.

**Goal:**
Develop an end-to-end containerized system for the **Jewish World War II Museum** to transcribe, translate, and summarize historical testimonies into multiple languages, facilitating deeper understanding and historical research.

## ✨ Features

- **Audio & Video Uploads:** Upload audio and video testimony files with automatic conversion/extraction (`FFmpeg`, `moviepy`, `pydub`).
- **AI Transcription with Hardware Acceleration:** Speech-to-text conversion powered by `Faster-Whisper` with configurable hardware selection (`auto`, `intel` via OpenVINO GenAI, `cuda`, or `cpu` fallback with `int8`).
- **Smart Summarization:** Generates extractive summaries of testimonies using `NLTK`.
- **Multilingual Support:** Transcripts and summaries are accessible in **Hebrew, English, and Russian** via Google Translator (`deep-translator`).
- **Keyword Search:** Search across video names, transcripts, and summaries in PostgreSQL to locate relevant testimonies.
- **Docker-First Deployment:** Full multi-container setup (`db`, `backend`, `frontend`) managed via Docker Compose and environment variables.

## 🛠️ Tech Stack

### Frontend
- **React.js & Nginx:** Built into static assets and served via Nginx inside Docker.

### Backend
- **Python Flask:** RESTful API server (`/upload`, `/transcribe`, `/summarize`, `/search`, `/videos`, `/delete`) with structured `logging`.
- **Media & AI / NLP:**
  - `Faster-Whisper` & `OpenVINO` (`openvino` / `openvino-genai` when enabled)
  - `NLTK` (`punkt_tab`, `stopwords`)
  - `deep-translator`
  - `FFmpeg`, `moviepy`, `pydub`

### Database & Infrastructure
- **PostgreSQL:** Relational database (`psycopg2-binary`) with persistent Docker volume storage.
- **Docker & Docker Compose:** Containerized orchestration for database, backend API, and frontend web app.

## ⚙️ System Architecture

The platform runs as containerized services orchestrated with Docker Compose:

1. **Frontend (`my-app` / Nginx):** Web interface for uploading media files, viewing/translating/summarizing transcripts, and searching testimonies.
2. **Backend (`Flask`):** Handles file ingestion, audio extraction/conversion, Whisper transcription, translation, summarization, and API routes.
3. **Database (`PostgreSQL`):** Stores testimony metadata, source language, transcripts, and summaries per language.
4. **Volumes:** Persistent storage for PostgreSQL data (`pgdata`), uploaded files (`uploads/`), and model cache/OpenVINO models.

## 🚀 Running with Docker

1. Create a local `.env` file from `.env.example` and set `POSTGRES_PASSWORD` along with your Whisper/hardware settings (`WHISPER_DEVICE_PREFERENCE`, `WHISPER_MODEL_SIZE`, `OPENVINO_WHISPER_DIR`).
2. Build and start all services:
   ```bash
   docker compose up --build -d
   ```

## 👥 Team & Acknowledgments

This project was developed and presented at **SCE Tech Fest 25** (Innovation Sustainability Community, SCE - Shamoon College of Engineering).

- **Developers:** Yoav Haviv Vaknin & Dimitri Shpak
- **Academic Advisors:** Mr. Idan Tubis, Prof. Shlomo Grinberg

---
<p align="center"><i>Ensuring valuable historical records remain accessible for future generations.</i></p>  
