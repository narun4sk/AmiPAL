#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
At most times you perhaps want to use AmiCmd as besides all the
connection parameters it also includes standard AMI commands. 
"""
import sys; sys.path.append('../../')
from AmiPAL import *

# Connection parameters
host = "127.0.0.2"
port = 5038
usr = "ami"
pwd = "QoDbwCYounN"

# Log type=2 logs to both stderr and file
log_cfg = dict(type=2, path='./')

acmd = AmiCmd.AmiCmd(host=host, port=port, usr=usr, pwd=pwd, log_cfg=log_cfg)
acmd.login()

# By now you should have 'AmiPAL.log' created in your current dir

# Press CTRL+C to exit

