# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A global pipeline handler for moderating Launchpad users.

The normal Mailman moderation handler isn't really sufficient to work with
Launchpad users.  We need to check things like personal standing in order to
determine whether non-members are allowed to post to a mailing list.
"""

import socket
import xmlrpclib

from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog


def process(mlist, msg, msgdata):
    """Check the standing of a non-Launchpad member.

    A message posted to a mailing list from a Launchpad member in good
    standing is allowed onto the list even if they are not members of the
    list.

    Because this handler comes before the standard Moderate handler, if the
    sender is not in good standing, we just defer to other decisions further
    along the pipeline.  If the sender is in good standing, we approve it.
    """
    sender = msg.get_sender()
    # Ask Launchpad about the standing of this member.
    in_good_standing = False
    proxy = xmlrpclib.ServerProxy(mm_cfg.XMLRPC_URL)
    try:
        # If an exception occurs here, say because we can't talk to Launchpad,
        # the message will end up in the normal moderation queue, held for
        # approval by the team owner.  This will be done by handlers further
        # along in the pipeline.
        in_good_standing = proxy.inGoodStanding(sender)
    except (xmlrpclib.ProtocolError, socket.error), error:
        syslog('xmlrpc', 'Cannot talk to Launchpad:\n%s', error)
    except xmlrpclib.Fault, error:
        syslog('xmlrpc', 'Launchpad exception: %s', error)
    # If the sender is a member in good standing, that's all we need to know
    # in order to let the message pass.
    if in_good_standing:
        msgdata['approved'] = True
