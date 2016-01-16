#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
In this example you will connect to the AMI control messaging exchange and execute
Ping command. Feel free to test other commands included in the AmiCmd package too.
- First start simple_loger.py
- Then run ping.py
- Check console window where you started simple_logger, it should have Pong response
  from the server 
Note: I use 'kombu' in this example, but please don't hesitate to use what you like,
for instance 'pika', if you are more proficient with it.
"""
from kombu.exceptions import socket as srv_idle
import kombu

name="AMI_CTL"
transport = 'pyamqp'
vhost = '/'
host = '127.0.0.1'
port = '5672'
usr = 'guest'
pwd = 'guest'
aid = "xQtvfosmBYg2w7YHCM0mm7NPfWigXbd7"

connection = kombu.Connection(transport=transport,
                              virtual_host=vhost,
                              hostname=host,
                              port=port,
                              userid=usr,
                              password=pwd,
                              )

channel = connection.channel()

exchange = kombu.Exchange(name=name,
                          type='topic',
                          channel=channel,
                          durable=True,
                          auto_delete=True,
                          delivery_mode='persistent'
                          )

exchange.declare(nowait=False)

producer = kombu.Producer(channel,
                          exchange=exchange,
                          routing_key=name,
                          auto_declare=False,
                          compression=False
                          )

def cmd(msg, *a, **kw):
    args = a if a else []
    kwargs = kw if kw else {}
    producer.publish(body={"aid":aid, "command":msg, "args":args, "kwargs":kwargs},
                     routing_key=name,
                     serializer='pickle',
                     delivery_mode='persistent',
                     retry=True
                     )
    try:    
        connection.drain_events(timeout=1)
    except srv_idle.timeout:
        pass

cmd("Ping")

connection.close()
