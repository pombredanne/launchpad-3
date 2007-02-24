# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces related to bugs."""

__metaclass__ = type

__all__ = [
    'CreateBugParams',
    'CreatedBugWithNoBugTasksError',
    'IBug',
    'IBugSet',
    'IBugDelta',
    'IBugAddForm',
    'IFrontPageBugAddForm',
    'IProjectBugAddForm',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Choice, Datetime, Int, List, Object, Text, TextLine)

from canonical.launchpad import _
from canonical.launchpad.fields import ContentNameField, Title, BugField, Tag
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.interfaces.messagetarget import IMessageTarget
from canonical.launchpad.interfaces.validation import non_duplicate_bug
from canonical.launchpad.validators.name import name_validator


class CreateBugParams:
    """The parameters used to create a bug."""

    def __init__(self, owner, title, comment=None, description=None, msg=None,
                 status=None, assignee=None, datecreated=None,
                 security_related=False, private=False, subscribers=(),
                 binarypackagename=None):
        self.owner = owner
        self.title = title
        self.comment = comment
        self.description = description
        self.msg = msg
        self.status = status
        self.assignee = assignee
        self.datecreated = datecreated
        self.security_related = security_related
        self.private = private
        self.subscribers = subscribers

        self.product = None
        self.distribution = None
        self.sourcepackagename = None
        self.binarypackagename = binarypackagename

    def setBugTarget(self, product=None, distribution=None,
                     sourcepackagename=None):
        """Set the IBugTarget in which the bug is being reported.

        :product: an IProduct
        :distribution: an IDistribution
        :sourcepackagename: an ISourcePackageName

        A product or distribution must be provided, or an AssertionError
        is raised.

        If product is specified, all other parameters must evaluate to
        False in a boolean context, or an AssertionError will be raised.

        If distribution is specified, sourcepackagename may optionally
        be provided. product must evaluate to False in a boolean
        context, or an AssertionError will be raised.
        """
        assert product or distribution, (
            "You must specify the product or distribution in which this "
            "bug exists")

        if product:
            conflicting_context = (
                distribution or sourcepackagename)
        elif distribution:
            conflicting_context = product

        assert not conflicting_context, (
            "You must specify either an upstream context or a distribution "
            "context, but not both.")

        self.product = product
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename


class BugNameField(ContentNameField):
    errormessage = _("%s is already in use by another bug.")

    @property
    def _content_iface(self):
        return IBug

    def _getByName(self, name):
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except NotFoundError:
            return None


class CreatedBugWithNoBugTasksError(Exception):
    """Raised when a bug is created with no bug tasks."""


class IBug(IMessageTarget):
    """The core bug entry."""

    id = Int(
        title=_('Bug ID'), required=True, readonly=True)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    date_last_updated = Datetime(
        title=_('Date Last Updated'), required=True, readonly=True)
    name = BugNameField(
        title=_('Nickname'), required=False,
        description=_("""A short and unique name.
        Add one only if you often need to retype the URL
        but have trouble remembering the bug number."""),
        constraint=name_validator)
    title = Title(
        title=_('Summary'), required=True,
        description=_("""A one-line summary of the problem."""))
    description = Text(
        title=_('Description'), required=True,
        description=_("""A detailed description of the problem,
        including the steps required to reproduce it."""))
    ownerID = Int(title=_('Owner'), required=True, readonly=True)
    owner = Attribute("The owner's IPerson")
    duplicateof = BugField(
        title=_('Duplicate Of'), required=False, constraint=non_duplicate_bug)
    private = Bool(
        title=_("Keep bug confidential"), required=False,
        description=_("Make this bug visible only to its subscribers"),
        default=False)
    security_related = Bool(
        title=_("Security vulnerability"), required=False,
        description=_(
        "Select this option if the bug describes a security vulnerability"),
        default=False)
    displayname = TextLine(title=_("Text of the form 'Bug #X"),
        readonly=True)
    activity = Attribute('SQLObject.Multijoin of IBugActivity')
    initial_message = Attribute(
        "The message that was specified when creating the bug")
    bugtasks = Attribute('BugTasks on this bug, sorted upstream, then '
        'ubuntu, then other distroreleases.')
    pillar_bugtasks = Attribute(
        'The bugtasks which relate only to "pillars", products or '
        'distributions, the major structural objects in Launchpad. '
        'This leaves out the tasks relating to more detailed release '
        'related things like distroreleases and product series.')
    productinfestations = Attribute('List of product release infestations.')
    packageinfestations = Attribute('List of package release infestations.')
    watches = Attribute('SQLObject.Multijoin of IBugWatch')
    externalrefs = Attribute('SQLObject.Multijoin of IBugExternalRef')
    cves = Attribute('CVE entries related to this bug.')
    cve_links = Attribute('LInks between this bug and CVE entries.')
    mentoring_offers = Attribute('Offers to mentor this bug fix')
    subscriptions = Attribute('SQLObject.Multijoin of IBugSubscription')
    duplicates = Attribute(
        'MultiJoin of the bugs which are dups of this one')
    attachments = Attribute("List of bug attachments.")
    questions = Attribute("List of questions related to this bug.")
    specifications = Attribute("List of related specifications.")
    bug_branches = Attribute(
        "Branches associated with this bug, usually "
        "branches on which this bug is being fixed.")
    tags = List(
        title=_("Tags"), description=_("Separated by whitespace."),
        value_type=Tag(), required=False)
    is_complete = Attribute(
        "True or False depending on whether this bug is considered "
        "completely addressed. A bug is Launchpad is completely addressed "
        "when there are no tasks that are still open for the bug.")


    def followup_subject():
        """Return a candidate subject for a followup message."""

    # subscription-related methods
    def subscribe(person):
        """Subscribe person to the bug. Returns an IBugSubscription."""

    def unsubscribe(person):
        """Remove this person's subscription to this bug."""

    def unsubscribeFromDupes(person):
        """Remove this person's subscription from all dupes of this bug."""

    def isSubscribed(person):
        """Is person subscribed to this bug?

        Returns True if the user is explicitly subscribed to this bug
        (no matter what the type of subscription), otherwise False.

        If person is None, the return value is always False.
        """

    def isSubscribedToDupes(person):
        """Is person directly subscribed to dupes of this bug?

        Returns True if the user is directly subscribed to at least one
        duplicate of this bug, otherwise False.
        """

    def getDirectSubscribers():
        """A list of IPersons that are directly subscribed to this bug.

        Direct subscribers have an entry in the BugSubscription table.
        """

    def getIndirectSubscribers():
        """A list of IPersons that are indirectly subscribed to this bug.

        Indirect subscribers get bugmail, but don't have an entry in the
        BugSubscription table. This includes bug contacts, subscribers from
        dupes, etc.
        """

    def getAlsoNotifiedSubscribers():
        """A list of IPersons in the "Also notified" subscriber list.

        This includes bug contacts and assignees, but not subscribers
        from duplicates.
        """

    def getSubscribersFromDuplicates():
        """A list of IPersons subscribed from dupes of this bug."""

    def notificationRecipientAddresses():
        """Return the list of email addresses that recieve notifications.

        If this bug is a duplicate of another bug, the CC'd list of
        the dup target will be appended to the list of recipient
        addresses.
        """

    def addChangeNotification(text, person):
        """Add a bug change notification."""

    def addCommentNotification(message):
        """Add a bug comment notification."""

    def addWatch(bugtracker, remotebug, owner):
        """Create a new watch for this bug on the given remote bug and bug
        tracker, owned by the person given as the owner.
        """

    def hasBranch(branch):
        """Is this branch linked to this bug?"""

    def addBranch(branch, whiteboard=None):
        """Associate a branch with this bug.

        Returns an IBugBranch.
        """

    def addAttachment(owner, file_, description, comment, filename,
                      is_patch=False):
        """Attach a file to this bug.

        :owner: An IPerson.
        :file_: A file-like object.
        :description: A brief description of the attachment.
        :comment: An IMessage or string.
        :filename: A string.
        :is_patch: A boolean.
        """

    def linkCVE(cve, user=None):
        """Ensure that this CVE is linked to this bug."""

    def unlinkCVE(cve, user=None):
        """Ensure that any links between this bug and the given CVE are
        removed.
        """

    def findCvesInText(text):
        """Find any CVE references in the given text, make sure they exist
        in the database, and are linked to this bug.
        """

    # Mentoring
    def isMentor(user):
        """True if the user is offering mentoring for this bug."""

    def offerMentoring(user, team):
        """Record that the user is willing to mentor anyone who is trying to
        fix this bug.
        """

    def retractMentoring(user):
        """Remove the offer of mentoring for this bug from this user."""

    def getMessageChunks():
        """Return MessageChunks corresponding to comments made on this bug"""

    def addNomination(owner, target):
        """Nominate a bug for an IDistroRelease or IProductSeries.

        :owner: An IPerson.
        :target: An IDistroRelease or IProductSeries.

        This method creates and returns a BugNomination. (See
        canonical.launchpad.database.bugnomination.BugNomination.)
        """

    def canBeNominatedFor(nomination_target):
        """Can this bug nominated for this target?

        :nomination_target: An IDistroRelease or IProductSeries.

        Returns True or False.
        """

    def getNominationFor(nomination_target):
        """Return the IBugNomination for the target.

        If no nomination is found, a NotFoundError is raised.

        :nomination_target: An IDistroRelease or IProductSeries.
        """

    def getNominations(target=None):
        """Return a list of all IBugNominations for this bug.

        The list is ordered by IBugNominations.target.bugtargetname.

        Optional filtering arguments:

        :target: An IProduct or IDistribution.
        """

    def getBugWatch(bugtracker, remote_bug):
        """Return the BugWatch that has the given bugtracker and remote bug.

        Return None if this bug doesn't have such a bug watch.
        """


class IBugDelta(Interface):
    """The quantitative change made to a bug that was edited."""

    bug = Attribute("The IBug, after it's been edited.")
    bugurl = Attribute("The absolute URL to the bug.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the bug itself
    title = Attribute("A dict with two keys, 'old' and 'new', or None.")
    description = Attribute("A dict with two keys, 'old' and 'new', or None.")
    private = Attribute("A dict with two keys, 'old' and 'new', or None.")
    security_related = Attribute(
        "A dict with two keys, 'old' and 'new', or None.")
    name = Attribute("A dict with two keys, 'old' and 'new', or None.")
    duplicateof = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "IBug's")

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
    packagename = Choice(
            title=_("Package Name"), required=False,
            description=_("""The package you found this bug in,
            which was installed via apt-get, rpm, emerge or similar."""),
            vocabulary="BinaryAndSourcePackageName")
    distribution = Choice(
            title=_("Linux Distribution"), required=True,
            description=_(
                "Ubuntu, Debian, Gentoo, etc. You can file bugs only on "
                "distrubutions using Malone as their primary bug "
                "tracker."),
            vocabulary="DistributionUsingMalone")
    owner = Int(title=_("Owner"), required=True)
    comment = Text(
        title=_('Further information, steps to reproduce,'
                ' version information, etc.'),
        required=True)


class IProjectBugAddForm(IBugAddForm):
    """Create a bug for an IProject."""
    product = Choice(
        title=_("Product"), required=True,
        vocabulary="ProjectProductsUsingMalone")


class IFrontPageBugAddForm(IBugAddForm):
    """Create a bug for any bug target."""

    bugtarget = Object(
        schema=IBugTarget, title=_("Where did you find the bug?"),
        required=True)


class IBugSet(Interface):
    """A set of bugs."""

    def get(bugid):
        """Get a specific bug by its ID.

        If it can't be found, NotFoundError will be raised.
        """

    def getByNameOrID(bugid):
        """Get a specific bug by its ID or nickname

        If it can't be found, NotFoundError will be raised.
        """

    def searchAsUser(user, duplicateof=None, orderBy=None, limit=None):
        """Find bugs matching the search criteria provided.

        To search as an anonymous user, the user argument passed
        should be None.
        """

    def queryByRemoteBug(bugtracker, remotebug):
        """Find one or None bugs in Malone that have a BugWatch matching the
        given bug tracker and remote bug id."""

    def createBug(bug_params):
        """Create a bug and return it.

        :bug_params: A CreateBugParams object.

        Things to note when using this factory:

          * if no description is passed, the comment will be used as the
            description

          * the reporter will be subscribed to the bug

          * distribution, product and package contacts (whichever ones are
            applicable based on the bug report target) will bug subscribed to
            all *public bugs only*

          * for public upstreams bugs where there is no upstream bug contact,
            the product owner will be subscribed instead

          * if either product or distribution is specified, an appropiate
            bug task will be created

          * binarypackagename, if not None, will be added to the bug's
            description
        """

