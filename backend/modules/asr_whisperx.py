# backend/modules/asr_whisperx.py
import os
import torch
import whisperx
from pathlib import Path
from typing import Optional, Dict, Any


def transcribe_with_whisperx(
    input_path: str,
    output_dir: Path,
    device: Optional[str] = None,
    batch_size: int = 16,
    compute_type: str = "float16",
    diarize: bool = False,
    hf_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform transcription using WhisperX with optional diarization.
    """

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model_name = os.getenv("WHISPER_MODEL", "small")

    print(f"[WhisperX] Loading model {model_name} on {device}...")
    model = whisperx.load_model(model_name, device=device, compute_type=compute_type)

    # Step 1 — Transcription
    print("[WhisperX] Transcribing...")
    result = model.transcribe(input_path, batch_size=batch_size)
    language = result.get("language", "unknown")

    # Step 2 — Alignment (for word-level timestamps)
    print("[WhisperX] Aligning timestamps...")
    model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
    result_aligned = whisperx.align(
        result["segments"], model_a, metadata, input_path, device, return_char_alignments=False
    )

    # Step 3 — Diarization (optional)
    if diarize:
        if not hf_token:
            raise ValueError("Diarization requires a HuggingFace token (pyannote).")
        print("[WhisperX] Performing diarization...")
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
        diarize_segments = diarize_model(input_path)
        result_aligned = whisperx.assign_word_speakers(diarize_segments, result_aligned)

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    import json
    out_json = output_dir / "transcript_whisperx.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result_aligned, f, ensure_ascii=False, indent=2)

    print("[WhisperX] Transcription complete.")
    return result_aligned
