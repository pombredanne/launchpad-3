"""Project-related Interfaces for Launchpad

(c) Canonical Ltd 2004
"""

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IProjectBugTracker(Interface):
    id = Int(title=_('ID'))
    project = Int(title=_('Owner'))
    bugtracker = Int(title=_('Bug Tracker'))
    
