"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings
from . import bot_pb2 as bot__pb2
GRPC_GENERATED_VERSION = '1.74.1'
GRPC_VERSION = grpc.__version__
_version_not_supported = False
try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True
if _version_not_supported:
    raise RuntimeError(f'The grpc package installed is at version {GRPC_VERSION},' + f' but the generated code in bot_pb2_grpc.py depends on' + f' grpcio>={GRPC_GENERATED_VERSION}.' + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}' + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.')

class BotServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.JoinMeeting = channel.unary_stream('/BotService/JoinMeeting', request_serializer=bot__pb2.JoinMeetingRequest.SerializeToString, response_deserializer=bot__pb2.JoinMeetingResponse.FromString, _registered_method=True)
        self.GetMeetingDetails = channel.unary_unary('/BotService/GetMeetingDetails', request_serializer=bot__pb2.MeetingDetailsRequest.SerializeToString, response_deserializer=bot__pb2.MeetingDetailsResponse.FromString, _registered_method=True)
        self.LeaveMeeting = channel.unary_unary('/BotService/LeaveMeeting', request_serializer=bot__pb2.LeaveMeetingRequest.SerializeToString, response_deserializer=bot__pb2.LeaveMeetingResponse.FromString, _registered_method=True)

class BotServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def JoinMeeting(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetMeetingDetails(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def LeaveMeeting(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

def add_BotServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {'JoinMeeting': grpc.unary_stream_rpc_method_handler(servicer.JoinMeeting, request_deserializer=bot__pb2.JoinMeetingRequest.FromString, response_serializer=bot__pb2.JoinMeetingResponse.SerializeToString), 'GetMeetingDetails': grpc.unary_unary_rpc_method_handler(servicer.GetMeetingDetails, request_deserializer=bot__pb2.MeetingDetailsRequest.FromString, response_serializer=bot__pb2.MeetingDetailsResponse.SerializeToString), 'LeaveMeeting': grpc.unary_unary_rpc_method_handler(servicer.LeaveMeeting, request_deserializer=bot__pb2.LeaveMeetingRequest.FromString, response_serializer=bot__pb2.LeaveMeetingResponse.SerializeToString)}
    generic_handler = grpc.method_handlers_generic_handler('BotService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('BotService', rpc_method_handlers)

class BotService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def JoinMeeting(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_stream(request, target, '/BotService/JoinMeeting', bot__pb2.JoinMeetingRequest.SerializeToString, bot__pb2.JoinMeetingResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def GetMeetingDetails(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/BotService/GetMeetingDetails', bot__pb2.MeetingDetailsRequest.SerializeToString, bot__pb2.MeetingDetailsResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def LeaveMeeting(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/BotService/LeaveMeeting', bot__pb2.LeaveMeetingRequest.SerializeToString, bot__pb2.LeaveMeetingResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)