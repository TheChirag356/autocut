# backend/modules/manim_ai.py
"""
Manim-AI: Generate caption-based animations from video transcripts.
This module reads a transcript (JSON) and creates synchronized kinetic-text animations
using the Manim library.
"""

import json
from pathlib import Path
from manim import *

# Directory setup
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "../../assets"
ANIMATIONS_DIR = ASSETS_DIR / "animations"
ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)


class CaptionScene(Scene):
    """
    Dynamic Manim scene that creates timed caption animations.
    """

    def __init__(self, captions: list[dict], **kwargs):
        self.captions = captions
        super().__init__(**kwargs)

    def construct(self):
        """
        Create a kinetic-typography-like text animation synchronized to caption timestamps.
        """
        for idx, caption in enumerate(self.captions):
            text = caption["text"]
            duration = max(1.5, caption["end"] - caption["start"])  # minimum 1.5 sec per caption

            # Create text element
            caption_text = Text(
                text,
                font="Inter",
                color=WHITE,
                weight=BOLD,
                t2c={"AI": YELLOW, "Co-Editor": BLUE_B},
            ).scale(0.7)
            caption_text.move_to(DOWN * 2)

            # Animate: fade in, wait, fade out
            self.play(FadeIn(caption_text, shift=UP), run_time=0.5)
            self.wait(duration * 0.6)
            self.play(FadeOut(caption_text, shift=DOWN), run_time=0.4)


def generate_caption_animation(transcript_path: str, output_name: str = "caption_animation.mp4"):
    """
    Given a Whisper/WhisperX transcript JSON, generate a text animation video using Manim.
    """
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract captions (handle both Whisper and WhisperX formats)
    segments = data.get("segments", [])
    captions = [{"text": seg["text"], "start": seg["start"], "end": seg["end"]} for seg in segments]

    # Output directory
    output_path = ANIMATIONS_DIR / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Render scene
    config.video_dir = str(ANIMATIONS_DIR)
    config.media_width = "1920"
    config.media_height = "1080"
    config.background_color = "#000000"
    config.output_file = str(output_path)

    print(f"[Manim-AI] Generating animation → {output_path.name}")
    scene = CaptionScene(captions)
    scene.render()
    print("[Manim-AI] Done.")

    return str(output_path)
