# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: fb47064d-e0cd-45d2-b552-f92e803aae71
"""Authentication and related things.

"""

from persistent import Persistent

__metaclass__ = type

class PasswordReminders(Persistent):
    """The object that manages password reminders.

    Get hold of this object by using the zodb connection:

    >>> from canonical.zodb import zodbconnection
    >>> reminders = zodbconnection.passwordreminders
    """

