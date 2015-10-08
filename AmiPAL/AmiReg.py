#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 11:22:18 2015

@author: Narunas K.

Part of the AmiPAL project :-: https://github.com/narunask/AmiPAL

LICENSE :-: BSD 3-Clause License :-: https://opensource.org/licenses/BSD-3-Clause
"""

import gc
from datetime import datetime
from cStringIO import StringIO
from collections import Sequence
from collections import OrderedDict as od
from collections import namedtuple as nt


class AmiLine(object):
    """
    Ami Line Object.
    """
    __slots__ = ("_nl", "_line", "_line_tuple", "_fake")
    def __init__(self, line_string):
        self._line = str(line_string)
        line_tuple = tuple(x.strip() for x in self._line.split(':', 1))
        # Validate in case we receive only "nl" or partial attribute line
        if not any(line_tuple):
            self._line_tuple = None
        else: self._line_tuple = line_tuple

    @classmethod
    def fake(cls, val=None):
        """
        Create fake event line.
        """
        self = cls.__new__(cls)
        if isinstance(val, (dict, od)):
            if len(val) != 1: ValueError("Supplied value must be a single key/value pair!")
            else: self._fake = val.items()[0]
        elif isinstance(val, (tuple, list)):
            if len(val) != 2: raise ValueError("Supplied value must be double tuple/list!")
            else: self._fake = val
        else:
            raise ValueError("Supplied value must be a single key/value dict or double tuple/list!")
        return self

    @property
    def nl(self):
        """
        New line terminator.
        """
        nl = "\r\n"
        if not hasattr(self, "_nl"):
            return nl
        elif not self._nl:
            return nl
        else:
            return self._nl

    @nl.setter
    def nl(self, val="\r\n"):
        self._nl = val

    @nl.deleter
    def nl(self):
        if hasattr(self, "_nl"):
            delattr(self, "_nl")

    @property
    def is_nl(self):
        """
        Return True if line is terminated correctly.
        """
        return self.s[-2:] == self.nl

    @property
    def s(self):
        """
        Original line string.
        """
        if hasattr(self, "_fake"):
            f = self._fake
            return str("%s: %s%s" % (f[0], f[1], self.nl))
        return self._line

    @property
    def a(self):
        """Attribute"""
        if hasattr(self, "_fake"):
            return self._fake[0]
        try:
            return self._line_tuple[0]
        except TypeError:
            return None

    @property
    def v(self):
        """Value"""
        if hasattr(self, "_fake"):
            return self._fake[1]
        try:
            return self._line_tuple[1]
        except (TypeError, IndexError):
            return None

    @property
    def t(self):
        """
        Tuple representation.
        """
        if hasattr(self, "_fake"):
            return self._fake
        if self._line_tuple and any(self._line_tuple):
            return self.a, self.v
        return None

    @property
    def d(self):
        """
        Dict representation.
        """
        if hasattr(self, "_fake"):
            f = self._fake
            return {f[0]: f[1]}
        if self._line_tuple and any(self._line_tuple):
            return {self.a: self.v}
        return None


class AmiEvent(Sequence):
    """
    Ami Event Object.
    """
    __slots__ = ("_event", "_extra")
    def __init__(self, event=""):
        self._event = self._validator(event)

    @staticmethod
    def _validator(val):
        if not val or not isinstance(val, (list, tuple)):
            raise ValueError("Supplied argument must be list or tuple!")
        if not all(map(lambda x: isinstance(x, AmiLine), val)):
            raise ValueError("All items from the iterable must be AmiLine instances!")
        return val

    # Required sequence methods
    def __getitem__(self, index):
        if hasattr(self, "_extra"):
            return (self._event + self._extra)[index]
        return self._event[index]

    def __len__(self):
        if hasattr(self, "_extra"):
            return len(self._event + self._extra)
        return len(self._event)

    # Custom methods
    def __repr__(self):
        """
        Represent Ami events as tuples.
        """
        return str(self.t)

    @property
    def t(self):
        """
        Tuple representation.
        """
        if hasattr(self, "_extra"):
            return tuple(line.t for line in (self._event + self._extra))
        return tuple(line.t for line in self._event)

    @property
    def d(self):
        """
        Dict representation.
        """
        if hasattr(self, "_extra"):
            return tuple(line.d for line in (self._event + self._extra))
        return tuple(line.d for line in self._event)

    @property
    def od(self):
        """
        Ordered Dict representation.
        """
        if hasattr(self, "_extra"):
            return od(line.t for line in (self._event + self._extra))
        return od(line.t for line in self._event)

    @property
    def extra(self):
        """
        Append extra AmiLines.
        """
        if hasattr(self, "_extra"):
            return self._extra
        return None

    @extra.setter
    def extra(self, val=None):
        self._extra = self._validator(val)

    @extra.deleter
    def extra(self, val=None):
        if hasattr(self, "_extra"):
            delattr(self, "_extra")


class AmiStrm(object):
    """
    Ami Stream Object.
    """
    __slots__ = ("nl", "_stream", "_lines", "_lines_raw")
    def __init__(self, stream="", tail=None):
        """
        Represent Ami text stream as list of Python objects.
        """
        self.nl = "\r\n"
        if stream == "":
            raise ValueError("stream argument cannot be empty!")
        if tail:
            self._stream = str(tail) + str(stream)
        else:
            self._stream = str(stream)

    @property
    def _id(self):
        """
        Use iso8601 datetime as internal ID.
        """
        return datetime.now().isoformat()

    @property
    def stream(self):
        """
        Return raw Ami stream we are currently working with.
        """
        if hasattr(self, "_stream"): return self._stream

    @property
    def lines(self):
        """
        Split Ami stream to the list of lines.
        """
        if hasattr(self, "_lines"): return self._lines
        self._lines = self._stream.splitlines()
        return self._lines

    @property
    def lines_raw(self):
        """
        Same as self.lines, but preserve new line terminator (nl).
        """
        if hasattr(self, "_lines_raw"): return self._lines_raw
        self._lines_raw = StringIO(self._stream).readlines()
        return self._lines_raw

    @property
    def chunks(self):
        """
        Split list of lines into chunks.
        Return only full chunks (blocks of stream terminated by x2 nl)
        """
        tmp, chunks = [], []
        for line in self.lines:
            if line:
                # Cast lines to AmiLine objects
                tmp.append(AmiLine(line))
            else:
                if tmp:
                    evid = AmiLine.fake({"areg_evid": self._id})
                    tmp.append(evid)
                    chunks.append(tuple(tmp))
                tmp = []
        return chunks

    @property
    def tail(self):
        """
        Determine if stream is a complete set of chunks.
        If not - last line will not be empty. We then return last (incomplete) chunk.
        Otherwise - return None.
        """
        nl = self.nl
        if not self.lines_raw[-1] == nl:
            chunk = []
            for line in reversed(self.lines_raw):
                if not line == nl:
                    chunk.append(line)
                else: break
            return ''.join(reversed(chunk))
        return None

    @property
    def events(self):
        """
        Convert self.chunks to the list of AmiEvent objects.
        """
        return [ AmiEvent(chunk) for chunk in self.chunks ]


class AmiReg(object):
    """
    Ami Event Registry (Container).
    """
    __slots__ = ("_id", "_id0", "_tail", "_stream", "_events", "_dt")
    def __init__(self):
        self._id = None
        self._id0 = None
        self._tail = None
        self._stream = None
        self._events = {e: [] for e in self.elist()}
        self._dt = nt("_dt", ["id", "data"], rename=True, verbose=False)


    @staticmethod
    def elist(e=None):
        """
        List of searchable events.
        """
        ami = ['AsteriskCallManager/1.1']
        ami_commands = ["WaitEvent", "QueueReset", "QueueReload", "QueueRule", "QueuePenalty",
        "QueueLog", "QueuePause", "QueueRemove", "QueueAdd", "QueueSummary", "QueueStatus",
        "Queues", "PCIMixMonitorMu", "MixMonitorMute", "VoicemailUsersL", "PlayDTMF", "MuteAudio",
        "MeetmeList", "MeetmeUnmute", "MeetmeMute", "IAXregistry", "IAXnetstats", "IAXpeerlist",
        "IAXpeers", "DAHDIRestart", "DAHDIShowChanne", "DAHDIDNDoff", "DAHDIDNDon", "DAHDIDialOffhoo",
        "DAHDIHangup", "DAHDITransfer", "AgentPause", "AgentLogoff", "Agents", "LocalOptimizeAw",
        "SIPnotify", "SIPshowregistry", "SIPqualifypeer", "SIPshowpeer", "SIPpeers", "AGI",
        "PCIUnpauseMonit", "PCIPauseMonitor", "UnpauseMonitor", "PauseMonitor", "ChangeMonitor",
        "StopMonitor", "Monitor", "DBDelTree", "DBDel", "DBPut", "DBGet", "Bridge", "Park",
        "ParkedCalls", "ShowDialPlan", "AOCMessage", "ModuleCheck", "ModuleLoad", "CoreShowChannel",
        "Reload", "CoreStatus", "CoreSettings", "UserEvent", "UpdateConfig", "SendText", "ListCommands",
        "MailboxCount", "MailboxStatus", "AbsoluteTimeout", "ExtensionState", "Command", "Originate",
        "Atxfer", "Redirect", "ListCategories", "CreateConfig", "Status", "GetConfigJSON", "GetConfig",
        "Getvar", "Setvar", "Ping", "Hangup", "Challenge", "Login", "Logoff", "Events", "DataGet"]
        common_events = ["Agentcallbacklogin", "Agentcallbacklogoff", "AgentCalled", "AgentComplete",
        "AgentConnect", "AgentDump", "Agentlogin", "Agentlogoff", "QueueMemberAdded", "QueueMemberPaused",
        "QueueMemberStatus", "Cdr", "Dial", "ExtensionStatus", "MusicOnHold", "Join", "Leave", "Link",
        "MeetmeJoin", "MeetmeLeave", "MeetmeStopTalking", "MeetmeTalking", "MessageWaiting",
        "Newcallerid", "Newchannel", "Newexten", "ParkedCall", "Rename", "SetCDRUserField", "Unlink",
        "UnParkedCall", "Alarm", "AlarmClear", "DNDState", "LogChannel", "PeerStatus", "Registry",
        "Shutdown", "VarSet"]
        custom_known = ["Newstate", "NewCallerid", "NewCallerid", "Newstate", "Newstate",
        "MonitorStart", "Newstate", "NewAccountCode", "RTCPReceived", "MonitorStop", "FullyBooted",
        "RTCPReceived", "RTCPReceived", "RTCPSent", "RTCPSent", "RTCPReceived", "RTCPReceived",
        "RTCPSent", "RTCPSent", "MonitorStop"]
        list_end = ["PeerlistComplete", "AgentsComplete"]
        areg_alien = ["areg_alien"]
        events = tuple(ami + sorted(ami_commands + common_events + custom_known + list_end) + areg_alien)
        if not e: return events
        return e in events

    @staticmethod
    def evid_sort(lst=None):
        """
        Sort by areg_evid field.
        """
        if not lst or not isinstance(lst, (list, tuple)):
            raise ValueError("Supplied argument must be list or tuple!")
        return sorted(lst, key=lambda x: x.od.get("areg_evid"))

    @property
    def id(self):
        """
        Use iso8601 datetime as internal ID.
        """
        return datetime.now().isoformat()

    def put_str(self, stream=None, id=None):
        """
        Collect Ami stream and parse it.
        """
        self._id0 = self._id              # Old id
        self._id = id if id else self.id  # New id
        if not stream or not isinstance(stream, str):
            raise ValueError("stream argument must be unempty string!")
        if self._tail:
            self._stream = AmiStrm(stream=stream, tail=self._tail)
        else:
            self._stream = AmiStrm(stream=stream)
        # Update tail
        self._tail = self._stream.tail
        # Now parse and store events
        self._put_events()

    @property
    def get_str(self):
        """
        Return latest AmiStrm Object.
        """
        dt = self._dt
        if self._stream: return dt(self._id, self._stream)
        return None

    @property
    def tail(self):
        """
        Return tail of the latest AmiStrm Object if any.
        """
        dt = self._dt
        if self._tail: return dt(self._id, self._tail)
        return None

    @property
    def _get_events(self):
        """
        Parse Ami events from the supplied Ami stream.
        """
        events = []
        id, data = self.get_str
        for event in data.events:
            evt = event.od.get("Event", None)
            if evt and self.elist(evt):
                k_line = AmiLine.fake({"areg_tag": "known"})
            else:
                k_line = AmiLine.fake({"areg_tag": "alien"})
            id_line = AmiLine.fake({"areg_id": id})
            event.extra = k_line, id_line
            events.append(event)
        return tuple(events)

    def _put_events(self):
        """
        Store Ami events in the buckets.
        """
        # If new id is the same as the old one - there's nothing to update
        if self._id0 == self._id:
            return None
        events = self._get_events
        for event in events:
            areg_tag = event.od.get("areg_tag")
            if areg_tag == "alien":
                self._events["areg_alien"].append(event)
            else:
                e = event.od.get("Event")
                self._events[e].append(event)
        # Update old id to prevent record doubling
        self._id0 = self._id

    @property
    def events(self):
        """
        Return not empty event buckets.
        """
        if self._events:
            return {k:v for k,v in self._events.iteritems() if v }
        return None

    def get_events(self):
        """
        Dummy method to be used in the AutoProxy object only.
        """
        return self.events

    def by_evid(self, evid=None, evt=None):
        """
        Find events by areg_evid, optionally search in the single evt group.
        """
        if not evid: return None
        if evt:
            if self.elist(evt):
                return tuple(event for event in self.events[evt] \
                                   if event.od.get('areg_evid') == evid)
        else:
            return tuple(event for egroup in self.events.values() \
                               for event in egroup if event.od.get('areg_evid') == evid)

    def sweep_le(self, evid=None, evt=None):
        """
        Remove events where areg_evid is less than evid,
        optionally search in the single evt group.
        """
        if not evid: return None
        if evt and self.elist(evt):
            for event in self.events[evt]:
                if event.od.get('areg_evid') < evid:
                    index = self.events[evt].index(event)
                    del self.events[evt][index]
        else:
            for egroup, events in self.events.iteritems():
                for event in events:
                    if event.od.get('areg_evid') < evid:
                        index = self.events[egroup].index(event)
                        del self.events[egroup][index]
        gc.collect() # collect garbage

    def drop_all(self, ex=None):
        """
        Drop all event groups excluding those in ex=[].
        """
        if ex and not isinstance(ex, (list, tuple)):
            raise ValueError("Supplied argument must be list or tuple!")
        if ex:
            groups = [x for x in self.events.keys() if x not in ex]
        else:
          groups = self.events.keys()
        for g in groups:
            self._events.update({g:[]})
        gc.collect() # collect garbage

    def drop(self, lst=None):
        """
        Drop only those event groups which are listed in the lst=[] (drop_all opposite).
        """
        if not lst or not isinstance(lst, (list, tuple)):
            raise ValueError("Supplied argument must be list or tuple!")
        keys = self.events.keys()
        groups = [x for x in lst if x in keys]
        for g in groups:
            self._events.update({g:[]})
        gc.collect() # collect garbage

    def by_value(self, val=None, evt=None, part=False):
        """
        Find events by attribute value, optionally search in the single evt group.
        When part=True, use partial match.
        """
        if not val: return None
        if evt and self.elist(evt):
            if part:
                return tuple(event for event in self.events[evt] \
                                   for e in event if all([e.v, val in e.v]))
            else:
                return tuple(event for event in self.events[evt] \
                                   for e in event if e.v == val)
        else:
            if part:
                return tuple(event for egroup in self.events.values() \
                                   for event in egroup for e in event if all([e.v, val in e.v]))
            else:
                return tuple(event for egroup in self.events.values() \
                                   for event in egroup for e in event if e.v == val)

    def by_attr(self, attr=None, evt=None, part=False):
        """
        Find events by attribute name, optionally search in the single evt group.
        When part=True, use partial match.
        """
        if not attr: return None
        if evt and self.elist(evt):
            if part:
                return tuple(event for event in self.events[evt] \
                                   for e in event if attr in e.a)
            else:
                return tuple(event for event in self.events[evt] \
                                   for e in event if e.a == attr)
        else:
            if part:
                return tuple(event for egroup in self.events.values() \
                                   for event in egroup for e in event if attr in e.a)
            else:
                return tuple(event for egroup in self.events.values() \
                                   for event in egroup for e in event if e.a == attr)


if __name__ == "__main__":
    #with open('big.log', 'r') as f:
    with open('testing.log', 'r') as f:
        line_lst = f.readlines()
        line_str = ''.join( x for x in line_lst if x != '\n' )
        s1 = line_str[100:300]
        s2 = line_str[300:800]
        strm1 = AmiStrm(s1)
        strm2 = AmiStrm(s2)
        reg = AmiReg()
        reg.put_str(line_str)
