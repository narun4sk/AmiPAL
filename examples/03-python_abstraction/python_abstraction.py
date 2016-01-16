#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
As soon as AMI text protocol stream is fed to the parser it is converted
to the series of the AmiReg.AmiEvent instances. AmiEvent objects have handy
properties which may represent events as OrderedDict, list of dicts or tuples.
What you'll do with these python objects is only limited by your creativity :)
"""
import sys; sys.path.append('../../')
from AmiPAL import *

class CustomCtl(AmiCtl.AmiCtl):
    """
    Subclass AmiCtl or AmiCmd and override their reactor method
    to do something useful.
    """
    def __init__(self, *a, **kw):
        super(CustomCtl, self).__init__(*a, **kw)

    def reactor(self, recv):
        # Feed data to parser
        self.parser.feed(recv)
        for event in self.parser.events:
            if event.od.get('Event') not in ['VarSet','RTCPSent','RTCPReceived']:
                print
                print "Received new AMI Event:"
                print type(event)
                print event.od  # Event as OrderedDict
                print event.d   # Event as list of dicts
                print event.t   # Event as list of tuples

# Connection parameters
host = "127.0.0.2"
port = 5038
usr = "ami"
pwd = "QoDbwCYounN"

# Log type=None disables logging, only ctl messages will appear
log_cfg = dict(type=None)

actl = CustomCtl(host=host, port=port, usr=usr, pwd=pwd, log_cfg=log_cfg)
actl.login()

# Please see included 'console.txt'.
# Your mileage may vary but overall results should be similar.

# Press CTRL+C to exit
