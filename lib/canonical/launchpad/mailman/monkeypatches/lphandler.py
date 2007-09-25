# Copyright 2007 Canonical Ltd.  All rights reserved.

"""A global pipeline handler for determining Launchpad membership."""


import datetime
import xmlrpclib

from Mailman import Errors
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog

# Keep a cache of known Launchpad members.  Check back with Launchpad once per
# day per poster.
_CACHE = {}
_MEMBER = object()
_NOT_A_MEMBER = object()



def process(mlist, msg, msgdata):
    if msgdata.get('approved'):
        return
    # Ask Launchpad whether the sender is a Launchpad member.  If not, discard
    # the message with extreme prejudice, but log this.
    sender = msg.get_sender()
    # Is this sender information in the cache and has the cache entry expired?
    last_date, status = _CACHE.get(sender, (None, _NOT_A_MEMBER))
    if last_date is not None and last_date == datetime.date.today():
        # The cache entry is good, so discard the message if the status makes
        # the sender not a member.  Otherwise return, letting the rest of the
        # process continue.
        if status is _NOT_A_MEMBER:
            raise Errors.DiscardMessage
        return
    # The cache entry was missing or out of date, so check with Launchpad.
    proxy = xmlrpclib.ServerProxy(mm_cfg.XMLRPC_URL)
    try:
        if proxy.isLaunchpadMember(sender):
            status =_MEMBER
        else:
            status = _NOT_A_MEMBER
    except xmlrpclib.ProtocolError, error:
        syslog('xmlrpc', 'Cannot talk to Launchpad:\n%s', error)
        # If we can't talk to Launchpad, I believe it's better to let the
        # message get posted to the list than to discard or hold it.
        return
    _CACHE[sender] = (datetime.date.today(), status)
    if status is _MEMBER:
        return
    # IncomingRunner already posts the Message-ID to the logs/vette for
    # discarded messages.
    syslog('vette', 'Sender is not a Launchpad member: %s', sender)
    raise Errors.DiscardMessage
