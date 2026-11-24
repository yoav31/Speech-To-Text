# db.py

import logging
import os
import psycopg2

logger = logging.getLogger(__name__)

ALLOWED_LANGUAGES = {"en", "he", "ru"}

def get_connection():
    """Open a connection to the PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        return conn

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=os.getenv("POSTGRES_DB", "speech_to_text"),
    )
    conn.autocommit = True
    return conn


def _validate_lang(lang: str) -> str:
    if lang not in ALLOWED_LANGUAGES:
        raise ValueError(f"Unsupported language: {lang}")
    return lang


def init_db():
    """Initialize the database schema if it doesn't exist."""
    logger.info("Initializing PostgreSQL database schema")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    name VARCHAR(255) PRIMARY KEY,
                    audio_file_url VARCHAR(500),
                    summary_en TEXT,
                    summary_he TEXT,
                    summary_ru TEXT,
                    transcribe_en TEXT,
                    transcribe_he TEXT,
                    transcribe_ru TEXT,
                    source_lang VARCHAR(8)
                );
                """
            )


def add_new_video(name: str, transcribe: str, source_lang: str, audio_url: str | None = None):
    """Add a new video to the database."""
    lang = _validate_lang(source_lang)
    column = f"transcribe_{lang}"
    sql = f"""
        INSERT INTO videos (name, {column}, source_lang, audio_file_url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name) DO NOTHING;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (name, transcribe, lang, audio_url))


def search_videos(keywords: str) -> list[str]:
    """Search for videos whose name, summary, or transcription contains the keywords."""
    words = [w.strip() for w in keywords.split() if w.strip()]
    if not words:
        return []

    conditions = []
    params = []

    searchable_columns = [
        "name",
        "summary_en",
        "summary_he",
        "summary_ru",
        "transcribe_en",
        "transcribe_he",
        "transcribe_ru",
    ]

    for word in words:
        pattern = f"%{word}%"
        for col in searchable_columns:
            conditions.append(f"{col} ILIKE %s")
            params.append(pattern)

    sql = f"SELECT DISTINCT name FROM videos WHERE {' OR '.join(conditions)} ORDER BY name;"
    logger.debug("Search SQL: %s | params: %s", sql, params)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    results = [row[0] for row in rows]
    logger.info("Search for '%s' found %d videos", keywords, len(results))
    return results


def add_summary(name: str, summary: str, target_lang: str):
    """Update a video's summary in the database."""
    lang = _validate_lang(target_lang)
    column = f"summary_{lang}"
    sql = f"UPDATE videos SET {column} = %s WHERE name = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (summary, name))


def add_transcribe(name: str, transcribe: str, target_lang: str):
    """Update a video's transcription in the database."""
    lang = _validate_lang(target_lang)
    column = f"transcribe_{lang}"
    sql = f"UPDATE videos SET {column} = %s WHERE name = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (transcribe, name))


def get_transcribe(video_name: str, target_lang: str) -> str | None:
    """Get transcription for a video."""
    lang = _validate_lang(target_lang)
    column = f"transcribe_{lang}"
    sql = f"SELECT {column} FROM videos WHERE name = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (video_name,))
            row = cur.fetchone()
    return row[0] if row else None


def get_summary(video_name: str, target_lang: str) -> str | None:
    """Get summary for a video."""
    lang = _validate_lang(target_lang)
    column = f"summary_{lang}"
    sql = f"SELECT {column} FROM videos WHERE name = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (video_name,))
            row = cur.fetchone()
    return row[0] if row else None


def set_source_lang(video_name: str, source: str):
    """Set source language for a video."""
    lang = _validate_lang(source)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE videos SET source_lang = %s WHERE name = %s;", (lang, video_name))


def get_source_lang(video_name: str) -> str | None:
    """Get source language for a video."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT source_lang FROM videos WHERE name = %s;", (video_name,))
            row = cur.fetchone()
    return row[0] if row else None


def get_all_videos() -> list[str]:
    """Get all video names from the database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM videos ORDER BY name;")
            rows = cur.fetchall()
    return [row[0] for row in rows]


def delete_video(video_name: str) -> bool:
    """Delete a video from the database."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM videos WHERE name = %s;", (video_name,))
                deleted_rows = cur.rowcount
        logger.info("Deleted video '%s' from database. Rows affected: %d", video_name, deleted_rows)
        return deleted_rows > 0
    except Exception as e:
        logger.error("Error deleting video '%s': %s", video_name, e)
        return False