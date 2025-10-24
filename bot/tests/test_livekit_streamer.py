import pytest
import queue
import threading
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock
from livekit import rtc, api
from livekit.rtc import AudioFrame

from bot.livekit_streamer.lk_streamer import LiveKitStreamer


@pytest.fixture
def mock_queue():
    return queue.Queue()


@pytest.fixture
def mock_event():
    event = threading.Event()
    event.clear()
    return event


@pytest.fixture
def streamer(mock_queue, mock_event):
    with patch("bot.livekit_streamer.lk_streamer.LIVEKIT_API_KEY", "test-key"), patch(
        "bot.livekit_streamer.lk_streamer.LIVEKIT_API_SECRET", "test-secret"
    ), patch("bot.livekit_streamer.lk_streamer.LIVEKIT_URL", "ws://test.url"), patch(
        "bot.livekit_streamer.lk_streamer.LIVEKIT_ROOM", "test-room"
    ), patch("bot.livekit_streamer.lk_streamer.SAMPLE_RATE", 16000), patch(
        "bot.livekit_streamer.lk_streamer.FRAME_DURATION", 0.02
    ):  # 20ms frame
        with patch.object(
            LiveKitStreamer, "_get_livekit_token", return_value="fake-init-token"
        ) as mock_get_token:
            instance = LiveKitStreamer(
                id="test-streamer-id",
                name="TestStreamerName",
                audio_queue=mock_queue,
                running=mock_event,
            )
            mock_get_token.assert_called_once()

    return instance


def test_init(streamer, mock_queue, mock_event):
    assert streamer.api_key == "test-key"
    assert streamer.api_secret == "test-secret"
    assert streamer.url == "ws://test.url"
    assert streamer.room_name == "test-room"
    assert streamer.participant_id == "test-streamer-id"
    assert streamer.participant_name == "TestStreamerName"
    assert streamer.token == "fake-init-token"
    assert streamer.sample_rate == 16000
    assert streamer.frame_duration == 0.02
    assert streamer.samples_per_frame == 320  # 16000 * 0.02
    assert streamer.audio_queue is mock_queue
    assert streamer.running is mock_event
    assert streamer.room is None
    assert streamer.audio_source is None


def test_get_livekit_token(streamer):
    with patch("bot.livekit_streamer.lk_streamer.api.AccessToken") as MockAccessToken:
        mock_token_instance = MagicMock()
        MockAccessToken.return_value = mock_token_instance
        mock_token_instance.with_identity.return_value = mock_token_instance
        mock_token_instance.with_name.return_value = mock_token_instance
        mock_token_instance.with_grants.return_value = mock_token_instance
        mock_token_instance.to_jwt.return_value = "fake-generated-token"

        token = streamer._get_livekit_token()

        assert token == "fake-generated-token"
        MockAccessToken.assert_called_with(streamer.api_key, streamer.api_secret)
        mock_token_instance.with_identity.assert_called_with(streamer.participant_id)
        mock_token_instance.with_name.assert_called_with(streamer.participant_name)
        mock_token_instance.with_grants.assert_called_once()

        grants_arg = mock_token_instance.with_grants.call_args[0][0]
        assert isinstance(grants_arg, api.VideoGrants)
        assert grants_arg.room_join is True
        assert grants_arg.room == streamer.room_name
        mock_token_instance.to_jwt.assert_called_once()


@pytest.mark.asyncio
async def test_stream_audio(streamer, mock_queue, mock_event):
    streamer.audio_source = MagicMock(spec=rtc.AudioSource)
    streamer.audio_source.capture_frame = AsyncMock()

    fake_audio_data = np.linspace(
        -0.5, 0.5, streamer.samples_per_frame + 50, dtype=np.float32
    )
    mock_queue.put(fake_audio_data)

    mock_event.set()

    # AsyncMock for sleep
    mock_sleep = AsyncMock()

    # side effect to clear event
    async def sleep_and_clear_event(*args, **kwargs):
        print("Mock sleep called, clearing running event...")
        mock_event.clear()  # stop loop on next iteration
        return None

    mock_sleep.side_effect = sleep_and_clear_event

    # patch asyncio.sleep with modified mock
    with patch("bot.livekit_streamer.lk_streamer.asyncio.sleep", mock_sleep):
        await streamer._stream_audio()

    assert streamer.audio_source.capture_frame.call_count > 0

    first_call_args = streamer.audio_source.capture_frame.call_args_list[0].args
    captured_frame = first_call_args[0]
    assert isinstance(captured_frame, AudioFrame)
    assert captured_frame.sample_rate == streamer.sample_rate
    captured_data = np.frombuffer(captured_frame.data, dtype=np.int16)
    assert np.max(np.abs(captured_data)) <= 32767

    mock_sleep.assert_called()

    assert mock_queue.empty()

    assert not mock_event.is_set()
