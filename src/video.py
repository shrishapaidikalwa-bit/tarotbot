"""Builds a voiced reel from (frame_image, narration) pairs using edge-tts + ffmpeg (both free)."""
import asyncio
import json
import os
import subprocess
from pathlib import Path


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-800:]}")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def tts(text, voice, out):
    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, voice, rate="-8%").save(str(out)))
        if os.path.getsize(out) < 1500:
            raise RuntimeError("empty audio")
    except Exception as e:
        print(f"TTS failed ({e}); using silent timing fallback")
        secs = max(4.0, len(text.split()) * 0.42)
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{secs:.2f}",
             "-acodec", "libmp3lame", str(out)])


def build_reel(frames, voice, out_path, workdir, music=None):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, (img, text) in enumerate(frames):
        audio, clip = workdir / f"a{i}.mp3", workdir / f"c{i}.mp4"
        tts(text, voice, audio)
        d = duration(audio) + 0.7
        run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(img), "-i", str(audio),
             "-af", "apad", "-t", f"{d:.2f}", "-c:v", "libx264", "-tune", "stillimage",
             "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-ar", "44100", "-ac", "2",
             "-b:a", "128k", str(clip)])
        clips.append(clip)
    lst = workdir / "list.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joined = workdir / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
         "-movflags", "+faststart", str(joined)])
    if music:
        run(["ffmpeg", "-y", "-i", str(joined), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex", "[1:a]volume=0.10[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest",
             "-movflags", "+faststart", str(out_path)])
    else:
        joined.replace(out_path)
    return out_path
