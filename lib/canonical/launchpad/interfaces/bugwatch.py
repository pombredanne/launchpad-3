# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug watch interfaces."""

__metaclass__ = type

__all__ = [
    'BugWatchErrorType',
    'IBugWatch',
    'IBugWatchSet',
    'NoBugTrackerFound',
    'UnrecognizedBugTrackerURL',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int, TextLine, Text

from canonical.launchpad import _
from canonical.launchpad.fields import StrippedTextLine
from canonical.launchpad.interfaces import IHasBug
from canonical.lazr import (
    DBEnumeratedType, DBItem, use_template)

class BugWatchErrorType(DBEnumeratedType):
    """An enumeration of possible BugWatch errors."""

    BUGNOTFOUND = DBItem(1, """
        Bug Not Found

        Launchpad could not find the specified bug on the remote server.
        """)

    CONNECTIONERROR = DBItem(2, """
        Connection Error

        Launchpad was unable to connect to the remote server.
        """)

    INVALIDBUGID = DBItem(3, """
        Invalid Bug ID

        The specified bug ID is not valid.
        """)

    TIMEOUT = DBItem(4, """
        Timeout

        Launchpad encountered a timeout when trying to connect to the
        remote server and was unable to retrieve the bug's status.
        """)

    UNPARSABLEBUG = DBItem(5, """
        Unparsable Bug

        Launchpad could not extract a status from the data it received
        from the remote server.
        """)

    UNPARSABLEBUGTRACKER = DBItem(6, """
        Unparsable Bug Tracker Version

        Launchpad could not determine the version of the bug tracker 
        software running on the remote server.
        """)

    UNSUPPORTEDBUGTRACKER = DBItem(7, """
        Unsupported Bugtracker Version

        The remote server is using a version of its bug tracker software
        which Launchpad does not currently support.
        """)


class IBugWatch(IHasBug):
    """A bug on a remote system."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    bugtracker = Choice(title=_('Bug System'), required=True,
        vocabulary='BugTracker', description=_("You can register "
        "new bug trackers from the Launchpad Bugs home page."))
    remotebug = StrippedTextLine(title=_('Remote Bug'), required=True,
        readonly=False, description=_("The bug number of this bug in the "
        "remote bug tracker."))
    remotestatus = TextLine(title=_('Remote Status'))
    lastchanged = Datetime(title=_('Last Changed'))
    lastchecked = Datetime(title=_('Last Checked'))
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True)
    owner = Int(title=_('Owner'), required=True, readonly=True)
    lasterror = Choice(
        title=_('Last Error'),
        vocabulary="BugWatchErrorType")

    # useful joins
    bugtasks = Attribute('The tasks which this watch will affect. '
        'In Launchpad, a bug watch can be linked to one or more tasks, and '
        'if it is linked and we notice a status change in the watched '
        'bug then we will try to update the Launchpad bug task accordingly.')

    # properties
    needscheck = Attribute("A True or False indicator of whether or not "
        "this watch needs to be synchronised. The algorithm used considers "
        "the severity of the bug, as well as the activity on the bug, to "
        "ensure that we spend most effort on high-importance and "
        "high-activity bugs.")

    # required for launchpad pages
    title = Text(title=_('Bug watch title'), readonly=True)

    url = Text(title=_('The URL at which to view the remote bug.'), readonly=True)

    def updateStatus(remote_status, malone_status):
        """Update the status of the bug watch and any linked bug task.

        The lastchanged attribute gets set to the current time.
        """

    def destroySelf():
        """Delete this bug watch."""

    def getLastErrorMessage():
        """Return a string describing the contents of the lasterror field."""


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

        Raise a NotFoundError if there is no IBugWatch
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

    def extractBugTrackerAndBug(url):
        """Extract the bug tracker and the bug number for the given URL.

        A tuple in the form of (bugtracker, remotebug) is returned,
        where bugtracker is a registered IBugTracer, and remotebug is a
        text string.

        A NoBugTrackerFound exception is raised if the base URL can be
        extracted, but no such bug tracker is registered in Launchpad.

        If no bug tracker type can be guessed, None is returned.
        """


class NoBugTrackerFound(Exception):
    """No bug tracker with the base_url is registered in Launchpad."""

    def __init__(self, base_url, remote_bug, bugtracker_type):
        Exception.__init__(self, base_url, remote_bug, bugtracker_type)
        self.base_url = base_url
        self.remote_bug = remote_bug
        self.bugtracker_type = bugtracker_type


class UnrecognizedBugTrackerURL(Exception):
    """The given URL isn't used by any bug tracker we support."""
