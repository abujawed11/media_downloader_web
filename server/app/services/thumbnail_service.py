"""Thumbnail generation service using FFmpeg."""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)


class ThumbnailService:
    """Generate video thumbnails using FFmpeg CLI."""

    @staticmethod
    async def generate_thumbnail(video_path: str, timestamp: float = 3.0) -> str:
        """
        Extract a single frame from the video at `timestamp` seconds.
        Returns the path to the generated JPEG thumbnail.
        Falls back to an earlier timestamp if the video is shorter.
        """
        output_path = video_path.rsplit(".", 1)[0] + "_thumb.jpg"

        try:
            # Probe duration first so we don't seek past end
            duration = ThumbnailService._get_duration(video_path)
            if duration and timestamp >= duration:
                timestamp = max(0, duration * 0.1)

            cmd = [
                "ffmpeg",
                "-y",               # overwrite output
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-vf", "scale=1280:-1",
                "-q:v", "2",        # quality (2 = high JPEG quality)
                output_path,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
            )

            if result.returncode == 0 and os.path.exists(output_path):
                return output_path

            # If ffmpeg failed, log stderr and raise
            logger.warning("ffmpeg thumbnail failed: %s", result.stderr.decode(errors="ignore"))
            raise RuntimeError(f"ffmpeg exited with code {result.returncode}")

        except FileNotFoundError:
            # ffmpeg not installed – return empty string so caller can fall back
            logger.warning("ffmpeg not found – skipping thumbnail generation")
            return ""
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg timed out generating thumbnail for %s", video_path)
            return ""
        except Exception as exc:
            logger.warning("Thumbnail generation failed: %s", exc)
            return ""

    @staticmethod
    def _get_duration(video_path: str) -> float:
        """Return video duration in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0:
                return float(result.stdout.decode().strip())
        except Exception:
            pass
        return 0.0
