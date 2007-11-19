# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Branch interfaces."""

__metaclass__ = type

__all__ = [
    'BranchCreationException',
    'BranchCreationForbidden',
    'BranchCreationNoTeamOwnedJunkBranches',
    'BranchCreatorNotMemberOfOwnerTeam',
    'BranchCreatorNotOwner',
    'BranchLifecycleStatus',
    'BranchLifecycleStatusFilter',
    'BranchListingSort',
    'BranchType',
    'BranchTypeError',
    'CannotDeleteBranch',
    'DEFAULT_BRANCH_STATUS_IN_LISTING',
    'IBranch',
    'IBranchSet',
    'IBranchDelta',
    'IBranchBatchNavigator',
    'IBranchListingFilter',
    'MAXIMUM_MIRROR_FAILURES',
    'MIRROR_TIME_INCREMENT',
    'UICreatableBranchType',
    'UnknownBranchTypeError'
    ]

from datetime import timedelta
from zope.interface import Interface, Attribute

from zope.component import getUtility
from zope.schema import Bool, Int, Choice, Text, TextLine, Datetime

from canonical.config import config

from canonical.launchpad import _
from canonical.launchpad.fields import Title, Summary, URIField, Whiteboard
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.webapp.interfaces import ITableBatchNavigator
from canonical.lazr import (
    DBEnumeratedType, DBItem, EnumeratedType, Item, use_template)


class BranchLifecycleStatus(DBEnumeratedType):
    """Branch Lifecycle Status

    This indicates the status of the branch, as part of an overall
    "lifecycle". The idea is to indicate to other people how mature this
    branch is, or whether or not the code in the branch has been deprecated.
    Essentially, this tells us what the author of the branch thinks of the
    code in the branch.
    """
    sort_order = (
        'MATURE', 'DEVELOPMENT', 'EXPERIMENTAL', 'MERGED', 'ABANDONED', 'NEW')

    NEW = DBItem(1, """
        New

        This branch has just been created, and we know nothing else about
        it.
        """)

    EXPERIMENTAL = DBItem(10, """
        Experimental

        This branch contains code that is considered experimental. It is
        still under active development and should not be merged into
        production infrastructure.
        """)

    DEVELOPMENT = DBItem(30, """
        Development

        This branch contains substantial work that is shaping up nicely, but
        is not yet ready for merging or production use. The work is
        incomplete, or untested.
        """)

    MATURE = DBItem(50, """
        Mature

        The developer considers this code mature. That means that it
        completely addresses the issues it is supposed to, that it is tested,
        and that it has been found to be stable enough for the developer to
        recommend it to others for inclusion in their work.
        """)

    MERGED = DBItem(70, """
        Merged

        This code has successfully been merged into its target branch(es),
        and no further development is anticipated on the branch.
        """)

    ABANDONED = DBItem(80, """
        Abandoned

        This branch contains work which the author has abandoned, likely
        because it did not prove fruitful.
        """)


class BranchType(DBEnumeratedType):
    """Branch Type

    The type of a branch determins the branch interaction with a number
    of other subsystems.
    """

    HOSTED = DBItem(1, """
        Hosted

        Hosted branches have their main repository on the supermirror.
        """)

    MIRRORED = DBItem(2, """
        Mirrored

        Mirrored branches are primarily hosted elsewhere and are
        periodically pulled from the remote site into the supermirror.
        """)

    IMPORTED = DBItem(3, """
        Imported

        Imported branches have been converted from some other revision
        control system into bzr and are made available through the supermirror.
        """)

    REMOTE = DBItem(4, """
        Remote

        Remote branches are those that are registered in Launchpad
        with an external location, but are not to be mirrored.
        """)


class UICreatableBranchType(EnumeratedType):
    """The types of branches that can be created through the web UI."""
    use_template(BranchType, exclude='IMPORTED')


DEFAULT_BRANCH_STATUS_IN_LISTING = (
    BranchLifecycleStatus.NEW,
    BranchLifecycleStatus.EXPERIMENTAL,
    BranchLifecycleStatus.DEVELOPMENT,
    BranchLifecycleStatus.MATURE)


# The maximum number of failures before we disable mirroring.
MAXIMUM_MIRROR_FAILURES = 5

# How frequently we mirror branches.
MIRROR_TIME_INCREMENT = timedelta(hours=6)


class BranchCreationException(Exception):
    """Base class for branch creation exceptions."""


class CannotDeleteBranch(Exception):
    """The branch cannot be deleted at this time."""


class UnknownBranchTypeError(Exception):
    """Raised when the user specifies an unrecognized branch type."""


class BranchCreationForbidden(BranchCreationException):
    """A Branch visibility policy forbids branch creation.

    The exception is raised if the policy for the product does not allow
    the creator of the branch to create a branch for that product.
    """


class BranchCreatorNotMemberOfOwnerTeam(BranchCreationException):
    """Branch creator is not a member of the owner team.

    Raised when a user is attempting to create a branch and set the owner of
    the branch to a team that they are not a member of.
    """


class BranchCreationNoTeamOwnedJunkBranches(BranchCreationException):
    """We forbid the creation of team-owned +junk branches.

    Raised when a user is attempting to create a team-owned +junk branch.
    """


class BranchCreatorNotOwner(BranchCreationException):
    """A user cannot create a branch belonging to another user.

    Raised when a user is attempting to create a branch and set the owner of
    the branch to another user.
    """


class BranchTypeError(Exception):
    """An operation cannot be performed for a particular branch type.

    Some branch operations are only valid for certain types of branches.  The
    BranchTypeError exception is raised if one of these operations is called
    with a branch of the wrong type.
    """


class BranchURIField(URIField):

    def _validate(self, value):
        # import here to avoid circular import
        from canonical.launchpad.webapp import canonical_url
        from canonical.launchpad.webapp.uri import URI

        super(BranchURIField, self)._validate(value)

        # XXX thumper 2007-06-12:
        # Move this validation code into IBranchSet so it can be
        # reused in the XMLRPC code, and the Authserver.
        # This also means we could get rid of the imports above.

        # URIField has already established that we have a valid URI
        uri = URI(value)
        supermirror_root = URI(config.codehosting.supermirror_root)
        launchpad_domain = config.launchpad.vhosts.mainsite.hostname
        if uri.underDomain(launchpad_domain):
            message = _(
                "For Launchpad to mirror a branch, the original branch cannot "
                "be on <code>%s</code>." % launchpad_domain)
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

    # XXX: TimPenhey 2007-08-31
    # The vocabulary set for branch_type is only used for the creation
    # of branches through the automatically generated forms, and doesn't
    # actually represent the complete range of real values that branch_type
    # may actually hold.  Import branches are not created in the same
    # way as Hosted, Mirrored or Remote branches.
    # There are two option:
    #   1) define a separate schema to use in the UI (sledgehammer solution)
    #   2) work out some way to specify a restricted vocabulary in the view
    # Personally I'd like a LAZR way to do number 2.
    branch_type = Choice(
        title=_("Branch Type"), required=True,
        vocabulary=UICreatableBranchType,
        description=_("Hosted branches have Launchpad code hosting as the "
                      "primary location and can be pushed to.  Mirrored "
                      "branches are pulled from the remote location "
                      "specified and cannot be pushed to.  Remote branches "
                      "are not mirrored by Launchpad, nor can they be "
                      "pushed to."))
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
        title=_('Branch URL'), required=False,
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
        title=_('Status'), vocabulary=BranchLifecycleStatus,
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
    mirror_request_time = Datetime(
        title=_("If this value is more recent than the last mirror attempt, "
                "then the branch will be mirrored on the next mirror run."),
        required=False)

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
    bug_branches = Attribute(
        "The bug-branch link objects that link this branch to bugs. ")

    related_bugs = Attribute(
        "The bugs related to this branch, likely branches on which "
        "some work has been done to fix this bug.")

    related_bug_tasks = Attribute(
        "For each related_bug, the bug task reported against this branch's "
        "product or the first bug task (in case where there is no task "
        "reported against the branch's product).")

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
    date_last_modified = Datetime(
        title=_('Date Last Modified'), required=True, readonly=False)

    def latest_revisions(quantity=10):
        """A specific number of the latest revisions in that branch."""

    landing_targets = Attribute(
        "The BranchMergeProposals where this branch is the source branch.")
    landing_candidates = Attribute(
        "The BranchMergeProposals where this branch is the target branch. "
        "Only active merge proposals are returned (those that have not yet "
        "been merged).")
    dependent_branches = Attribute(
        "The BranchMergeProposals where this branch is the dependent branch. "
        "Only active merge proposals are returned (those that have not yet "
        "been merged).")
    def addLandingTarget(registrant, target_branch, dependent_branch=None,
                         whiteboard=None, date_created=None):
        """Create a new BranchMergeProposal with this branch as the source.

        Both the target_branch and the dependent_branch, if it is there,
        must be branches of the same project as the source branch.

        Branches without associated projects, junk branches, cannot
        specify landing targets.

        :param registrant: The person who is adding the landing target.
        :param target_branch: Must be another branch, and different to self.
        :param dependent_branch: Optional but if it is not None, it must be
            another branch.
        :param whiteboard: Optional.  Just text, notes or instructions
            pertinant to the landing such as testing notes.
        :param date_created: Used to specify the date_created value of the
            merge request.
        """

    def revisions_since(timestamp):
        """Revisions in the history that are more recent than timestamp."""

    code_is_browseable = Attribute(
        "Is the code in this branch accessable through codebrowse?")

    def getBzrUploadURL(person=None):
        """Return the URL for this person to push to the branch.

        If user is None a placeholder is used for the username if
        one is required.
        """

    def getBzrDownloadURL(person=None):
        """Return the URL for this person to branch the branch.

        If the branch is public, the anonymous http location is used,
        otherwise the url uses the smartserver.

        If user is None a placeholder is used for the username if
        one is required.
        """

    def canBeDeleted():
        """Can this branch be deleted in its current state.

        A branch is considered deletable if it has no revisions, is not
        linked to any bugs, specs, productseries, or code imports, and
        has no subscribers.
        """

    def associatedProductSeries():
        """Return the product series that this branch is associated with.

        A branch may be associated with a product series as either a
        user_branch or import_branch.  Also a branch can be associated
        with more than one product series as a user_branch.
        """

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

    def getNotificationRecipients():
        """Return a complete INotificationRecipientSet instance.

        The INotificationRecipientSet instance contains the subscribers
        and their subscriptions.
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

    def getPullURL():
        """Return the URL used to pull the branch into the mirror area."""

    def requestMirror():
        """Request that this branch be mirrored on the next run of the branch
        puller.
        """

    def startMirroring():
        """Signal that this branch is being mirrored."""

    def mirrorComplete(last_revision_id):
        """Signal that a mirror attempt has completed successfully.

        :param last_revision_id: The revision ID of the tip of the mirrored
            branch.
        """

    def mirrorFailed(reason):
        """Signal that a mirror attempt failed.

        :param reason: An error message that will be displayed on the branch
            detail page.
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
        """Return the number of branches in the database.

        Only counts public branches.
        """

    def countBranchesWithAssociatedBugs():
        """Return the number of branches that have bugs associated.

        Only counts public branches.
        """

    def get(branch_id, default=None):
        """Return the branch with the given id.

        Return the default value if there is no such branch.
        """

    def new(branch_type, name, creator, owner, product, url, title=None,
            lifecycle_status=BranchLifecycleStatus.NEW, author=None,
            summary=None, home_page=None, whiteboard=None, date_created=None):
        """Create a new branch.

        Raises BranchCreationForbidden if the creator is not allowed
        to create a branch for the specified product.

        If product is None (indicating a +junk branch) then the owner must not
        be a team, except for the special case of the ~vcs-imports celebrity.
        """

    def delete(branch):
        """Delete the specified branch."""

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

    def getRecentlyChangedBranches(
        branch_count=None, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """Return a result set of branches that have been recently updated.

        Only HOSTED and MIRRORED branches are returned in the result set.

        If branch_count is specified, the result set will contain at most
        branch_count items.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """

    def getRecentlyImportedBranches(
        branch_count=None, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """Return a result set of branches that have been recently imported.

        The result set only contains IMPORTED branches.

        If branch_count is specified, the result set will contain at most
        branch_count items.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """

    def getRecentlyRegisteredBranches(
        branch_count=None, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """Return a result set of branches that have been recently registered.

        If branch_count is specified, the result set will contain at most
        branch_count items.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """

    def getLastCommitForBranches(branches):
        """Return a map of branch to last commit time."""

    def getBranchesForOwners(people):
        """Return the branches that are owned by the people specified."""

    def getBranchesForPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None, sort_by=None):
        """Branches associated with person with appropriate lifecycle.

        XXX: thumper 2007-03-23:
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

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        :param sort_by: What to sort the returned branches by.
        :type sort_by: A value from the `BranchListingSort` enumeration or
            None.
        """

    def getBranchesAuthoredByPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None, sort_by=None):
        """Branches authored by person with appropriate lifecycle.

        Only branches that are authored by the person are returned.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        :param sort_by: What to sort the returned branches by.
        :type sort_by: A value from the `BranchListingSort` enumeration or
            None.
        """

    def getBranchesRegisteredByPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None, sort_by=None):
        """Branches registered by person with appropriate lifecycle.

        Only branches registered by the person but *NOT* authored by
        the person are returned.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        :param sort_by: What to sort the returned branches by.
        :type sort_by: A value from the `BranchListingSort` enumeration or
            None.
        """

    def getBranchesSubscribedByPerson(
        person, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None, sort_by=None):
        """Branches subscribed by person with appropriate lifecycle.

        All branches where the person has subscribed to the branch
        are returned.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        :param sort_by: What to sort the returned branches by.
        :type sort_by: A value from the `BranchListingSort` enumeration or
            None.
        """

    def getBranchesForProduct(
        product, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None, sort_by=None):
        """Branches associated with product with appropriate lifecycle.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        :param sort_by: What to sort the returned branches by.
        :type sort_by: A value from the `BranchListingSort` enumeration or
            None.
        """

    def getBranchesForProject(
        project, lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None, sort_by=None):
        """Branches associated with project with appropriate lifecycle.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        :param sort_by: What to sort the returned branches by.
        :type sort_by: A value from the `BranchListingSort` enumeration or
            None.
        """

    def getHostedBranchesForPerson(person):
        """Return the hosted branches that the given person can write to."""

    def getLatestBranchesForProduct(product, quantity, visible_by_user=None):
        """Return the most recently created branches for the product.

        At most `quantity` branches are returned. Branches that have been
        merged or abandoned don't appear in the results -- only branches that
        match `DEFAULT_BRANCH_STATUS_IN_LISTING`.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """

    def getPullQueue(branch_type):
        """Return a queue of branches to mirror using the puller.

        :param branch_type: A value from the `BranchType` enum.
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


# XXX: TimPenhey 2007-07-23 bug=66950: The enumerations and interface
# to do with branch listing/filtering/ordering are used only in
# browser/branchlisting.py.

class BranchLifecycleStatusFilter(EnumeratedType):
    """Branch Lifecycle Status Filter

    Used to populate the branch lifecycle status filter widget.
    UI only.
    """
    use_template(BranchLifecycleStatus)

    sort_order = (
        'CURRENT', 'ALL', 'NEW', 'EXPERIMENTAL', 'DEVELOPMENT', 'MATURE',
        'MERGED', 'ABANDONED')

    CURRENT = Item("""
        New, Experimental, Development or Mature

        Show the currently active branches.
        """)

    ALL = Item("""
        Any Status

        Show all the branches.
        """)


class BranchListingSort(EnumeratedType):
    """Choices for how to sort branch listings."""

    # XXX: MichaelHudson 2007-10-17 bug=153891: We allow sorting on quantities
    # that are not visible in the listing!

    PRODUCT = Item("""
        by project name

        Sort branches by name of the project the branch is for.
        """)

    LIFECYCLE = Item("""
        by lifecycle status

        Sort branches by the lifecycle status.
        """)

    AUTHOR = Item("""
        by author name

        Sort branches by the display name of the author.
        """)

    NAME = Item("""
        by branch name

        Sort branches by the display name of the registrant.
        """)

    REGISTRANT = Item("""
        by registrant name

        Sort branches by the display name of the registrant.
        """)

    MOST_RECENTLY_CHANGED_FIRST = Item("""
        most recently changed first

        Sort branches from the most recently to the least recently
        changed.
        """)

    LEAST_RECENTLY_CHANGED_FIRST = Item("""
        least recently changed first

        Sort branches from the least recently to the most recently
        changed.
        """)

    NEWEST_FIRST = Item("""
        newest first

        Sort branches from newest to oldest.
        """)

    OLDEST_FIRST = Item("""
        oldest first

        Sort branches from oldest to newest.
        """)


class IBranchListingFilter(Interface):
    """The schema for the branch listing filtering/ordering form."""

    # Stats and status attributes
    lifecycle = Choice(
        title=_('Lifecycle Filter'), vocabulary=BranchLifecycleStatusFilter,
        default=BranchLifecycleStatusFilter.CURRENT,
        description=_(
        "The author's assessment of the branch's maturity. "
        " Mature: recommend for production use."
        " Development: useful work that is expected to be merged eventually."
        " Experimental: not recommended for merging yet, and maybe ever."
        " Merged: integrated into mainline, of historical interest only."
        " Abandoned: no longer considered relevant by the author."
        " New: unspecified maturity."))

    sort_by = Choice(
        title=_('ordered by'), vocabulary=BranchListingSort,
        default=BranchListingSort.LIFECYCLE)

