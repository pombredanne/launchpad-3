
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine

class IBugWatch(Interface):
    """A bug on a remote system."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    bugtracker = Choice(title=_('Bug System'), required=True,
            vocabulary='BugTracker')
    remotebug = TextLine(title=_('Remote Bug'), required=True, readonly=False)
    # TODO: default should be NULL, but column is NOT NULL
    remotestatus = TextLine(
            title=_('Remote Status'), required=True, readonly=True, default=u''
            )
    lastchanged = Datetime(
            title=_('Last Changed'), required=True, readonly=True
            )
    lastchecked = Datetime(
            title=_('Last Checked'), required=True, readonly=True
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True
            )
    owner = Int(
            title=_('Owner'), required=True, readonly=True
            )


class IBugWatchSet(Interface):
    """A set for IBugWatch objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugWatch"""

    def __iter__():
        """Iterate through BugWatches for a given bug."""


