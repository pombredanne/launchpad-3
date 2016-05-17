# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'GitRef',
    'GitRefFrozen',
    ]

from datetime import datetime
import json
from urllib import quote_plus

from lazr.lifecycle.event import ObjectCreatedEvent
import pytz
from storm.locals import (
    DateTime,
    Int,
    Not,
    Reference,
    Store,
    Unicode,
    )
from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.code.enums import (
    BranchMergeProposalStatus,
    GitObjectType,
    )
from lp.code.errors import (
    BranchMergeProposalExists,
    InvalidBranchMergeProposal,
    )
from lp.code.event.branchmergeproposal import (
    BranchMergeProposalNeedsReviewEvent,
    )
from lp.code.interfaces.branch import WrongNumberOfReviewTypeArguments
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES,
    )
from lp.code.interfaces.gitcollection import IAllGitRepositories
from lp.code.interfaces.githosting import IGitHostingClient
from lp.code.interfaces.gitref import IGitRef
from lp.code.model.branchmergeproposal import (
    BranchMergeProposal,
    BranchMergeProposalGetter,
    )
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.constants import UTC_NOW
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.features import getFeatureFlag
from lp.services.memcache.interfaces import IMemcacheClient


class GitRefMixin:
    """Methods and properties common to GitRef and GitRefFrozen.

    These can be derived solely from the repository and path, and so do not
    require a database record.
    """

    @property
    def display_name(self):
        """See `IGitRef`."""
        return self.identity

    # For IHasMergeProposals views.
    displayname = display_name

    @property
    def name(self):
        """See `IGitRef`."""
        if self.path.startswith("refs/heads/"):
            return self.path[len("refs/heads/"):]
        else:
            return self.path

    @property
    def identity(self):
        """See `IGitRef`."""
        return "%s:%s" % (self.repository.shortened_path, self.name)

    @property
    def unique_name(self):
        """See `IGitRef`."""
        return "%s:%s" % (self.repository.unique_name, self.name)

    @property
    def owner(self):
        """See `IGitRef`."""
        return self.repository.owner

    @property
    def target(self):
        """See `IGitRef`."""
        return self.repository.target

    @property
    def namespace(self):
        """See `IGitRef`."""
        return self.repository.namespace

    def getCodebrowseUrl(self):
        """See `IGitRef`."""
        return "%s?h=%s" % (
            self.repository.getCodebrowseUrl(), quote_plus(self.name))

    def getCodebrowseUrlForRevision(self, commit):
        """See `IGitRef`."""
        return self.repository.getCodebrowseUrlForRevision(commit)

    @property
    def information_type(self):
        """See `IGitRef`."""
        return self.repository.information_type

    @property
    def private(self):
        """See `IGitRef`."""
        return self.repository.private

    def visibleByUser(self, user):
        """See `IGitRef`."""
        return self.repository.visibleByUser(user)

    @property
    def reviewer(self):
        """See `IGitRef`."""
        # XXX cjwatson 2015-04-17: We should have ref-pattern-specific
        # reviewers.
        return self.repository.reviewer

    @property
    def code_reviewer(self):
        """See `IGitRef`."""
        # XXX cjwatson 2015-04-17: We should have ref-pattern-specific
        # reviewers.
        return self.repository.code_reviewer

    def isPersonTrustedReviewer(self, reviewer):
        """See `IGitRef`."""
        # XXX cjwatson 2015-04-17: We should have ref-pattern-specific
        # reviewers.
        return self.repository.isPersonTrustedReviewer(reviewer)

    @property
    def subscriptions(self):
        """See `IGitRef`."""
        return self.repository.subscriptions

    @property
    def subscribers(self):
        """See `IGitRef`."""
        return self.repository.subscribers

    def subscribe(self, person, notification_level, max_diff_lines,
                  code_review_level, subscribed_by):
        """See `IGitRef`."""
        return self.repository.subscribe(
            person, notification_level, max_diff_lines, code_review_level,
            subscribed_by)

    def getSubscription(self, person):
        """See `IGitRef`."""
        return self.repository.getSubscription(person)

    def getNotificationRecipients(self):
        """See `IGitRef`."""
        return self.repository.getNotificationRecipients()

    @property
    def landing_targets(self):
        """See `IGitRef`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.source_git_repository == self.repository,
            BranchMergeProposal.source_git_path == self.path)

    @property
    def landing_candidates(self):
        """See `IGitRef`."""
        # Circular import.
        from lp.code.model.gitrepository import GitRepository

        result = Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.target_git_repository == self.repository,
            BranchMergeProposal.target_git_path == self.path,
            Not(BranchMergeProposal.queue_status.is_in(
                BRANCH_MERGE_PROPOSAL_FINAL_STATES)))

        def eager_load(rows):
            load_related(
                GitRepository, rows,
                ["source_git_repositoryID", "prerequisite_git_repositoryID"])

        return DecoratedResultSet(result, pre_iter_hook=eager_load)

    @property
    def dependent_landings(self):
        """See `IGitRef`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.prerequisite_git_repository == self.repository,
            BranchMergeProposal.prerequisite_git_path == self.path,
            Not(BranchMergeProposal.queue_status.is_in(
                BRANCH_MERGE_PROPOSAL_FINAL_STATES)))

    def getMergeProposals(self, status=None, visible_by_user=None,
                          merged_revision_ids=None, eager_load=False):
        """See `IGitRef`."""
        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS)

        collection = getUtility(IAllGitRepositories).visibleByUser(
            visible_by_user)
        return collection.getMergeProposals(
            status, target_repository=self.repository, target_path=self.path,
            merged_revision_ids=merged_revision_ids, eager_load=eager_load)

    def getDependentMergeProposals(self, status=None, visible_by_user=None,
                                   eager_load=False):
        """See `IGitRef`."""
        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS)

        collection = getUtility(IAllGitRepositories).visibleByUser(
            visible_by_user)
        return collection.getMergeProposals(
            status, prerequisite_repository=self.repository,
            prerequisite_path=self.path, eager_load=eager_load)

    @property
    def pending_writes(self):
        """See `IGitRef`."""
        return self.repository.pending_writes

    def _getLog(self, start, limit=None, stop=None,
                enable_hosting=None, enable_memcache=None, logger=None):
        if enable_hosting is None:
            enable_hosting = not getFeatureFlag(
                u"code.git.log.disable_hosting")
        if enable_memcache is None:
            enable_memcache = not getFeatureFlag(
                u"code.git.log.disable_memcache")
        hosting_client = getUtility(IGitHostingClient)
        memcache_client = getUtility(IMemcacheClient)
        path = self.repository.getInternalPath()
        memcache_key = "%s:git-log:%s:%s" % (config.instance_name, path, start)
        if limit is not None:
            memcache_key += ":limit=%s" % limit
        if stop is not None:
            memcache_key += ":stop=%s" % stop
        if isinstance(memcache_key, unicode):
            memcache_key = memcache_key.encode("UTF-8")
        log = None
        if enable_memcache:
            cached_log = memcache_client.get(memcache_key)
            if cached_log is not None:
                try:
                    log = json.loads(cached_log)
                except Exception:
                    logger.exception(
                        "Cannot load cached log information for %s:%s; "
                        "deleting" % (path, start))
                    memcache_client.delete(memcache_key)
        if log is None:
            if enable_hosting:
                log = removeSecurityProxy(hosting_client.getLog(
                    path, start, limit=limit, stop=stop, logger=logger))
                if enable_memcache:
                    memcache_client.set(memcache_key, json.dumps(log))
            else:
                # Fall back to synthesising something reasonable based on
                # information in our own database.
                epoch = datetime.fromtimestamp(0, tz=pytz.UTC)
                log = [{
                    "sha1": self.commit_sha1,
                    "message": self.commit_message,
                    "author": None if self.author is None else {
                        "name": self.author.name_without_email,
                        "email": self.author.email,
                        "time": (self.author_date - epoch).total_seconds(),
                        },
                    "committer": None if self.committer is None else {
                        "name": self.committer.name_without_email,
                        "email": self.committer.email,
                        "time": (self.committer_date - epoch).total_seconds(),
                        },
                    }]
        return log

    def getCommits(self, start, limit=None, stop=None,
                   start_date=None, end_date=None, logger=None):
        # Circular import.
        from lp.code.model.gitrepository import parse_git_commits

        log = self._getLog(start, limit=limit, stop=stop, logger=logger)
        parsed_commits = parse_git_commits(log)
        revisions = []
        for commit in log:
            if "sha1" not in commit:
                continue
            parsed_commit = parsed_commits[commit["sha1"]]
            author_date = parsed_commit.get("author_date")
            if start_date is not None:
                if author_date is None or author_date < start_date:
                    continue
            if end_date is not None:
                if author_date is None or author_date > end_date:
                    continue
            revisions.append(parsed_commit)
        return revisions

    def getLatestCommits(self, quantity=10):
        return self.getCommits(self.commit_sha1, limit=quantity)

    @property
    def has_commits(self):
        return len(self.getLatestCommits())

    @property
    def recipes(self):
        """See `IHasRecipes`."""
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        from lp.code.model.sourcepackagerecipedata import (
            SourcePackageRecipeData,
            )
        revspecs = set([self.path, self.name])
        if self.path == self.repository.default_branch:
            revspecs.add(None)
        recipes = SourcePackageRecipeData.findRecipes(
            self.repository, revspecs=list(revspecs))
        hook = SourcePackageRecipe.preLoadDataForSourcePackageRecipes
        return DecoratedResultSet(recipes, pre_iter_hook=hook)


@implementer(IGitRef)
class GitRef(StormBase, GitRefMixin):
    """See `IGitRef`."""

    __storm_table__ = 'GitRef'
    __storm_primary__ = ('repository_id', 'path')

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    path = Unicode(name='path', allow_none=False)

    commit_sha1 = Unicode(name='commit_sha1', allow_none=False)

    object_type = EnumCol(enum=GitObjectType, notNull=True)

    author_id = Int(name='author', allow_none=True)
    author = Reference(author_id, 'RevisionAuthor.id')
    author_date = DateTime(
        name='author_date', tzinfo=pytz.UTC, allow_none=True)

    committer_id = Int(name='committer', allow_none=True)
    committer = Reference(committer_id, 'RevisionAuthor.id')
    committer_date = DateTime(
        name='committer_date', tzinfo=pytz.UTC, allow_none=True)

    commit_message = Unicode(name='commit_message', allow_none=True)

    @property
    def commit_message_first_line(self):
        return self.commit_message.split("\n", 1)[0]

    def addLandingTarget(self, registrant, merge_target,
                         merge_prerequisite=None, whiteboard=None,
                         date_created=None, needs_review=None,
                         description=None, review_requests=None,
                         commit_message=None):
        """See `IGitRef`."""
        if not self.namespace.supports_merge_proposals:
            raise InvalidBranchMergeProposal(
                "%s repositories do not support merge proposals." %
                self.namespace.name)
        if self == merge_target:
            raise InvalidBranchMergeProposal(
                "Source and target references must be different.")
        if not merge_target.repository.isRepositoryMergeable(self.repository):
            raise InvalidBranchMergeProposal(
                "%s is not mergeable into %s" % (
                    self.identity, merge_target.identity))
        if merge_prerequisite is not None:
            if not merge_target.repository.isRepositoryMergeable(
                    merge_prerequisite.repository):
                raise InvalidBranchMergeProposal(
                    "%s is not mergeable into %s" % (
                        merge_prerequisite.identity, self.identity))
            if self == merge_prerequisite:
                raise InvalidBranchMergeProposal(
                    "Source and prerequisite references must be different.")
            if merge_target == merge_prerequisite:
                raise InvalidBranchMergeProposal(
                    "Target and prerequisite references must be different.")

        getter = BranchMergeProposalGetter
        for existing_proposal in getter.activeProposalsForBranches(
                self, merge_target):
            raise BranchMergeProposalExists(existing_proposal)

        if date_created is None:
            date_created = UTC_NOW

        if needs_review:
            queue_status = BranchMergeProposalStatus.NEEDS_REVIEW
            date_review_requested = date_created
        else:
            queue_status = BranchMergeProposalStatus.WORK_IN_PROGRESS
            date_review_requested = None

        if review_requests is None:
            review_requests = []

        # If no reviewer is specified, use the default for the branch.
        if len(review_requests) == 0:
            review_requests.append((merge_target.code_reviewer, None))

        kwargs = {}
        for prefix, obj in (
                ("source", self),
                ("target", merge_target),
                ("prerequisite", merge_prerequisite)):
            if obj is not None:
                kwargs["%s_git_repository" % prefix] = obj.repository
                kwargs["%s_git_path" % prefix] = obj.path
                kwargs["%s_git_commit_sha1" % prefix] = obj.commit_sha1

        bmp = BranchMergeProposal(
            registrant=registrant, whiteboard=whiteboard,
            date_created=date_created,
            date_review_requested=date_review_requested,
            queue_status=queue_status, commit_message=commit_message,
            description=description, **kwargs)

        for reviewer, review_type in review_requests:
            bmp.nominateReviewer(
                reviewer, registrant, review_type, _notify_listeners=False)

        notify(ObjectCreatedEvent(bmp, user=registrant))
        if needs_review:
            notify(BranchMergeProposalNeedsReviewEvent(bmp))

        return bmp

    def createMergeProposal(self, registrant, merge_target,
                            merge_prerequisite=None, needs_review=True,
                            initial_comment=None, commit_message=None,
                            reviewers=None, review_types=None):
        """See `IGitRef`."""
        if reviewers is None:
            reviewers = []
        if review_types is None:
            review_types = []
        if len(reviewers) != len(review_types):
            raise WrongNumberOfReviewTypeArguments(
                'reviewers and review_types must be equal length.')
        review_requests = zip(reviewers, review_types)
        return self.addLandingTarget(
            registrant, merge_target, merge_prerequisite,
            needs_review=needs_review, description=initial_comment,
            commit_message=commit_message, review_requests=review_requests)


@implementer(IGitRef)
class GitRefFrozen(GitRefMixin):
    """A frozen Git reference.

    This is like a GitRef, but is frozen at a particular commit, even if the
    real reference has moved on or has been deleted.  It isn't necessarily
    backed by a real database object, and will retrieve columns from the
    database when required.  Use this when you have a
    repository/path/commit_sha1 that you want to pass around as a single
    object, but don't necessarily know that the ref still exists.
    """

    def __init__(self, repository, path, commit_sha1):
        self.repository_id = repository.id
        self.repository = repository
        self.path = path
        self.commit_sha1 = commit_sha1

    @property
    def _self_in_database(self):
        """Return the equivalent database-backed record of self."""
        ref = IStore(GitRef).get(GitRef, (self.repository_id, self.path))
        if ref is None:
            raise NotFoundError(
                "Repository '%s' does not currently contain a reference named "
                "'%s'" % (self.repository, self.path))
        return ref

    def __getattr__(self, name):
        return getattr(self._self_in_database, name)

    def __setattr__(self, name, value):
        if name in ("repository_id", "repository", "path", "commit_sha1"):
            self.__dict__[name] = value
        else:
            setattr(self._self_in_database, name, value)

    def __eq__(self, other):
        return (
            self.repository == other.repository and
            self.path == other.path and
            self.commit_sha1 == other.commit_sha1)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.repository) ^ hash(self.path) ^ hash(self.commit_sha1)
