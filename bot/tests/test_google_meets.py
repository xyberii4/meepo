import pytest
import queue
import threading
import numpy as np
import base64
from unittest.mock import MagicMock, patch, mock_open, ANY

from bot.selenium_bot.google_meets import Bot


@pytest.fixture
def mock_queue():
    return queue.Queue()


@pytest.fixture
def mock_pending():
    return threading.Event()


@pytest.fixture
def mock_joined():
    return threading.Event()


@pytest.fixture
def mock_running():
    return threading.Event()


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.quit = MagicMock()
    driver.execute_script = MagicMock()
    return driver


@pytest.fixture
def bot_instance(mock_queue, mock_pending, mock_joined, mock_running, mock_driver):
    """Provides a Bot instance with a mocked driver."""
    # Patch _setup_driver during init to inject our mock driver
    with patch.object(Bot, "_setup_driver", return_value=mock_driver):
        instance = Bot(
            id="test-bot-id",
            name="TestBotName",
            meeting_link="http://fake.meeting.link",
            audio_queue=mock_queue,
            pending=mock_pending,
            joined=mock_joined,
            running=mock_running,
        )
    return instance


def test_init(
    bot_instance, mock_queue, mock_pending, mock_joined, mock_running, mock_driver
):
    """Tests __init__ sets attributes correctly."""
    assert bot_instance.id == "test-bot-id"
    assert bot_instance.bot_name == "TestBotName"
    assert bot_instance.meeting_link == "http://fake.meeting.link"
    assert bot_instance.driver is mock_driver  # Check mock driver was injected
    assert bot_instance.timeout == 60
    assert not bot_instance.audio_capture_started
    assert bot_instance.audio_queue is mock_queue
    assert bot_instance.pending is mock_pending
    assert bot_instance.joined is mock_joined
    assert bot_instance.running is mock_running


@patch("bot.selenium_bot.google_meets.uc.Chrome")
@patch("bot.selenium_bot.google_meets.BROWSER_EXECUTABLE", "/mock/browser")
@patch("bot.selenium_bot.google_meets.DRIVER_EXECUTABLE", "/mock/driver")
def test_setup_driver(
    MockUcChrome, mock_queue, mock_pending, mock_joined, mock_running
):
    """Tests _setup_driver configures and calls uc.Chrome correctly."""
    mock_driver_instance = MagicMock()
    MockUcChrome.return_value = mock_driver_instance

    bot = Bot("id", "name", "link", mock_queue, mock_pending, mock_joined, mock_running)

    assert bot.driver is mock_driver_instance
    MockUcChrome.assert_called_once()
    _, call_kwargs = MockUcChrome.call_args

    options = call_kwargs.get("options")

    assert options is not None
    assert "--mute-audio" in options.arguments
    assert options.capabilities.get("goog:loggingPrefs") == {"browser": "ALL"}

    assert call_kwargs.get("browser_executable_path") == "/mock/browser"
    assert call_kwargs.get("driver_executable_path") == "/mock/driver"
    assert call_kwargs.get("headless") is False


def test_get_participants(bot_instance, mock_driver):
    """Tests get_participants extracts text from mocked elements."""
    mock_element1 = MagicMock()
    mock_element1.text = " Alice "
    mock_element2 = MagicMock()
    mock_element2.text = "Bob"
    mock_element3 = MagicMock()
    mock_element3.text = ""

    mock_wait = MagicMock()
    mock_wait.until.return_value = [mock_element1, mock_element2, mock_element3]

    with patch("bot.selenium_bot.google_meets.WebDriverWait", return_value=mock_wait):
        participants = bot_instance.get_participants()

        mock_wait.until.assert_called_once()
        assert participants == ["Alice", "Bob"]


@patch("builtins.open", new_callable=mock_open, read_data="mock_js_script_content")
@patch("os.path.join")
def test_inject_audio_capture_script(
    mock_os_join, mock_file_open, bot_instance, mock_driver
):
    mock_os_join.return_value = "/fake/path/to/audio_capture.js"

    bot_instance._inject_audio_capture_script()

    mock_os_join.assert_called_once()
    mock_file_open.assert_called_with("/fake/path/to/audio_capture.js", "r")
    mock_driver.execute_script.assert_called_once_with("mock_js_script_content")


def test_start_audio_capture_success(bot_instance, mock_driver):
    mock_driver.execute_script.return_value = True  # simulate success from JS

    bot_instance._start_audio_capture()

    mock_driver.execute_script.assert_called_once_with(
        "return window.audioCapture.startCapture();"
    )
    assert bot_instance.audio_capture_started is True


def test_start_audio_capture_failure(bot_instance, mock_driver):
    mock_driver.execute_script.return_value = False  # Simulate failure from JS

    with pytest.raises(Exception, match="Failed to start audio capture"):
        bot_instance._start_audio_capture()

    mock_driver.execute_script.assert_called_once_with(
        "return window.audioCapture.startCapture();"
    )
    assert bot_instance.audio_capture_started is False


def test_get_audio_chunks(bot_instance, mock_driver):
    mock_driver.execute_script.return_value = [
        {"data": "...", "timestamp": 123}
    ]  # dummy return

    chunks = bot_instance._get_audio_chunks()

    mock_driver.execute_script.assert_called_once_with(
        "return window.audioCapture.getAudioChunks(true);"
    )
    assert chunks == [{"data": "...", "timestamp": 123}]


def test_stop_audio_capture(bot_instance, mock_driver):
    bot_instance._stop_audio_capture()

    mock_driver.execute_script.assert_called_once_with(
        "window.audioCapture.stopCapture();"
    )


def test_decode_audio_chunk(bot_instance):
    fake_audio = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    fake_audio_bytes = fake_audio.tobytes()
    fake_audio_base64 = base64.b64encode(fake_audio_bytes).decode("utf-8")

    mock_chunk = {
        "data": fake_audio_base64,
        "timestamp": 12345,
        "sampleRate": 48000,
        "length": len(fake_audio),
    }

    decoded = bot_instance._decode_audio_chunk(mock_chunk)

    assert decoded["timestamp"] == 12345
    assert decoded["sample_rate"] == 48000
    assert decoded["length"] == 3
    np.testing.assert_array_almost_equal(decoded["audio_data"], fake_audio)
    assert decoded["audio_data"].dtype == np.float32
