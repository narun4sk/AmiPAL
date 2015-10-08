#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 15:01:27 2015

@author: Narunas K.

Part of the AmiPAL project :-: https://github.com/narunask/AmiPAL

LICENSE :-: BSD 3-Clause License :-: https://opensource.org/licenses/BSD-3-Clause
"""

import gevent
from operator import itemgetter as ig

## Ami Controller
from AmiCtl import AmiCtl


class AmiCmd(AmiCtl):
    """
    AMI built-in Commands (Actions).
    """
    def __init__(self, **kwargs):
        """Send various AMI queries"""
        super(AmiCmd, self).__init__(**kwargs)
        # Response timeout between retries
        self._sec_towait = 1
        self._re_timeout = .2

    def _response(self, id=None, evend=None, wait=None):
        """
        Wait for the Ami response sec_towait seconds, retrying every re_timeout seconds.
        """
        if not id:
            raise ValueError("<_response> Err: Id cannot be be blank")
        sec_towait = self._sec_towait
        re_timeout = self._re_timeout
        while True:
            reg = self.reg.by_value(str(id))
            # If we expect a list in the response - check if we've got full list
            if evend and len([item.d[0] for item in reg for i in item if any([i.a=="Response", i.v==evend])])==2:
                return reg
            # Else if there's a response return regardles if it's an error or a full response
            elif not evend and len([item.d[0] for item in reg for i in item if i.a=="Response"])==1:
                return reg
            else:
                if sec_towait >= 0:
                    gevent.sleep(re_timeout)
                else: break
            sec_towait -= re_timeout

    def scalls(self):
        """
        Find started calls. SubEvent: Begin
        """
        fi = lambda x: x[0] if len(x)!=0 else []  # First item otherwise empty list
        scalls = []
        for devent in self.reg.get_events().get('Dial',[]):
            if devent.od.get('SubEvent') == 'Begin':
                suniq = devent.od.get('UniqueID')
                duniq = devent.od.get('DestUniqueID')
                srcid = devent.od.get('CallerIDNum')
                dstid = devent.od.get('Dialstring')
                newch = fi(self.reg.by_value(suniq, evt="Newchannel"))
                srcex = newch.od.get('CallerIDNum') if newch else ""
                dstex = newch.od.get('Exten') if newch else ""
                scalls.append((suniq, duniq, srcid, dstid, srcex, dstex))
        return scalls

    def ecalls(self):
        """
        Find ended calls. SubEvent: End
        """
        return [(e.od.get('UniqueID'), e.od.get('DialStatus')) \
                for e in self.reg.get_events().get('Dial',[]) if e.od.get('SubEvent') == 'End']

    def secalls(self):
        """
        Find calls which have started and now are ended.
        """
        uniqid = ig(0)
        fi = lambda x: x[0] if len(x)!=0 else []  # First item otherwise empty list
        scalls = self.scalls()
        ecalls = self.ecalls()
        sc = map(uniqid, scalls)
        ec = map(uniqid, ecalls)
        se = [x for x in sc if x in ec]
        #return [set(fi([sx for sx in scalls if uniqid(sx)==x]) + fi([ex for ex in ecalls if uniqid(ex)==x])) for x in se]
        #sc[0] + tuple(x for x in ec[0] if x not in sc[0])
        secalls = []
        for x in se:
            fsx = fi([sx for sx in scalls if uniqid(sx)==x])
            fex = fi([ex for ex in ecalls if uniqid(ex)==x])
            secalls.append(fsx + tuple([i for i in fex if i not in fsx]))
        return secalls

    def lcalls(self):
        """
        Find live calls. Started but yet not ended.
        """
        uniqid = ig(0)
        scalls = self.scalls()
        ecalls = self.ecalls()
        sc = map(uniqid, scalls)
        ec = map(uniqid, ecalls)
        lc = [x for x in sc if x not in ec]
        return [ s for l in lc for s in scalls if uniqid(s)==l]

    @staticmethod
    def evid_sort(lst=None):
        """
        Sort by areg_evid field.
        """
        if not lst or not isinstance(lst, (list, tuple)):
            raise ValueError("Supplied argument must be list or tuple!")
        return sorted(lst, key=lambda x: x.od.get("areg_evid"))

    def __query(self, action, required, optional, a, kw, evend=None):
        """
        Private helper method to handle multi-argument input.
        """
        args_ini = {k:"" for k in required + optional}
        # If there are required args and none are supplied via 'a' or 'kw'
        if required and not any([a, kw]):
            raise ValueError("Err :-: Please supply all required arguments: (%s)" % ', '.join(required))
        if self._soc:
            if all([a,kw]): return  # disallow argument mixing
            # Positional arguments can only be used for the required args input if any
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
            return self._response(req_id, evend)

    def Ping(self):
        """
        A 'Ping' action will ellicit a 'Pong' response.
        Used to keep the manager connection open.
        """
        action = "Ping"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            return self._response(req_id)

    def ListCommands(self):
        """
        Returns the action name and synopsis for every action that is
        available to the user.
        """
        action = "ListCommands"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response = self._response(req_id)
            return self.evid_sort(response)

    def SIPshowregistry(self):
        """
        Show SIP registrations (text format).
        """
        action = "SIPshowregistry"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response = self._response(req_id, evend="RegistrationsComplete")
            return self.evid_sort(response)

    def SIPpeers(self):
        """
        Lists SIP peers in text format with details on current status.
        """
        action = "SIPpeers"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response = self._response(req_id, evend="PeerlistComplete")
            return self.evid_sort(response)

    def SIPshowpeer(self, *a, **kw):
        """
        Show one SIP peer with details on current status.
        Required args:
            - Peer: The peer name you want to check.
        """
        action = "SIPshowpeer"
        required = ["Peer"]
        optional = []
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)


    def SIPqualifypeer(self, *a, **kw):
        """
        Qualify a SIP peer.
        # Required args:
            - Peer: The peer name you want to qualify.
        """
        action = "SIPqualifypeer"
        required = ["Peer"]
        optional = []
        response = self.__query(action, required, optional, a=a, kw=kw)
        return response

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
        response = self.__query(action, required, optional, a=a, kw=kw, evend='ShowDialPlanComplete')
        return self.evid_sort(response)


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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return response

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)

    def ParkedCalls(self):
        """
        List parked calls.
        """
        action = "ParkedCalls"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response = self._response(req_id, evend="ParkedCallsComplete")
            return self.evid_sort(response)

    def Queues(self):
        """
        Show queues information. Check the log for the output
        """
        action = "Queues"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)

    def Agents(self):
        """
        Will list info about all possible agents.
        """
        if self._soc:
            action = "Agents"
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response =  self._response(req_id, evend="AgentsComplete")
            return self.evid_sort(response)

    def CoreShowChannels(self):
        """
        List currently defined channels and some information about them.
        """
        action = "CoreShowChannels"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response = self._response(req_id, evend='CoreShowChannelsComplete')
            return self.evid_sort(response)

    def CoreStatus(self):
        """
        Show PBX core status variables.
        """
        action = "CoreStatus"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response = self._response(req_id)
            return self.evid_sort(response)

    def CoreSettings(self):
        """
        Show PBX core settings (version etc).
        """
        action = "CoreSettings"
        if self._soc:
            # Send command to AMI and capture request id
            req_id = self.cmd(action)
            response =  self._response(req_id)
            return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw, evend="StatusComplete")
        return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)

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
        response = self.__query(action, required, optional, a=a, kw=kw)
        return self.evid_sort(response)



if __name__ == "__main__":
    host = "127.0.0.1"
    port = 56002
    usr = "ami"
    pwd = "secret"

    acmd = AmiCmd(host=host, port=port, usr=usr, pwd=pwd)
    acmd.login()
    acmd.SIPpeers()
