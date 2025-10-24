import pytest
import grpc
import threading
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from bot.pb import bot_pb2
from bot.server import MeetingBotServicer
from bot import server as bot_server
from bot.models import Session

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_context():
    context = MagicMock(spec=grpc.aio.ServicerContext)
    context.set_code = MagicMock()
    context.set_details = MagicMock()
    return context


@patch("bot.server.asyncio.get_running_loop")
@patch("bot.server.threading.Thread")
@patch("bot.server.LiveKitStreamer")
@patch("bot.server.Bot")
async def test_join_meeting_success(
    MockBot,
    MockLiveKit,
    MockThread,
    MockGetLoop,
    mock_context,
):
    event_store = {}  # store real events

    mock_bot_instance = MockBot.return_value

    def bot_init_capture(*args, **kwargs):
        print("Captured Bot init, storing real events...")
        event_store["pending"] = args[4]
        event_store["joined"] = args[5]
        assert isinstance(event_store["pending"], threading.Event)
        assert isinstance(event_store["joined"], threading.Event)
        return mock_bot_instance

    MockBot.side_effect = bot_init_capture

    mock_thread_instance = MagicMock()
    mock_thread_instance.start = MagicMock()
    MockThread.return_value = mock_thread_instance

    mock_executor = AsyncMock()  # AsyncMock as run_in_executor is awaited

    async def run_in_executor_side_effect(executor, func, *args):
        func_name = getattr(func, "__name__", "unknown")
        func_self = getattr(func, "__self__", None)

        print(f"run_in_executor called with func: {func_name}")

        if func_name == "wait" and isinstance(func_self, threading.Event):
            event = func_self
            print(f"Intercepted run_in_executor for event.wait() for {event}")
            print("Simulating event.set()")
            event.set()
            await asyncio.sleep(0)  # yield control briefly
            print("Returning from mocked event.wait()")
            return None
        else:
            print(
                f"Warning: Unexpected function passed to run_in_executor: {func_name}"
            )
            await asyncio.sleep(0)
            return None

    mock_executor.run_in_executor = AsyncMock(side_effect=run_in_executor_side_effect)
    MockGetLoop.return_value = mock_executor

    meepo_id = "test-meepo-1"
    bot_id = "test-bot-1"
    request = bot_pb2.JoinMeetingRequest(
        meepo_id=meepo_id, bot_id=bot_id, url="http://fake.url", name="TestBot"
    )

    servicer = MeetingBotServicer()
    responses = []
    print("Calling JoinMeeting...")
    async for resp in servicer.JoinMeeting(request, mock_context):
        print(f"Received response: state={resp.state}")
        responses.append(resp)
    print("JoinMeeting call finished.")

    print(f"Join meeting responses: {[r.state for r in responses]}")
    assert (
        len(responses) == 3
    ), f"Expected 3 responses, got {len(responses)}: {[r.state for r in responses]}"
    assert responses[0].state == bot_pb2.JoinMeetingResponse.RECEIVED
    assert responses[1].state == bot_pb2.JoinMeetingResponse.PENDING
    assert responses[2].state == bot_pb2.JoinMeetingResponse.JOINED
    assert responses[2].bot_id == bot_id

    MockBot.assert_called_once()
    MockLiveKit.assert_called_once()
    assert MockThread.call_count == 2  # threads created for bot and livekit
    assert mock_thread_instance.start.call_count == 2

    assert mock_executor.run_in_executor.call_count == 2
    mock_executor.run_in_executor.assert_any_call(None, event_store["pending"].wait)
    mock_executor.run_in_executor.assert_any_call(None, event_store["joined"].wait)

    assert bot_id in bot_server._active_sessions


async def test_get_meeting_details_success(mock_context):
    meepo_id = "test-meepo-2"
    bot_id = "test-bot-2"
    mock_bot = MagicMock()
    mock_bot.get_participants.return_value = ["Participant A", "Participant B"]
    mock_session: Session = {
        "bot": mock_bot,
        "livekit_streamer": MagicMock(),
        "selenium_evt": MagicMock(),
        "livekit_evt": MagicMock(),
    }
    bot_server._active_sessions[bot_id] = mock_session
    request = bot_pb2.MeetingDetailsRequest(bot_id=bot_id, meepo_id=meepo_id)
    servicer = MeetingBotServicer()
    response = await servicer.GetMeetingDetails(request, mock_context)
    mock_bot.get_participants.assert_called_once()
    assert len(response.participants) == 2
    assert response.participants[0].name == "Participant A"
    mock_context.set_code.assert_not_called()


async def test_get_meeting_details_not_found(mock_context):
    meepo_id = "test-meepo-nf"
    bot_id = "test-bot-nf"
    request = bot_pb2.MeetingDetailsRequest(bot_id=bot_id, meepo_id=meepo_id)
    servicer = MeetingBotServicer()
    response = await servicer.GetMeetingDetails(request, mock_context)
    assert len(response.participants) == 0
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)
    mock_context.set_details.assert_called_once()


async def test_leave_meeting_success(mock_context):
    meepo_id = "test-meepo-3"
    bot_id = "test-bot-3"
    mock_selenium_evt = MagicMock(spec=threading.Event)
    mock_livekit_evt = MagicMock(spec=threading.Event)
    mock_session: Session = {
        "bot": MagicMock(),
        "livekit_streamer": MagicMock(),
        "selenium_evt": mock_selenium_evt,
        "livekit_evt": mock_livekit_evt,
    }
    bot_server._active_sessions[bot_id] = mock_session
    request = bot_pb2.LeaveMeetingRequest(bot_id=bot_id, meepo_id=meepo_id)
    servicer = MeetingBotServicer()
    response = await servicer.LeaveMeeting(request, mock_context)
    mock_selenium_evt.clear.assert_called_once()
    mock_livekit_evt.clear.assert_called_once()
    assert bot_id not in bot_server._active_sessions
    assert response.state == bot_pb2.LeaveMeetingResponse.DONE


async def test_leave_meeting_not_found(mock_context):
    meepo_id = "test-meepo-lnf"
    bot_id = "test-bot-lnf"
    request = bot_pb2.LeaveMeetingRequest(bot_id=bot_id, meepo_id=meepo_id)
    servicer = MeetingBotServicer()
    response = await servicer.LeaveMeeting(request, mock_context)
    assert response.state == bot_pb2.LeaveMeetingResponse.FAILED
    assert "not found" in response.message.lower()


async def test_join_meeting_already_exists(mock_context):
    meepo_id = "test-meepo-ae"
    bot_id = "test-bot-ae"
    bot_server._active_sessions[bot_id] = {"bot": MagicMock()}
    request = bot_pb2.JoinMeetingRequest(
        meepo_id=meepo_id, bot_id=bot_id, url="http://fake.url", name="TestBotAE"
    )
    servicer = MeetingBotServicer()
    responses = []
    async for resp in servicer.JoinMeeting(request, mock_context):
        responses.append(resp)
    assert len(responses) == 1
    assert responses[0].state == bot_pb2.JoinMeetingResponse.FAILED
    assert "already active" in responses[0].message.lower()
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.ALREADY_EXISTS)
    mock_context.set_details.assert_called_once()
