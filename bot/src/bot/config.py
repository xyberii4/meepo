from dotenv import load_dotenv
import yaml
import os


load_dotenv()

with open("config.yaml", "r") as f:
    yaml_config = yaml.safe_load(f)

# LiveKit configuration
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_ROOM = os.environ.get("LIVEKIT_ROOM", "")

# audio configuration
SAMPLE_RATE = yaml_config.get("audio", {}).get("sample_rate", 48000)
FRAME_DURATION = yaml_config.get("audio", {}).get("frame_duration", 0.01)  # in seconds

# bot configuration
BROWSER_EXECUTABLE = yaml_config.get("bot", {}).get(
    "browser_executable", "/usr/bin/chromium"
)
DRIVER_EXECUTABLE = yaml_config.get("bot", {}).get(
    "driver_executable", "/usr/bin/chromedriver"
)
