#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
# AMI built-in Commands (Actions).

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

## Ami Controller
from AmiCtl import AmiCtl

# Main Ami event registry class
from AmiReg import AmiReg



class EventParser(AmiReg):
    """
    Customized Ami event registry.
    """
    def __init__(self, *a, **kw):
        super(EventParser, self).__init__(*a, **kw)

    def onEvent(self, event):
        if event.od.get('Event') not in ['VarSet','RTCPSent','RTCPReceived']:
            print "~ # ~"


class AmiCmd(AmiCtl):
    """
    AMI built-in Commands (Actions).
    """
    # Cache for commands that return list
    _cache = {}
    # List of Command IDs waiting for response
    _pending = set()
    # End event headers of the commands that return list
    _evend = {"RegistrationsComplete", "PeerlistComplete",
              "ParkedCallsComplete", "AgentsComplete",
              "StatusComplete", "ShowDialPlanComplete",
              "CoreShowChannelsComplete"}

    def __init__(self, **kwargs):
        super(AmiCmd, self).__init__(**kwargs)
        # Response timeout between retries
        self._sec_towait = 1
        self._re_timeout = .2
        # Stream to python object parser
        self.parser = AmiReg()


    def reactor(self, recv, *a, **kw):
        """
        React, when data is received.
        """
        cache = self._cache
        pending = self._pending
        evend = self._evend
        # Feed data to parser
        self.parser.feed(recv)
        for event in self.parser.events:
            # Event as OrderedDict
            od = event.od
            # Command ID
            cid = od.get("ActionID")

            if od.get("Event") in evend and cid in pending and cid in cache:
                for x in cache[cid]:
                    print x
                print
                del cache[cid]
                pending.discard(cid)
            elif cid in pending and cid in cache:
                cache[cid].append(event.od)
            elif od.get("Response")=="Success" and cid in pending and cid not in cache:
                for x in event.d:
                    print x
                print
                self._pending.discard(cid)


    def __query(self, action, required, optional, a, kw, evend=None):
        """
        Private helper method to handle multi-argument input.
        """
        args_ini = {k:"" for k in required + optional}
        # If there are required args and none are supplied via 'a' or 'kw'
        if required and not any([a, kw]):
            raise ValueError("Err :-: Please supply all required arguments: (%s)" % ', '.join(required))
        if self.soc.connected:
            if all([a,kw]): return  # disallow argument mixing
            # Positional arguments can only be used for the required args input if there are any
            if a and len(a) == len(required):
                args_ini.update({k: a[required.index(k)] for k in required})
            # Make sure that all required args are supplied via kw, if kw is the input method
            if kw and len(kw) >= len(required):
                keys = kw.keys()
                if required and not all([k in keys for k in required]):
                    raise ValueError("Err :-: Please supply all required arguments: (%s)" % ', '.join(required))
                args_ini.update({k: kw.get(k) for k in required + optional})
            # Extract final set of arguments
            args = {k:v for k,v in args_ini.items() if v}
            # Send command to AMI and capture request id
            req_id = self.cmd(action, **args)
            self._pending.add(req_id)
            return req_id


    def Ping(self, *a, **kw):
        """
        A 'Ping' action will ellicit a 'Pong' response.
        Used to keep the manager connection open.
        """
        action = "Ping"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            return req_id


    def ListCommands(self, *a, **kw):
        """
        Returns the action name and synopsis for every action that is
        available to the user.
        """
        action = "ListCommands"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            return req_id


    def SIPshowregistry(self, *a, **kw):
        """
        Show SIP registrations (text format).
        """
        action = "SIPshowregistry"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            self._cache[req_id] = []
            return req_id


    def SIPpeers(self, *a, **kw):
        """
        Lists SIP peers in text format with details on current status.
        """
        action = "SIPpeers"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            self._cache[req_id] = []
            return req_id


    def SIPshowpeer(self, *a, **kw):
        """
        Show one SIP peer with details on current status.
        Required args:
            - Peer: The peer name you want to check.
        """
        action = "SIPshowpeer"
        required = ["Peer"]
        optional = []
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def SIPqualifypeer(self, *a, **kw):
        """
        Qualify a SIP peer.
        # Required args:
            - Peer: The peer name you want to qualify.
        """
        action = "SIPqualifypeer"
        required = ["Peer"]
        optional = []
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def ShowDialPlan(self, *a, **kw):
        """
        Show dialplan contexts and extensions. Be aware that showing the full
        dialplan may take a lot of capacity.
        # Optional args:
            - Extension: Show a specific extension.
            - Context: Show a specific context.
        """
        action = "ShowDialPlan"
        required = []
        optional = ["Extension", "Context"]
        req_id = self.__query(action, required, optional, a=a, kw=kw, evend='ShowDialPlanComplete')
        self._cache[req_id] = []
        return req_id


    def Context(self, *a, **kw):
        """
        Custom method. List unique dialplan contexts.
        # Optional args:
            - Extension: Show a specific extension.
        """
        return sorted({x.od['Context'] for x in self.ShowDialPlan(*a, **kw) if x.od.get('Context')})


    def Originate(self, *a, **kw):
        """
        Generates an outgoing call to a <Extension>/<Context>/<Priority> or
        <Application>/<Data>.
        # Required args:
            - Channel: Channel name to call.

        # Optional args:
            - Exten: Extension to use (requires 'Context' and 'Priority')
            - Context: Context to use (requires 'Exten' and 'Priority')
            - Priority: Priority to use (requires 'Exten' and 'Context')
            - Application: Application to execute.
            - Data: Data to use (requires 'Application').
            - Timeout: How long to wait for call to be answered (in ms.).
            - CallerID: Caller ID to be set on the outgoing channel.
            - Variable: Channel variable to set, multiple Variable: headers are allowed.
            - Account: Account code.
            - Async: Set to 'true' for fast origination.
            - Codecs: Comma-separated list of codecs to use for this call.

        e.g. dict(Channel="SIP/965", Exten="965", Context="default",
                  Priority="1", CallerID="666", Timeout="10000", Async="Yes")
             dict(Channel="SIP/965", CallerID="666", Timeout="10000", Async="Yes")
        """
        action = "Originate"
        required = ["Channel"]
        optional = ["Exten", "Context", "Priority", "Application", "Data", "Timeout",
                    "CallerID", "Variable", "Account", "Async", "Codecs"]
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def Hangup(self, *a, **kw):
        """
        Hangup channel.
        # Required args:
            - Channel: Channel name to be hangup.

        # Optional args:
            - Cause: Numeric hangup cause.
        """
        action = "Hangup"
        required = ["Channel"]
        optional = ["Cause"]
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def Redirect(self, *a, **kw):
        """
        Redirect (transfer) a call.
        # Required args:
            - Channel: Channel to redirect.
            - Exten: Extension to transfer to.
            - Context: Context to transfer to.
            - Priority: Priority to transfer to.

        # Optional args:
            - ExtraChannel: Second call leg to transfer (optional).
            - ExtraExten: Extension to transfer extrachannel to (optional).
            - ExtraContext: Context to transfer extrachannel to (optional).
            - ExtraPriority: Priority to transfer extrachannel to (optional).
        """
        action = "Redirect"
        required = ["Channel", "Exten", "Context", "Priority"]
        optional = ["ExtraChannel", "ExtraExten", "ExtraContext", "ExtraPriority"]
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def Atxfer(self, *a, **kw):
        """
        Attended transfer.
        # Required args:
            - Channel: Transferer's channel.
            - Exten: Extension to transfer to.
            - Context: Context to transfer to.
            - Priority: Priority to transfer to.
        """
        action = "Atxfer"
        required = ["Channel", "Exten", "Context", "Priority"]
        optional = []
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def PlayDTMF(self, *a, **kw):
        """
        Play DTMF digit (signal) on a specific channel.
        # Required args:
            - Channel: Channel name to send digit to.
            - Digit: The DTMF digit to play.
        """
        action = "PlayDTMF"
        required = ["Channel", "Digit"]
        optional = []
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def Bridge(self, *a, **kw):
        """
        Bridge together two channels already in the PBX.
        # Required args:
            - Channel1: Channel to Bridge to Channel2.
            - Channel2: Channel to Bridge to Channel1.

        # Optional args:
            - Tone: Play courtesy tone to Channel2 (yes/no).
        """
        action = "Bridge"
        required = ["Channel1", "Channel2"]
        optional = ["Tone"]
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def Park(self, *a, **kw):
        """
        Park a channel.
        # Required args:
            - Channel: Channel name to park.
            - Channel2: Channel to return to if timeout.

        # Optional args:
            - Timeout: Number of milliseconds to wait before callback.
            - Parkinglot: Specify in which parking lot to park the channel.
        """
        action = "Park"
        required = ["Channel", "Channel2"]
        optional = ["Timeout", "Parkinglot"]
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def ParkedCalls(self, *a, **kw):
        """
        List parked calls.
        """
        action = "ParkedCalls"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            self._cache[req_id] = []
            return req_id


    def Queues(self, *a, **kw):
        """
        Show queues information. Check the log for the output
        """
        action = "Queues"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)


    def Agents(self, *a, **kw):
        """
        Will list info about all possible agents.
        """
        if self.soc.connected:
            action = "Agents"
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            self._cache[req_id] = []
            return req_id


    def CoreShowChannels(self, *a, **kw):
        """
        List currently defined channels and some information about them.
        """
        action = "CoreShowChannels"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            self._cache[req_id] = []
            return req_id


    def CoreStatus(self, *a, **kw):
        """
        Show PBX core status variables.
        """
        action = "CoreStatus"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            return req_id


    def CoreSettings(self, *a, **kw):
        """
        Show PBX core settings (version etc).
        """
        action = "CoreSettings"
        if self.soc.connected:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            self._pending.add(req_id)
            return req_id


    def Status(self, *a, **kw):
        """
        Will return the status information of each channel along with the
        value for the specified channel variables.
        # Optional args:
            - Channel: The name of the channel to query for status.
            - Variables: Comma ',' separated list of variable to include.
        """
        action = "Status"
        required = []
        optional = ["Channel", "Variables"]
        req_id = self.__query(action, required, optional, a=a, kw=kw, evend="StatusComplete")
        self._cache[req_id] = []
        return req_id


    def GetConfig(self, *a, **kw):
        """
        This action will dump the contents of a configuration file by category
        and contents or optionally by specified category only.
        # Required args:
            - Filename: Configuration filename (e.g. "foo.conf").

        # Optional args:
            - Category: Category in configuration file.
        """
        action = "GetConfig"
        required = ["Filename"]
        optional = ["Category"]
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id


    def GetConfigJSON(self, *a, **kw):
        """
        This action will dump the contents of a configuration file by category
        and contents in JSON format. This only makes sense to be used using rawman
        over the HTTP interface.
        # Required args:
            - Filename: Configuration filename (e.g. "foo.conf").
        """
        action = "GetConfigJSON"
        required = ["Filename"]
        optional = []
        req_id = self.__query(action, required, optional, a=a, kw=kw)
        return req_id



if __name__ == "__main__":
    host = "127.0.0.2"
    port = 5038
    usr = "ami"
    pwd = "QoDbwCYounN"

    acmd = AmiCmd(host=host, port=port, usr=usr, pwd=pwd)
    acmd.login()