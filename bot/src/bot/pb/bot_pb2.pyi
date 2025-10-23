from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union
DESCRIPTOR: _descriptor.FileDescriptor

class JoinMeetingRequest(_message.Message):
    __slots__ = ('meepo_id', 'bot_id', 'url', 'name')
    MEEPO_ID_FIELD_NUMBER: _ClassVar[int]
    BOT_ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    meepo_id: str
    bot_id: str
    url: str
    name: str

    def __init__(self, meepo_id: _Optional[str]=..., bot_id: _Optional[str]=..., url: _Optional[str]=..., name: _Optional[str]=...) -> None:
        ...

class JoinMeetingResponse(_message.Message):
    __slots__ = ('state', 'message', 'bot_id')

    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RECEIVED: _ClassVar[JoinMeetingResponse.State]
        PENDING: _ClassVar[JoinMeetingResponse.State]
        JOINED: _ClassVar[JoinMeetingResponse.State]
        FAILED: _ClassVar[JoinMeetingResponse.State]
    RECEIVED: JoinMeetingResponse.State
    PENDING: JoinMeetingResponse.State
    JOINED: JoinMeetingResponse.State
    FAILED: JoinMeetingResponse.State
    STATE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    BOT_ID_FIELD_NUMBER: _ClassVar[int]
    state: JoinMeetingResponse.State
    message: str
    bot_id: str

    def __init__(self, state: _Optional[_Union[JoinMeetingResponse.State, str]]=..., message: _Optional[str]=..., bot_id: _Optional[str]=...) -> None:
        ...

class MeetingDetailsRequest(_message.Message):
    __slots__ = ('bot_id', 'meepo_id')
    BOT_ID_FIELD_NUMBER: _ClassVar[int]
    MEEPO_ID_FIELD_NUMBER: _ClassVar[int]
    bot_id: str
    meepo_id: str

    def __init__(self, bot_id: _Optional[str]=..., meepo_id: _Optional[str]=...) -> None:
        ...

class MeetingDetailsResponse(_message.Message):
    __slots__ = ('participants',)
    PARTICIPANTS_FIELD_NUMBER: _ClassVar[int]
    participants: _containers.RepeatedCompositeFieldContainer[Participant]

    def __init__(self, participants: _Optional[_Iterable[_Union[Participant, _Mapping]]]=...) -> None:
        ...

class Participant(_message.Message):
    __slots__ = ('name',)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str

    def __init__(self, name: _Optional[str]=...) -> None:
        ...

class LeaveMeetingRequest(_message.Message):
    __slots__ = ('bot_id', 'meepo_id')
    BOT_ID_FIELD_NUMBER: _ClassVar[int]
    MEEPO_ID_FIELD_NUMBER: _ClassVar[int]
    bot_id: str
    meepo_id: str

    def __init__(self, bot_id: _Optional[str]=..., meepo_id: _Optional[str]=...) -> None:
        ...

class LeaveMeetingResponse(_message.Message):
    __slots__ = ('state', 'message')

    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RECEIVED: _ClassVar[LeaveMeetingResponse.State]
        DONE: _ClassVar[LeaveMeetingResponse.State]
        FAILED: _ClassVar[LeaveMeetingResponse.State]
    RECEIVED: LeaveMeetingResponse.State
    DONE: LeaveMeetingResponse.State
    FAILED: LeaveMeetingResponse.State
    STATE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    state: LeaveMeetingResponse.State
    message: str

    def __init__(self, state: _Optional[_Union[LeaveMeetingResponse.State, str]]=..., message: _Optional[str]=...) -> None:
        ...