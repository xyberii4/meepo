import threading
import asyncio
import grpc
from grpc import aio
import queue

from typing import Dict, Any
from concurrent import futures

from bot.models import Session

from .pb import bot_pb2
from .pb import bot_pb2_grpc

from bot.selenium_bot.google_meets import Bot
from bot.livekit_streamer.lk_streamer import LiveKitStreamer


_active_sessions: Dict[str, Session] = {}


class MeetingBotServicer(bot_pb2_grpc.BotServiceServicer):
    async def JoinMeeting(self, request, context):
        """
        Implements the JoinMeeting RPC.
        Starts a new meeting bot session and streams status updates.
        """
        meepo_id = request.meepo_id
        bot_id = request.bot_id
        meeting_link = request.url
        bot_name = request.name

        if bot_id in _active_sessions:
            print(
                f"[{meepo_id} | {bot_id}] JoinMeeting request for already active bot."
            )
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(f"Bot session with ID {bot_id} is already active.")
            yield bot_pb2.JoinMeetingResponse(
                state=bot_pb2.JoinMeetingResponse.FAILED,
                message=f"Bot {bot_id} is already active.",
                bot_id=bot_id,
            )
            return

        audio_queue = queue.Queue()
        selenium_running = threading.Event()
        pending = threading.Event()
        joined = threading.Event()
        livekit_running = threading.Event()

        # send a RECEIVED response.
        yield bot_pb2.JoinMeetingResponse(
            state=bot_pb2.JoinMeetingResponse.RECEIVED,
            message=f"Received request for meepo {meepo_id}, bot {bot_id}",
            bot_id=bot_id,
        )

        try:
            print(f"[{meepo_id} | {bot_id}] Starting bot and LiveKit streamer...")

            bot_instance = Bot(
                bot_id,
                bot_name,
                meeting_link,
                audio_queue,
                pending,
                joined,
                selenium_running,
            )
            lks = LiveKitStreamer(bot_id, bot_name, audio_queue, livekit_running)

            selenium_thread = threading.Thread(target=bot_instance.execute)
            selenium_thread.daemon = True
            selenium_thread.start()

            livekit_thread = threading.Thread(target=lks.execute)
            livekit_thread.daemon = True
            livekit_thread.start()

            # pending
            await asyncio.get_running_loop().run_in_executor(None, pending.wait)
            yield bot_pb2.JoinMeetingResponse(
                state=bot_pb2.JoinMeetingResponse.PENDING,
                message=f"Bot {bot_id} (meepo {meepo_id}) is pending.",
                bot_id=bot_id,
            )

            # joined
            await asyncio.get_running_loop().run_in_executor(None, joined.wait)
            yield bot_pb2.JoinMeetingResponse(
                state=bot_pb2.JoinMeetingResponse.JOINED,
                message=f"Bot {bot_id} (meepo {meepo_id}) has joined the meeting.",
                bot_id=bot_id,
            )

            _active_sessions[bot_id] = {
                "bot": bot_instance,
                "livekit_streamer": lks,
                "selenium_evt": selenium_running,
                "livekit_evt": livekit_running,
            }

        except Exception as e:
            print(f"[{meepo_id} | {bot_id}] An error occurred: {e}")
            livekit_running.clear()
            selenium_running.clear()
            yield bot_pb2.JoinMeetingResponse(
                state=bot_pb2.JoinMeetingResponse.FAILED,
                message=f"An error occurred: {e}",
                bot_id=bot_id,
            )

    async def GetMeetingDetails(self, request, context):
        """
        Implements the GetMeetingDetails RPC.
        Returns details about the current meeting, such as participants.
        """
        bot_id = request.bot_id
        meepo_id = request.meepo_id

        print(f"[{meepo_id} | {bot_id}] Received GetMeetingDetails request.")

        bot_session = _active_sessions.get(bot_id, None)

        if bot_session is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(
                f"Bot session with ID {bot_id} (for meepo {meepo_id}) not found."
            )
            return bot_pb2.MeetingDetailsResponse()

        bot_instance = bot_session.get("bot")
        if bot_instance:
            participants = bot_instance.get_participants()
        else:
            participants = []

        return bot_pb2.MeetingDetailsResponse(
            participants=[
                bot_pb2.Participant(
                    name=p,
                )
                for p in participants
            ],
        )

    async def LeaveMeeting(self, request, context):
        bot_id = request.bot_id
        meepo_id = request.meepo_id

        print(f"[{meepo_id} | {bot_id}] Received LeaveMeeting request.")

        bot_session = _active_sessions.get(bot_id, None)

        if bot_session is None:
            return bot_pb2.LeaveMeetingResponse(
                state=bot_pb2.LeaveMeetingResponse.FAILED,
                message=f"Bot session with ID {bot_id} (for meepo {meepo_id}) not found.",
            )

        selenium_evt = bot_session.get("selenium_evt")
        livekit_evt = bot_session.get("livekit_evt")

        try:
            if selenium_evt:
                selenium_evt.clear()
            if livekit_evt:
                livekit_evt.clear()

            if bot_id in _active_sessions:
                del _active_sessions[bot_id]
                print(f"[{meepo_id} | {bot_id}] Session cleaned up.")

            return bot_pb2.LeaveMeetingResponse(
                state=bot_pb2.LeaveMeetingResponse.DONE,
                message=f"Bot {bot_id} successfully left.",
            )
        except Exception as e:
            print(
                f"[{meepo_id} | {bot_id}] An error occurred while leaving the meeting: {e}"
            )
            return bot_pb2.LeaveMeetingResponse(
                state=bot_pb2.LeaveMeetingResponse.FAILED,
                message=f"An error occurred while leaving the meeting: {e}",
            )


async def serve():
    """
    Main function to start the gRPC server.
    """
    server = aio.server(futures.ThreadPoolExecutor(max_workers=10))
    bot_pb2_grpc.add_BotServiceServicer_to_server(MeetingBotServicer(), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    print("Meeting Bot gRPC server started on port 50051.")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
