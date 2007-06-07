# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Branch interfaces."""

__metaclass__ = type

__all__ = [
    'DEFAULT_BRANCH_STATUS_IN_LISTING',
    'IBranch',
    'IBranchSet',
    'IBranchDelta',
    'IBranchLifecycleFilter',
    'IBranchBatchNavigator',
    ]

from zope.interface import Interface, Attribute

from zope.component import getUtility
from zope.schema import Bool, Int, Choice, Text, TextLine, Datetime

from canonical.config import config
from canonical.lp.dbschema import (BranchLifecycleStatus,
                                   BranchLifecycleStatusFilter)

from canonical.launchpad import _
from canonical.launchpad.fields import Title, Summary, URIField, Whiteboard
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.webapp.interfaces import ITableBatchNavigator


DEFAULT_BRANCH_STATUS_IN_LISTING = (
    BranchLifecycleStatus.NEW,
    BranchLifecycleStatus.EXPERIMENTAL,
    BranchLifecycleStatus.DEVELOPMENT,
    BranchLifecycleStatus.MATURE)


class BranchURIField(URIField):

    def _validate(self, value):
        # import here to avoid circular import
        from canonical.launchpad.webapp import canonical_url
        from canonical.launchpad.webapp.uri import URI

        super(BranchURIField, self)._validate(value)
        # URIField has already established that we have a valid URI
        uri = URI(value)
        supermirror_root = URI(config.launchpad.supermirror_root)
        launchpad_domain = config.launchpad.vhosts.mainsite.hostname
        if (supermirror_root.contains(uri)
            or uri.underDomain(launchpad_domain)):
            message = _(
                "Don't manually register a bzr branch on "
                "<code>%s</code>. Create it by SFTP, and it "
                "is registered automatically." % uri.host)
            raise LaunchpadValidationError(message)

        if IBranch.providedBy(self.context) and self.context.url == str(uri):
            return # url was not changed

        if uri.path == '/':
            message = _(
                "URLs for branches cannot point to the root of a site.")
            raise LaunchpadValidationError(message)

        branch = getUtility(IBranchSet).getByUrl(str(uri))
        if branch is not None:
            message = _(
                "The bzr branch <a href=\"%s\">%s</a> is already registered "
                "with this URL.")
            raise LaunchpadValidationError(
                message, canonical_url(branch), branch.displayname)


class IBranchBatchNavigator(ITableBatchNavigator):
    """A marker interface for registering the appropriate branch listings."""
    

class IBranch(IHasOwner):
    """A Bazaar branch."""

    id = Int(title=_('ID'), readonly=True, required=True)
    name = TextLine(
        title=_('Name'), required=True, description=_("Keep very "
        "short, unique, and descriptive, because it will be used in URLs. "
        "Examples: main, devel, release-1.0, gnome-vfs."),
        constraint=name_validator)
    title = Title(
        title=_('Title'), required=False, description=_("Describe the "
        "branch as clearly as possible in up to 70 characters. This "
        "title is displayed in every branch list or report."))
    summary = Summary(
        title=_('Summary'), required=False, description=_("A "
        "single-paragraph description of the branch. This will be "
        "displayed on the branch page."))
    url = BranchURIField(
        title=_('Branch URL'), required=True,
        allowed_schemes=['http', 'https', 'ftp', 'sftp', 'bzr+ssh'],
        allow_userinfo=False,
        allow_query=False,
        allow_fragment=False,
        trailing_slash=False,
        description=_("The URL where the Bazaar branch is hosted. This is "
            "the URL used to checkout the branch. The only branch format "
            "supported is that of the Bazaar revision control system, see "
            "www.bazaar-vcs.org for more information."))

    whiteboard = Whiteboard(title=_('Whiteboard'), required=False,
        description=_('Notes on the current status of the branch.'))
    mirror_status_message = Text(
        title=_('The last message we got when mirroring this branch '
                'into supermirror.'), required=False, readonly=False)

    private = Bool(
        title=_("Keep branch confidential"), required=False,
        description=_("Make this branch visible only to its subscribers"),
        default=False)

    # People attributes
    """Product owner, it can either a valid Person or Team
            inside Launchpad context."""
    owner = Choice(title=_('Owner'), required=True, vocabulary='ValidOwner',
        description=_("Branch owner, either a valid Person or Team."))
    author = Choice(
        title=_('Author'), required=False, vocabulary='ValidPersonOrTeam',
        description=_("The author of the branch. Leave blank if the author "
                      "does not have a Launchpad account."))

    # Product attributes
    product = Choice(
        title=_('Project'), required=False, vocabulary='Product',
        description=_("The project this branch belongs to."))
    product_name = Attribute("The name of the project, or '+junk'.")

    # Display attributes
    unique_name = Attribute(
        "Unique name of the branch, including the owner and project names.")
    displayname = Attribute(
        "The branch title if provided, or the unique_name.")
    sort_key = Attribute(
        "Key for sorting branches for display.")


    # Home page attributes
    home_page = URIField(
        title=_('Web Page'), required=False,
        allowed_schemes=['http', 'https', 'ftp'],
        allow_userinfo=False,
        description=_("The URL of a web page describing the branch, "
                      "if there is such a page."))

    # Stats and status attributes
    lifecycle_status = Choice(
        title=_('Status'), vocabulary='BranchLifecycleStatus',
        default=BranchLifecycleStatus.NEW,
        description=_(
        "The author's assessment of the branch's maturity. "
        " Mature: recommend for production use."
        " Development: useful work that is expected to be merged eventually."
        " Experimental: not recommended for merging yet, and maybe ever."
        " Merged: integrated into mainline, of historical interest only."
        " Abandoned: no longer considered relevant by the author."
        " New: unspecified maturity."))

    # Mirroring attributes
    last_mirrored = Datetime(
        title=_("Last time this branch was successfully mirrored."),
        required=False)
    last_mirrored_id = Text(
        title=_("Last mirrored revision ID"), required=False,
        description=_("The head revision ID of the branch when last "
                      "successfully mirrored."))
    last_mirror_attempt = Datetime(
        title=_("Last time a mirror of this branch was attempted."),
        required=False)
    mirror_failures = Attribute(
        "Number of failed mirror attempts since the last successful mirror.")
    pull_disabled = Bool(
        title=_("Do not try to pull this branch anymore."),
        description=_("Disable periodic pulling of this branch by Launchpad. "
                      "That will prevent connection attempts to the branch "
                      "URL. Use this if the branch is no longer available."))

    # Scanning attributes
    last_scanned = Datetime(
        title=_("Last time this branch was successfully scanned."),
        required=False)
    last_scanned_id = Text(
        title=_("Last scanned revision ID"), required=False,
        description=_("The head revision ID of the branch when last "
                      "successfully scanned."))
    revision_count = Int(
        title=_("Revision count"),
        description=_("The number of revisions in the branch")
        )

    warehouse_url = Attribute(
        "URL for accessing the branch by ID. "
        "This is for in-datacentre services only and allows such services to "
        "be unaffected during branch renames. "
        "See doc/bazaar for more information about the branch warehouse.")

    # Bug attributes
    related_bugs = Attribute(
        "The bugs related to this branch, likely branches on which "
        "some work has been done to fix this bug.")

    # Specification attributes
    spec_links = Attribute("Specifications linked to this branch")

    # Joins
    revision_history = Attribute(
        """The sequence of BranchRevision for the mainline of that branch.

        They are ordered with the most recent revision first, and the list
        only contains those in the "leftmost tree", or in other words
        the revisions that match the revision history from bzrlib for this
        branch.
        """)
    subscriptions = Attribute("BranchSubscriptions associated to this branch.")
    subscribers = Attribute("Persons subscribed to this branch.")

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    def latest_revisions(quantity=10):
        """A specific number of the latest revisions in that branch."""

    def revisions_since(timestamp):
        """Revisions in the history that are more recent than timestamp."""

    # subscription-related methods
    def subscribe(person, notification_level, max_diff_lines):
        """Subscribe this person to the branch.

        :return: new or existing BranchSubscription."""

    def getSubscription(person):
        """Return the BranchSubscription for this person."""

    def hasSubscription(person):
        """Is this person subscribed to the branch?"""

    def unsubscribe(person):
        """Remove the person's subscription to this branch."""

    def getBranchRevision(sequence):
        """Gets the BranchRevision for the given sequence number.

        If no such BranchRevision exists, None is returned.
        """

    def createBranchRevision(sequence, revision):
        """Create a new BranchRevision for this branch."""

    def getTipRevision():
        """Returns the Revision associated with the last_scanned_id.

        Will return None if last_scanned_id is None, or if the id
        is not found (as in a ghost revision).
        """

    def updateScannedDetails(revision_id, revision_count):
        """Updates attributes associated with the scanning of the branch.

        A single entry point that is called solely from the branch scanner
        script.
        """

    def getAttributeNotificationAddresses():
        """Return a list of email addresses of interested subscribers.

        Only branch subscriptions that specified an interest in
        attribute notifications will have specified email addresses added.
        """

    def getRevisionNotificationDetails():
        """Return a map of max diff size to a list of email addresses.
        
        Only branch subscriptions that specified an interest in
        revision notifications will have their specified email addresses added.

        If a user has subscribed to a branch directly, the settings
        that the user specifies overrides the settings of a team that the
        user is a member of.
        """
        
    def getScannerData():
        """Retrieve the full ancestry of a branch for the branch scanner.

        The branch scanner script is the only place where we need to retrieve
        all the BranchRevision rows for a branch. Since the ancestry of some
        branches is into the tens of thousands we don't want to materialise
        BranchRevision instances for each of these.

        :return: tuple of three items.
            1. Ancestry set of bzr revision-ids.
            2. History list of bzr revision-ids. Similar to the result of
               bzrlib.Branch.revision_history().
            3. Dictionnary mapping bzr bzr revision-ids to the database ids of
               the corresponding BranchRevision rows for this branch.
        """


class IBranchSet(Interface):
    """Interface representing the set of branches."""

    def __getitem__(branch_id):
        """Return the branch with the given id.

        Raise NotFoundError if there is no such branch.
        """

    def __iter__():
        """Return an iterator that will go through all branches."""

    def count():
        """Return the number of branches in the database."""

    def countBranchesWithAssociatedBugs():
        """Return the number of branches that have bugs associated."""

    def get(branch_id, default=None):
        """Return the branch with the given id.

        Return the default value if there is no such branch.
        """

    def new(name, owner, product, url, title,
            lifecycle_status=BranchLifecycleStatus.NEW, author=None,
            summary=None, home_page=None, date_created=None):
        """Create a new branch."""

    def getByUniqueName(unique_name, default=None):
        """Find a branch by its ~owner/product/name unique name.

        Return the default value if no match was found.
        """

    def getByUrl(url, default=None):
        """Find a branch by URL.

        Either from the external specified in Branch.url, or from the
        supermirror URL on http://bazaar.launchpad.net/.

        Return the default value if no match was found.
        """

    def getBranchesToScan():
        """Return an iterator for the branches that need to be scanned."""

    def getProductDevelopmentBranches(products):
        """Return branches that are associated with the products dev series.

        The branches will be either the import branches if imported, or
        the user branches if native.
        """

    def getActiveUserBranchSummaryForProducts(products):
        """Return the branch count and last commit time for the products.

        Only active branches are counted (i.e. not Merged or Abandoned),
        and only non import branches are counted.
        """

    def getRecentlyChangedBranches(branch_count):
        """Return a list of branches that have been recently updated.

        The list will contain at most branch_count items, and excludes
        branches owned by the vcs-imports user.
        """

    def getRecentlyImportedBranches(branch_count):
        """Return a list of branches that have been recently imported.

        The list will contain at most branch_count items, and only
        has branches owned by the vcs-imports user.
        """

    def getRecentlyRegisteredBranches(branch_count):
        """Return a list of branches that have been recently registered.

        The list will contain at most branch_count items.
        """

    def getLastCommitForBranches(branches):
        """Return a map of branch to last commit time."""

    def getBranchesForOwners(people):
        """Return the branches that are owned by the people specified."""

    def getBranchesForPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING):
        """Branches associated with person with appropriate lifecycle.

        XXX: thumper 2007-03-23
        The intent here is to just show interesting branches for the
        person.
        Following a chat with lifeless we'd like this to be listed and
        ordered by interest and last activity where activity is defined
        as linking a bug or spec, changing the status of said link,
        updating ui attributes of the branch, committing code to the
        branch.
        Branches of most interest to a person are their subscribed
        branches, and the branches that they have registered and authored.

        All branches that are either registered or authored by person
        are shown, as well as their subscribed branches.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.
        """
        
    def getBranchesAuthoredByPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING):
        """Branches authored by person with appropriate lifecycle.

        Only branches that are authored by the person are returned.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.
        """
        
    def getBranchesRegisteredByPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING):
        """Branches registered by person with appropriate lifecycle.

        Only branches registered by the person but *NOT* authored by
        the person are returned.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.
        """
        
    def getBranchesSubscribedByPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING):
        """Branches subscribed by person with appropriate lifecycle.

        All branches where the person has subscribed to the branch
        are returned.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.
        """
        
    def getBranchesForProduct(
        product, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING):
        """Branches associated with product with appropriate lifecycle.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.
        """


class IBranchDelta(Interface):
    """The quantitative changes made to a branch that was edited or altered."""

    branch = Attribute("The IBranch, after it's been edited.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the branch itself, we provide just the new changed value
    name = Attribute("Old and new names or None.")
    title = Attribute("Old and new branch titles or None.")
    summary = Attribute("The branch summary or None.")
    url = Attribute("Old and new branch URLs or None.")
    whiteboard = Attribute("The branch whiteboard or None.")
    lifecycle_status = Attribute("Old and new lifecycle status, or None.")
    revision_count = Attribute("Old and new revision counts, or None.")
    last_scanned_id = Attribute("The revision id of the tip revision.")


class IBranchLifecycleFilter(Interface):
    """A helper interface to render lifecycle filter choice."""

    # Stats and status attributes
    lifecycle = Choice(
        title=_('Lifecycle Filter'), vocabulary='BranchLifecycleStatusFilter',
        default=BranchLifecycleStatusFilter.CURRENT,
        description=_(
        "The author's assessment of the branch's maturity. "
        " Mature: recommend for production use."
        " Development: useful work that is expected to be merged eventually."
        " Experimental: not recommended for merging yet, and maybe ever."
        " Merged: integrated into mainline, of historical interest only."
        " Abandoned: no longer considered relevant by the author."
        " New: unspecified maturity."))
