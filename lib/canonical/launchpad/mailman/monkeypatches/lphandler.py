# Copyright 2007 Canonical Ltd.  All rights reserved.

"""A global pipeline handler for determining Launchpad membership."""


import xmlrpclib

from Mailman import Errors
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog



def process(mlist, msg, msgdata):
    if msgdata.get('approved'):
        return
    # Ask Launchpad whether the sender is a Launchpad member.  If not, discard
    # the message with extreme prejudice, but log this.
    proxy = xmlrpclib.ServerProxy(mm_cfg.XMLRPC_URL)
    sender = msg.get_sender()
    try:
        is_member = proxy.isLaunchpadMember(sender)
    except xmlrpclib.ProtocolError, error:
        syslog('xmlrpc', 'Cannot talk to Launchpad:\n%s', error)
        # If we can't talk to Launchpad, I believe it's better to let the
        # message get posted to the list than to discard or hold it.
        return
    if is_member:
        return
    # IncomingRunner already posts the Message-ID to the logs/vette for
    # discarded messages.
    syslog('vette', 'Sender is not a Launchpad member: %s', sender)
    raise Errors.DiscardMessage
