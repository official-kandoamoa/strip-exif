#!/usr/bin/env python3
"""
strip_exif.py — Remove ALL metadata from images AND videos.

For JPG/PNG, this re-encodes just the raw pixel data into a brand new file
(EXIF, ICC profiles, XMP, IPTC, comments, thumbnails all dropped). This
avoids the common mistake of merely deleting the EXIF tag, which can leave
leftover bytes/segments in the file.

For video files (mp4, mov, mkv, avi, webm, m4v), this uses ffmpeg to strip
all container/stream metadata (creation time, GPS location, device/encoder
tags, chapters, etc.) via a fast stream copy — no re-encoding, no quality
loss. Requires ffmpeg to be installed and on PATH.

Usage:
    python3 strip_exif.py input.jpg [output.jpg]
    python3 strip_exif.py input.mp4 [output.mp4]
    python3 strip_exif.py --dir /path/to/folder   # process every supported file in a folder (in place, unless --outdir given)
    python3 strip_exif.py "photos/img_*.jpg"      # wildcard pattern (quote it so the shell doesn't expand it)
    python3 strip_exif.py "clips/vid_?.mp4"       # '?' matches exactly one character

Wildcard support (only these two characters are special):
    *   matches any number of characters (including none)
    ?   matches exactly one character
    All other characters are matched literally. Quote the pattern in your
    shell so strip_exif.py (not the shell) does the matching.

Supported formats:
    Images: .jpg, .jpeg, .png
    Videos: .mp4, .mov, .m4v, .mkv, .avi, .webm

Options:
    --dir DIR         Process all supported image/video files in DIR
    --outdir DIR      Where to write cleaned files (default: overwrite in place)
    --suffix SUFFIX   Suffix to add before extension for output files (e.g. "_clean")
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
SUPPORTED_EXTS = IMAGE_EXTS | VIDEO_EXTS


def pattern_to_regex(pattern: str) -> re.Pattern:
    """Convert a pattern using only '*' and '?' into a compiled regex."""
    regex_chars = []
    for ch in pattern:
        if ch == "*":
            regex_chars.append(".*")
        elif ch == "?":
            regex_chars.append(".")
        else:
            regex_chars.append(re.escape(ch))
    return re.compile("^" + "".join(regex_chars) + "$")


def is_pattern(s: str) -> bool:
    return "*" in s or "?" in s


def gather_by_pattern(pattern_str: str):
    """Resolve a path containing '*'/'?' against existing files."""
    p = Path(pattern_str)
    directory = p.parent if str(p.parent) != "" else Path(".")
    if not directory.is_dir():
        sys.exit(f"Not a directory: {directory}")

    regex = pattern_to_regex(p.name)
    return sorted(f for f in directory.iterdir() if f.is_file() and regex.match(f.name))


def strip_video_metadata(input_path: Path, output_path: Path) -> None:
    """Strip video metadata using ffmpeg stream copying."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to strip metadata from video files but was not found on PATH.")

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path), "-map", "0",
        "-map_metadata", "-1", "-map_chapters", "-1",
        "-fflags", "+bitexact", "-flags:v", "+bitexact",
        "-flags:a", "+bitexact", "-c", "copy", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {input_path}:\n{result.stderr}")

    _strip_stream_metadata(output_path)


def _strip_stream_metadata(path: Path) -> None:
    """Best-effort second pass clearing metadata on every stream."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        return
    stream_indices = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
    if not stream_indices:
        return

    tmp_path = path.with_name(path.stem + ".mdtmp" + path.suffix)
    cmd = ["ffmpeg", "-y", "-i", str(path), "-map", "0", "-map_metadata", "-1"]
    for idx in stream_indices:
        cmd += [f"-metadata:s:{idx}", ""]
    cmd += ["-c", "copy", str(tmp_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and tmp_path.exists():
        os.replace(tmp_path, path)
    elif tmp_path.exists():
        tmp_path.unlink()


def strip_metadata(input_path: Path, output_path: Path) -> None:
    """Strip metadata from an image or video based on its extension."""
    ext = input_path.suffix.lower()
    if ext in VIDEO_EXTS:
        strip_video_metadata(input_path, output_path)
        return

    with Image.open(input_path) as img:
        img.load()
        mode, size = img.mode, img.size
        clean_img = Image.frombytes(mode, size, img.tobytes())
        src_ext = input_path.suffix.lower()
        if src_ext in (".jpg", ".jpeg"):
            save_kwargs = dict(format="JPEG", quality=95, optimize=True)
        elif src_ext == ".png":
            save_kwargs = dict(format="PNG", optimize=True)
        else:
            raise ValueError(f"Unsupported extension: {src_ext}")
        clean_img.save(output_path, **save_kwargs)


def process_file(input_path: Path, output_path: Path) -> None:
    strip_metadata(input_path, output_path)
    print(f"[OK] {input_path} -> {output_path}")


def make_tmp_path(p: Path) -> Path:
    """Build a temporary path that keeps the real file extension."""
    return p.with_name(p.stem + ".tmp" + p.suffix)


def gather_files(directory: Path):
    return [p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTS and p.is_file()]


def main():
    parser = argparse.ArgumentParser(description="Strip all metadata from JPG/PNG images and video files.")
    parser.add_argument("input", nargs="?", help="Input image or video file")
    parser.add_argument("output", nargs="?", help="Output file (optional)")
    parser.add_argument("--dir", help="Process all supported image/video files in this directory")
    parser.add_argument("--outdir", help="Directory to write cleaned files to")
    parser.add_argument("--suffix", default="", help="Suffix to insert before extension for outputs")
    args = parser.parse_args()

    if args.dir:
        directory = Path(args.dir)
        if not directory.is_dir():
            sys.exit(f"Not a directory: {directory}")
        outdir = Path(args.outdir) if args.outdir else directory
        outdir.mkdir(parents=True, exist_ok=True)
        files = gather_files(directory)
        if not files:
            print("No supported image/video files found.")
            return
        for input_path in files:
            out_path = outdir / (input_path.stem + args.suffix + input_path.suffix)
            process_file(input_path, out_path)

    elif args.input and is_pattern(args.input):
        if args.output:
            sys.exit("Cannot specify an explicit output file when using a wildcard pattern (* or ?).")
        matches = gather_by_pattern(args.input)
        if not matches:
            print(f"No files matched pattern: {args.input}")
            return
        outdir = Path(args.outdir) if args.outdir else None
        if outdir:
            outdir.mkdir(parents=True, exist_ok=True)
        for input_path in matches:
            if outdir:
                out_path = outdir / (input_path.stem + args.suffix + input_path.suffix)
                process_file(input_path, out_path)
            elif args.suffix:
                out_path = input_path.with_name(input_path.stem + args.suffix + input_path.suffix)
                process_file(input_path, out_path)
            else:
                tmp_path = make_tmp_path(input_path)
                process_file(input_path, tmp_path)
                os.replace(tmp_path, input_path)
                print(f"[OK] Overwrote in place: {input_path}")

    elif args.input:
        input_path = Path(args.input)
        if not input_path.is_file():
            sys.exit(f"File not found: {input_path}")
        if args.output:
            output_path = Path(args.output)
        elif args.suffix:
            output_path = input_path.with_name(input_path.stem + args.suffix + input_path.suffix)
        else:
            output_path = input_path
        if output_path == input_path:
            tmp_path = make_tmp_path(input_path)
            process_file(input_path, tmp_path)
            os.replace(tmp_path, input_path)
            print(f"[OK] Overwrote in place: {input_path}")
        else:
            process_file(input_path, output_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
