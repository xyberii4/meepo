import asyncio
import pytest
import pytest_asyncio
import grpc
from grpc.experimental import aio
from concurrent import futures
from unittest.mock import patch  # Needed to clear sessions

# Adjust import paths if needed
from bot.server import MeetingBotServicer
from bot.pb import bot_pb2_grpc
from bot import server as bot_server  # Import the server module itself


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for our test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def grpc_server():
    """Fixture to start and stop an in-process gRPC server."""
    server = aio.server(futures.ThreadPoolExecutor(max_workers=10))
    bot_pb2_grpc.add_BotServiceServicer_to_server(MeetingBotServicer(), server)

    # Use a standard localhost port for testing
    listen_addr = "127.0.0.1:50051"
    server.add_insecure_port(listen_addr)

    await server.start()
    print(f"\nTest gRPC server started on {listen_addr}")
    yield server, listen_addr  # Yield server and address
    print("\nStopping test gRPC server...")
    await server.stop(0)
    print("Test gRPC server stopped.")


@pytest_asyncio.fixture(scope="module")
async def grpc_client(grpc_server):
    """Fixture to create a gRPC client (stub) connected to the test server."""
    _, listen_addr = grpc_server  # Get address from grpc_server fixture
    channel = aio.insecure_channel(listen_addr)
    stub = bot_pb2_grpc.BotServiceStub(channel)
    print(f"Test gRPC client connected to {listen_addr}")
    yield stub
    print("Closing test gRPC client channel...")
    await channel.close()
    print("Test gRPC client channel closed.")


@pytest.fixture(autouse=True)
def clear_active_sessions():
    """
    This fixture automatically runs for every test, ensuring the
    _active_sessions dictionary is empty before each test run.
    """
    # Access the _active_sessions dictionary via the imported module
    print("\nClearing active sessions before test...")
    bot_server._active_sessions.clear()
    yield  # Run the test
    print("Clearing active sessions after test...")
    bot_server._active_sessions.clear()  # Ensure clean state after test
