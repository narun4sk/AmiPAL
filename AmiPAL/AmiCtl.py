#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
# Ami Controller

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

from gevent import monkey; monkey.patch_all()
import gevent, logging
from gevent import socket, sleep
from gevent.queue import Queue

# Messaging
import kombu
from kombu.exceptions import socket as srv_idle

# Stdlib
from types import ListType, DictType, StringType
from datetime import datetime

# Main Ami event registry class
from AmiReg import AmiReg


LOG_NAME = "AmiPAL"
CTL_LOG = LOG_NAME + "-CTL"
CTL_ID = "xQtvfosmBYg2w7YHCM0mm7NPfWigXbd7"


class AmiCtl(object):
    """
    Ami Controller
    """
    nl = "\r\n"        # New line terminator
    timeout = .01      # Global timeout setting
    parser = AmiReg()
    log_cfg = dict(type=1, path="./")
    log, ctllog = [ None ] * 2
    _ctl_id = CTL_ID

    def __init__(self, usr="ami", pwd="secret", *a, **kw):
        """
        Base Class for connecting, logging in and sending commands to the AMI.
        """
        # Configure logger
        if kw.get("log_cfg"):
            self.log_cfg = kw.get("log_cfg")
        self._set_logging()
        # Asterisk manager username and password
        self.usr = str(usr)
        self.pwd = str(pwd)
        # Asterisk manager socket object
        host = kw.get("host") or "127.0.0.1"
        port = kw.get("port") or 5038
        buff = kw.get("buff") or 4096
        self.soc = AmiSocket(host=host, port=port, buff=buff)
        # Data channel queues
        self._outq = Queue()    # Write queue
        # Control messaging queue
        self._ctlq = CTLQueue('AMI_CTL', on_recv=[self._ctl_handler])
        # Authorized controller IDs
        self.ctl_id_list = { self._ctl_id }


    def reactor(self, recv):
        """
        React, when data is received
        """

    @property
    def _id(self):
        """
        Use iso8601 datetime as internal ID
        """
        return datetime.now().isoformat()


    def login(self):
        """
        Log in to the server.
        """
        # Reconnect on every attempt to login
        self.logoff()
        # Init socket
        self.soc.connect()
        # Init login cmd keyword arguments
        action_kw = {"Username"    : "{usr}".format(usr=self.usr),
                     "Secret"      : "{pwd}".format(pwd=self.pwd),}
        # Send login command
        self.cmd("Login", **action_kw)
        # Start I/O workers + logger
        self._startIO()


    def logoff(self):
        """
        Log off from the server.
        """
        if self.soc.connected:
            # Send logoff command
            self.cmd("Logoff")
            # Close connection
            self.soc.close()


    def _soc_reader(self, soc=None, rPut=None):
        """
        Read from the socket and push events to the reactor.
        """
        self.ctllog.critical("Spawned _soc_reader")
        while self.soc.connected:
            sleep(self.timeout)
            recv = self.soc.recv()
            self.reactor(recv[1])
            log_msg = "[ Received from AMI %4s bytes -- %s ]:\n%s"
            self.log.error(log_msg, recv[0], self._id, recv[1])
            if recv[0]==0: soc.close()


    def _soc_writer(self, soc=None):
        """
        Write to the socket.
        """
        self.ctllog.critical("Spawned _soc_writer")
        #if not self.connected: return
        while self.soc.connected:
            sleep(self.timeout)
            if not self._outq.empty():
                msg = self._outq.get_nowait()
                log_msg = "[ Sending to AMI %4s bytes -- %s ]:\n%s"
                self.log.error(log_msg, len(msg), self._id, msg)
                self.soc.send(msg)


    def _ctl_handler(self, body, message):
        """
        Route control messages.
        """
        self.ctllog.critical("Fired _ctl_handler")
        assert type(body) is DictType, "ctl_handler received message body which is not a DictType: %r" % body
        aid = body.get("aid")
        if aid not in self.ctl_id_list:
            log_msg = "Wrong aid -- [ %s ]"
            self.ctllog.critical(log_msg, aid)
            self.log.warning(log_msg, aid)
            return

        command = body.get("command")
        a = body.get("args", [])
        kw = body.get("kwargs", {})

        log_msg = "[aid: %s] - [cmd: %s] - [args: %s] - [kwargs: %s]"
        self.ctllog.critical(log_msg, aid, command, a, kw)
        self.log.warning(log_msg, aid, command, a, kw)

        assert type(command) is StringType, "ctl_handler received command name which is not a StringType: %r" % command
        assert type(a) is ListType, "ctl_handler received command args list which is not a ListType: %r" % a
        assert type(kw) is DictType, "ctl_handler received command keyword args dict which is not a DictType: %r" % kw
        if hasattr(self, command):
            getattr(self, command)(*a, **kw)


    def _ctl_dispatch(self):
        """
        Dispatch ctl commands.
        """
        self.ctllog.critical("Spawned _ctl_dispatch")
        while self.soc.connected:
            sleep(self.timeout)
            self._ctlq.drain()


    def _command(self, action=None, **kw):
        """
        Craft AMI command from user input
        Every AMI command consist of Action command and optional Arguments:
        - action = str
        - args = {}
        """
        if not action or not isinstance(action, str) :
            raise ValueError("<_build_command> Err: Action must be 'str' type")

        command = []
        id = self._id      # Set Internal Command ID
        nl = self.nl       # Define new line terminator

        # Deal with action arg
        command.append( "Action: {action}".format(action=action) )
        command.append( "ActionID: {id}".format(id=id))

        # Deal with optional keyword arguments
        if kw:
            for arg, value in kw.iteritems():
                command.append( "{arg}: {value}".format(arg=arg, value=value))

        # Double nl at the end is required to submit AMI command
        final_command = nl.join(command) + nl*2

        # Also return internal ID with the final command
        return (id, final_command)


    def cmd(self, action=None, **kw):
        """
        Send AMI command to the server.
        """
        id, command = self._command(action=action, **kw)
        if self.soc.connected:
            self._outq.put(command)
        else:
            raise IOError("<cmd> Err: Socket is dead!")
        return id


    def _startIO(self, *a, **kw):
        """Start I/O workers + logger"""
        try:
            r = gevent.spawn(self._soc_reader)
            w = gevent.spawn(self._soc_writer)
            ctl = gevent.spawn(self._ctl_dispatch)
            gevent.joinall([r, w, ctl])
        except KeyboardInterrupt:
            log_msg = "Killing I/O workers softly: %s"
            self.ctllog.critical(log_msg, self._id)
            self.log.warning(log_msg, self._id)
        except Exception as e:
            log_msg = "Something bad happened: %s\n%s"
            self.ctllog.critical(log_msg, self._id, e)
            self.log.warning(log_msg, self._id, e)
        finally:
            gevent.killall([r, w, ctl])
            self.logoff()


    def _set_logging(self):
        """
        Initialise loggers.
        """
        name = LOG_NAME
        log_type = self.log_cfg.get("type")
        path = self.log_cfg.get("path") or "./"

        # Destination to severity level map
        # Messages which are less severe than lvl will be ignored (CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET)
        lvl = dict(console=logging.ERROR, file=logging.WARNING, both=logging.INFO, ctl=logging.CRITICAL)

        log = logging.getLogger(name)
        ctllog = logging.getLogger(name + "-CTL")

        # The level set in the 'root' logger determines which severity of messages it will pass to its handlers.
        # The level set in each handler determines which messages that handler will send on.
        ctllog.setLevel(lvl["ctl"])
        log.setLevel(lvl["both"])

        # Control logger accept only critical level messages and is always set
        fmt = logging.Formatter("## ~%(process)d~ %(message)s")
        handler = logging.StreamHandler()
        handler.setLevel(lvl["ctl"])
        handler.setFormatter(fmt)
        ctllog.addHandler(handler)
        ctllog.critical("Done setting up Control Logger.")

        self.ctllog = ctllog
        self.log = log

        ctllog.critical("Configured log type: %s", log_type)

        def set_console():
            ctllog.critical("Spawned console logger")
            fmt = logging.Formatter("## ~%(process)d~ %(message)s")
            handler = logging.StreamHandler()
            handler.setLevel(lvl["console"])
            handler.setFormatter(fmt)
            log.addHandler(handler)
        def set_file():
            ctllog.critical("Spawned file logger")
            file_path = path + name + ".log"
            fmt = logging.Formatter("## ~%(process)d~ %(message)s")
            handler = logging.FileHandler(filename=file_path, mode="a", delay=0)
            handler.setLevel(lvl["file"])
            handler.setFormatter(fmt)
            log.addHandler(handler)

        if log_type in [0, "console"]:
            set_console()
        elif log_type in [1, "file"]:
            set_file()
        elif log_type in [2, "both"]:
            set_console()
            set_file()


class AmiSocket(object):
    """
    Base connection class.
    """
    soc = None
    soc_ERR = None
    connected = False


    def __init__(self, host="127.0.0.1", port=5038, buff=4096):
        self.host = str(host)
        self.port = int(port)
        self.buffer = int(buff)
        self.log = logging.getLogger(LOG_NAME)
        self.ctllog = logging.getLogger(CTL_LOG)


    def connect(self):
        """
        Connect to AMI socket.
        """
        if not self.connected:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Claim the same port, don't wait
            soc.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Don't buffer, send straight away
            try:
                #print "Connecting to Asterisk manager..."
                log_msg = "Connecting to Asterisk manager: %s:%s"
                self.ctllog.critical(log_msg, self.host, self.port)
                self.log.warning(log_msg, self.host, self.port)
                soc.connect((self.host, self.port))
            except Exception as e:
                #print "Socket connection failed.", e
                log_msg = "Connection failed:\n%s"
                self.ctllog.critical(log_msg, e)
                self.log.warning(log_msg, e)
                self.connected = False
                self.soc_ERR = e
            else:
                log_msg = "Connected."
                self.ctllog.critical(log_msg)
                self.log.warning(log_msg)
                self.connected = True
                self.soc = soc
        else:
            log_msg = "Already connected to %s:%s"
            self.ctllog.critical(log_msg)
            self.log.warning(log_msg)
            self.ctllog.critical(log_msg, self.host, self.port)


    def close(self):
        """
        Close AMI socket connection.
        """
        if self.connected:
            log_msg = "Terminating connection: %s:%s"
            self.ctllog.critical(log_msg, self.host, self.port)
            self.log.warning(log_msg, self.host, self.port)
            self.soc.shutdown(socket.SHUT_RDWR)
            self.soc.close()
            self.soc = None
            self.connected = False
        else:
            log_msg = "Already disconnected from %s:%s"
            self.ctllog.critical(log_msg, self.host, self.port)
            self.log.warning(log_msg, self.host, self.port)
            self.ctllog.critical(log_msg, self.host, self.port)


    def recv(self):
        if self.connected:
            recv = self.soc.recv(self.buffer)
            return len(recv), recv


    def send(self, msg):
        if self.connected:
            self.soc.sendall(msg)



class CTLQueue(object):
    """
    AMI control queue.
    """
    transport = "pyamqp"
    vhost = "/"
    host = "127.0.0.1"
    port = "5672"
    usr = "guest"
    pwd = "guest"
    _Connection = kombu.Connection
    _Exchange = kombu.Exchange
    _Queue = kombu.Queue
    _Producer = kombu.Producer
    _Consumer = kombu.Consumer

    aid = "xQtvfosmBYg2w7YHCM0mm7NPfWigXbd7"

    def __init__(self, name, on_recv=[lambda x:x], *a, **kw):
        """
        Message queue to send control commands to the AMI.
        Default transport is via RabbitMQ backend.
        """
        self.log = logging.getLogger(LOG_NAME)
        self.ctllog = logging.getLogger(CTL_LOG)
        self.queue_name = name
        connection = self._Connection(transport=self.transport,
                                      virtual_host=self.vhost,
                                      hostname=self.host,
                                      port=self.port,
                                      userid=self.usr,
                                      password=self.pwd,
                                      )
        self._connection = connection
        channel = connection.channel()
        self._channel = channel
        exchange = self._Exchange(name=name, type="topic", channel=channel, durable=True, auto_delete=True, delivery_mode="persistent")
        exchange.declare(nowait=False)
        self._exchange = exchange
        queue = self._Queue(name="", channel=channel, exchange=exchange, routing_key=name, durable=True, auto_delete=True, exclusive=False)
        queue.declare(nowait=False)
        self._queue = queue
        consumer = self._Consumer(channel=channel, queues=[queue], accept=["pickle", "json"], auto_declare=False, no_ack=True, callbacks=on_recv)
        consumer.consume()
        self._consumer = consumer
        producer = self._Producer(channel, exchange=exchange, routing_key=name, auto_declare=False, compression=False)
        self._producer = producer
        #log_msg = "\"%s\" - control message queue now is ready."
        log_msg = "Initialised control messaging queue \"%s\"."
        self.ctllog.critical(log_msg, name)
        self.log.warning(log_msg, name)


    def put(self, msg):
        """
        Place message to the control queue.
        """
        name = self.queue_name
        self._producer.publish(body=msg, routing_key=name, serializer='pickle', delivery_mode='persistent', retry=True)


    def drain(self, timeout=None):
        """
        Send and receive messages from the queue. This will also pass received messages to the registered callbacks.
        By default this is blocking operation, change timeout argument to change this behaviour.
        """
        try:
            self._connection.drain_events(timeout=timeout)
        except srv_idle.timeout:
            pass


    def close(self):
        self._connection.close()


    def tst(self, msg, *a, **kw):
        args = a if a else []
        kwargs = kw if kw else {}
        self.put({"aid":self.aid, "command":msg, "args":args, "kwargs":kwargs})
        self.drain(timeout=1)



if __name__ == "__main__":
    host = "127.0.0.2"
    port = 5038
    usr = "ami"
    pwd = "QoDbwCYounN"
    log_cfg = dict(type=2)
    actl = AmiCtl(host=host, port=port, usr=usr, pwd=pwd, log_cfg=log_cfg)
    actl.login()
