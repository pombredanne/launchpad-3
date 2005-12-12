# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug tracker interfaces."""

__metaclass__ = type

__all__ = [
    'IBugTracker',
    'IBugTrackerSet',
    ]

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Int, Text, TextLine, Choice

from canonical.lp import dbschema

_ = MessageIDFactory('launchpad')

class IBugTracker(Interface):
    """A remote a bug system."""

    id = Int(title=_('ID'))
    bugtrackertype = Choice(
        title=_('Bug Tracker Type'),
        vocabulary="BugTrackerType",
        default=dbschema.BugTrackerType.BUGZILLA)
    name = TextLine(
        title=_('Name'),
        description=_('An URL-friendly name for the bug tracker, '
        'such as "mozilla-bugs".'))
    title = TextLine(
        title=_('Title'),
        description=_('A descriptive label for this tracker to show in listings.'))
    summary = Text(
        title=_('Summary'),
        description=_('A brief introduction or overview of this bug tracker instance.'))
    baseurl = TextLine(
        title=_('Base URL'),
        description=_('The top-level URL for the bug tracker. This '
        'must be accurate so that Malone can link to external bug reports.'))
    owner = Int(title=_('Owner'))
    contactdetails = Text(
        title=_('Contact details'),
        description=_(
            'The contact details for the external bug tracker (so that, for '
            'example, its administrators can be contacted about a security '
            'breach).'))
    watches = Attribute('The remote watches on this bug tracker.')
    projects = Attribute("The projects which use this bug tracker.")

    latestwatches = Attribute("Return the last 10 watches created.")


class IBugTrackerSet(Interface):
    """A set of IBugTracker's.

    Each BugTracker is a distinct instance of a bug tracking tool. For
    example, bugzilla.mozilla.org is distinct from bugzilla.gnome.org.
    """

    title = Attribute('Title')

    bugtracker_count = Attribute("The number of registered bug trackers.")

    def __getitem__(name):
        """Get a BugTracker by its name in the database.

        Note: We do not want to expose the BugTracker.id to the world
        so we use its name.
        """

    def __iter__():
        """Iterate through BugTrackers."""

    def queryByBaseURL(baseurl):
        """Return one or None BugTracker's by baseurl"""

    def ensureBugTracker(baseurl, owner, bugtrackertype,
        title=None, summary=None, contactdetails=None, name=None):
        """Make sure that there is a bugtracker for the given base url, and
        if not, then create one using the given attributes.
        """

    def search():
        """Search all the IBugTrackers in the system."""

    def normalise_baseurl(baseurl):
        """Turn https into http, so that we do not create multiple
        bugtrackers unnecessarily."""


