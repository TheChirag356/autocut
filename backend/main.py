import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any
import modules.diarization
import aiofiles
import whisper
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "../assets/inputs"
OUTPUT_DIR = BASE_DIR / "../assets/outputs"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="AutoCut - Whisper Transcription API", version="0.1")

MODEL = None


class TranscriptionResult(BaseModel):
    task_id: str
    model: str
    language: str | None
    segments: list
    srt_path: str
    json_path: str

@app.on_event("startup")
def load_model():
    """
    Loads the Whisper model into a global variable once at startup.
    Change model_name to "small", "base", "medium", "large" depending on resources.
    """
    global MODEL
    model_name = os.getenv("WHISPER_MODEL", "small")  # change to "base" or "medium" as needed
    print(f"Loading Whisper model: {model_name} ... (this may take a while)")
    MODEL = whisper.load_model(model_name)
    print("Model loaded.")

def _format_srt(segments: list) -> str:
    """
    Convert Whisper segments into SRT formatted string.
    segments: list of dicts with keys 'start', 'end', 'text'
    """
    def _sec_to_srt_timestamp(s: float) -> str:
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = int(s % 60)
        ms = int((s - int(s)) * 1000)
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"

    lines = []
    for i, seg in enumerate(segments, start=1):
        start = _sec_to_srt_timestamp(seg["start"])
        end = _sec_to_srt_timestamp(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def _save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    """
    Save an UploadFile to destination (async).
    """
    async with aiofiles.open(destination, "wb") as out_file:
        while content := await upload_file.read(1024 * 1024):
            await out_file.write(content)
    await upload_file.close()


def transcribe_file_sync(file_path: str, output_dir: Path):
    """
    Run whisper transcription (synchronous) and write outputs.
    """
    # model is global
    global MODEL
    if MODEL is None:
        raise RuntimeError("Whisper model is not loaded.")

    # use model.transcribe to get segments
    # set word_timestamps True if using a Whisper fork that supports it.
    result = MODEL.transcribe(file_path, fp16=False)  # set fp16=True if supported & GPU available

    # ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # prepare JSON out
    json_path = output_dir / "transcript.json"
    _write_json(json_path, result)

    # segments list is under result["segments"]
    segments = result.get("segments", [])
    segments_simple = [
        {"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()}
        for s in segments
    ]

    srt_content = _format_srt(segments_simple)
    srt_path = output_dir / "transcript.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return {
        "model": result.get("model", None),
        "language": result.get("language", None),
        "segments": segments_simple,
        "srt_path": str(srt_path),
        "json_path": str(json_path),
    }


@app.post("/transcribe", response_model=TranscriptionResult)
async def transcribe(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload an audio/video file and transcribe it using Whisper.
    This endpoint saves the file and performs synchronous transcription in a background thread.
    """
    # Basic file validation
    if file.content_type.split("/")[0] not in {"audio", "video"}:
        raise HTTPException(status_code=400, detail="Only audio/video uploads are supported")

    task_id = uuid.uuid4().hex
    task_input_dir = (INPUT_DIR / task_id)
    task_output_dir = (OUTPUT_DIR / task_id)
    task_input_dir.mkdir(parents=True, exist_ok=True)
    task_output_dir.mkdir(parents=True, exist_ok=True)

    saved_path = task_input_dir / file.filename
    await _save_upload_file(file, saved_path)

    # Run transcription synchronously but launched via background task (so HTTP returns once transcription finishes).
    # NOTE: FastAPI BackgroundTasks run in same process synchronously, so for heavy CPU-bound jobs consider Celery/RQ.
    def _run_and_save():
        try:
            out = transcribe_file_sync(str(saved_path), task_output_dir)
            # augment with task id
            out["task_id"] = task_id
            # store final JSON summary
            _write_json(task_output_dir / "summary.json", out)
        except Exception as e:
            # write error file for debugging
            _write_json(task_output_dir / "error.json", {"error": str(e)})

    # Add to background so response is returned while background runs (note: still same process).
    background_tasks.add_task(_run_and_save)

    # Return immediate response that transcription has started (task id)
    return JSONResponse(
        status_code=202,
        content={
            "task_id": task_id,
            "model": os.getenv("WHISPER_MODEL", "small"),
            "language": None,
            "segments": [],
            "srt_path": "",
            "json_path": "",
        },
    )


@app.get("/transcript/{task_id}", response_model=Dict[str, Any])
def get_transcript(task_id: str):
    """
    Retrieve transcription summary if available.
    """
    out_dir = OUTPUT_DIR / task_id
    summary_path = out_dir / "summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Transcription not ready or task id not found")
    import json
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

if __name__ == "__main__":
    media_path = input("Enter path to your audio/video file: ").strip()

    if not os.path.isfile(media_path):
        print("File not found. Check the path.")
        raise SystemExit

    print(f"[*] Selected: {media_path}")
    transcript = modules.diarization.transcribe_media(media_path)