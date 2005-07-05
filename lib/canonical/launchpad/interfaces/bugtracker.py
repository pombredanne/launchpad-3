
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine

class IBugTracker(Interface):
    """A remote a bug system."""

    id = Int(title=_('ID'))
    bugtrackertype = Int(title=_('Bug Tracker Type'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    summary = Text(title=_('Summary'))
    baseurl = TextLine(title=_('Base URL'))
    owner = Int(title=_('Owner'))
    contactdetails = Text(title=_('Contact details'))
    watches = Attribute(_('The remote watches on this bug tracker.'))

    # properties
    watchcount = Attribute("Return the number of watches on this "
        "bugtracker.")

    latestwatches = Attribute("Return the last 10 watches created.")

class IBugTrackerSet(Interface):
    """A set of IBugTracker's.

    Each BugTracker is a distinct instance of a bug tracking tool. For
    example, bugzilla.mozilla.org is distinct from bugzilla.gnome.org.
    """

    title = Attribute('Title')

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

    def normalise_baseurl(baseurl):
        """Turn https into http, so that we do not create multiple
        bugtrackers unnecessarily."""

