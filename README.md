AmiPAL
---

### Python Abstraction Layer for Asterisk manager interface

LICENSE: [BSD 3-Clause License](https://opensource.org/licenses/BSD-3-Clause)

---

*AmiPAL* consists of 3 fundamental components:

1. ***AmiReg*** - *Ami Event Registry* wraps *Ami Stream*,  *Ami Event* and *Ami Line* objects.
2. ***AmiCtl*** - *Ami Controller* simplifies connecting the server, logging in/out and sending commands to Ami.
3. ***AmiCmd*** - *AMI built-in Commands* supports many standard Ami commands like SIPpeers, ShowDialPlan, Originate, etc.

Project has been started with an aim to simplify Asterisk debugging.   
Ami Events exposed via *AmiReg* are Python objects which can be presented as lists of tuples, ordered dicts or lists of dicts. Such objects can be searched via *AmiReg* methods *by_value* and *by_attr*.   
*AmiCmd* makes it really easy to interact with Ami through its standard commands, thus Originate calls, Hangup channels, preview Dialplans, list Peers and many more. It also provides some non standard functions to keep track of the started calls, ended and live calls.    
*AmiCtl* makes it simple to connect to Ami on the the server, login/logoff and log Ami responses, so you could forget about telnet, netcat or similar.

Try it and make sure you will report any bug when discovered :-)