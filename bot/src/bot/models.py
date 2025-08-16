from typing import TypedDict
import threading
import bot.selenium_bot.google_meets as bot
import bot.livekit_streamer.lk_streamer as lk_streamer


class Session(TypedDict):
    bot: bot.Bot
    livekit_streamer: lk_streamer.LiveKitStreamer
    selenium_evt: threading.Event
    livekit_evt: threading.Event
