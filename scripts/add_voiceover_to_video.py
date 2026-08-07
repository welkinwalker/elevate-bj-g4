"""Project Elevate: Automated Voiceover & Video Synthesis Pipeline.

Synthesizes professional voice commentary for the Project Elevate HR & IT Agent
demonstration video, combining standard use cases and edge case handling into
a seamless multi-media walkthrough.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from gtts import gTTS
except ImportError:
    print("Installing gTTS...")
    subprocess.run([sys.executable, "-m", "pip", "install", "gtts"], check=True)
    from gTTS import gTTS


# Structured Commentary Segments for the Elevate Demonstration Video
DEFAULT_COMMENTARY_SEGMENTS: List[Tuple[float, str]] = [
    (
        0.0,
        "Welcome to the demonstration of Project Elevate, an enterprise HR and IT Virtual Assistant "
        "built natively on the Google Cloud AI platform, Google Agent Development Kit, and Model Armor."
    ),
    (
        8.0,
        "First, let's explore standard HR policy inquiries. When an employee inquires about bereavement leave "
        "or remote work expense policies, Elevate uses Vertex AI Search to retrieve strictly grounded answers "
        "complete with verified, clickable Markdown deep-link citations, ensuring zero hallucination."
    ),
    (
        22.0,
        "Next, Elevate connects to WorkWeek HCM via real-time FastMCP toolsets. "
        "The agent queries live vacation and sick leave balances and seamlessly books time off requests "
        "with instant confirmation."
    ),
    (
        35.0,
        "Now, let's observe how Elevate smoothly handles complex edge cases and guardrails. "
        "When an employee attempts to book leave with invalid inverted dates or insufficient balance, "
        "Elevate's transactional validation interceptor rejects the invalid state before making backend mutations."
    ),
    (
        50.0,
        "Next, we test security resilience against adversarial attacks. When faced with direct prompt injection "
        "or jailbreak overrides, Google Cloud Model Armor immediately detects the threat and neutralizes the payload."
    ),
    (
        65.0,
        "Furthermore, any sensitive personal data such as Social Security Numbers and phone numbers "
        "is automatically redacted pre-LLM, preventing privacy leakage."
    ),
    (
        80.0,
        "Finally, Elevate handles multi-system cross-domain orchestration, chaining policy lookup, "
        "WorkWeek profile updates, and ServiceImmediately IT incident management into a single conversational flow."
    ),
    (
        95.0,
        "With 100% CI/CD quality gate pass rate, zero safety breaches, and sub-second latency, "
        "Project Elevate delivers production-grade enterprise agentic AI for Google Cloud customers."
    ),
]


def generate_voiceover_track(
    segments: List[Tuple[float, str]], output_audio_path: Path
) -> Path:
    """Generates audio files for each segment and concatenates them with appropriate timing."""
    temp_dir = output_audio_path.parent / "temp_audio_segments"
    temp_dir.mkdir(parents=True, exist_ok=True)

    segment_files = []
    for i, (timestamp, text) in enumerate(segments):
        seg_file = temp_dir / f"segment_{i:02d}.mp3"
        print(f"[TTS] Generating segment {i + 1}/{len(segments)} (Time: {timestamp}s): {text[:60]}...")
        tts = gTTS(text=text, lang="en", tld="com", slow=False)
        tts.save(str(seg_file))
        segment_files.append((timestamp, seg_file))

    # Build combined audio track using ffmpeg adelay and amix
    print("[FFmpeg] Assembling unified voiceover track...")
    filter_complex = []
    inputs = []
    for i, (ts, path) in enumerate(segment_files):
        inputs.extend(["-i", str(path)])
        delay_ms = int(ts * 1000)
        filter_complex.append(f"[{i}]adelay={delay_ms}|{delay_ms}[a{i}]")

    mix_inputs = "".join(f"[a{i}]" for i in range(len(segment_files)))
    filter_complex.append(f"{mix_inputs}amix=inputs={len(segment_files)}:normalize=0[aout]")

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(filter_complex),
        "-map",
        "[aout]",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(output_audio_path),
    ]

    subprocess.run(cmd, check=True)
    print(f"✅ Voiceover track generated: {output_audio_path}")
    return output_audio_path


def mux_video_and_audio(
    input_video_path: Path, input_audio_path: Path, output_video_path: Path
) -> Path:
    """Combines original video with the new voiceover commentary track."""
    print(f"[FFmpeg] Muxing video ({input_video_path}) with voiceover ({input_audio_path})...")
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video_path),
        "-i",
        str(input_audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        str(output_video_path),
    ]
    subprocess.run(cmd, check=True)
    print(f"🎉 Final narrated video created: {output_video_path}")
    return output_video_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Add voiceover commentary to Project Elevate demo video.")
    parser.add_argument("--video", type=str, default="artifacts/input_video.mp4", help="Path to input video file")
    parser.add_argument("--output", type=str, default="artifacts/elevate_demo_with_voiceover.mp4", help="Path to output video file")
    args = parser.parse_args()

    video_file = Path(args.video).resolve()
    output_file = Path(args.output).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    audio_file = output_file.parent / "elevate_voiceover_track.mp3"
    generate_voiceover_track(DEFAULT_COMMENTARY_SEGMENTS, audio_file)

    if video_file.exists():
        mux_video_and_audio(video_file, audio_file, output_file)
    else:
        print(f"\nℹ️  Input video '{video_file}' not found locally.")
        print(f"   Please place your video at '{video_file}' and run:")
        print(f"   ./.venv/bin/python scripts/add_voiceover_to_video.py --video {video_file} --output {output_file}")


if __name__ == "__main__":
    main()
