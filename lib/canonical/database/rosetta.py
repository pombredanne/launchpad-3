# Copyright (c) 2004 Canonical Ltd
#
# Rosetta Database Access Classes
"""Rosetta Classes

These classes implement access to the Rosetta tables in the Launchpad
database. Rosetta is the Canonical Translation Portal, aimed at
making sure that every piece of open source software is translated
into every language.
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

