# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine

class IBugWatch(Interface):
    """A bug on a remote system."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    bugtracker = Choice(
        title=_('Bug System'), required=True, vocabulary='BugTracker')
    remotebug = TextLine(
        title=_('Remote Bug'), required=True, readonly=False)
    remotestatus = TextLine(title=_('Remote Status'))
    lastchanged = Datetime(title=_('Last Changed'))
    lastchecked = Datetime(title=_('Last Checked'))
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True)
    owner = Int(title=_('Owner'), required=True, readonly=True)

    # required for launchpad pages
    title = Attribute('Bug watch title')


class IBugWatchSet(Interface):
    """The set of IBugWatch's."""

    bug = Int(title=_("Bug id"), readonly=True)
    title = Attribute('Title')

    def __getitem__(key):
        """Get a BugWatch"""

    def __iter__():
        """Iterate through BugWatches for a given bug."""

    def get(id):
        """Get an IBugWatch by its ID.

        Raise a zope.exceptions.NotFoundError if there is no IBugWatch
        matching the given id.
        """
