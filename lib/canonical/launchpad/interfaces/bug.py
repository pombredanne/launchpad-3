# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces related to bugs."""

__metaclass__ = type

__all__ = [
    'BugCreationConstraintsError',
    'IBug',
    'IBugSet',
    'IBugDelta',
    'IBugAddForm',
    'IBugTarget',
    'BugDistroReleaseTargetDetails']

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.interfaces import (
    non_duplicate_bug, IMessageTarget)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.fields import Title, Summary

_ = MessageIDFactory('launchpad')

class BugCreationConstraintsError(Exception):
    """Raised when a bug is created with not all constraints satisfied.

    Currently the only constraint is that it should have at least one
    bug task.
    """


class IBug(Interface, IMessageTarget):
    """The core bug entry."""

    id = Int(
        title=_('Bug ID'), required=True, readonly=True)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    name = TextLine(
        title=_('Nickname'), required=False,
        description=_("""A short and unique name for this bug.
        Add a nickname only if you often need to retype the URL
        but have trouble remembering the bug number."""),
        constraint=name_validator)
    title = Title(
        title=_('Title'), required=True,
        description=_("""A one-line summary of the problem."""))
    summary = Summary(
        title=_('Summary'), required=False,
        description=_("""A single paragraph
        description that should capture the essence of the bug, where it
        has been observed, and what triggers it."""))
    description = Text(
        title=_('Description'), required=True,
        description=_("""A detailed description of the problem,
        including the steps required to reproduce it."""))
    ownerID = Int(title=_('Owner'), required=True, readonly=True)
    owner = Attribute("The owner's IPerson")
    duplicateof = Int(
        title=_('Duplicate Of'), required=False, constraint=non_duplicate_bug)
    communityscore = Int(
        title=_('Community Score'), required=True, readonly=True, default=0)
    communitytimestamp = Datetime(
        title=_('Community Timestamp'), required=True, readonly=True)
    hits = Int(
        title=_('Hits'), required=True, readonly=True, default=0)
    hitstimestamp = Datetime(
        title=_('Hits Timestamp'), required=True, readonly=True)
    activityscore = Int(
        title=_('Activity Score'), required=True, readonly=True,
        default=0)
    activitytimestamp = Datetime(
        title=_('Activity Timestamp'), required=True, readonly=True)
    private = Bool(
        title=_("Keep bug confidential"), required=False,
        description=_(
        "Select this option if, for instance, this bug exposes a "
        "security vulnerability. Before you set this, make sure you "
        "have subscribed anyone who needs to see this bug."),
        default=False)

    displayname = TextLine(title=_("Text of the form 'Bug #X"),
        readonly=True)
    activity = Attribute('SQLObject.Multijoin of IBugActivity')
    initial_message = Attribute(
        "The message that was specified when creating the bug")
    bugtasks = Attribute('BugTasks on this bug, sorted upstream, then '
        'ubuntu, then other distroreleases.')
    productinfestations = Attribute('List of product release infestations.')
    packageinfestations = Attribute('List of package release infestations.')
    watches = Attribute('SQLObject.Multijoin of IBugWatch')
    externalrefs = Attribute('SQLObject.Multijoin of IBugExternalRef')
    cves = Attribute('CVE entries related to this bug.')
    cve_links = Attribute('LInks between this bug and CVE entries.')
    subscriptions = Attribute('SQLObject.Multijoin of IBugSubscription')
    duplicates = Attribute(
        'MultiJoin of the bugs which are dups of this one')
    attachments = Attribute("List of bug attachments.")
    tickets = Attribute("List of support tickets related to this bug.")
    specifications = Attribute("List of related specifications.")

    def followup_subject():
        """Return a candidate subject for a followup message."""

    # subscription-related methods
    def subscribe(person):
        """Subscribe person to the bug. Returns an IBugSubscription."""

    def unsubscribe(person):
        """Remove this person's subscription to this bug."""

    def isSubscribed(person):
        """Is person subscribed to this bug?

        Returns True if the user is explicitly subscribed to this bug
        (no matter what the type of subscription), otherwise False.
        """

    def notificationRecipientAddresses():
        """Return the list of email addresses that recieve notifications.

        If this bug is a duplicate of another bug, the CC'd list of
        the dup target will be appended to the list of recipient
        addresses.
        """

    def addWatch(bugtracker, remotebug, owner):
        """Create a new watch for this bug on the given remote bug and bug
        tracker, owned by the person given as the owner.
        """

    # CVE related methods
    def linkCVE(cve, user=None):
        """Ensure that this CVE is linked to this bug."""

    def unlinkCVE(cve, user=None):
        """Ensure that any links between this bug and the given CVE are
        removed.
        """

    def findCvesInText(self, bug, text):
        """Find any CVE references in the given text, make sure they exist
        in the database, and are linked to this bug.
        """


class IBugTarget(Interface):
    """An entity on which a bug can be reported.

    Examples include an IDistribution, an IDistroRelease and an
    IProduct.
    """
    def searchTasks(search_params):
        """Search the IBugTasks reported on this entity.

        :search_params: a BugTaskSearchParams object

        Return an iterable of matching results.

        Note: milestone is currently ignored for all IBugTargets
        except IProduct.
        """

    def newBug(owner, title, description):
        """Create a new bug on this target, with the given title,
        description and owner.
        """

    bugtasks = Attribute("A list of BugTasks for this target.")


class BugDistroReleaseTargetDetails:
    """The details of a bug targeted to a specific IDistroRelease.

    The following attributes are provided:

    :release: The IDistroRelease.
    :istargeted: Is there a fix targeted to this release?
    :sourcepackage: The sourcepackage to which the fix would be targeted.
    :assignee: An IPerson, or None if no assignee.
    :status: A BugTaskStatus dbschema item, or None, if release is not targeted.
    """
    def __init__(self, release, istargeted=False, sourcepackage=None,
                 assignee=None, status=None):
        self.release = release
        self.istargeted = istargeted
        self.sourcepackage = sourcepackage
        self.assignee = assignee
        self.status = status


class IBugDelta(Interface):
    """The quantitative change made to a bug that was edited."""

    bug = Attribute("The IBug, after it's been edited.")
    bugurl = Attribute("The absolute URL to the bug.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the bug itself
    title = Attribute("The new bug title or None.")
    summary = Attribute("The new bug summary or None.")
    description = Attribute("The new bug description or None.")
    private = Attribute("A dict with two keys, 'old' and 'new', or None.")
    name = Attribute("A dict with two keys, 'old' and 'new', or None.")
    duplicateof = Attribute(
        "The ID of which this bug report is a duplicate, or None.")

    # other things linked to the bug
    external_reference = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "IBugExternalRefs.")
    bugwatch = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "IBugWatch's.")
    attachment = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "IBugAttachment's.")
    cve = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "ICve's")
    added_bugtasks = Attribute(
        "A list or tuple of IBugTasks, one IBugTask, or None.")
    bugtask_deltas = Attribute(
        "A sequence of IBugTaskDeltas, one IBugTaskDelta or None.")


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
            description=_("""Ubuntu, Debian, Gentoo, etc."""),
            vocabulary="Distribution")
    owner = Int(title=_("Owner"), required=True)
    comment = Text(title=_('Description'), required=True,
            description=_("""A detailed description of the problem you are
            seeing."""))
    private = Bool(
            title=_("Should this bug be kept confidential?"), required=False,
            description=_(
                "Check this box if, for example, this bug exposes a security "
                "vulnerability. If you select this option, you must manually "
                "CC the people to whom this bug should be visible."),
            default=False)


class IBugSet(IAddFormCustomization):
    """A set of bugs."""

    title = Attribute('Title')

    def __getitem__(bugid):
        """Get a Bug."""

    def __iter__():
        """Iterate through Bugs."""

    def get(bugid):
        """Get a specific bug by its ID.

        If it can't be found, a zope.exceptions.NotFoundError will be
        raised.
        """

    def searchAsUser(user, duplicateof=None, orderBy=None, limit=None):
        """Find bugs matching the search criteria provided.

        To search as an anonymous user, the user argument passed
        should be None.
        """

    def queryByRemoteBug(bugtracker, remotebug):
        """Find one or None bugs in Malone that have a BugWatch matching the
        given bug tracker and remote bug id."""

    def createBug(self, distribution=None, sourcepackagename=None,
        binarypackagename=None, product=None, comment=None,
        description=None, msg=None, summary=None, datecreated=None,
        title=None, private=False, owner=None):
        """Create a new bug, using the given details."""

