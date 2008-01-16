# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A global pipeline handler for inserting Launchpad specific headers."""

from email.Utils import make_msgid
from string import Template

from Mailman import mm_cfg


def process(mlist, msg, msgdata):
    """Add RFC 2369 and RFC 5064 headers."""
    # Start by deleting any existing such headers in the message already.
    for header in ('list-id', 'list-help', 'list-post', 'list-archive',
                   'list-owner', 'list-subscribe', 'list-unsubscribe',
                   'archived-at'):
        del msg[header]
    # Calculate values used both in the RFC 2369 and 5064 headers, and in the
    # message footer decoration.
    list_name = mlist.internal_name()
    list_owner = Template(
        mm_cfg.LIST_OWNER_HEADER_TEMPLATE).safe_substitute(
        team_name=list_name)
    list_archive = Template(
        mm_cfg.LIST_ARCHIVE_HEADER_TEMPLATE).safe_substitute(
        team_name=list_name)
    list_post = mlist.GetListEmail()
    list_unsubscribe = mm_cfg.LIST_SUBSCRIPTION_HEADERS
    list_help = mm_cfg.LIST_HELP_HEADER
    # Add the RFC 2369 headers.
    msg['List-Id'] = '<%s.%s>' % (list_name, mlist.host_name)
    msg['List-Help'] = '<%s>' % list_help
    # We really don't want to have to VERP these headers in, so we use a
    # generic header that Launchpad will redirect to the user's actual page.
    # The subscribe and unsubscribe pages are the same.
    msg['List-Subscribe'] = list_unsubscribe
    msg['List-Unsubscribe'] = list_unsubscribe
    msg['List-Post'] = '<mailto:%s>' % list_post
    msg['List-Archive'] = '<%s>' % list_archive
    msg['List-Owner'] = '<%s>' % list_owner
    # Add the RFC 5064 header.  In order to do so, the message must have
    # exactly one Message-ID header.  If it has no such header, add one.  If
    # it has multiple such headers, keep only the first.
    message_ids = msg.get_all('message-id', [])
    if len(message_ids) == 0:
        msg['Message-ID'] = message_id = make_msgid()
    elif len(message_ids) == 1:
        message_id = message_ids[0]
    else:
        message_id = message_ids[0]
        del msg['message-id']
        msg['Message-ID'] = message_id
    # Set up message metadata for header/footer decoration interpolation in
    # the Decorate handler.
    msgdata['decoration-data'] = dict(
        list_owner=list_owner,
        list_post=list_post,
        list_unsubscribe=list_unsubscribe,
        list_help=list_help,
        )
