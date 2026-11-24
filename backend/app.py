# app.py

import logging
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from moviepy import VideoFileClip
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from db import (
    add_new_video,
    add_summary,
    add_transcribe,
    delete_video,
    get_all_videos,
    get_source_lang,
    get_summary,
    get_transcribe,
    init_db,
    search_videos,
)
from speech import (
    ensure_nltk_data,
    summarize_audio,
    transcribe_audio,
    translate,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ensure_nltk_data()

app = Flask(__name__)
CORS(app)

init_db()

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_LANGUAGES = {"en", "he", "ru"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}


def extract_audio_from_video(video_path: str) -> str:
    audio_path = os.path.splitext(video_path)[0] + ".wav"
    with VideoFileClip(video_path) as clip:
        if clip.audio is None:
            raise ValueError("Video file does not contain an audio track")
        clip.audio.write_audiofile(
            audio_path,
            fps=16000,
            nbytes=2,
            codec="pcm_s16le",
            logger=None,
        )
    return audio_path


def convert_to_wav(source_path: str) -> str:
    output_path = os.path.splitext(source_path)[0] + ".wav"
    audio = AudioSegment.from_file(source_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(output_path, format="wav")
    return output_path


@app.route("/")
def index():
    return "Speech-to-Text API is running."


@app.route("/upload", methods=["POST"])
def upload_audio():
    logger.info("Upload request received")

    if "file" not in request.files:
        logger.warning("No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if not file.filename:
        logger.warning("No file selected")
        return jsonify({"error": "No selected file"}), 400

    target_lang = request.form.get("language")
    if target_lang not in ALLOWED_LANGUAGES:
        logger.error("Unsupported language: %s", target_lang)
        return jsonify({"error": "Unsupported language"}), 400

    safe_name = secure_filename(file.filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
    file.save(filepath)
    logger.info("Saved uploaded file to: %s", filepath)

    ext = os.path.splitext(safe_name)[1].lower()
    try:
        if ext in VIDEO_EXTENSIONS:
            filepath = extract_audio_from_video(filepath)
        elif ext != ".wav":
            filepath = convert_to_wav(filepath)
    except Exception as e:
        logger.error("Audio extraction/conversion failed for %s: %s", safe_name, e)
        return jsonify({"error": f"Audio processing failed: {e}"}), 400

    try:
        logger.info("Starting transcription for %s in language %s", safe_name, target_lang)
        transcribed_text, detected_lang = transcribe_audio(filepath, user_language=target_lang)
    except Exception as e:
        logger.error("Transcription failed for %s: %s", safe_name, e)
        return jsonify({"error": f"Transcription failed: {e}"}), 500

    video_name = os.path.splitext(safe_name)[0]
    add_new_video(video_name, transcribed_text, detected_lang, filepath)

    return jsonify({
        "message": "File processed successfully",
        "video_name": video_name,
        "language": target_lang,
        "detected_language": detected_lang,
        "transcribe": transcribed_text,
    }), 200


@app.route("/transcribe", methods=["GET"])
def transcribe_route():
    video = request.args.get("video_name")
    target_lang = request.args.get("language", "he")

    logger.info("Transcribe request for video: %s, language: %s", video, target_lang)

    if not video or target_lang not in ALLOWED_LANGUAGES:
        logger.error("Invalid parameters - video: %s, language: %s", video, target_lang)
        return jsonify({"error": "Missing or invalid parameters"}), 400

    existing = get_transcribe(video, target_lang)
    if existing is not None:
        return jsonify({"result": existing}), 200

    src_lang = get_source_lang(video)
    source_text = get_transcribe(video, src_lang) if src_lang else None
    if not source_text:
        return jsonify({"error": "Video or source transcription not found"}), 404

    logger.info("Transcription not found for %s in %s, translating from %s", video, target_lang, src_lang)
    try:
        translated_text = translate(source_text, src_lang, target_lang)
    except Exception as e:
        logger.error("Translation failed for %s: %s", video, e)
        return jsonify({"error": f"Translation failed: {e}"}), 500

    add_transcribe(video, translated_text, target_lang)
    return jsonify({"result": translated_text}), 200


@app.route("/summarize", methods=["GET"])
def summarize_route():
    video = request.args.get("video_name")
    target_lang = request.args.get("language")

    logger.info("Summarize request for video: %s, language: %s", video, target_lang)

    if not video or target_lang not in ALLOWED_LANGUAGES:
        logger.error("Invalid parameters - video: %s, language: %s", video, target_lang)
        return jsonify({"error": "Missing or invalid parameters"}), 400

    existing_summary = get_summary(video, target_lang)
    if existing_summary is not None:
        return jsonify({"result": existing_summary}), 200

    src_lang = get_source_lang(video)
    source_text = get_transcribe(video, src_lang) if src_lang else None
    if not source_text:
        return jsonify({"error": "Video or source transcription not found"}), 404

    logger.info("Summary not found for %s in %s, generating new summary", video, target_lang)
    try:
        summary = summarize_audio(source_text, src_lang, target_lang)
    except Exception as e:
        logger.error("Summarization failed for %s: %s", video, e)
        return jsonify({"error": f"Summarization failed: {e}"}), 500

    add_summary(video, summary, target_lang)
    return jsonify({"result": summary}), 200


@app.route("/search", methods=["GET"])
def search_route():
    keywords = request.args.get("keywords")
    logger.info("Search request with keywords: %s", keywords)

    if not keywords:
        logger.warning("Search request without keywords")
        return jsonify({"error": "Missing keywords parameter"}), 400

    videos = search_videos(keywords)
    logger.info("Search completed, found %d videos", len(videos))
    return jsonify({"results": videos}), 200


@app.route("/videos", methods=["GET"])
def get_all_videos_route():
    """Get all videos from the database"""
    logger.info("Request for all videos")
    try:
        videos = get_all_videos()
        logger.info("Found %d videos in database", len(videos))
        return jsonify({"videos": videos}), 200
    except Exception as e:
        logger.error("Error getting all videos: %s", e)
        return jsonify({"error": "Failed to retrieve videos"}), 500


@app.route("/delete", methods=["DELETE"])
def delete_video_route():
    """Delete a video from the database"""
    video_name = request.args.get("video_name")
    logger.info("Delete request for video: %s", video_name)

    if not video_name:
        logger.error("Delete request without video_name parameter")
        return jsonify({"error": "Missing video_name parameter"}), 400

    try:
        success = delete_video(video_name)
        if success:
            logger.info("Successfully deleted video: %s", video_name)
            return jsonify({"message": f"Video '{video_name}' deleted successfully"}), 200

        logger.warning("Video not found or could not be deleted: %s", video_name)
        return jsonify({"error": "Video not found or could not be deleted"}), 404
    except Exception as e:
        logger.error("Error deleting video %s: %s", video_name, e)
        return jsonify({"error": "Failed to delete video"}), 500


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)