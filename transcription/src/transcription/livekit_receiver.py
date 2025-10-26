import asyncio
import numpy as np

from livekit import api, rtc


class LiveKitReceiver:
    def __init__(
        self,
        id: str,
        name: str,
        api_key: str,
        api_secret: str,
        room_name: str,
        room_url: str,
        audio_queue: asyncio.Queue,
    ):
        self.id = id
        self.name = name + "-scriber"
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws_url = room_url
        self.room_name = room_name
        self.room: rtc.Room | None = None
        self.audio_queue = audio_queue
        self._stop_event = asyncio.Event()
        self._track_found_event = asyncio.Event()
        self._stream_task: asyncio.Task | None = None
        self.stream_started_event = asyncio.Event()

    def _generate_token(self):
        token = (
            api.AccessToken(self.api_key, self.api_secret)
            .with_identity(self.id)
            .with_name(self.name)
            .with_grants(api.VideoGrants(room_join=True, room=self.room_name))
        )
        return token.to_jwt()

    def _convert_to_16bit(self, event: rtc.AudioFrameEvent):
        try:
            frame = event.frame
            audio_data = np.frombuffer(frame.data, dtype=np.int16)

            return audio_data.tobytes(), frame.sample_rate

        except Exception as e:
            print(f"[{self.id}] Error converting audio frame: {e}")
            return None, None

    async def _stream_audio(self, track: rtc.Track):
        print(f"[{self.id}] Starting audio stream...")
        audio_stream = rtc.AudioStream(track)
        frame_count = 0
        try:
            async for frame_event in audio_stream:
                if self._stop_event.is_set():
                    break

                frame_count += 1

                try:
                    pcm_data, original_sample_rate = self._convert_to_16bit(frame_event)

                    if pcm_data is not None:
                        metadata = {
                            "sample_rate": original_sample_rate,
                            "channels": 1,
                            "sample_width": 2,
                        }
                        await self.audio_queue.put((pcm_data, metadata))
                    else:
                        print(
                            f"[{self.id}] WARNING: Failed to convert audio frame, skipping"
                        )

                except Exception as e:
                    print(
                        f"[{self.id}] Error processing audio frame {frame_count}: {e}"
                    )
                    continue

        except asyncio.CancelledError:
            print(f"[{self.id}] Audio stream cancelled.")
        except Exception as e:
            print(f"[{self.id}] Error during audio streaming: {e}")
        finally:
            print(
                f"[{self.id}] Audio streaming stopped after processing {frame_count} frames."
            )

    def stop(self):
        print(f"[{self.id}] Stop signal received. Shutting down LiveKit connection...")
        self._stop_event.set()

    async def connect_and_stream(self):
        token = self._generate_token()
        self.room = rtc.Room()

        @self.room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                print(
                    f"[{self.id}] Subscribed to audio track from participant '{participant.identity}'"
                )

                if self._stream_task is None:
                    self._stream_task = asyncio.create_task(self._stream_audio(track))
                    self._track_found_event.set()
                    self.stream_started_event.set()

        try:
            print(f"[{self.id}] Attempting to connect to room '{self.room_name}'...")

            await self.room.connect(self.ws_url, token)

            print(f"[{self.id}] Successfully connected to room.")

            for participant in self.room.remote_participants.values():
                for publication in participant.track_publications.values():
                    if (
                        publication.track
                        and publication.kind == rtc.TrackKind.KIND_AUDIO
                    ):
                        on_track_subscribed(publication.track, publication, participant)
                        break

            print(f"[{self.id}] Waiting for audio track...")
            await asyncio.wait_for(self._track_found_event.wait(), timeout=30)

            print(f"[{self.id}] Audio track found, processing stream...")
            await self._stop_event.wait()

        except asyncio.TimeoutError:
            print(f"[{self.id}] TIMEOUT: waiting for audio track")
        except asyncio.CancelledError:
            print(f"[{self.id}] Connection and streaming task cancelled.")
        except Exception as e:
            print(f"[{self.id}] An error occurred: {e}")
        finally:
            if self._stream_task:
                self._stream_task.cancel()

                try:
                    await asyncio.wait_for(self._stream_task, timeout=5)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            if self.room and self.room.isconnected:
                await self.room.disconnect()
                print(f"[{self.id}] Disconnected from LiveKit room.")
