#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 11:22:18 2015

@author: Narunas K.

Part of the AmiPAL project :-: https://github.com/narunask/AmiPAL

LICENSE :-: BSD 3-Clause License :-: https://opensource.org/licenses/BSD-3-Clause
"""

import gevent, gipc, logging
from gevent import socket, sleep
from gevent import select
from datetime import datetime
from multiprocessing.managers import BaseManager

# Ami Event Registry
from AmiReg import AmiReg


class AmiCtl(object):
    """
    Ami Controller
    """

    def __init__(self, host="127.0.0.1", port=5038, usr="ami", pwd="secret"):
        """
        Base Class for connecting, logging in and sending commands to the AMI
        """
        self._nl = "\r\n"       # New line terminator
        self.host = str(host)
        self.port = int(port)
        self.usr = str(usr)
        self.pwd = str(pwd)
        self._soc = None
        self._poller = None
        self.timeout = .01      # Global timeout setting
        self.log_type = 1       # "raw_verbose"
        self.reg = self._reg    # Event Container


    def _id(self):
        """
        Use iso8601 datetime as internal ID
        """
        return datetime.now().isoformat()


    @property
    def _reg(self):
        """
        Proxy to event container.
        """
        exposed = ["by_attr", "by_evid", "by_value", "evid_sort", "drop", "drop_all", "sweep_le",
                   "elist", "put_str", "get_events"]
        BaseManager.register('reg', AmiReg, exposed=exposed)
        manager = BaseManager()
        manager.start()
        return manager.reg()


    def _connect(self):
        """
        Connect to the remote socket.
        """
        if not self._soc:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Claim the same port, don't wait
            soc.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Don't buffer, send straight away
            soc.setblocking(0)                                         # Don't block, return immediately
            err = soc.connect_ex((self.host, self.port))
            self._soc = soc


    def _close(self):
        """
        Close remote socket connection.
        """
        if self._soc:
            self._soc.shutdown(socket.SHUT_RDWR)
            self._soc.close()
            self._soc = None


    def _reader(self, soc=None, rPut=None):
        """
        Read from the socket and fill event container.
        """
        if not rPut:
            raise IOError("<_reader> Err: Broken pipe!")
        reg = self.reg
        with rPut:
            poller = select.poll()
            poller.register(soc, select.POLLIN)
            while True:
                sleep(self.timeout)
                r_ready = poller.poll(2)
                if r_ready:
                    recv = soc.recv(8192)
                    id = self._id()
                    msg = (id, recv)
                    rPut.put(msg)
                    reg.put_str(recv)
                    if not soc: break


    def _writer(self, soc=None, wGet=None):
        """
        Write to the socket.
        """
        if not wGet:
            raise IOError("<_writer> Err: Broken pipe!")
        with wGet:
            poller = select.poll()
            poller.register(soc, select.POLLOUT)
            while True:
                sleep(self.timeout)
                w_ready = poller.poll(2)
                msg = wGet.get()
                if w_ready:
                    print "## Sending:\n{}".format(msg)
                    soc.sendall(msg)
                    if not soc: break


    def _logger(self, rGet=None):
        """
        Check read queue and log responses.
        """
        if not rGet:
            raise IOError("<_logger> Err: Broken pipe!")
        # Init logging format and location
        if not isinstance(self.log_type, int) and not self.log_type:
            # Logging is turned off
            return
        elif self.log_type in (0, "raw"):
            log_name = "raw"
            self.__set_logger(name=log_name, file_name="ami_stream_{}.log".format(log_name))
            log = logging.getLogger(log_name)
            log_format = "{msg}"
        elif self.log_type in (1, "raw_verbose"):
            log_name = "raw_verbose"
            self.__set_logger(name=log_name, file_name="ami_stream_{}.log".format(log_name))
            log = logging.getLogger(log_name)
            log_format = "#### Received from AMI {bytes} bytes -- {id}:\n{msg}"
        elif self.log_type in (2, "print"):
            log_name = "print"
            self.__set_logger(name=log_name, file_name=None)
            log = logging.getLogger(log_name)
            log_format = "{msg}"
        elif self.log_type in (3, "print_verbose"):
            log_name = "print_verbose"
            self.__set_logger(name=log_name, file_name=None)
            log = logging.getLogger(log_name)
            log_format = "#### Received from AMI {bytes} bytes -- {id}:\n{msg}"
        else:
            log_name = "unknown_verbose"
            self.__set_logger(name=log_name, file_name=None)
            log = logging.getLogger(log_name)
            log_format = "#### Received from AMI {bytes} bytes -- {id}:\n{msg}"
        # Start logging
        with rGet:
            while True:
                sleep(self.timeout)
                msg = rGet.get()
                log.info(log_format.format(id=msg[0], msg=msg[1], bytes=str(len(msg[1]))))


    def __set_logger(self, name="raw", file_name="ami_stream.log", level=logging.INFO, format="%(message)s"):
        """
        Init logger settings.
        """
        log = logging.getLogger(name)
        log.setLevel(level)
        formatter = logging.Formatter(format)
        if file_name:
            fileHandler = logging.FileHandler(filename=file_name, mode="a", delay=0)
            fileHandler.setFormatter(formatter)
            log.addHandler(fileHandler)
        else:
            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(formatter)
            log.addHandler(streamHandler)


    @property
    def _pipes(self):
        """
        Get communication channels dict.
        """
        if not hasattr(self, "_pipes_dict"):
            self._pipes_dict = dict(zip(("rGet","rPut"), gipc.pipe()) +
                                    zip(("wGet","wPut"), gipc.pipe())
                                    )
        return self._pipes_dict


    @_pipes.deleter
    def _pipes(self):
        """
        Kill communication channels.
        """
        if hasattr(self, "_pipes_dict"):
            try:
                for p in getattr(self, "_pipes_dict").values():
                    if not p._closed:
                        p.close()
            except KeyboardInterrupt:
                pass
            finally:
                delattr(self, "_pipes_dict")


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
        id = self._id()     # Set Internal Command ID
        nl = self._nl       # Define new line terminator

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


    def _startIO(self, **kw):
        """
        Start I/O workers + logger.
        """
        soc = self._soc
        rPut = kw.get("rPut")
        wGet = kw.get("wGet")
        rGet = kw.get("rGet")
        try:
            r = gevent.spawn(self._reader, soc=soc, rPut=rPut)
            w = gevent.spawn(self._writer, soc=soc, wGet=wGet)
            l = gevent.spawn(self._logger, rGet=rGet)
            gevent.joinall([r, w, l])
        except KeyboardInterrupt:
            pass


    def cmd(self, action=None, **kw):
        """
        Send AMI command to the server.
        """
        id, command = self._command(action=action, **kw)
        if self._soc:
            wPut = self._pipes.get("wPut")
            wPut.put(command)
        else:
            raise IOError("<cmd> Err: Socket is dead!")
        return id


    def login(self):
        """
        Log in to the server.
        """
        # Reconnect on every attempt to login
        self.logoff()
        # Init pipes
        pipes = dict(rPut = self._pipes.get("rPut"),
                     wGet = self._pipes.get("wGet"),
                     rGet = self._pipes.get("rGet"),
                     )
        # Init socket
        self._connect()
        # Init login cmd keyword arguments
        action_kw = {"Username"    : "{usr}".format(usr=self.usr),
                     "Secret"      : "{pwd}".format(pwd=self.pwd),}
        # Send login command
        self.cmd("Login", **action_kw)
        # Start I/O workers + logger
        self._startIO_P = gipc.start_process(self._startIO, name="startIO_Process", kwargs=pipes)


    def logoff(self):
        """
        Log off from the server.
        """
        if self._soc:
            # Send logoff command
            self.cmd("Logoff")
            # Close connection
            self._close()
            # Terminate I/O proc
            if self._startIO_P:
                self._startIO_P.terminate()
                self._startIO_P.join()
            # Kill pipes
            del self._pipes


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 56002
    usr = "ami"
    pwd = "secret"

    actl = AmiCtl(host=host, port=port, usr=usr, pwd=pwd)
    actl.log_type = "raw_verbose"
    #actl.log_type = 3
    actl.login()
