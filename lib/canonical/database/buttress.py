# Copyright (c) 2004 Canonical Ltd
#
# Buttress Database Access Classes
"""Buttress Classes

These classes implement access to the Buttress tables in the Launchpad
database. Buttress is our Arch Repository Management infrastructure,
that coordinates and manages tens of thousands of branches in thousands
of Arch archives.
"""


# Zope/Python standard libraries
from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements, Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('canonical')

# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema import Password, Bool

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
# TODO: Move this wrapper here
from canonical.database.sqlbase import SQLBase, quote

