# Copyright 2007 Canonical Ltd.  All rights reserved.

# Pick up the standard Mailman defaults
# pylint: disable-msg=W0401
from Mailman.Defaults import *

# Use a name for the site list that is very unlikely to conflict with any
# possible Launchpad team name.  The default is "mailman" and that doesn't cut
# it. :)  The site list is never used by Launchpad, but it's required by
# Mailman 2.1.
MAILMAN_SITE_LIST = 'unused_mailman_site_list'

# We don't need to coordinate aliases with a mail server because we'll be
# pulling incoming messages from a POP account.
MTA = None

# Disable runners for features we don't need.
QRUNNERS = [
    ('ArchRunner',     1), # messages for the archiver
    ('BounceRunner',   1), # for processing the qfile/bounces directory
##     ('CommandRunner',  1), # commands and bounces from the outside world
    ('IncomingRunner', 1), # posts from the outside world
##     ('NewsRunner',     1), # outgoing messages to the nntpd
    ('OutgoingRunner', 1), # outgoing messages to the smtpd
    ('VirginRunner',   1), # internally crafted (virgin birth) messages
    ('RetryRunner',    1), # retry temporarily failed deliveries
    # Non-standard runners we've added.
    ('XMLRPCRunner',   1), # Poll for XMLRPC requests
    ]

# Other list defaults.
# pylint: disable-msg=E0602
DEFAULT_GENERIC_NONMEMBER_ACTION = 3 # Discard
DEFAULT_SEND_REMINDERS = No
DEFAULT_SEND_WELCOME_MSG = Yes
DEFAULT_SEND_GOODBYE_MSG = No
DEFAULT_DIGESTABLE = No
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_DISABLE = No
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_REMOVAL = No
VERP_PERSONALIZED_DELIVERIES = Yes
DEFAULT_FORWARD_AUTO_DISCARDS = No

# Modify the global pipeline to add some handlers for Launchpad specific
# functionality.
# - ensure posters are Launchpad members.
GLOBAL_PIPELINE.insert(0, 'LaunchpadMember')
# - insert our own RFC 2369 and RFC 5064 headers; this must appear after
#   CookHeaders
index = GLOBAL_PIPELINE.index('CookHeaders')
GLOBAL_PIPELINE.insert(index + 1, 'LaunchpadHeaders')
# - Insert our own moderation handler just before the standard Mailman
#   handler.  We can still keep the latter, it just will not do anything
#   currently.
index = GLOBAL_PIPELINE.index('Moderate')
GLOBAL_PIPELINE.insert(index, 'LPModerate')
