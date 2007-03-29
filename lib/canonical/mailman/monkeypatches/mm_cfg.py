"""This module contains your site-specific settings.

From a brand new distribution it should be copied to mm_cfg.py.  If you
already have an mm_cfg.py, be careful to add in only the new settings you
want.  Mailman's installation procedure will never overwrite your mm_cfg.py
file.

The complete set of distributed defaults, with documentation, are in the file
Defaults.py.  In mm_cfg.py, override only those you want to change, after the

  from Defaults import *

line (see below).

Note that these are just default settings; many can be overridden via the
administrator and user interfaces on a per-list or per-user basis.

"""

###############################################
# Here's where we get the distributed defaults.

from Defaults import *

##################################################
# Put YOUR site-specific settings below this line.

# Our fake MTA module; no MTA integration necessary.
MTA = "noop"

# XXX BarryWarsaw: for now, turn off all archiving.
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
    # Non-standard runners we've added.  XXX BarryWarsaw: not yet implemented.
##     ('POPRunner',      1), # POP new messages to us
##     ('XMLRPCRunner',   1), # Poll for XMLRPC requests
    ]

DEFAULT_GENERIC_NONMEMBER_ACTION = 3 # Discard
DEFAULT_SEND_REMINDERS = No
DEFAULT_SEND_WELCOME_MSG = No
DEFAULT_SEND_GOODBYE_MSG = No
DEFAULT_DIGESTABLE = No
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_DISABLE = No
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_REMOVAL = No

##################################################
# Don't add anything else below here.  Run-time
# settings will be added automatically.

