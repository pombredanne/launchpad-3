# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C
"""Bug tables

"""

# Zope/Python standard libraries
from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('canonical')

# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
# TODO: Move this wrapper here
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import * # XXX STEVEA SUCKS

from canonical.launchpad.interfaces import * # XXX STEVEA SUCKS

from canonical.lp import dbschema
from canonical.launchpad.interfaces import IBug, IBugAttachment, IBugActivity, \
    IBugExternalRef, IBugMessage, IBugSubscription, IProductBugAssignment, \
    ISourcepackageBugAssignment, IBugSystemType, IBugWatch

def is_allowed_filename(value):
    if '/' in value: # Path seperator
        return False
    if '\\' in value: # Path seperator
        return False
    if '?' in value: # Wildcard
        return False
    if '*' in value: # Wildcard
        return False
    if ':' in value: # Mac Path seperator, DOS drive indicator
        return False
    return True

