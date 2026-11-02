"""Conservative audio-level silence detection using FFmpeg."""

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Audio whose peak level is at or below this threshold is treated
# as near-silent. Validate this threshold against real recordings.
SILENCE_THRESHOLD_DBFS = -55.0


class AudioSilenceDetectionService:
    """Detect near-silent audio using FFmpeg volume analysis."""

    def __init__(
        self,
        threshold_dbfs: float = SILENCE_THRESHOLD_DBFS,
    ) -> None:
        self.threshold_dbfs = threshold_dbfs

    def is_silent(self, audio_path: str | Path) -> bool | None:
        """
        Return True for near-silent audio, False for audible audio,
        or None when analysis cannot be completed reliably.
        """
        command = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i", str(audio_path),
            "-af", "volumedetect",
            "-f", "null",
            "-",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.warning(
                "FFmpeg silence analysis unavailable for %s.",
                audio_path,
            )
            return None

        output = result.stderr or ""

        if result.returncode != 0:
            logger.warning(
                "FFmpeg could not analyze audio file %s.",
                audio_path,
            )
            return None

        match = re.search(
            r"max_volume:\s*(-?inf|-?\d+(?:\.\d+)?)\s*dB",
            output,
            re.IGNORECASE,
        )

        if not match:
            logger.warning(
                "FFmpeg returned no usable peak-volume measurement."
            )
            return None

        peak = match.group(1).lower()

        if peak == "-inf":
            return True

        return float(peak) <= self.threshold_dbfs