"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 6, 32, 0, '', 'bot.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\tbot.proto"Q\n\x12JoinMeetingRequest\x12\x10\n\x08meepo_id\x18\x01 \x01(\t\x12\x0e\n\x06bot_id\x18\x02 \x01(\t\x12\x0b\n\x03url\x18\x03 \x01(\t\x12\x0c\n\x04name\x18\x04 \x01(\t"\x9d\x01\n\x13JoinMeetingResponse\x12)\n\x05state\x18\x01 \x01(\x0e2\x1a.JoinMeetingResponse.State\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x0e\n\x06bot_id\x18\x03 \x01(\t":\n\x05State\x12\x0c\n\x08RECEIVED\x10\x00\x12\x0b\n\x07PENDING\x10\x01\x12\n\n\x06JOINED\x10\x02\x12\n\n\x06FAILED\x10\x03"9\n\x15MeetingDetailsRequest\x12\x0e\n\x06bot_id\x18\x01 \x01(\t\x12\x10\n\x08meepo_id\x18\x02 \x01(\t"<\n\x16MeetingDetailsResponse\x12"\n\x0cparticipants\x18\x01 \x03(\x0b2\x0c.Participant"\x1b\n\x0bParticipant\x12\x0c\n\x04name\x18\x01 \x01(\t"7\n\x13LeaveMeetingRequest\x12\x0e\n\x06bot_id\x18\x01 \x01(\t\x12\x10\n\x08meepo_id\x18\x02 \x01(\t"\x80\x01\n\x14LeaveMeetingResponse\x12*\n\x05state\x18\x01 \x01(\x0e2\x1b.LeaveMeetingResponse.State\x12\x0f\n\x07message\x18\x02 \x01(\t"+\n\x05State\x12\x0c\n\x08RECEIVED\x10\x00\x12\x08\n\x04DONE\x10\x01\x12\n\n\x06FAILED\x10\x022\xcb\x01\n\nBotService\x12:\n\x0bJoinMeeting\x12\x13.JoinMeetingRequest\x1a\x14.JoinMeetingResponse0\x01\x12D\n\x11GetMeetingDetails\x12\x16.MeetingDetailsRequest\x1a\x17.MeetingDetailsResponse\x12;\n\x0cLeaveMeeting\x12\x14.LeaveMeetingRequest\x1a\x15.LeaveMeetingResponseB4Z2github.com/xyberii4/meepo/gateway/internal/grpc/pbb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'bot_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    _globals['DESCRIPTOR']._loaded_options = None
    _globals['DESCRIPTOR']._serialized_options = b'Z2github.com/xyberii4/meepo/gateway/internal/grpc/pb'
    _globals['_JOINMEETINGREQUEST']._serialized_start = 13
    _globals['_JOINMEETINGREQUEST']._serialized_end = 94
    _globals['_JOINMEETINGRESPONSE']._serialized_start = 97
    _globals['_JOINMEETINGRESPONSE']._serialized_end = 254
    _globals['_JOINMEETINGRESPONSE_STATE']._serialized_start = 196
    _globals['_JOINMEETINGRESPONSE_STATE']._serialized_end = 254
    _globals['_MEETINGDETAILSREQUEST']._serialized_start = 256
    _globals['_MEETINGDETAILSREQUEST']._serialized_end = 313
    _globals['_MEETINGDETAILSRESPONSE']._serialized_start = 315
    _globals['_MEETINGDETAILSRESPONSE']._serialized_end = 375
    _globals['_PARTICIPANT']._serialized_start = 377
    _globals['_PARTICIPANT']._serialized_end = 404
    _globals['_LEAVEMEETINGREQUEST']._serialized_start = 406
    _globals['_LEAVEMEETINGREQUEST']._serialized_end = 461
    _globals['_LEAVEMEETINGRESPONSE']._serialized_start = 464
    _globals['_LEAVEMEETINGRESPONSE']._serialized_end = 592
    _globals['_LEAVEMEETINGRESPONSE_STATE']._serialized_start = 549
    _globals['_LEAVEMEETINGRESPONSE_STATE']._serialized_end = 592
    _globals['_BOTSERVICE']._serialized_start = 595
    _globals['_BOTSERVICE']._serialized_end = 798