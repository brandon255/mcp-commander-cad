"""Text-to-speech with pluggable backends: pyttsx3 (offline), OpenAI, Edge TTS."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Interface that every TTS backend must implement."""

    @abstractmethod
    def speak(self, text: str) -> None:
        ...

    @abstractmethod
    def speak_to_file(self, text: str, filepath: str | Path) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    def cleanup(self) -> None:
        pass


class Pyttsx3Engine(TTSEngine):
    def __init__(self, voice: str = "default", rate: int = 175, volume: float = 1.0) -> None:
        self._rate = rate
        self._volume = volume
        self._voice_id = voice
        import pyttsx3
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", self._rate)
        self._engine.setProperty("volume", self._volume)
        voices = self._engine.getProperty("voices")
        if self._voice_id != "default":
            for v in voices:
                if self._voice_id.lower() in v.id.lower():
                    self._engine.setProperty("voice", v.id)
                    break
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()

    def speak_to_file(self, text: str, filepath: str | Path) -> None:
        with self._lock:
            self._engine.save_to_file(text, str(filepath))
            self._engine.runAndWait()

    def stop(self) -> None:
        with self._lock:
            self._engine.stop()


class OpenAITTSEngine(TTSEngine):
    def __init__(self, voice: str = "alloy", model: str = "tts-1",
                 api_key_env: str = "OPENAI_API_KEY", base_url: str | None = None) -> None:
        import os
        from openai import OpenAI
        self._voice = voice
        self._model = model
        self._client = OpenAI(api_key=os.environ.get(api_key_env, ""), base_url=base_url)
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        import tempfile
        data = self._synthesize_to_bytes(text)
        tmp = Path(tempfile.mktemp(suffix=".mp3"))
        tmp.write_bytes(data)
        try:
            self._play_file(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    def speak_to_file(self, text: str, filepath: str | Path) -> None:
        data = self._synthesize_to_bytes(text)
        Path(filepath).write_bytes(data)

    def _synthesize_to_bytes(self, text: str) -> bytes:
        response = self._client.audio.speech.create(
            model=self._model, voice=self._voice, input=text, response_format="mp3",
        )
        return response.content

    def _play_file(self, filepath: Path) -> None:
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(str(filepath))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.quit()
        except Exception:
            import subprocess, sys
            if sys.platform == "win32":
                subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["afplay", str(filepath)], check=False)
            else:
                subprocess.run(["mpg123", str(filepath)], check=False)

    def stop(self) -> None:
        try:
            import pygame
            pygame.mixer.music.stop()
        except Exception:
            pass


class EdgeTTSEngine(TTSEngine):
    def __init__(self, voice: str = "en-US-AriaNeural") -> None:
        self._voice = voice
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".mp3"))
        try:
            self.speak_to_file(text, tmp)
            self._play(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    def speak_to_file(self, text: str, filepath: str | Path) -> None:
        import asyncio, edge_tts
        loop = asyncio.new_event_loop()
        try:
            communicate = edge_tts.Communicate(text, self._voice)
            loop.run_until_complete(communicate.save(str(filepath)))
        finally:
            loop.close()

    def _play(self, filepath: Path) -> None:
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(str(filepath))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.quit()
        except Exception:
            import subprocess, sys
            if sys.platform == "win32":
                subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["afplay", str(filepath)], check=False)
            else:
                subprocess.run(["mpg123", str(filepath)], check=False)

    def stop(self) -> None:
        try:
            import pygame
            pygame.mixer.music.stop()
        except Exception:
            pass


def create_tts_engine(backend: str = "pyttsx3", voice: str = "default", **kwargs: Any) -> TTSEngine:
    if backend == "pyttsx3":
        return Pyttsx3Engine(voice=voice, **kwargs)
    if backend == "openai":
        return OpenAITTSEngine(voice=voice if voice != "default" else "alloy", **kwargs)
    if backend == "edge":
        return EdgeTTSEngine(voice=voice if voice != "default" else "en-US-AriaNeural", **kwargs)
    raise ValueError(f"Unknown TTS backend: {backend!r}. Use pyttsx3, openai, or edge.")


class TextToSpeech:
    def __init__(self, backend: str = "pyttsx3", voice: str = "default", **kwargs: Any) -> None:
        self._engine = create_tts_engine(backend, voice, **kwargs)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def speak(self, text: str) -> None:
        self._stop_event.clear()
        self._engine.speak(text)

    def speak_async(self, text: str) -> None:
        self.stop()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._engine.stop()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

    def speak_to_file(self, text: str, filepath: str | Path) -> None:
        self._engine.speak_to_file(text, filepath)

    def cleanup(self) -> None:
        self.stop()
        self._engine.cleanup()
