from typing import Optional, Callable, Awaitable

import whisper
import asyncio
import functools
import numpy as np

TranscriptionCallback = Callable[[str], Awaitable[None]]


class WhisperTranscriber:
    """
    Consumes audio from an asyncio.Queue, buffers it, converts it for Whisper,
    transcribes chunks, and calls a callback with the results.
    """

    def __init__(
        self,
        audio_queue: asyncio.Queue,
        transcription_callback: TranscriptionCallback,
        model_name: str = "base",
        chunk_duration: float = 5.0,  # seconds of audio to accumulate
        id: str = "transcriber",
    ):
        self.audio_queue = audio_queue
        self.transcription_callback = transcription_callback
        self.model_name = model_name
        self.chunk_duration = chunk_duration
        self.id = id

        self.model = None
        self._stop_event = asyncio.Event()
        self._process_task: Optional[asyncio.Task] = None

        # audio buffer (mono 16-bit PCM bytes)
        self._audio_buffer = bytearray()
        self._buffer_sample_rate = None
        self._accumulated_samples = 0

    async def _load_model(self):
        if self.model:
            return
        print(f"[{self.id}] Loading Whisper model '{self.model_name}'...")
        loop = asyncio.get_running_loop()
        try:
            self.model = await loop.run_in_executor(
                None, whisper.load_model, self.model_name
            )
            print(f"[{self.id}] Model '{self.model_name}' loaded.")
        except Exception as e:
            print(f"[{self.id}] ERROR: Failed to load Whisper model: {e}")
            raise

    def _bytes_to_whisper_input(self, audio_data: bytes) -> np.ndarray:
        """
        Convert mono 16-bit PCM bytes to float32 NumPy array normalized for Whisper.
        """
        if not audio_data:
            return np.array([], dtype=np.float32)
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        audio_float = audio_np.astype(np.float32) / 32768.0
        return audio_float

    async def _transcribe_chunk(self, audio_data: bytes, sample_rate: int) -> str:
        if not self.model or not audio_data or sample_rate is None:
            return ""

        duration_sec = len(audio_data) / (
            sample_rate * 2
        )  # 2 bytes per sample for int16
        print(
            f"[{self.id}] Preparing {duration_sec:.2f}s mono audio chunk for transcription..."
        )

        # minimum duration check
        min_duration_for_whisper = 0.1
        if duration_sec < min_duration_for_whisper:
            print(f"[{self.id}] Audio chunk too short ({duration_sec:.2f}s), skipping.")
            return ""

        try:
            audio_np = self._bytes_to_whisper_input(audio_data)

            print(f"[{self.id}] Transcribing audio (shape: {audio_np.shape})...")
            loop = asyncio.get_running_loop()
            transcribe_func = functools.partial(
                self.model.transcribe, audio_np, language="en", fp16=False
            )

            result = await loop.run_in_executor(None, transcribe_func)
            text = result.get("text", "").strip()

            # print(f"[{self.id}] Transcription result: '{text}'")

            return text
        except Exception as e:
            print(f"[{self.id}] Error during transcription execution: {e}")

            return ""

    async def _process_audio_queue(self):
        print(f"[{self.id}] Starting audio processing...")

        while not self._stop_event.is_set():
            try:
                audio_data_bytes, metadata = await asyncio.wait_for(
                    self.audio_queue.get(), timeout=0.5
                )

                if audio_data_bytes is None:
                    print(f"[{self.id}] Received None signal, stopping loop.")
                    break

                sample_rate = metadata.get("sample_rate")
                sample_width = metadata.get("sample_width")
                channels = metadata.get("channels", 1)

                if sample_width != 2:
                    print(
                        f"[{self.id}] Warning: Expected 16-bit audio, got {sample_width*8}-bit. Skipping."
                    )
                    self.audio_queue.task_done()
                    continue

                if self._buffer_sample_rate is None:
                    print(f"[{self.id}] Detected stream sample rate: {sample_rate} Hz")
                    self._buffer_sample_rate = sample_rate
                elif sample_rate != self._buffer_sample_rate:
                    print(
                        f"[{self.id}] Warning: Sample rate mismatch ({sample_rate} vs {self._buffer_sample_rate}). Skipping."
                    )
                    self.audio_queue.task_done()
                    continue

                # convert to mono
                if channels > 1:
                    audio_np_int16 = np.frombuffer(audio_data_bytes, dtype=np.int16)
                    mono_audio_np = (
                        audio_np_int16.reshape(-1, channels)
                        .mean(axis=1)
                        .astype(np.int16)
                    )
                    processed_audio_bytes = mono_audio_np.tobytes()
                    num_samples_added = len(mono_audio_np)
                else:
                    processed_audio_bytes = audio_data_bytes
                    num_samples_added = (
                        len(processed_audio_bytes) // sample_width
                    )  # 2 bytes/sample

                self._audio_buffer.extend(processed_audio_bytes)
                self._accumulated_samples += num_samples_added

                current_duration = self._accumulated_samples / self._buffer_sample_rate

                if current_duration >= self.chunk_duration:
                    print(
                        f"[{self.id}] Buffer reached {current_duration:.2f}s, transcribing..."
                    )
                    combined_audio_bytes = bytes(self._audio_buffer)
                    current_sample_rate = self._buffer_sample_rate

                    self._audio_buffer.clear()
                    self._accumulated_samples = 0

                    text = await self._transcribe_chunk(
                        combined_audio_bytes, current_sample_rate
                    )
                    if text:
                        await self.transcription_callback(text)

                self.audio_queue.task_done()

            except asyncio.TimeoutError:
                if self._stop_event.is_set():
                    break
                continue
            except asyncio.CancelledError:
                print(f"[{self.id}] Processing task cancelled.")
                break
            except Exception as e:
                print(f"[{self.id}] Error in processing loop: {e}")
                try:
                    self.audio_queue.task_done()
                except ValueError:
                    pass
                await asyncio.sleep(0.1)

        if self._audio_buffer and self._buffer_sample_rate:
            print(
                f"[{self.id}] Processing remaining audio buffer ({self._accumulated_samples / self._buffer_sample_rate:.2f}s)..."
            )
            remaining_audio_bytes = bytes(self._audio_buffer)
            self._audio_buffer.clear()
            self._accumulated_samples = 0
            text = await self._transcribe_chunk(
                remaining_audio_bytes, self._buffer_sample_rate
            )
            if text:
                await self.transcription_callback(text)

        print(f"[{self.id}] Audio processing loop stopped.")

    async def start(self):
        if self._process_task and not self._process_task.done():
            print(f"[{self.id}] Transcription service already running or starting.")
            return

        print(f"[{self.id}] Starting transcription service...")
        self._stop_event.clear()
        self._audio_buffer.clear()
        self._accumulated_samples = 0
        self._buffer_sample_rate = None

        await self._load_model()
        if not self.model:
            print(f"[{self.id}] Model could not be loaded. Aborting start.")
            return

        self._process_task = asyncio.create_task(self._process_audio_queue())
        print(f"[{self.id}] Transcription service started.")

    def stop(self):
        if self._stop_event.is_set():
            print(f"[{self.id}] Stop already requested.")
            return
        print(f"[{self.id}] Stop signal received. Signalling processing loop to end...")
        self._stop_event.set()
        self.audio_queue.put_nowait((None, None))

    async def wait_until_done(self):
        if self._process_task:
            print(f"[{self.id}] Waiting for transcription task to finish...")
            try:
                await asyncio.wait_for(
                    self._process_task, timeout=self.chunk_duration + 5.0
                )
                print(f"[{self.id}] Transcription task finished.")
            except asyncio.TimeoutError:
                print(
                    f"[{self.id}] WARNING: Transcription task timed out during shutdown."
                )
                self._process_task.cancel()
                try:
                    await self._process_task
                except asyncio.CancelledError:
                    print(f"[{self.id}] Transcription task cancelled.")
            except Exception as e:
                print(f"[{self.id}] Error waiting for transcription task: {e}")
            finally:
                self._process_task = None
