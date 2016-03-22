# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Errors used in the lp/code modules."""

__metaclass__ = type
__all__ = [
    'AlreadyLatestFormat',
    'BadBranchMergeProposalSearchContext',
    'BadStateTransition',
    'BranchCreationException',
    'BranchCreationForbidden',
    'BranchCreatorNotMemberOfOwnerTeam',
    'BranchCreatorNotOwner',
    'BranchExists',
    'BranchHasPendingWrites',
    'BranchTargetError',
    'BranchTypeError',
    'BuildAlreadyPending',
    'BuildNotAllowedForDistro',
    'BranchMergeProposalExists',
    'CannotDeleteBranch',
    'CannotDeleteGitRepository',
    'CannotHaveLinkedBranch',
    'CannotUpgradeBranch',
    'CannotUpgradeNonHosted',
    'CodeImportAlreadyRequested',
    'CodeImportAlreadyRunning',
    'CodeImportNotInReviewedState',
    'ClaimReviewFailed',
    'DiffNotFound',
    'GitDefaultConflict',
    'GitRecipesFeatureDisabled',
    'GitRepositoryCreationException',
    'GitRepositoryCreationFault',
    'GitRepositoryCreationForbidden',
    'GitRepositoryCreatorNotMemberOfOwnerTeam',
    'GitRepositoryCreatorNotOwner',
    'GitRepositoryDeletionFault',
    'GitRepositoryExists',
    'GitRepositoryScanFault',
    'GitTargetError',
    'InvalidBranchMergeProposal',
    'InvalidNamespace',
    'NoLinkedBranch',
    'NoSuchBranch',
    'NoSuchGitReference',
    'NoSuchGitRepository',
    'PrivateBranchRecipe',
    'PrivateGitRepositoryRecipe',
    'ReviewNotPending',
    'StaleLastMirrored',
    'TooNewRecipeFormat',
    'UnknownBranchTypeError',
    'UpdatePreviewDiffNotReady',
    'UpgradePending',
    'UserHasExistingReview',
    'UserNotBranchReviewer',
    'WrongBranchMergeProposal',
]

import httplib

from bzrlib.plugins.builder.recipe import RecipeParseError
from lazr.restful.declarations import error_status

from lp.app.errors import (
    NameLookupFailed,
    NotFoundError,
    )

# Annotate the RecipeParseError's with a 400 webservice status.
error_status(httplib.BAD_REQUEST)(RecipeParseError)


class BadBranchMergeProposalSearchContext(Exception):
    """The context is not valid for a branch merge proposal search."""


@error_status(httplib.BAD_REQUEST)
class BadStateTransition(Exception):
    """The user requested a state transition that is not possible."""


class BranchCreationException(Exception):
    """Base class for branch creation exceptions."""


@error_status(httplib.CONFLICT)
class BranchExists(BranchCreationException):
    """Raised when creating a branch that already exists."""

    def __init__(self, existing_branch):
        # XXX: TimPenhey 2009-07-12 bug=405214: This error
        # message logic is incorrect, but the exact text is being tested
        # in branch-xmlrpc.txt.
        params = {'name': existing_branch.name}
        if existing_branch.product is None:
            params['maybe_junk'] = 'junk '
            params['context'] = existing_branch.owner.name
        else:
            params['maybe_junk'] = ''
            params['context'] = '%s in %s' % (
                existing_branch.owner.name, existing_branch.product.name)
        message = (
            'A %(maybe_junk)sbranch with the name "%(name)s" already exists '
            'for %(context)s.' % params)
        self.existing_branch = existing_branch
        BranchCreationException.__init__(self, message)


class BranchHasPendingWrites(Exception):
    """Raised if the branch can't be processed because a write is pending.

    In this case the operation can usually be retried in a while.

    See bug 612171.
    """


class BranchTargetError(Exception):
    """Raised when there is an error determining a branch target."""


@error_status(httplib.BAD_REQUEST)
class CannotDeleteBranch(Exception):
    """The branch cannot be deleted at this time."""


class BranchCreationForbidden(BranchCreationException):
    """A Branch visibility policy forbids branch creation.

    The exception is raised if the policy for the product does not allow
    the creator of the branch to create a branch for that product.
    """


@error_status(httplib.BAD_REQUEST)
class BranchCreatorNotMemberOfOwnerTeam(BranchCreationException):
    """Branch creator is not a member of the owner team.

    Raised when a user is attempting to create a branch and set the owner of
    the branch to a team that they are not a member of.
    """


@error_status(httplib.BAD_REQUEST)
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


class InvalidBranchException(Exception):
    """Base exception for an error resolving a branch for a component.

    Subclasses should set _msg_template to match their required display
    message.
    """

    _msg_template = "Invalid branch for: %s"

    def __init__(self, component):
        self.component = component
        # It's expected that components have a name attribute,
        # so let's assume they will and deal with any error if it occurs.
        try:
            component_name = component.name
        except AttributeError:
            component_name = str(component)
        # The display_message contains something readable for the user.
        self.display_message = self._msg_template % component_name
        Exception.__init__(self, self._msg_template % (repr(component),))


class CannotHaveLinkedBranch(InvalidBranchException):
    """Raised when we try to get the linked branch for a thing that can't."""

    _msg_template = "%s cannot have linked branches."


class CannotUpgradeBranch(Exception):
    """"Made for subclassing."""

    def __init__(self, branch):
        super(CannotUpgradeBranch, self).__init__(
            self._msg_template % branch.bzr_identity)
        self.branch = branch


class AlreadyLatestFormat(CannotUpgradeBranch):
    """Raised on attempt to upgrade a branch already in the latest format."""

    _msg_template = (
        'Branch %s is in the latest format, so it cannot be upgraded.')


class CannotUpgradeNonHosted(CannotUpgradeBranch):

    """Raised on attempt to upgrade a non-Hosted branch."""

    _msg_template = 'Cannot upgrade non-hosted branch %s'


class UpgradePending(CannotUpgradeBranch):

    """Raised on attempt to upgrade a branch already in the latest format."""

    _msg_template = 'An upgrade is already in progress for branch %s.'


class ClaimReviewFailed(Exception):
    """The user cannot claim the pending review."""


@error_status(httplib.BAD_REQUEST)
class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


@error_status(httplib.BAD_REQUEST)
class BranchMergeProposalExists(InvalidBranchMergeProposal):
    """Raised if there is already a matching BranchMergeProposal."""

    def __init__(self, existing_proposal):
        # Circular import.
        from lp.code.interfaces.branch import IBranch
        # display_name is the newer style, but IBranch uses the older style.
        if IBranch.providedBy(existing_proposal.merge_source):
            display_name = "displayname"
        else:
            display_name = "display_name"
        super(BranchMergeProposalExists, self).__init__(
                'There is already a branch merge proposal registered for '
                'branch %s to land on %s that is still active.' %
                (getattr(existing_proposal.merge_source, display_name),
                 getattr(existing_proposal.merge_target, display_name)))
        self.existing_proposal = existing_proposal


class InvalidNamespace(Exception):
    """Raised when someone tries to lookup a namespace with a bad name.

    By 'bad', we mean that the name is unparsable. It might be too short, too
    long or malformed in some other way.
    """

    def __init__(self, name):
        self.name = name
        Exception.__init__(
            self, "Cannot understand namespace name: '%s'" % (name,))


class NoLinkedBranch(InvalidBranchException):
    """Raised when there's no linked branch for a thing."""

    _msg_template = "%s has no linked branch."


class NoSuchBranch(NameLookupFailed):
    """Raised when we try to load a branch that does not exist."""

    _message_prefix = "No such branch"


class StaleLastMirrored(Exception):
    """Raised when last_mirrored_id is out of date with on-disk value."""

    def __init__(self, db_branch, info):
        """Constructor.

        :param db_branch: The database branch.
        :param info: A dict of information about the branch, as produced by
            lp.codehosting.bzrutils.get_branch_info
        """
        self.db_branch = db_branch
        self.info = info
        Exception.__init__(
            self,
            'Database last_mirrored_id %s does not match on-disk value %s' %
            (db_branch.last_mirrored_id, self.info['last_revision_id']))


@error_status(httplib.BAD_REQUEST)
class PrivateBranchRecipe(Exception):

    def __init__(self, branch):
        message = (
            'Recipe may not refer to private branch: %s' % branch.identity)
        self.branch = branch
        Exception.__init__(self, message)


@error_status(httplib.BAD_REQUEST)
class PrivateGitRepositoryRecipe(Exception):

    def __init__(self, repository):
        message = (
            'Recipe may not refer to private repository: %s' %
            repository.identity)
        self.repository = repository
        Exception.__init__(self, message)


class ReviewNotPending(Exception):
    """The requested review is not in a pending state."""


class UpdatePreviewDiffNotReady(Exception):
    """Raised if the preview diff is not ready to run."""


class UserHasExistingReview(Exception):
    """The user has an existing review."""


class UserNotBranchReviewer(Exception):
    """The user who attempted to review the merge proposal isn't a reviewer.

    A specific reviewer may be set on a branch.  If a specific reviewer
    isn't set then any user in the team of the owner of the branch is
    considered a reviewer.
    """


class WrongBranchMergeProposal(Exception):
    """The comment requested is not associated with this merge proposal."""


class UnknownBranchTypeError(Exception):
    """Raised when the user specifies an unrecognized branch type."""


class GitRepositoryCreationException(Exception):
    """Base class for Git repository creation exceptions."""


@error_status(httplib.CONFLICT)
class GitRepositoryExists(GitRepositoryCreationException):
    """Raised when creating a Git repository that already exists."""

    def __init__(self, existing_repository):
        params = {
            "name": existing_repository.name,
            "context": existing_repository.namespace.name,
            }
        message = (
            'A Git repository with the name "%(name)s" already exists for '
            '%(context)s.' % params)
        self.existing_repository = existing_repository
        GitRepositoryCreationException.__init__(self, message)


@error_status(httplib.BAD_REQUEST)
class CannotDeleteGitRepository(Exception):
    """The Git repository cannot be deleted at this time."""


class GitRepositoryCreationForbidden(GitRepositoryCreationException):
    """A visibility policy forbids Git repository creation.

    The exception is raised if the policy for the project does not allow the
    creator of the repository to create a repository for that project.
    """


@error_status(httplib.BAD_REQUEST)
class GitRepositoryCreatorNotMemberOfOwnerTeam(GitRepositoryCreationException):
    """Git repository creator is not a member of the owner team.

    Raised when a user is attempting to create a repository and set the
    owner of the repository to a team that they are not a member of.
    """


@error_status(httplib.BAD_REQUEST)
class GitRepositoryCreatorNotOwner(GitRepositoryCreationException):
    """A user cannot create a Git repository belonging to another user.

    Raised when a user is attempting to create a repository and set the
    owner of the repository to another user.
    """


class GitRepositoryCreationFault(Exception):
    """Raised when there is a hosting fault creating a Git repository."""


class GitRepositoryScanFault(Exception):
    """Raised when there is a fault scanning a repository."""


class GitRepositoryDeletionFault(Exception):
    """Raised when there is a fault deleting a repository."""


class GitTargetError(Exception):
    """Raised when there is an error determining a Git repository target."""


class NoSuchGitRepository(NameLookupFailed):
    """Raised when we try to load a Git repository that does not exist."""

    _message_prefix = "No such Git repository"


class NoSuchGitReference(NotFoundError):
    """Raised when we try to look up a Git reference that does not exist."""

    def __init__(self, repository, path):
        self.repository = repository
        self.path = path
        self.message = (
            "The repository at %s does not contain a reference named '%s'." %
            (repository.display_name, path))
        NotFoundError.__init__(self, self.message)

    def __str__(self):
        return self.message


@error_status(httplib.CONFLICT)
class GitDefaultConflict(Exception):
    """Raised when trying to set a Git repository as the default for
    something that already has a default."""

    def __init__(self, existing_repository, target, owner=None):
        params = {
            "unique_name": existing_repository.unique_name,
            "target": target.displayname,
            }
        if owner is None:
            message = (
                "The default repository for '%(target)s' is already set to "
                "%(unique_name)s." % params)
        else:
            params["owner"] = owner.displayname
            message = (
                "%(owner)s's default repository for '%(target)s' is already "
                "set to %(unique_name)s." % params)
        self.existing_repository = existing_repository
        self.target = target
        self.owner = owner
        Exception.__init__(self, message)


@error_status(httplib.BAD_REQUEST)
class CodeImportNotInReviewedState(Exception):
    """Raised when the user requests an import of a non-automatic import."""


class CodeImportAlreadyRequested(Exception):
    """Raised when the user requests an import that is already requested."""

    def __init__(self, msg, requesting_user):
        super(CodeImportAlreadyRequested, self).__init__(msg)
        self.requesting_user = requesting_user


@error_status(httplib.BAD_REQUEST)
class CodeImportAlreadyRunning(Exception):
    """Raised when the user requests an import that is already running."""


@error_status(httplib.BAD_REQUEST)
class TooNewRecipeFormat(Exception):
    """The format of the recipe supplied was too new."""

    def __init__(self, supplied_format, newest_supported):
        super(TooNewRecipeFormat, self).__init__()
        self.supplied_format = supplied_format
        self.newest_supported = newest_supported


@error_status(httplib.UNAUTHORIZED)
class GitRecipesFeatureDisabled(Exception):
    """Only certain users can create new Git recipes."""

    def __init__(self):
        message = "You do not have permission to create Git recipes."
        Exception.__init__(self, message)


@error_status(httplib.BAD_REQUEST)
class RecipeBuildException(Exception):

    def __init__(self, recipe, distroseries, template):
        self.recipe = recipe
        self.distroseries = distroseries
        msg = template % {'recipe': recipe, 'distroseries': distroseries}
        Exception.__init__(self, msg)


class BuildAlreadyPending(RecipeBuildException):
    """A build was requested when an identical build was already pending."""

    def __init__(self, recipe, distroseries):
        RecipeBuildException.__init__(
            self, recipe, distroseries,
            'An identical build of this recipe is already pending.')


class BuildNotAllowedForDistro(RecipeBuildException):
    """A build was requested against an unsupported distroseries."""

    def __init__(self, recipe, distroseries):
        RecipeBuildException.__init__(
            self, recipe, distroseries,
            'A build against this distro is not allowed.')


@error_status(httplib.BAD_REQUEST)
class DiffNotFound(Exception):
    """A `IPreviewDiff` with the timestamp was not found."""
