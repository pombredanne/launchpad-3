# Copyright 2007 Canonical Ltd.  All rights reserved.

# Pick up the standard Mailman defaults
from Mailman.Defaults import *

# Use a name for the site list that is very unlikely to conflict with any
# possible Launchpad team name.  The default is "mailman" and that doesn't cut
# it. :)  The site list is never used by Launchpad, but it's required by
# Mailman 2.1.
MAILMAN_SITE_LIST = 'unused_mailman_site_list'

# We don't need to coordinate aliases with a mail server because we'll be
# pulling incoming messages from a POP account.
MTA = None

# Turn off all archiving.
ARCHIVE_TO_MBOX = -1

# Disable runners for features we don't need.
QRUNNERS = [
##     ('ArchRunner',     1), # messages for the archiver
    ('BounceRunner',   1), # for processing the qfile/bounces directory
##     ('CommandRunner',  1), # commands and bounces from the outside world
##     ('IncomingRunner', 1), # posts from the outside world
##     ('NewsRunner',     1), # outgoing messages to the nntpd
    ('OutgoingRunner', 1), # outgoing messages to the smtpd
    ('VirginRunner',   1), # internally crafted (virgin birth) messages
    ('RetryRunner',    1), # retry temporarily failed deliveries
    # XXX BarryWarsaw 2007-03-29: not yet implemented.
    # Non-standard runners we've added.
##     ('POPRunner',      1), # POP new messages to us
    ('XMLRPCRunner',   1), # Poll for XMLRPC requests
    ]

# Other list defaults.
DEFAULT_GENERIC_NONMEMBER_ACTION = 3 # Discard
DEFAULT_SEND_REMINDERS = No
DEFAULT_SEND_WELCOME_MSG = Yes
DEFAULT_SEND_GOODBYE_MSG = No
DEFAULT_DIGESTABLE = No
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_DISABLE = No
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_REMOVAL = No
