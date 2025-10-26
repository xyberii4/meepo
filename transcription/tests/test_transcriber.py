import pytest
import asyncio
from pathlib import Path
import soundfile as sf
import numpy as np
from unittest.mock import AsyncMock

from transcription.transcriber import WhisperTranscriber, TranscriptionCallback

TEST_WAV_FILE = Path(__file__).parent / "test.wav"
MODEL_NAME = "tiny.en"
TRANSCRIPTION_INTERVAL = 3.0
CHUNK_DURATION_MS = 100
STREAM_DURATION_LIMIT_SEC = 10.0

if not TEST_WAV_FILE.exists():
    pytest.fail(f"Required test audio file not found: {TEST_WAV_FILE}", pytrace=False)
else:
    try:
        audio_info = sf.info(str(TEST_WAV_FILE))
        assert (
            audio_info.subtype
            in ("PCM_16", "PCM_S8", "PCM_U8", "PCM_32", "FLOAT", "DOUBLE")
        ), f"Test audio format ({audio_info.subtype}) not directly readable as int16/float"
        print(
            f"\n[Setup] Test audio: {TEST_WAV_FILE.name}, Duration: {audio_info.duration:.2f}s, Rate: {audio_info.samplerate}Hz, Channels: {audio_info.channels}"
        )
    except Exception as e:
        pytest.fail(
            f"Error validating test audio file '{TEST_WAV_FILE}': {e}", pytrace=False
        )


@pytest.fixture
def audio_queue():
    return asyncio.Queue()


@pytest.fixture
def transcript_collector():
    results = []
    callback_mock = AsyncMock(spec=TranscriptionCallback)

    async def side_effect(text: str):
        print(f"\n>>> Callback received: '{text}'")
        results.append(text)

    callback_mock.side_effect = side_effect
    return results, callback_mock


class MockAudioStreamer:
    def __init__(
        self,
        wav_file_path: str,
        audio_queue: asyncio.Queue,
        chunk_size_ms: int = 100,
        target_sample_rate: int = 16000,
        max_duration_sec: float = float("inf"),
    ):
        self.wav_file_path = wav_file_path
        self.audio_queue = audio_queue
        self.chunk_size_ms = chunk_size_ms
        self._stop_event = asyncio.Event()
        self._target_sample_rate = target_sample_rate
        self.max_duration_sec = max_duration_sec

    def _read_wav_file(self):
        try:
            audio_data_float, source_sample_rate = sf.read(
                str(self.wav_file_path), dtype="float32", always_2d=True
            )

            if audio_data_float.shape[1] > 1:
                audio_data_mono = np.mean(audio_data_float, axis=1)
            else:
                audio_data_mono = audio_data_float[:, 0]

            if source_sample_rate != self._target_sample_rate:
                num_samples_new = int(
                    len(audio_data_mono) * self._target_sample_rate / source_sample_rate
                )
                audio_data_resampled = np.interp(
                    np.linspace(0, len(audio_data_mono), num_samples_new),
                    np.arange(len(audio_data_mono)),
                    audio_data_mono,
                )
                self.current_sample_rate = self._target_sample_rate
            else:
                audio_data_resampled = audio_data_mono
                self.current_sample_rate = source_sample_rate

            audio_int16 = (np.clip(audio_data_resampled, -1.0, 1.0) * 32767).astype(
                np.int16
            )

            self.audio_bytes = audio_int16.tobytes()
            samples_per_chunk = int(
                self.current_sample_rate * (self.chunk_size_ms / 1000.0)
            )

            self.bytes_per_sample = 2
            self.chunk_size_bytes = samples_per_chunk * self.bytes_per_sample
            self.metadata = {
                "sample_rate": self.current_sample_rate,
                "channels": 1,
                "sample_width": 2,
            }

        except Exception as e:
            print(f"[MockStreamer] Error reading/preparing audio file: {e}")
            self.audio_bytes = None
            raise

    async def stream_audio(self):
        if not hasattr(self, "audio_bytes"):
            self._read_wav_file()

        if self.audio_bytes is None or self.chunk_size_bytes <= 0:
            print("[MockStreamer] Error: No audio data or invalid chunk size.")
            await self.audio_queue.put((None, None))
            return

        print(f"[MockStreamer] Starting stream (limit: {self.max_duration_sec}s)...")

        offset = 0
        chunk_count = 0
        streamed_duration_sec = 0.0
        chunk_duration_sec = self.chunk_size_ms / 1000.0

        while offset < len(self.audio_bytes) and not self._stop_event.is_set():
            if streamed_duration_sec >= self.max_duration_sec:
                print(
                    f"[MockStreamer] Reached duration limit ({self.max_duration_sec}s)."
                )
                break
            chunk = self.audio_bytes[offset : offset + self.chunk_size_bytes]

            if not chunk:
                break

            await self.audio_queue.put((chunk, self.metadata))

            chunk_count += 1
            streamed_duration_sec += chunk_duration_sec

            await asyncio.sleep(chunk_duration_sec)

            offset += self.chunk_size_bytes

        print(
            f"[MockStreamer] Finished streaming {chunk_count} chunks ({streamed_duration_sec:.2f}s)."
        )
        await self.audio_queue.put((None, None))

    def stop(self):
        self._stop_event.set()


@pytest.mark.asyncio
async def test_whisper_transcriber_integration(audio_queue, transcript_collector):
    collected_transcripts, callback_mock = transcript_collector

    streamer = MockAudioStreamer(
        wav_file_path=str(TEST_WAV_FILE),
        audio_queue=audio_queue,
        chunk_size_ms=CHUNK_DURATION_MS,
        target_sample_rate=16000,
        max_duration_sec=STREAM_DURATION_LIMIT_SEC,
    )

    transcriber = WhisperTranscriber(
        audio_queue=audio_queue,
        transcription_callback=callback_mock,
        model_name=MODEL_NAME,
        chunk_duration=TRANSCRIPTION_INTERVAL,
        id="test-transcriber",
    )

    print("\n[Test] STARTING TRANSCRIPTION INTEGRATION TEST")

    stream_task = None
    try:
        await transcriber.start()
        print("[Test] Waiting for model load...")

        max_wait_time = 60
        start_time = asyncio.get_event_loop().time()
        while not transcriber.model:
            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                pytest.fail(
                    f"Whisper model failed to load within {max_wait_time} seconds."
                )

            await asyncio.sleep(0.5)
        print("[Test] Model loaded.")

        stream_task = asyncio.create_task(streamer.stream_audio())

        await stream_task
        print("[Test] Audio streaming finished.")

        print("[Test] Waiting for transcriber task...")
        await transcriber.wait_until_done()

    except Exception as e:
        print(f"Test failed during execution: {e}")
        streamer.stop()
        transcriber.stop()

        if stream_task and not stream_task.done():
            stream_task.cancel()
        raise
    finally:
        streamer.stop()
        if not transcriber._stop_event.is_set():
            transcriber.stop()
        await transcriber.wait_until_done()

    final_transcription = " ".join(collected_transcripts).strip()

    print("\n[Test] FINAL TRANSCRIPTION:")
    print(f"'{final_transcription}'")

    callback_mock.assert_called()
    assert len(transcriber._audio_buffer) == 0, "Audio buffer not empty"

    print("Test passed!")
