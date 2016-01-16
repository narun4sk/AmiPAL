#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
# Ami Event Registry

## Part of the AmiPAL project ~:~ https://github.com/narunask/AmiPAL

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions
   and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of
   conditions and the following disclaimer in the documentation and/or other materials provided
   with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to
   endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Copyright (c) 2016 Narunas K. All rights reserved.
"""

from cStringIO import StringIO
from collections import Sequence
from collections import OrderedDict as od


class AmiLine(object):
    """
    Ami Line Object.
    """
    __slots__ = ("nl", "_line", "linet", "_fake")

    # New line terminator
    nl = "\r\n"

    def __init__(self, line_string):
        # Ensure input line is string
        self._line = str(line_string)
        # Convert line string into attribute, value tuple
        lt = tuple(x.strip() for x in self._line.split(':', 1))
        # Validate in case we received "nl" or incomplete attribute line
        if not any(lt):
            self.linet = None
        else: self.linet = lt

    @classmethod
    def fake(cls, val=None):
        """
        Create fake event line. Useful if you want to add event id or similar.
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
    def is_nl(self):
        """
        Return True if line is terminated correctly.
        """
        return self.s[-2:] == self.nl

    @property
    def s(self):
        """
        Original line in string format.
        """
        if hasattr(self, "_fake"):
            f = self._fake
            return str("{0}: {1}{2}".format(f[0], f[1], self.nl))
        return self._line

    @property
    def a(self):
        """
        Line attribute part.
        """
        if hasattr(self, "_fake"):
            return self._fake[0]
        try:
            return self.linet[0]
        except TypeError:
            return None

    @property
    def v(self):
        """
        Attribute's value part.
        """
        if hasattr(self, "_fake"):
            return self._fake[1]
        try:
            return self.linet[1]
        except (TypeError, IndexError):
            return None

    @property
    def t(self):
        """
        Line attribute, value tuple view.
        """
        if hasattr(self, "_fake"):
            return self._fake
        if self.linet and any(self.linet):
            return self.a, self.v
        return None

    @property
    def d(self):
        """
        Line dict view.
        """
        if hasattr(self, "_fake"):
            f = self._fake
            return {f[0]: f[1]}
        if self.linet and any(self.linet):
            return {self.a: self.v}
        return None


class AmiEvent(Sequence):
    """
    Ami Event Object.
    """
    __slots__ = ("_event", "_extra")

    def __init__(self, event=""):
        """
        Cast Ami event view to the list of tuples, list of dicts or the ordered dict.
        Must be initialised with the AmiLine instances sequence.
        """
        self._event = self.validate(event)

    @staticmethod
    def validate(val):
        if not isinstance(val, Sequence):
            raise ValueError("Supplied argument must be sequence.")
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

    ## - Custom methods - ##
    def __repr__(self):
        return str(self.t)

    @property
    def e(self):
        return self._event

    @property
    def t(self):
        """
        View Ami event as tuple of tuples.
        """
        event = self._event
        if hasattr(self, "_extra"):
            event += self._extra
        return tuple(line.t for line in event)

    @property
    def d(self):
        """
        View Ami event as tuple of dicts.
        """
        event = self._event
        if hasattr(self, "_extra"):
            event += self._extra
        return tuple(line.d for line in event)

    @property
    def od(self):
        """
        View Ami event as ordered dict (most useful).
        """
        event = self._event
        if hasattr(self, "_extra"):
            event += self._extra
        return od(line.t for line in event)

    @property
    def extra(self):
        """
        Append extra AmiLines.
        """
        if hasattr(self, "_extra"):
            return self._extra
        return None

    @extra.setter
    def set_extra(self, val=None):
        self._extra = self.validate(val)

    @extra.deleter
    def del_extra(self, val=None):
        if hasattr(self, "_extra"):
            delattr(self, "_extra")


class AmiStrm(object):
    """
    Ami Stream Object.
    """
    __slots__ = ("nl", "_stream", "_lines", "_lines_raw")

    # New line terminator
    nl = "\r\n"

    def __init__(self, stream="", tail=None):
        """
        Cast Ami text stream to the list of Python objects.
        """
        if stream == "":
            raise ValueError("stream argument cannot be empty!")
        if tail:
            self._stream = str(tail) + str(stream)
        else:
            self._stream = str(stream)

    @property
    def stream(self):
        """
        Return raw Ami text stream as it was provided.
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
        Return only full chunks (blocks of stream terminated by x2 nl).
        """
        tmp, chunks = [], []
        for line in self.lines:
            if line:
                # Cast lines to AmiLine objects
                tmp.append(AmiLine(line))
            else: # Event terminator was found (2x nl)
                if tmp: # If event was not empty
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
        Convert self.chunks to the generator of AmiEvent objects.
        """
        return ( AmiEvent(chunk) for chunk in self.chunks )


class AmiReg(object):
    """
    Ami Event Registry.
    """
    __slots__ = ("_tail", "_stream")

    def __init__(self):
        """
        Feed Ami text stream chunks to this object, override 'onEvent' method to attach a callback.
        """
        self._tail = None
        self._stream = None # Temporary AmiStrm container

    def onEvent(self, event):
        """
        Override this method to attach your callback. event = AmiEvent instance.
        """
        pass #print event.d

    def feed(self, stream=None, id=None):
        """
        Collect Ami stream and parse it.
        """
        if not stream or not isinstance(stream, str):
            raise ValueError("Input is expected to be non empty string.")
        if self._tail:
            self._stream = AmiStrm(stream=stream, tail=self._tail)
        else:
            self._stream = AmiStrm(stream=stream)
        # Update tail
        self._tail = self.str.tail
        # Call onEvent for each event in the stream
        for event in self.events:
            self.onEvent(event)

    @property
    def str(self):
        """
        Return latest AmiStrm object.
        """
        return self._stream

    @property
    def events(self):
        """
        Return parsed events generator in this stream chunk.
        """
        return self.str.events

    @property
    def tail(self):
        """
        Return tail of the latest AmiStrm Object if any.
        """
        return self._tail



if __name__ == "__main__":
    with open('big.log', 'r') as f:
    #with open('testing.log', 'r') as f:
        line_lst = f.readlines()
        line_str = ''.join( x for x in line_lst if x != '\n' )
        s1 = line_str[100:300]
        s2 = line_str[300:800]
        strm1 = AmiStrm(s1)
        strm2 = AmiStrm(s2)
        reg = AmiReg()
        reg.feed(line_str)
