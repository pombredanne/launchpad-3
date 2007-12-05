# Copyright 2007 Canonical Ltd.  All rights reserved.

"""A global pipeline handler for determining Launchpad membership."""


import socket
import datetime
import xmlrpclib

from Mailman import Errors
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog


def process(mlist, msg, msgdata):
    """Discard the message if it doesn't come from a Launchpad member."""
    if msgdata.get('approved'):
        return
    # Ask Launchpad whether the sender is a Launchpad member.  If not, discard
    # the message with extreme prejudice, but log this.
    sender = msg.get_sender()
    # Check with Launchpad about whether the sender is a member or not.  If we
    # can't talk to Launchpad, I believe it's better to let the message get
    # posted to the list than to discard or hold it.
    is_member = True
    proxy = xmlrpclib.ServerProxy(mm_cfg.XMLRPC_URL)
    try:
        is_member = proxy.isRegisteredInLaunchpad(sender)
    except (xmlrpclib.ProtocolError, socket.error), error:
        syslog('xmlrpc', 'Cannot talk to Launchpad:\n%s', error)
    except xmlrpclib.Fault, error:
        syslog('xmlrpc', 'Launchpad exception: %s', error)
    # This handler can just return if the sender is a member of Launchpad.
    if is_member:
        return
    # Some automated processes will also send messages to the mailing list.
    # For example, if the list is a contact address for a team and that team
    # is the contact address for a project's answer tracker, an automated
    # message will be sent from Launchpad.  Check for a header that indicates
    # this was a Launchpad generated message.
    if msg['x-generated-by'] == 'Launchpad (canonical.com)':
        # Since this message is coming from Launchpad, pre-approve it.  Yes,
        # this could be spoofed, but there's really no other way (currently)
        # to do it.
        msgdata['approved'] = True
        return
    # IncomingRunner already posts the Message-ID to the logs/vette for
    # discarded messages, so we only need to add a little more detail here.
    syslog('vette', 'Sender is not a Launchpad member: %s', sender)
    raise Errors.DiscardMessage
