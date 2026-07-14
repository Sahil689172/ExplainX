"""IndicTrans2 offline EN→Indic translation (lazy singleton, transformers only)."""

from __future__ import annotations

import re
import threading
from typing import Any

from app.core.errors import ExplainXError

# FLORES / IndicTrans2 language codes
SRC_LANG = "eng_Latn"
TGT_LANG_BY_CODE = {
    "hi": "hin_Deva",
    "te": "tel_Telu",
}

DEFAULT_MODEL_ID = "ai4bharat/indictrans2-en-indic-dist-200M"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")
_LANG_TAG = re.compile(r"^[a-z]{3}_[A-Za-z]+\s+")

_lock = threading.Lock()
_model: Any = None
_tokenizer: Any = None
_device: str | None = None
_loaded_model_id: str | None = None


class TranslationFailedError(ExplainXError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="TRANSLATION_FAILED",
            status_code=500,
            details=details,
            retriable=False,
        )


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]
    return parts or [text.strip()]


def _preprocess_batch(
    sentences: list[str], *, src_lang: str, tgt_lang: str
) -> list[str]:
    """Format sentences the way IndicTrans2 HF tokenizers expect (no toolkit)."""
    return [f"{src_lang} {tgt_lang} {s.strip()}" for s in sentences if s.strip()]


def _postprocess_batch(decoded: list[str]) -> list[str]:
    """Light cleanup of decoded model outputs."""
    cleaned: list[str] = []
    for text in decoded:
        t = (text or "").strip()
        # Drop leading FLORES tags if the decoder echoed them.
        while _LANG_TAG.match(t):
            t = _LANG_TAG.sub("", t, count=1).strip()
        cleaned.append(t)
    return cleaned


def _ensure_loaded(model_id: str) -> None:
    """Load tokenizer + model once per process via transformers only."""
    global _model, _tokenizer, _device, _loaded_model_id

    if _model is not None and _loaded_model_id == model_id:
        return

    with _lock:
        if _model is not None and _loaded_model_id == model_id:
            return
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise TranslationFailedError(
                "Translation dependencies missing. Install torch, transformers, "
                "and sentencepiece (pip install -e \".[translation]\").",
                details={"missing": str(exc)},
            ) from exc

        device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            load_kwargs: dict[str, Any] = {"trust_remote_code": True}
            if device == "cuda":
                load_kwargs["torch_dtype"] = torch.float16
            model = AutoModelForSeq2SeqLM.from_pretrained(model_id, **load_kwargs)
            model = model.to(device)
            model.eval()
        except Exception as exc:  # noqa: BLE001
            raise TranslationFailedError(
                f"Failed to load IndicTrans2 model {model_id!r}.",
                details={"error": str(exc), "model_id": model_id},
            ) from exc

        _tokenizer = tokenizer
        _model = model
        _device = device
        _loaded_model_id = model_id


def translate_english_to(
    text: str,
    *,
    target_lang: str,
    model_id: str = DEFAULT_MODEL_ID,
    batch_size: int = 4,
) -> str:
    """Translate English text to Hindi (hi) or Telugu (te)."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise TranslationFailedError(
            "Cannot translate empty text.",
            details={"field": "text"},
        )

    code = (target_lang or "").strip().lower()[:2]
    tgt = TGT_LANG_BY_CODE.get(code)
    if tgt is None:
        raise TranslationFailedError(
            f"Unsupported translation target: {target_lang!r}. Use hi or te.",
            details={"target_lang": target_lang, "supported": list(TGT_LANG_BY_CODE)},
        )

    _ensure_loaded(model_id)
    assert _model is not None and _tokenizer is not None and _device is not None

    import torch

    sentences = _split_sentences(cleaned)
    translations: list[str] = []

    try:
        for i in range(0, len(sentences), batch_size):
            chunk = sentences[i : i + batch_size]
            batch = _preprocess_batch(chunk, src_lang=SRC_LANG, tgt_lang=tgt)
            inputs = _tokenizer(
                batch,
                truncation=True,
                padding="longest",
                max_length=256,
                return_tensors="pt",
                return_attention_mask=True,
            ).to(_device)

            with torch.inference_mode():
                generated = _model.generate(
                    **inputs,
                    use_cache=True,
                    min_length=0,
                    max_length=256,
                    num_beams=5,
                    num_return_sequences=1,
                )

            decoded = _tokenizer.batch_decode(
                generated,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )
            translations.extend(_postprocess_batch(decoded))
    except ExplainXError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TranslationFailedError(
            "IndicTrans2 translation failed.",
            details={"error": str(exc), "target_lang": code},
        ) from exc

    return " ".join(t.strip() for t in translations if t and t.strip()).strip()
