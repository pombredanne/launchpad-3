
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine

class IBugTrackerType(Interface):
    """A type of supported remote bug system, eg Bugzilla."""

    id = Int(title=_('ID'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    homepage = TextLine(title=_('Homepage'))
    owner = Int(title=_('Owner'))


class IBugTracker(Interface):
    """A remote a bug system."""

    id = Int(title=_('ID'))
    bugtrackertype = Int(title=_('Bug System Type'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    shortdesc = Text(title=_('Short Description'))
    baseurl = TextLine(title=_('Base URL'))
    owner = Int(title=_('Owner'))
    contactdetails = Text(title=_('Contact details'))
    watches = Attribute(_('The remote watches on this bug tracker.'))

    def watchcount():
        """Return the number of watches on this bugtracker."""


class IBugTrackerSet(Interface):
    """An interface for the BugTrackerSet. This models a set of BugTracker's
    (either the full set in the db or a subset). Each BugTracker is a
    distinct instance of a bug tracking tool. For example,
    bugzilla.mozilla.org is distinct from bugzilla.gnome.org.
    """

    def __getitem__(name):
        """Get a BugTracker by its name in the database. NB! We do not want to
        expose the BugTracker.id to the world so we use its name.
        """

    def __iter__():
        """Iterate through BugTrackers."""


