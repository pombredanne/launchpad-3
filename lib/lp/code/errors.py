# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Errors used in the lp/code modules."""

__metaclass__ = type
__all__ = [
    'BadBranchMergeProposalSearchContext',
    'BadStateTransition',
    'BuildAlreadyPending',
    'BranchMergeProposalExists',
    'CodeImportAlreadyRequested',
    'CodeImportAlreadyRunning',
    'CodeImportNotInReviewedState',
    'ClaimReviewFailed',
    'ForbiddenInstruction',
    'InvalidBranchMergeProposal',
    'ReviewNotPending',
    'TooManyBuilds',
    'TooNewRecipeFormat',
    'UnknownBranchTypeError',
    'UserHasExistingReview',
    'UserNotBranchReviewer',
    'WrongBranchMergeProposal',
]

from lazr.restful.declarations import webservice_error


class BadBranchMergeProposalSearchContext(Exception):
    """The context is not valid for a branch merge proposal search."""


class BadStateTransition(Exception):
    """The user requested a state transition that is not possible."""


class ClaimReviewFailed(Exception):
    """The user cannot claim the pending review."""


class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


class BranchMergeProposalExists(InvalidBranchMergeProposal):
    """Raised if there is already a matching BranchMergeProposal."""

    webservice_error(400) #Bad request.


class ReviewNotPending(Exception):
    """The requested review is not in a pending state."""


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


class CodeImportNotInReviewedState(Exception):
    """Raised when the user requests an import of a non-automatic import."""

    webservice_error(400)


class CodeImportAlreadyRequested(Exception):
    """Raised when the user requests an import that is already requested."""

    def __init__(self, msg, requesting_user):
        super(CodeImportAlreadyRequested, self).__init__(msg)
        self.requesting_user = requesting_user


class CodeImportAlreadyRunning(Exception):
    """Raised when the user requests an import that is already running."""

    webservice_error(400)


class ForbiddenInstruction(Exception):
    """A forbidden instruction was found in the recipe."""

    def __init__(self, instruction_name):
        super(ForbiddenInstruction, self).__init__()
        self.instruction_name = instruction_name


class TooNewRecipeFormat(Exception):
    """The format of the recipe supplied was too new."""

    def __init__(self, supplied_format, newest_supported):
        super(TooNewRecipeFormat, self).__init__()
        self.supplied_format = supplied_format
        self.newest_supported = newest_supported


class RecipeBuildException(Exception):

    def __init__(self, recipe, distroseries, template):
        self.recipe = recipe
        self.distroseries = distroseries
        msg = template % {'recipe': recipe, 'distroseries': distroseries}
        Exception.__init__(self, msg)


class TooManyBuilds(RecipeBuildException):
    """A build was requested that exceeded the quota."""

    webservice_error(400)

    def __init__(self, recipe, distroseries):
        RecipeBuildException.__init__(
            self, recipe, distroseries,
            'You have exceeded your quota for recipe %(recipe)s for'
            ' distroseries %(distroseries)s')


class BuildAlreadyPending(RecipeBuildException):
    """A build was requested when an identical build was already pending."""

    webservice_error(400)

    def __init__(self, recipe, distroseries):
        RecipeBuildException.__init__(
            self, recipe, distroseries,
            'An identical build of this recipe is already pending.')


class BuildNotAllowedForDistro(RecipeBuildException):
    """A build was request against a distroseries that is not supported."""

    webservice_error(400)

    def __init__(self, recipe, distroseries):
        RecipeBuildException.__init__(
            self, recipe, distroseries,
            'A build against this distro is not allowed.')
