# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A pipeline handler for holding list non-members postings for approval.
"""

import xmlrpclib

from email.Utils import formatdate, make_msgid

from Mailman import Errors
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog


def process(mlist, msg, msgdata):
    """Handle all list non-member postings.

    For Launchpad members who are not list-members, a previous handler will
    check their personal standing to see if they are allowed to post.  This
    handler takes care of all other cases and it overrides Mailman's standard
    Moderate handler.  It also knows how to hold messages in Launchpad's
    librarian.
    """
    # If the message is already approved, then this handler is done.
    if msgdata.get('approved'):
        return
    # If the sender is a member of the mailing list, then this handler is
    # done.  Note that we don't need to check the member's Moderate flag as
    # the original Mailman handler does, because for Launchpad, we know it
    # will always be unset.
    for sender in msg.get_senders():
        if mlist.isMember(sender):
            return
    # From here on out, we're dealing with senders who are not members of the
    # mailing list.  They are also not Launchpad members in good standing or
    # we'd have already approved the message.  So now the message must be held
    # in Launchpad for approval via the LP u/i.
    sender = msg.get_sender()
    # Hold the message in Mailman too so that it's easier to resubmit it after
    # approval via the LP u/i.  If the team administrator ends up rejecting
    # the message, it will also be easy to discard it on the Mailman side.
    # But this way, we don't have to reconstitute the message from the
    # librarian if it gets approved.   However, unlike the standard Moderate
    # handler, we don't craft all the notification messages about this hold.
    # We also need to keep track of the message-id (which better be unique)
    # because that's how we communicate about the message's status.
    request_id = mlist.HoldMessage(msg, 'Not subscribed', msgdata)
    # This is a hack because by default Mailman cannot look up held messages
    # by message-id.  This works because Mailman's persistency layer simply
    # pickles the MailList object, mostly without regard to a known schema.
    assert mlist.Locked(), (
        'Mailing list should be locked: %s', mlist.internal_name())
    holds = mlist.__dict__.setdefault('held_message_ids', {})
    message_id = msg.get('message-id')
    if message_id is None:
        msg['Message-ID'] = message_id = make_msgid()
    if message_id in holds:
        # No legitimate sender should ever give us a message with a duplicate
        # message id, so treat this as spam.
        syslog('vette',
               'Discarding duplicate held message-id: %s', message_id)
        raise Errors.DiscardMessage
    holds[message_id] = request_id
    # In addition to Message-ID, the librarian requires a Date header.
    if msg.get('date') is None:
        msg['Date'] = formatdate()
    # Store the message in the librarian.
    proxy = xmlrpclib.ServerProxy(mm_cfg.XMLRPC_URL)
    # This will fail if we can't talk to Launchpad.  That's okay though
    # because Mailman's IncomingRunner will re-queue the message and re-start
    # processing at this handler.
    proxy.holdMessage(mlist.internal_name(), msg.as_string())
    syslog('vette', 'Holding message for LP approval: %s', message_id)
    # Raise this exception, signaling to the incoming queue runner that it is
    # done processing this message, and should not send it through any further
    # handlers.
    raise Errors.HoldMessage
