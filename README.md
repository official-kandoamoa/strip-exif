**AI-assisted development disclosure:** This project was heavily developed with assistance from ChatGPT, Grok, and/or Claude. The author used the free versions of these large language models. AI-generated suggestions were reviewed, adapted, and tested by the author, but the project may still contain errors or limitations.

# Strip EXIF

A simple Python command-line tool for removing metadata from images and videos.

`strip_exif.py` removes embedded metadata such as **EXIF, GPS/location data, ICC profiles, XMP, IPTC, comments, thumbnails, device information, creation timestamps, chapters, and other container/stream metadata**.

For images, the tool creates a fresh file from the raw pixel data. For videos, it uses FFmpeg stream copying, so video/audio is **not re-encoded** and there is no quality loss.

## Features

* Strip metadata from JPG, JPEG, and PNG images
* Strip metadata from MP4, MOV, M4V, MKV, AVI, and WebM videos
* Remove GPS/location and device metadata
* Process an entire directory
* Support `*` and `?` filename patterns
* Write cleaned files to a separate directory
* Add a custom suffix to output filenames
* Overwrite files in place when desired
* Video processing uses stream copy — no re-encoding or quality loss

## Requirements

Python 3 and Pillow are required for all media. FFmpeg and ffprobe must be on `PATH` for video files.

```bash
pip install Pillow
ffmpeg -version
ffprobe -version
```

## Usage

```bash
python3 strip_exif.py input.jpg output.jpg
python3 strip_exif.py input.mp4 output.mp4
python3 strip_exif.py photo.jpg                 # overwrite in place
python3 strip_exif.py photo.jpg --suffix "_clean"
python3 strip_exif.py --dir photos/
python3 strip_exif.py --dir photos/ --outdir cleaned/
python3 strip_exif.py "photos/img_*.jpg" --suffix "_clean"
python3 strip_exif.py "clips/vid_?.mp4" --outdir cleaned/
```

Quote wildcard patterns so your shell does not expand them before the script receives them. `*` matches any number of characters and `?` matches exactly one character; all other characters are literal.

## Supported Formats

Images: `.jpg`, `.jpeg`, `.png`  
Videos: `.mp4`, `.mov`, `.m4v`, `.mkv`, `.avi`, `.webm`

## How It Works

Images are fully loaded and reconstructed from raw pixel data, then saved without EXIF, ICC, XMP, IPTC, comments, thumbnails, or other ancillary metadata. JPEG files are re-encoded at quality 95 and may experience additional compression loss.

Videos are processed with FFmpeg using `-c copy`, so audio and video streams are not re-encoded. Global metadata and chapters are removed, followed by a best-effort pass to clear per-stream metadata.

## Privacy

Removing metadata does not make media completely anonymous. Visible content can still reveal locations, people, documents, screens, or other identifying information.

## License

MIT License. See [LICENSE](LICENSE).
