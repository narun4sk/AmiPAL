AmiPAL
---

### Python Abstraction Layer for Asterisk manager interface

LICENSE: [BSD 3-Clause License](https://opensource.org/licenses/BSD-3-Clause)

---

Project has been started with an aim to simplify Asterisk debugging and learn more about it's internals.

*AmiPAL* consists of 3 fundamental components:

1. ***AmiReg*** - *Ami Event Registry*. This is parser object where actual `Python Abstraction` happens.
2. ***AmiCtl*** - *Ami Controller*. Provides utilities for connecting to the server, logging and doing things with Ami in general.
3. ***AmiCmd*** - *AMI Commands*. Provide a great deal of standard Ami commands, such as `SIPpeers`, `ShowDialPlan`, `Originate`, etc.

*Dependencies*:

- [gevent](http://www.gevent.org) - very fast, ultra light, async AmiPAL gearbox
- [kombu](http://kombu.readthedocs.org/en/latest) - chosen in favor of multiple backends support
- [rabbitmq](http://www.rabbitmq.com/getstarted.html) - used by default, but in orchestration with *kombu* can be replaced to one of the many other backends (eg. Redis)

*Quick Example*

    from AmiPAL.AmiCtl import AmiCtl
    
    class CustomCtl(AmiCtl):
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


If all went well, you should be seeing very similar output:


    ## ~4401~ Done setting up Control Logger.
    ## ~4401~ Configured log type: None
    ## ~4401~ Initialised control messaging queue "AMI_CTL".
    No handlers could be found for logger "AmiPAL"
    ## ~4401~ Connecting to Asterisk manager: 127.0.0.2:5038
    ## ~4401~ Connected.
    ## ~4401~ Spawned _soc_reader
    ## ~4401~ Spawned _soc_writer
    ## ~4401~ Spawned _ctl_dispatch
    
    Received new AMI Event:
    <class 'AmiPAL.AmiReg.AmiEvent'>
    OrderedDict([('Asterisk Call Manager/1.1', None), ('Response', 'Success'), ('ActionID', '2016-01-15T23:03:55.415517'), ('Message', 'Authentication accepted')])
    ({'Asterisk Call Manager/1.1': None}, {'Response': 'Success'}, {'ActionID': '2016-01-15T23:03:55.415517'}, {'Message': 'Authentication accepted'})
    (('Asterisk Call Manager/1.1', None), ('Response', 'Success'), ('ActionID', '2016-01-15T23:03:55.415517'), ('Message', 'Authentication accepted'))
    
    Received new AMI Event:
    <class 'AmiPAL.AmiReg.AmiEvent'>
    OrderedDict([('Event', 'FullyBooted'), ('Privilege', 'system,all'), ('Status', 'Fully Booted')])
    ({'Event': 'FullyBooted'}, {'Privilege': 'system,all'}, {'Status': 'Fully Booted'})
    (('Event', 'FullyBooted'), ('Privilege', 'system,all'), ('Status', 'Fully Booted'))
    ^CKeyboardInterrupt
    ## ~4401~ Killing I/O workers softly: 2016-01-15T23:03:58.399609
    ## ~4401~ Terminating connection: 127.0.0.2:5038


Have fun and make sure you report all bugs when discovered :-)
