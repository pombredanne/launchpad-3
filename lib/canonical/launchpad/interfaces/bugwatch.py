# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug watch interfaces."""

__metaclass__ = type

__all__ = [
    'IBugWatch',
    'IBugWatchSet',
    ]

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int, TextLine

_ = MessageIDFactory('launchpad')

class IBugWatch(Interface):
    """A bug on a remote system."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    bugtracker = Choice(title=_('Bug System'), required=True,
        vocabulary='BugTracker', description=_("The bug tracker in which "
        "the remote bug is found. Choose from the list. You can register "
        "additional bug trackers from the Malone home page."))
    remotebug = TextLine(title=_('Remote Bug'), required=True,
        readonly=False, description=_("The bug number of this bug in the "
        "remote bug system. Please take care to enter it exactly."))
    remotestatus = TextLine(title=_('Remote Status'))
    lastchanged = Datetime(title=_('Last Changed'))
    lastchecked = Datetime(title=_('Last Checked'))
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True)
    owner = Int(title=_('Owner'), required=True, readonly=True)

    # useful joins
    bugtasks = Attribute('The tasks which this watch will affect. '
        'In Malone, a bug watch can be linked to one or more tasks, and '
        'if it is linked and we notice a status change in the watched '
        'bug then we will try to update the Malone bug task accordingly.')

    # properties
    needscheck = Attribute("A True or False indicator of whether or not "
        "this watch needs to be synchronised. The algorithm used considers "
        "the severity of the bug, as well as the activity on the bug, to "
        "ensure that we spend most effort on high priority and high "
        "activity bugs.")

    # required for launchpad pages
    title = Attribute('Bug watch title')

    url = Attribute('The URL at which to view the remote bug.')


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

    def search():
        """Search through all the IBugWatches in the system."""

    def fromText(text, bug, owner):
        """Create one or more BugWatch's by analysing the given text. This
        will look for reference to known or new bug tracking instances and
        create the relevant watches. It returns a (possibly empty) list of
        watches created.
        """

    def fromMessage(message, bug):
        """Create one or more BugWatch's by analysing the given email. The
        owner of the BugWatch's will be the sender of the message.
        It returns a (possibly empty) list of watches created.
        """

    def createBugWatch(bug, owner, bugtracker, remotebug):
        """Create an IBugWatch.

        :bug: The IBug to which the watch is linked.
        :owner: The IPerson who created the IBugWatch.
        :bugtracker: The external IBugTracker.
        :remotebug: A string.
        """
