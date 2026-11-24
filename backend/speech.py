# speech.py

import logging
import os
import subprocess
from string import punctuation
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NLTK_DATA_DIR = "/usr/local/share/nltk_data"

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
            nltk.download(package_name, download_dir=NLTK_DATA_DIR, quiet=True)


def has_intel_gpu() -> bool:
    if os.name == "nt":
        try:
            output = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            if "intel" in output.lower():
                return True
        except Exception:
            pass

    try:
        import openvino as ov

        core = ov.Core()
        return any("GPU" in device.upper() for device in core.available_devices)
    except Exception:
        return False


def has_cuda() -> bool:
    try:
        import ctranslate2

        if ctranslate2.get_supported_compute_types("cuda"):
            return True
    except Exception:
        pass

    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def try_init_openvino(openvino_dir: str | None):
    if not (openvino_dir and os.path.isdir(openvino_dir) and has_intel_gpu()):
        return None
    try:
        import openvino_genai as ov_genai

        logger.info("Using Intel GPU via OpenVINO GenAI: %s", openvino_dir)
        pipe = ov_genai.WhisperPipeline(openvino_dir, device="GPU")
        return ("openvino", pipe)
    except Exception as exc:
        logger.warning("OpenVINO GPU init failed (%s).", exc)
        return None


def try_init_cuda(model_size: str):
    if not has_cuda():
        return None
    try:
        compute_type = os.getenv("WHISPER_CUDA_COMPUTE_TYPE", "float16")
        logger.info("Using NVIDIA CUDA with faster-whisper (model=%s, compute_type=%s)", model_size, compute_type)
        cuda_model = WhisperModel(model_size, device="cuda", compute_type=compute_type)
        return ("faster-whisper", cuda_model)
    except Exception as exc:
        logger.warning("CUDA init failed (%s).", exc)
        return None


def init_cpu(model_size: str):
    cpu_threads = min(os.cpu_count() or 4, 8)
    logger.info(
        "Using faster-whisper on CPU (model=%s, compute_type=int8, threads=%d)",
        model_size,
        cpu_threads,
    )
    cpu_model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        cpu_threads=cpu_threads,
        num_workers=1,
    )
    return ("faster-whisper", cpu_model)


def init_whisper_engine(
    default_model_size: str = "medium",
    default_openvino_dir: str | None = None,
):
    openvino_dir = os.getenv("OPENVINO_WHISPER_DIR", default_openvino_dir)
    model_size = os.getenv("WHISPER_MODEL_SIZE") or os.getenv("WHISPER_CPU_MODEL") or default_model_size
    preference = os.getenv("WHISPER_DEVICE_PREFERENCE", "auto").strip().lower()

    if preference == "cpu":
        return init_cpu(model_size)

    if preference == "cuda":
        engine = try_init_cuda(model_size)
        if engine:
            return engine
        logger.warning("Requested CUDA, falling back to CPU.")
        return init_cpu(model_size)

    if preference == "intel":
        engine = try_init_openvino(openvino_dir)
        if engine:
            return engine
        logger.warning("Requested Intel GPU, falling back to CPU.")
        return init_cpu(model_size)

    # מצב auto: מנסה Intel GPU אם מוגדר מודל OpenVINO, אחרת CUDA אם זמין, ואז CPU
    engine = try_init_openvino(openvino_dir)
    if engine:
        return engine

    engine = try_init_cuda(model_size)
    if engine:
        return engine

    return init_cpu(model_size)


ensure_nltk_data()
_whisper_backend, _whisper_engine = init_whisper_engine(default_model_size="medium")


def summarize_nltk_freq(text: str, num_sentences: int = 3) -> str:
    sentences = sent_tokenize(text)
    if len(sentences) <= num_sentences:
        return text.strip()

    words = word_tokenize(text.lower())
    stop_words = set(stopwords.words("english") + list(punctuation))

    freq: dict[str, float] = {}
    for w in words:
        if w not in stop_words:
            freq[w] = freq.get(w, 0) + 1

    max_freq = max(freq.values(), default=1)
    for w in freq:
        freq[w] /= max_freq

    scores: dict[int, float] = {}
    for idx, sent in enumerate(sentences):
        for w in word_tokenize(sent.lower()):
            if w in freq:
                scores[idx] = scores.get(idx, 0.0) + freq[w]

    top_indices = sorted(
        sorted(scores, key=scores.get, reverse=True)[:num_sentences]
    )
    return " ".join(sentences[i].strip() for i in top_indices if sentences[i].strip())


def chunk_sentences(text: str, max_chars: int = 1000) -> list[str]:
    sentences = sent_tokenize(text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        potential = f"{current} {sentence}".strip() if current else sentence
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
    chunks = chunk_sentences(text, max_chars=1000)
    translated: list[str] = []

    lang_map = {"en": "english", "he": "hebrew", "ru": "russian"}
    source_lang = lang_map.get(src, src)
    target_lang = lang_map.get(dest, dest)

    for chunk in chunks:
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(chunk)
            translated.append(result if result else chunk)
        except Exception as e:
            logger.error(f"[translate_google] Error translating chunk: {e}")
            translated.append(chunk)

    return " ".join(translated)


def transcribe_audio(audio_path: str, user_language: str = None):
    if _whisper_backend == "openvino":
        if user_language:
            result = _whisper_engine.generate(audio_path, language=f"<|{user_language}|>")
        else:
            result = _whisper_engine.generate(audio_path)
        text = str(result).strip()
        src = user_language if user_language in ["he", "ru", "en"] else "en"
        return text, src

    segments, info = _whisper_engine.transcribe(
        audio_path,
        beam_size=5,
        language=user_language,
        vad_filter=True,
    )
    text = " ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
    detected_lang = getattr(info, "language", None)
    src = (
        user_language
        if user_language
        else (detected_lang if detected_lang in ["he", "ru", "en"] else "en")
    )
    return text, src


def translate(transcribe: str, source_lang: str, target_lang: str):
    text = transcribe
    if source_lang != target_lang:
        text = translate_google(text, src=source_lang, dest=target_lang)
    return text


def summarize_audio(transcribe: str, source_lang: str, target_lang: str) -> str:
    summary = summarize_nltk_freq(transcribe, num_sentences=5)
    if source_lang != target_lang:
        summary = translate_google(summary, src=source_lang, dest=target_lang)
    return summary