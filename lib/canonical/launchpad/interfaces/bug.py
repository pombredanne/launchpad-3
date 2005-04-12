__metaclass__ = object

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema.interfaces import IText, ITextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.lp import dbschema
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.fields import Title, Summary


# CONTENT
class IBug(Interface):
    """The core bug entry."""

    id = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Nickname'), required=False,
            description=_("""A short and unique name for this bug. Very few
                bugs have a nickname, they are just bugs that are so
                significant that people will actually remember the
                name. Please don't set a nickname for the bug unless you
                are certain that this is the sort of bug that the entire
                community, upstream and all distro's, will phear."""),
            constraint=valid_name,
            )
    title = Title(
            title=_('Title'), required=True,
            description=_("""A one-line summary of the problem"""),
            )
    shortdesc = Summary(
            title=_('Summary'), required=False,
            description=_("""The bug summary is a single paragraph
            description that should capture the essence of the bug, where it
            has been observed, and what triggers it."""),
            )
    description = Text(
            title=_('Description'), required=False,
            description=_("""A detailed description of the problem,
            including the steps required to reproduce it""")
            )
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
    owner = Attribute("The owner's IPerson")
    duplicateof = Int(
            title=_('Duplicate Of'), required=False,
            )
    communityscore = Int(
            title=_('Community Score'), required=True, readonly=True,
            default=0,
            )
    communitytimestamp = Datetime(
            title=_('Community Timestamp'), required=True, readonly=True,
            #default=datetime.utcnow,
            )
    hits = Int(
            title=_('Hits'), required=True, readonly=True,
            default=0,
            )
    hitstimestamp = Datetime(
            title=_('Hits Timestamp'), required=True, readonly=True,
            #default=datetime.utcnow,
            )
    activityscore = Int(
            title=_('Activity Score'), required=True, readonly=True,
            default=0,
            )
    activitytimestamp = Datetime(
            title=_('Activity Timestamp'),
            required=True, readonly=True,
            #default=datetime.utcnow,
            )
    private = Bool(
            title=_("Should this bug be kept confidential?"), required=False,
            description=_(
                "Check this box if, for example, this bug exposes a security "
                "vulnerability. If selected, this bug will be visible only to "
                "its subscribers."),
            default=False)

    activity = Attribute('SQLObject.Multijoin of IBugActivity')
    messages = Attribute('SQLObject.RelatedJoin of IMessages')
    bugtasks = Attribute('SQLObject.Multijoin of IBugTask')
    productinfestations = Attribute('List of product release infestations.')
    packageinfestations = Attribute('List of package release infestations.')
    watches = Attribute('SQLObject.Multijoin of IBugWatch')
    externalrefs = Attribute('SQLObject.Multijoin of IBugExternalRef')
    cverefs = Attribute('CVE references for this bug')
    subscriptions = Attribute('SQLObject.Multijoin of IBugSubscription')

    def followup_title():
        """Return a candidate title for a followup message."""

    def subscribe(person, subscription):
        """Subscribe person to the bug, with the provided subscription type.

        Returns an IBugSubscription. Raises a ValueError if the person is
        already subscribed.
        """

    def unsubscribe(person):
        """Remove this person's subscription to this bug.

        Raises a ValueError if the person wasn't subscribed.
        """

    def isSubscribed(person):
        """Is person subscribed to this bug?

        Returns True if the user is explicitly subscribed to this bug
        (no matter what the type of subscription), otherwise False.
        """

    def notificationRecipientAddresses():
        """Return the list of email addresses that recieve notifications.
        """


class IBugDelta(Interface):
    """The quantitative change made to a bug that was edited."""

    bug = Attribute("The IBug, after it's been edited.")
    bugurl = Attribute("The absolute URL to the bug.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the bug itself
    title = Attribute("The new bug title or None.")
    shortdesc = Attribute("The new bug shortdesc or None.")
    description = Attribute("The new bug description or None.")
    private = Attribute("A hash with two keys, 'old' and 'new', or None.")
    name = Attribute("A hash with two keys, 'old' and 'new', or None.")

    # other things linked to the bug
    external_reference = Attribute(
        "An IBugExternalRef added to a bug, or None.")
    bugwatch = Attribute("An IBugWatch added to a bug, or None.")
    cveref = Attribute("An ICVERef added to a bug, or None.")
    bugtask_deltas = Attribute(
        "A tuple of IBugTaskDelta, one IBugTaskDelta or None.")


class IBugAddForm(IBug):
    """Information we need to create a bug"""
    id = Int(title=_("Bug #"), required=False)
    product = Choice(
            title=_("Product"), required=False,
            description=_("""The thing you found this bug in,
            which was installed by something other than apt-get, rpm,
            emerge or similar"""),
            vocabulary="Product")
    sourcepackagename = Choice(
            title=_("Source Package Name"), required=False,
            description=_("""The distribution package you found
            this bug in, which was installed via apt-get, rpm,
            emerge or similar."""),
            vocabulary="SourcePackageName")
    distribution = Choice(
            title=_("Linux Distribution"), required=False,
            description=_("""Debian, Redhat, Gentoo, etc."""),
            vocabulary="Distribution")
    binarypackage = Choice(
            title=_("Binary Package"), required=False,
            vocabulary="BinaryPackage")
    owner = Int(title=_("Owner"), required=True)
    comment = Text(title=_('Comment'), required=True,
            description=_("""A detailed description of the problem you are
            seeing."""))
    private = Bool(
            title=_("Should this bug be kept confidential?"), required=False,
            description=_(
                "Check this box if, for example, this bug exposes a security "
                "vulnerability. If you select this option, you must manually "
                "CC the people to whom this bug should be visible."),
            default=False)


# Interfaces for set
class IBugSet(IAddFormCustomization):
    """A set for bugs."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a Bug."""

    def __iter__():
        """Iterate through Bugs."""

    def get(bugid):
        """Get a specific bug by its ID."""
