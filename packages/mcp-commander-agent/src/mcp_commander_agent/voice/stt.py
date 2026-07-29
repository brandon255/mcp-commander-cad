"""Speech-to-text using faster-whisper with VAD and microphone recording."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of a speech-to-text transcription."""
    text: str
    confidence: float
    language: str
    segments: list[dict[str, Any]]


class VoiceActivityDetector:
    """Simple energy-based voice activity detection."""

    def __init__(self, threshold: float = 0.5, silence_timeout: float = 2.0,
                 sample_rate: int = 16000, frame_size: int = 512):
        self.threshold = threshold
        self.silence_timeout = silence_timeout
        self.sample_rate = sample_rate
        self.frame_size = frame_size

    def _compute_energy(self, frame: np.ndarray) -> float:
        """Compute RMS energy of an audio frame."""
        rms = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
        return float(rms)

    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech based on energy threshold."""
        if len(audio) == 0:
            return False
        energy = self._compute_energy(audio)
        return energy > self.threshold


class SpeechToText:
    """Speech-to-text engine using faster-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        language: str = "en",
        device: str = "auto",
        compute_type: str = "int8",
        vad_threshold: float = 0.5,
        silence_timeout: float = 2.0,
        sample_rate: int = 16000,
        max_record_seconds: float = 30.0,
    ) -> None:
        self.model_size = model_size
        self.language = language
        self.sample_rate = sample_rate
        self.max_record_seconds = max_record_seconds
        self.vad = VoiceActivityDetector(
            threshold=vad_threshold,
            silence_timeout=silence_timeout,
            sample_rate=sample_rate,
        )

        resolved_device = self._resolve_device(device)
        self.model = self._load_model(resolved_device, compute_type)
        logger.info(
            "STT model '%s' loaded on %s (compute_type=%s)",
            model_size, resolved_device, compute_type,
        )

    @staticmethod
    def _resolve_device(device: str) -> str:
        """Resolve 'auto' to 'cuda' or 'cpu'."""
        if device != "auto":
            return device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            logger.warning("torch not installed -- falling back to CPU")
            return "cpu"

    def _load_model(self, device: str, compute_type: str) -> Any:
        """Load the faster-whisper model."""
        from faster_whisper import WhisperModel
        return WhisperModel(self.model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_data: np.ndarray) -> TranscriptionResult:
        """Transcribe raw audio data (float32 mono at sample_rate)."""
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Ensure mono
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]

        lang = self.language if self.language != "auto" else None

        segments_iter, info = self.model.transcribe(
            audio_data,
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
            ),
        )

        segments_list: list[dict[str, Any]] = []
        texts: list[str] = []
        confidences: list[float] = []

        for seg in segments_iter:
            seg_dict = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "avg_logprob": seg.avg_logprob,
                "no_speech_prob": seg.no_speech_prob,
            }
            segments_list.append(seg_dict)
            texts.append(seg_dict["text"])
            confidence = max(0.0, min(1.0, 1.0 + seg.avg_logprob))
            confidences.append(confidence)

        full_text = " ".join(texts).strip()
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0

        logger.debug("STT result: '%s' (confidence=%.2f)", full_text, avg_confidence)

        return TranscriptionResult(
            text=full_text,
            confidence=avg_confidence,
            language=info.language if info else self.language,
            segments=segments_list,
        )

    def transcribe_file(self, filepath: str) -> TranscriptionResult:
        """Transcribe from an audio file."""
        audio, sr = self._load_audio_file(filepath)
        if sr != self.sample_rate:
            import torch
            from torchaudio import functional as F
            audio = F.resample(
                torch.tensor(audio), sr, self.sample_rate
            ).numpy()
        return self.transcribe(audio)

    def _load_audio_file(self, filepath: str) -> tuple[np.ndarray, int]:
        """Load an audio file, returning (samples, sample_rate)."""
        try:
            import soundfile as sf
            data, sr = sf.read(filepath, dtype="float32")
            return data, sr
        except ImportError:
            pass

        try:
            from scipy.io import wavfile
            sr, data = wavfile.read(filepath)
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            return data, sr
        except ImportError:
            raise RuntimeError(
                "Cannot read audio file. Install soundfile or scipy: "
                "pip install soundfile"
            )

    def listen(self, duration: float | None = None) -> np.ndarray:
        """Record from microphone and return audio data.

        If *duration* is given, records for exactly that many seconds.
        Otherwise, uses VAD to detect speech end (silence after speech).
        """
        if duration is not None:
            return self._record_fixed(duration)
        return self._record_vad()

    def _record_fixed(self, duration: float) -> np.ndarray:
        """Record for a fixed duration."""
        logger.info("Recording for %.1f seconds...", duration)
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        logger.info("Recording complete (%d samples).", len(audio))
        return audio.flatten()

    def _record_vad(self) -> np.ndarray:
        """Record using VAD -- wait for speech, then record until silence."""
        logger.info("Listening for speech (press Ctrl+C to stop)...")

        frame_samples = self.vad.frame_size
        max_samples = int(self.max_record_seconds * self.sample_rate)
        silence_frames_needed = int(self.vad.silence_timeout * self.sample_rate / frame_samples)

        all_audio: list[np.ndarray] = []
        speech_started = False
        silence_count = 0
        total_samples = 0

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=frame_samples,
        )

        try:
            with stream:
                while total_samples < max_samples:
                    frame, _ = stream.read(frame_samples)
                    frame_flat = frame.flatten()

                    if not speech_started:
                        if self.vad.is_speech(frame_flat):
                            speech_started = True
                            all_audio.append(frame_flat)
                            silence_count = 0
                            total_samples += len(frame_flat)
                            logger.debug("Speech detected -- recording...")
                    else:
                        all_audio.append(frame_flat)
                        total_samples += len(frame_flat)

                        if self.vad.is_speech(frame_flat):
                            silence_count = 0
                        else:
                            silence_count += 1

                        if silence_count >= silence_frames_needed:
                            logger.debug(
                                "Silence detected after %d frames -- stopping.",
                                silence_count,
                            )
                            break
        except Exception as exc:
            logger.error("Microphone recording error: %s", exc)
            raise

        if not all_audio:
            logger.warning("No speech detected.")
            return np.array([], dtype=np.float32)

        audio = np.concatenate(all_audio)
        logger.info(
            "Recorded %.2f seconds of audio.", len(audio) / self.sample_rate
        )
        return audio
