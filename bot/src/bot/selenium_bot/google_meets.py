from bot.config import (
    BROWSER_EXECUTABLE,
    DRIVER_EXECUTABLE,
)

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import time
import os
import queue
import threading
import numpy as np
import base64
import traceback


class Bot:
    def __init__(
        self,
        id: str,
        name: str,
        meeting_link: str,
        audio_queue: queue.Queue,
        pending: threading.Event,
        joined: threading.Event,
        running: threading.Event,
    ):
        self.meeting_link = meeting_link
        self.id = id
        self.bot_name = name

        self.driver = self._setup_driver()
        self.timeout = 60  # seconds

        self.audio_capture_started = False
        self.audio_queue = audio_queue

        self.pending = pending
        self.joined = joined
        self.running = running

    def _setup_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_argument("--mute-audio")

        options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        driver = uc.Chrome(
            options=options,
            browser_executable_path=BROWSER_EXECUTABLE,
            driver_executable_path=DRIVER_EXECUTABLE,
            headless=False,  # Google Meets blocks headless browsers
        )

        return driver

    def join_meeting(self):
        self.running.set()
        self.pending.clear()
        self.joined.clear()

        self.driver.get(self.meeting_link)

        print(f"[{self.id}] Joining meeting {self.meeting_link} as {self.bot_name}...")

        try:
            try:
                # disable microphone and camera
                disable_dev_button = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[jsname='IbE0S']")
                    )
                )
                disable_dev_button.click()
            except TimeoutException:
                pass

            time.sleep(0.5)

            # enter bot name
            name_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[jsname='YPqjbf']")
                )
            )
            name_box.send_keys(self.bot_name)
            time.sleep(0.5)

            # request to join
            join_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(), 'Ask to join')]")
                )
            )
            join_button.click()
            self.pending.set()  # waiting to join

        except TimeoutException as e:
            raise TimeoutException(f"Failed to join meeting: {e}.")
        except Exception as e:
            raise Exception(f"An error occurred while trying to join the meeting: {e}")

        print(f"[{self.id}] Requested to join meeting...")

        try:
            # check if entered meeting
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[@aria-label='Leave call']")
                )
            )

            self.pending.clear()
            self.joined.set()
            print(f"[{self.id}] Successfully joined the meeting!")
        except TimeoutException as e:
            raise TimeoutException(f"Timed out waiting for the meeting to start: {e}.")

    def get_participants(self) -> list[str]:
        try:
            participantElems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//div[@jsname='giiMnc']//span[@class='notranslate']")
                )
            )

            return [elem.text.strip() for elem in participantElems if elem.text]
        except Exception as e:
            raise Exception(f"Error retrieving participants: {e}")

    # inject script into browser
    def _inject_audio_capture_script(self):
        script_path = os.path.join(os.path.dirname(__file__), "audio_capture.js")
        script = open(script_path, "r").read()

        self.driver.execute_script(script)

    # execute injected script
    def _start_audio_capture(self):
        try:
            print(f"[{self.id}] Starting audio capture...")
            result = self.driver.execute_script(
                "return window.audioCapture.startCapture();"
            )
            if result:
                print(f"[{self.id}] Audio capture started!")
                self.audio_capture_started = True
            else:
                self.audio_capture_started = False
                raise Exception("Failed to start audio capture")
        except Exception as e:
            self.audio_capture_started = False
            raise Exception(f"Error starting audio capture: {e}")

    def _get_audio_chunks(self):
        try:
            chunks = self.driver.execute_script(
                "return window.audioCapture.getAudioChunks(true);"
            )
            return chunks if chunks else []
        except Exception as e:
            raise Exception(f"Error getting audio chunks: {e}")

    def _stop_audio_capture(self):
        try:
            self.driver.execute_script("window.audioCapture.stopCapture();")
            print(f"[{self.id}] Audio capture stopped")
        except Exception as e:
            raise Exception(f"Error stopping audio capture: {e}")

    def _decode_audio_chunk(self, chunk):
        try:
            # Decode base64 to bytes
            audio_bytes = base64.b64decode(chunk["data"])
            # Convert bytes back to float32 array
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            return {
                "timestamp": chunk["timestamp"],
                "audio_data": audio_array,
                "sample_rate": chunk["sampleRate"],
                "length": chunk["length"],
            }
        except Exception as e:
            raise Exception(f"Error decoding audio chunk: {e}")

    def _cleanup(self):
        if self.audio_capture_started:
            self._stop_audio_capture()

        try:
            try:
                # multiple participants triggers an overlay which must be closed before interacting with the page
                overlay = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//button[@data-mdc-dialog-action="ok"]')
                    )
                )
                overlay.click()
            except TimeoutException:
                pass

            leave_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[@aria-label='Leave call']")
                )
            )
            leave_button.click()
            self.joined.clear()
            print(f"[{self.id}] Successfully left the meeting.")

            self.driver.quit()
        except TimeoutException:
            raise TimeoutException("Failed to leave the meeting: Timeout occurred.")

    def execute(self):
        # retrieves audio in real-time via Web Audio API
        try:
            print(f"[{self.id}] Starting bot {self.bot_name}...")
            self.join_meeting()
            print(f"[{self.id}] Bot {self.bot_name} has joined the meeting.")
            print(f"[{self.id}] Starting audio capture script...")
            self._inject_audio_capture_script()
            self._start_audio_capture()

            while self.running.is_set():
                chunks = self._get_audio_chunks()
                if chunks:
                    for chunk in chunks:
                        decoded = self._decode_audio_chunk(chunk)
                        audio_data = decoded["audio_data"]
                        self.audio_queue.put_nowait(audio_data)

                time.sleep(0.1)

        except Exception as e:
            traceback.print_exc()
            raise Exception(f"An error occurred during execution: {e}")
        finally:
            self._cleanup()
