# speech.py

import logging
import os
import subprocess
from string import punctuation
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NLTK_DATA_DIR = "/usr/local/share/nltk_data"
MODEL_DIR = os.getenv(
    "OPENVINO_WHISPER_DIR",
    "/app/models/whisper-small-ov",
)

_whisper_engine = None
_whisper_device = None


def ensure_nltk_data() -> None:
    if NLTK_DATA_DIR not in nltk.data.path:
        nltk.data.path.insert(0, NLTK_DATA_DIR)

    resources = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
    ]

    for resource_path, package_name in resources:
        try:
            nltk.data.find(resource_path)
        except (LookupError, OSError):
            logger.info("Downloading NLTK resource: %s", package_name)
            nltk.download(
                package_name,
                download_dir=NLTK_DATA_DIR,
                quiet=True,
            )


def init_whisper_engine():
    global _whisper_engine, _whisper_device

    import openvino_genai

    if not os.path.isdir(MODEL_DIR):
        raise FileNotFoundError(
            f"OpenVINO model directory not found: {MODEL_DIR}"
        )

    for device in ("GPU", "CPU"):
        try:
            logger.info("Initializing OpenVINO Whisper on %s", device)

            engine = openvino_genai.WhisperPipeline(
                MODEL_DIR,
                device,
            )

            _whisper_engine = engine
            _whisper_device = device

            logger.info(
                "OpenVINO Whisper initialized successfully on %s",
                device,
            )
            return engine

        except Exception as exc:
            logger.warning(
                "OpenVINO initialization failed on %s: %s",
                device,
                exc,
            )

    raise RuntimeError("Failed to initialize OpenVINO Whisper on GPU or CPU")


def load_audio_16k(audio_path: str) -> list[float]:
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-i", audio_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "pipe:1",
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        check=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.decode(errors="replace")
            or "FFmpeg audio conversion failed"
        )

    import numpy as np

    audio = np.frombuffer(
        proc.stdout,
        dtype=np.float32,
    )

    if audio.size == 0:
        raise ValueError("Audio file contains no audio samples")

    return audio.tolist()


ensure_nltk_data()
init_whisper_engine()


def transcribe_audio(audio_path: str, user_language: str = None):
    audio = load_audio_16k(audio_path)

    language = user_language or "en"

    logger.info(
        "Transcribing audio using OpenVINO on %s, language=%s",
        _whisper_device,
        language,
    )

    result = _whisper_engine.generate(
        audio,
        language=f"<|{language}|>",
        task="transcribe",
    )

    texts = getattr(result, "texts", None)

    if texts is None:
        text = str(result).strip()
    else:
        text = " ".join(
            part.strip()
            for part in texts
            if part and part.strip()
        ).strip()

    return text, language


def summarize_nltk_freq(text: str, num_sentences: int = 3) -> str:
    sentences = sent_tokenize(text)

    if len(sentences) <= num_sentences:
        return text.strip()

    words = word_tokenize(text.lower())
    stop_words = set(stopwords.words("english") + list(punctuation))

    freq: dict[str, float] = {}

    for word in words:
        if word not in stop_words:
            freq[word] = freq.get(word, 0) + 1

    max_freq = max(freq.values(), default=1)

    for word in freq:
        freq[word] /= max_freq

    scores: dict[int, float] = {}

    for idx, sentence in enumerate(sentences):
        for word in word_tokenize(sentence.lower()):
            if word in freq:
                scores[idx] = scores.get(idx, 0.0) + freq[word]

    top_indices = sorted(
        sorted(scores, key=scores.get, reverse=True)[:num_sentences]
    )

    return " ".join(
        sentences[i].strip()
        for i in top_indices
        if sentences[i].strip()
    )


def chunk_sentences(text: str, max_chars: int = 1000) -> list[str]:
    sentences = sent_tokenize(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        potential = (
            f"{current} {sentence}".strip()
            if current
            else sentence
        )

        if len(potential) > max_chars:
            if current:
                chunks.append(current)
            current = sentence
        else:
            current = potential

    if current:
        chunks.append(current)

    return chunks


def translate_google(text: str, src: str, dest: str) -> str:
    from deep_translator import GoogleTranslator

    chunks = chunk_sentences(text, max_chars=1000)
    translated: list[str] = []

    lang_map = {
        "en": "english",
        "he": "hebrew",
        "ru": "russian",
    }

    source_lang = lang_map.get(src, src)
    target_lang = lang_map.get(dest, dest)

    for chunk in chunks:
        try:
            translator = GoogleTranslator(
                source=source_lang,
                target=target_lang,
            )
            result = translator.translate(chunk)
            translated.append(result if result else chunk)

        except Exception as exc:
            logger.error(
                "[translate_google] Error translating chunk: %s",
                exc,
            )
            translated.append(chunk)

    return " ".join(translated)


def translate(transcribe: str, source_lang: str, target_lang: str):
    text = transcribe

    if source_lang != target_lang:
        text = translate_google(
            text,
            src=source_lang,
            dest=target_lang,
        )

    return text


def summarize_audio(
    transcribe: str,
    source_lang: str,
    target_lang: str,
) -> str:
    summary = summarize_nltk_freq(
        transcribe,
        num_sentences=5,
    )

    if source_lang != target_lang:
        summary = translate_google(
            summary,
            src=source_lang,
            dest=target_lang,
        )

    return summary
