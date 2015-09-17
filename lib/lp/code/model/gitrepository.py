# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'get_git_repository_privacy_filter',
    'GitRepository',
    'GitRepositorySet',
    ]

from datetime import datetime
import email
from functools import partial
from itertools import (
    chain,
    groupby,
    )
from operator import attrgetter
from urllib import quote_plus

from bzrlib import urlutils
import pytz
from storm.databases.postgres import Returning
from storm.expr import (
    And,
    Coalesce,
    Insert,
    Join,
    Not,
    Or,
    Select,
    SQL,
    )
from storm.info import (
    ClassAlias,
    get_cls_info,
    )
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Unicode,
    )
from storm.store import Store
from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer
from zope.security.interfaces import Unauthorized
from zope.security.proxy import (
    ProxyFactory,
    removeSecurityProxy,
    )

from lp import _ as msg
from lp.app.enums import (
    InformationType,
    PRIVATE_INFORMATION_TYPES,
    PUBLIC_INFORMATION_TYPES,
    )
from lp.app.errors import (
    SubscriptionPrivacyViolation,
    UserCannotUnsubscribePerson,
    )
from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.launchpad import (
    ILaunchpadCelebrities,
    IPrivacy,
    )
from lp.app.interfaces.services import IService
from lp.code.enums import GitObjectType
from lp.code.errors import (
    CannotDeleteGitRepository,
    GitDefaultConflict,
    GitTargetError,
    NoSuchGitReference,
    )
from lp.code.event.git import GitRefsUpdatedEvent
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES,
    notify_modified,
    )
from lp.code.interfaces.gitcollection import (
    IAllGitRepositories,
    IGitCollection,
    )
from lp.code.interfaces.githosting import IGitHostingClient
from lp.code.interfaces.gitlookup import IGitLookup
from lp.code.interfaces.gitnamespace import (
    get_git_namespace,
    IGitNamespacePolicy,
    )
from lp.code.interfaces.gitrepository import (
    GitIdentityMixin,
    IGitRepository,
    IGitRepositorySet,
    user_has_special_git_repository_access,
    )
from lp.code.interfaces.revision import IRevisionSet
from lp.code.mail.branch import send_git_repository_modified_notifications
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.gitref import GitRef
from lp.code.model.gitsubscription import GitSubscription
from lp.registry.enums import PersonVisibility
from lp.registry.errors import CannotChangeInformationType
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifactGrantSource,
    IAccessArtifactSource,
    IAccessPolicySource,
    )
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.role import IHasOwner
from lp.registry.interfaces.sharingjob import (
    IRemoveArtifactSubscriptionsJobSource,
    )
from lp.registry.model.accesspolicy import (
    AccessPolicyGrant,
    reconcile_access_for_artifact,
    )
from lp.registry.model.person import Person
from lp.registry.model.teammembership import TeamParticipation
from lp.services.config import config
from lp.services.database import bulk
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.database.stormexpr import (
    Array,
    ArrayAgg,
    ArrayIntersects,
    BulkUpdate,
    Values,
    )
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.mail.notificationrecipientset import NotificationRecipientSet
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.services.webapp.authorization import available_with_permission
from lp.services.webhooks.interfaces import IWebhookSet
from lp.services.webhooks.model import WebhookTargetMixin


object_type_map = {
    "commit": GitObjectType.COMMIT,
    "tree": GitObjectType.TREE,
    "blob": GitObjectType.BLOB,
    "tag": GitObjectType.TAG,
    }


def git_repository_modified(repository, event):
    """Update the date_last_modified property when a GitRepository is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Git repositories.
    """
    if event.edited_fields:
        repository.date_last_modified = UTC_NOW
        send_git_repository_modified_notifications(repository, event)


@implementer(IGitRepository, IHasOwner, IPrivacy, IInformationType)
class GitRepository(StormBase, WebhookTargetMixin, GitIdentityMixin):
    """See `IGitRepository`."""

    __storm_table__ = 'GitRepository'

    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    owner_id = Int(name='owner', allow_none=False)
    owner = Reference(owner_id, 'Person.id')

    reviewer_id = Int(name='reviewer', allow_none=True)
    reviewer = Reference(reviewer_id, 'Person.id')

    project_id = Int(name='project', allow_none=True)
    project = Reference(project_id, 'Product.id')

    distribution_id = Int(name='distribution', allow_none=True)
    distribution = Reference(distribution_id, 'Distribution.id')

    sourcepackagename_id = Int(name='sourcepackagename', allow_none=True)
    sourcepackagename = Reference(sourcepackagename_id, 'SourcePackageName.id')

    name = Unicode(name='name', allow_none=False)

    description = Unicode(name='description', allow_none=True)

    information_type = EnumCol(enum=InformationType, notNull=True)
    owner_default = Bool(name='owner_default', allow_none=False)
    target_default = Bool(name='target_default', allow_none=False)

    _default_branch = Unicode(name='default_branch', allow_none=True)

    def __init__(self, registrant, owner, target, name, information_type,
                 date_created, reviewer=None, description=None):
        super(GitRepository, self).__init__()
        self.registrant = registrant
        self.owner = owner
        self.reviewer = reviewer
        self.name = name
        self.description = description
        self.information_type = information_type
        self.date_created = date_created
        self.date_last_modified = date_created
        self.project = None
        self.distribution = None
        self.sourcepackagename = None
        if IProduct.providedBy(target):
            self.project = target
        elif IDistributionSourcePackage.providedBy(target):
            self.distribution = target.distribution
            self.sourcepackagename = target.sourcepackagename
        self.owner_default = False
        self.target_default = False

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    @property
    def unique_name(self):
        names = {"owner": self.owner.name, "repository": self.name}
        if self.project is not None:
            fmt = "~%(owner)s/%(project)s"
            names["project"] = self.project.name
        elif self.distribution is not None:
            fmt = "~%(owner)s/%(distribution)s/+source/%(source)s"
            names["distribution"] = self.distribution.name
            names["source"] = self.sourcepackagename.name
        else:
            fmt = "~%(owner)s"
        fmt += "/+git/%(repository)s"
        return fmt % names

    def __repr__(self):
        return "<GitRepository %r (%d)>" % (self.unique_name, self.id)

    @cachedproperty
    def target(self):
        """See `IGitRepository`."""
        if self.project is not None:
            return self.project
        elif self.distribution is not None:
            return self.distribution.getSourcePackage(self.sourcepackagename)
        else:
            return self.owner

    def _checkPersonalPrivateOwnership(self, new_owner):
        if (self.information_type in PRIVATE_INFORMATION_TYPES and
            (not new_owner.is_team or
             new_owner.visibility != PersonVisibility.PRIVATE)):
            raise GitTargetError(
                "Only private teams may have personal private "
                "repositories.")

    def setTarget(self, target, user):
        """See `IGitRepository`."""
        if IPerson.providedBy(target):
            new_owner = IPerson(target)
            self._checkPersonalPrivateOwnership(new_owner)
        else:
            new_owner = self.owner
        namespace = get_git_namespace(target, new_owner)
        if (self.information_type not in
            namespace.getAllowedInformationTypes(user)):
            raise GitTargetError(
                "%s repositories are not allowed for target %s." % (
                    self.information_type.title, target.displayname))
        namespace.moveRepository(self, user, rename_if_necessary=True)
        self._reconcileAccess()

    @property
    def namespace(self):
        """See `IGitRepository`."""
        return get_git_namespace(self.target, self.owner)

    def setOwnerDefault(self, value):
        """See `IGitRepository`."""
        if value:
            # Check for an existing owner-target default.
            repository_set = getUtility(IGitRepositorySet)
            existing = repository_set.getDefaultRepositoryForOwner(
                self.owner, self.target)
            if existing is not None and existing != self:
                raise GitDefaultConflict(
                    existing, self.target, owner=self.owner)
        self.owner_default = value

    def setTargetDefault(self, value):
        """See `IGitRepository`."""
        if value:
            # Check for an existing target default.
            existing = getUtility(IGitRepositorySet).getDefaultRepository(
                self.target)
            if existing is not None and existing != self:
                raise GitDefaultConflict(existing, self.target)
        self.target_default = value
        if IProduct.providedBy(self.target):
            get_property_cache(self.target)._default_git_repository = (
                self if value else None)

    @property
    def display_name(self):
        return self.git_identity

    @property
    def code_reviewer(self):
        """See `IGitRepository`."""
        if self.reviewer:
            return self.reviewer
        else:
            return self.owner

    def isPersonTrustedReviewer(self, reviewer):
        """See `IGitRepository`."""
        if reviewer is None:
            return False
        # We trust Launchpad admins.
        lp_admins = getUtility(ILaunchpadCelebrities).admin
        # Both the branch owner and the review team are checked.
        owner = self.owner
        review_team = self.code_reviewer
        return (
            reviewer.inTeam(owner) or
            reviewer.inTeam(review_team) or
            reviewer.inTeam(lp_admins))

    def getInternalPath(self):
        """See `IGitRepository`."""
        # This may need to change later to improve support for sharding.
        # See also `IGitLookup.getByHostingPath`.
        return str(self.id)

    def getCodebrowseUrl(self):
        """See `IGitRepository`."""
        return urlutils.join(
            config.codehosting.git_browse_root, self.shortened_path)

    def getCodebrowseUrlForRevision(self, commit):
        return "%s/commit/?id=%s" % (
            self.getCodebrowseUrl(), quote_plus(str(commit)))

    @property
    def git_https_url(self):
        """See `IGitRepository`."""
        # XXX wgrant 2015-06-12: This guard should be removed once we
        # support Git HTTPS auth.
        if self.visibleByUser(None):
            return urlutils.join(
                config.codehosting.git_browse_root, self.shortened_path)
        else:
            return None

    @property
    def git_ssh_url(self):
        """See `IGitRepository`."""
        return urlutils.join(
            config.codehosting.git_ssh_root, self.shortened_path)

    @property
    def private(self):
        return self.information_type in PRIVATE_INFORMATION_TYPES

    def _reconcileAccess(self):
        """Reconcile the repository's sharing information.

        Takes the information_type and target and makes the related
        AccessArtifact and AccessPolicyArtifacts match.
        """
        wanted_links = None
        pillars = []
        # For private personal repositories, we calculate the wanted grants.
        if (not self.project and not self.distribution and
            not self.information_type in PUBLIC_INFORMATION_TYPES):
            aasource = getUtility(IAccessArtifactSource)
            [abstract_artifact] = aasource.ensure([self])
            wanted_links = set(
                (abstract_artifact, policy) for policy in
                getUtility(IAccessPolicySource).findByTeam([self.owner]))
        else:
            # We haven't yet quite worked out how distribution privacy
            # works, so only work for projects for now.
            if self.project is not None:
                pillars = [self.project]
        reconcile_access_for_artifact(
            self, self.information_type, pillars, wanted_links)

    @property
    def refs(self):
        """See `IGitRepository`."""
        return Store.of(self).find(
            GitRef, GitRef.repository_id == self.id).order_by(GitRef.path)

    @property
    def branches(self):
        """See `IGitRepository`."""
        return Store.of(self).find(
            GitRef,
            GitRef.repository_id == self.id,
            GitRef.path.startswith(u"refs/heads/")).order_by(GitRef.path)

    @property
    def default_branch(self):
        """See `IGitRepository`."""
        return self._default_branch

    @default_branch.setter
    def default_branch(self, value):
        """See `IGitRepository`."""
        ref = self.getRefByPath(value)
        if ref is None:
            raise NoSuchGitReference(self, value)
        if self._default_branch != ref.path:
            self._default_branch = ref.path
            getUtility(IGitHostingClient).setProperties(
                self.getInternalPath(), default_branch=ref.path)

    def getRefByPath(self, path):
        paths = [path]
        if not path.startswith(u"refs/heads/"):
            paths.append(u"refs/heads/%s" % path)
        for try_path in paths:
            ref = Store.of(self).find(
                GitRef,
                GitRef.repository_id == self.id,
                GitRef.path == try_path).one()
            if ref is not None:
                return ref
        return None

    @staticmethod
    def _convertRefInfo(info):
        """Validate and canonicalise ref info from the hosting service.

        :param info: A dict of {"object":
            {"sha1": sha1, "type": "commit"/"tree"/"blob"/"tag"}}.

        :raises ValueError: if the dict is malformed.
        :return: A dict of {"sha1": sha1, "type": `GitObjectType`}.
        """
        if "object" not in info:
            raise ValueError('ref info does not contain "object" key')
        obj = info["object"]
        if "sha1" not in obj:
            raise ValueError('ref info object does not contain "sha1" key')
        if "type" not in obj:
            raise ValueError('ref info object does not contain "type" key')
        if not isinstance(obj["sha1"], basestring) or len(obj["sha1"]) != 40:
            raise ValueError('ref info sha1 is not a 40-character string')
        if obj["type"] not in object_type_map:
            raise ValueError('ref info type is not a recognised object type')
        sha1 = obj["sha1"]
        if isinstance(sha1, bytes):
            sha1 = sha1.decode("US-ASCII")
        return {"sha1": sha1, "type": object_type_map[obj["type"]]}

    def createOrUpdateRefs(self, refs_info, get_objects=False, logger=None):
        """See `IGitRepository`."""
        def dbify_values(values):
            return [
                list(chain.from_iterable(
                    bulk.dbify_value(col, val)
                    for col, val in zip(columns, value)))
                for value in values]

        # Flush everything up to here, as we may need to invalidate the
        # cache after updating.
        store = Store.of(self)
        store.flush()

        # Try a bulk update first.
        column_names = [
            "repository_id", "path", "commit_sha1", "object_type",
            "author_id", "author_date", "committer_id", "committer_date",
            "commit_message",
            ]
        column_types = [
            ("repository", "integer"),
            ("path", "text"),
            ("commit_sha1", "character(40)"),
            ("object_type", "integer"),
            ("author", "integer"),
            ("author_date", "timestamp without time zone"),
            ("committer", "integer"),
            ("committer_date", "timestamp without time zone"),
            ("commit_message", "text"),
            ]
        columns = [getattr(GitRef, name) for name in column_names]
        values = [
            (self.id, path, info["sha1"], info["type"],
             info.get("author"), info.get("author_date"),
             info.get("committer"), info.get("committer_date"),
             info.get("commit_message"))
            for path, info in refs_info.items()]
        db_values = dbify_values(values)
        new_refs_expr = Values("new_refs", column_types, db_values)
        new_refs = ClassAlias(GitRef, "new_refs")
        updated_columns = {
            getattr(GitRef, name): getattr(new_refs, name)
            for name in column_names if name not in ("repository_id", "path")}
        update_filter = And(
            GitRef.repository_id == new_refs.repository_id,
            GitRef.path == new_refs.path)
        primary_key = get_cls_info(GitRef).primary_key
        updated = list(store.execute(Returning(BulkUpdate(
            updated_columns, table=GitRef, values=new_refs_expr,
            where=update_filter, primary_columns=primary_key))))
        if updated:
            # Some existing GitRef objects may no longer be valid.  Without
            # knowing which ones we already have, it's safest to just
            # invalidate everything.
            store.invalidate()

        # If there are any remaining items, create them.
        create_db_values = dbify_values([
            value for value in values if (value[0], value[1]) not in updated])
        if create_db_values:
            created = list(store.execute(Returning(Insert(
                columns, values=create_db_values,
                primary_columns=primary_key))))
        else:
            created = []

        self.date_last_modified = UTC_NOW
        if updated:
            notify(GitRefsUpdatedEvent(
                self, [value[1] for value in updated], logger))
        if get_objects:
            return bulk.load(GitRef, updated + created)

    def removeRefs(self, paths):
        """See `IGitRepository`."""
        Store.of(self).find(
            GitRef,
            GitRef.repository == self, GitRef.path.is_in(paths)).remove()
        self.date_last_modified = UTC_NOW

    def planRefChanges(self, hosting_path, logger=None):
        """See `IGitRepository`."""
        hosting_client = getUtility(IGitHostingClient)
        new_refs = {}
        for path, info in hosting_client.getRefs(hosting_path).items():
            try:
                new_refs[path] = self._convertRefInfo(info)
            except ValueError as e:
                if logger is not None:
                    logger.warning(
                        "Unconvertible ref %s %s: %s" % (path, info, e))
        current_refs = {ref.path: ref for ref in self.refs}
        refs_to_upsert = {}
        for path, info in new_refs.items():
            current_ref = current_refs.get(path)
            if (current_ref is None or
                info["sha1"] != current_ref.commit_sha1 or
                info["type"] != current_ref.object_type):
                refs_to_upsert[path] = info
            elif (info["type"] == GitObjectType.COMMIT and
                  (current_ref.author_id is None or
                   current_ref.author_date is None or
                   current_ref.committer_id is None or
                   current_ref.committer_date is None or
                   current_ref.commit_message is None)):
                # Only request detailed commit metadata for refs that point
                # to commits.
                refs_to_upsert[path] = info
        refs_to_remove = set(current_refs) - set(new_refs)
        return refs_to_upsert, refs_to_remove

    @staticmethod
    def fetchRefCommits(hosting_path, refs, logger=None):
        """See `IGitRepository`."""
        oids = sorted(set(info["sha1"] for info in refs.values()))
        commits = {
            commit.get("sha1"): commit
            for commit in getUtility(IGitHostingClient).getCommits(
                hosting_path, oids, logger=logger)}
        authors_to_acquire = []
        committers_to_acquire = []
        for info in refs.values():
            commit = commits.get(info["sha1"])
            if commit is None:
                continue
            author = commit.get("author")
            if author is not None:
                if "time" in author:
                    info["author_date"] = datetime.fromtimestamp(
                        author["time"], tz=pytz.UTC)
                if "name" in author and "email" in author:
                    author_addr = email.utils.formataddr(
                        (author["name"], author["email"]))
                    info["author_addr"] = author_addr
                    authors_to_acquire.append(author_addr)
            committer = commit.get("committer")
            if committer is not None:
                if "time" in committer:
                    info["committer_date"] = datetime.fromtimestamp(
                        committer["time"], tz=pytz.UTC)
                if "name" in committer and "email" in committer:
                    committer_addr = email.utils.formataddr(
                        (committer["name"], committer["email"]))
                    info["committer_addr"] = committer_addr
                    committers_to_acquire.append(committer_addr)
            if "message" in commit:
                info["commit_message"] = commit["message"]
        revision_authors = getUtility(IRevisionSet).acquireRevisionAuthors(
            authors_to_acquire + committers_to_acquire)
        for info in refs.values():
            author = revision_authors.get(info.get("author_addr"))
            if author is not None:
                info["author"] = author.id
            committer = revision_authors.get(info.get("committer_addr"))
            if committer is not None:
                info["committer"] = committer.id

    def synchroniseRefs(self, refs_to_upsert, refs_to_remove, logger=None):
        """See `IGitRepository`."""
        if refs_to_upsert:
            self.createOrUpdateRefs(refs_to_upsert, logger=logger)
        if refs_to_remove:
            self.removeRefs(refs_to_remove)

    @cachedproperty
    def _known_viewers(self):
        """A set of known persons able to view this repository.

        This method must return an empty set or repository searches will
        trigger late evaluation.  Any 'should be set on load' properties
        must be done by the repository search.

        If you are tempted to change this method, don't. Instead see
        visibleByUser which defines the just-in-time policy for repository
        visibility, and IGitCollection which honours visibility rules.
        """
        return set()

    def visibleByUser(self, user):
        """See `IGitRepository`."""
        if self.information_type in PUBLIC_INFORMATION_TYPES:
            return True
        elif user is None:
            return False
        elif user.id in self._known_viewers:
            return True
        else:
            return not getUtility(IAllGitRepositories).withIds(
                self.id).visibleByUser(user).is_empty()

    def getAllowedInformationTypes(self, user):
        """See `IGitRepository`."""
        if user_has_special_git_repository_access(user):
            # Admins can set any type.
            types = set(PUBLIC_INFORMATION_TYPES + PRIVATE_INFORMATION_TYPES)
        else:
            # Otherwise the permitted types are defined by the namespace.
            policy = IGitNamespacePolicy(self.namespace)
            types = set(policy.getAllowedInformationTypes(user))
        return types

    def transitionToInformationType(self, information_type, user,
                                    verify_policy=True):
        """See `IGitRepository`."""
        if self.information_type == information_type:
            return
        if (verify_policy and
            information_type not in self.getAllowedInformationTypes(user)):
            raise CannotChangeInformationType("Forbidden by project policy.")
        self.information_type = information_type
        self._reconcileAccess()
        if (information_type in PRIVATE_INFORMATION_TYPES and
                not self.subscribers.is_empty()):
            # Grant the subscriber access if they can't see the repository.
            service = getUtility(IService, "sharing")
            blind_subscribers = service.getPeopleWithoutAccess(
                self, self.subscribers)
            if len(blind_subscribers):
                service.ensureAccessGrants(
                    blind_subscribers, user, gitrepositories=[self],
                    ignore_permissions=True)
        # As a result of the transition, some subscribers may no longer have
        # access to the repository.  We need to run a job to remove any such
        # subscriptions.
        getUtility(IRemoveArtifactSubscriptionsJobSource).create(user, [self])

    def setName(self, new_name, user):
        """See `IGitRepository`."""
        self.namespace.moveRepository(self, user, new_name=new_name)

    def setOwner(self, new_owner, user):
        """See `IGitRepository`."""
        if self.owner == self.target:
            self._checkPersonalPrivateOwnership(new_owner)
            new_target = new_owner
        else:
            new_target = self.target
        new_namespace = get_git_namespace(new_target, new_owner)
        new_namespace.moveRepository(self, user, rename_if_necessary=True)
        self._reconcileAccess()

    @property
    def subscriptions(self):
        return Store.of(self).find(
            GitSubscription,
            GitSubscription.repository == self)

    @property
    def subscribers(self):
        return Store.of(self).find(
            Person,
            GitSubscription.person_id == Person.id,
            GitSubscription.repository == self)

    def userCanBeSubscribed(self, person):
        """See `IGitRepository`."""
        return not (
            person.is_team and
            self.information_type in PRIVATE_INFORMATION_TYPES and
            person.anyone_can_join())

    def subscribe(self, person, notification_level, max_diff_lines,
                  code_review_level, subscribed_by):
        """See `IGitRepository`."""
        if not self.userCanBeSubscribed(person):
            raise SubscriptionPrivacyViolation(
                "Open and delegated teams cannot be subscribed to private "
                "repositories.")
        # If the person is already subscribed, update the subscription with
        # the specified notification details.
        subscription = self.getSubscription(person)
        if subscription is None:
            subscription = GitSubscription(
                person=person, repository=self,
                notification_level=notification_level,
                max_diff_lines=max_diff_lines, review_level=code_review_level,
                subscribed_by=subscribed_by)
            Store.of(subscription).flush()
        else:
            subscription.notification_level = notification_level
            subscription.max_diff_lines = max_diff_lines
            subscription.review_level = code_review_level
        # Grant the subscriber access if they can't see the repository.
        service = getUtility(IService, "sharing")
        _, _, repositories, _ = service.getVisibleArtifacts(
            person, gitrepositories=[self], ignore_permissions=True)
        if not repositories:
            service.ensureAccessGrants(
                [person], subscribed_by, gitrepositories=[self],
                ignore_permissions=True)
        return subscription

    def getSubscription(self, person):
        """See `IGitRepository`."""
        if person is None:
            return None
        return Store.of(self).find(
            GitSubscription,
            GitSubscription.person == person,
            GitSubscription.repository == self).one()

    def getSubscriptionsByLevel(self, notification_levels):
        """See `IGitRepository`."""
        # XXX: JonathanLange 2009-05-07 bug=373026: This is only used by real
        # code to determine whether there are any subscribers at the given
        # notification levels. The only code that cares about the actual
        # object is in a test:
        # test_only_nodiff_subscribers_means_no_diff_generated.
        return Store.of(self).find(
            GitSubscription,
            GitSubscription.repository == self,
            GitSubscription.notification_level.is_in(notification_levels))

    def hasSubscription(self, person):
        """See `IGitRepository`."""
        return self.getSubscription(person) is not None

    def unsubscribe(self, person, unsubscribed_by, ignore_permissions=False):
        """See `IGitRepository`."""
        subscription = self.getSubscription(person)
        if subscription is None:
            # Silent success seems order of the day (like bugs).
            return
        if (not ignore_permissions
            and not subscription.canBeUnsubscribedByUser(unsubscribed_by)):
            raise UserCannotUnsubscribePerson(
                '%s does not have permission to unsubscribe %s.' % (
                    unsubscribed_by.displayname,
                    person.displayname))
        store = Store.of(subscription)
        store.remove(subscription)
        artifact = getUtility(IAccessArtifactSource).find([self])
        getUtility(IAccessArtifactGrantSource).revokeByArtifact(
            artifact, [person])
        store.flush()

    def getNotificationRecipients(self):
        """See `IGitRepository`."""
        recipients = NotificationRecipientSet()
        for subscription in self.subscriptions:
            if subscription.person.is_team:
                rationale = 'Subscriber @%s' % subscription.person.name
            else:
                rationale = 'Subscriber'
            recipients.add(subscription.person, subscription, rationale)
        return recipients

    @property
    def landing_targets(self):
        """See `IGitRepository`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.source_git_repository == self)

    def getActiveLandingTargets(self, paths):
        """Merge proposals not in final states where these refs are source."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.source_git_repository == self,
            BranchMergeProposal.source_git_path.is_in(paths),
            Not(BranchMergeProposal.queue_status.is_in(
                BRANCH_MERGE_PROPOSAL_FINAL_STATES)))

    @property
    def landing_candidates(self):
        """See `IGitRepository`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.target_git_repository == self,
            Not(BranchMergeProposal.queue_status.is_in(
                BRANCH_MERGE_PROPOSAL_FINAL_STATES)))

    def getActiveLandingCandidates(self, paths):
        """Merge proposals not in final states where these refs are target."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.target_git_repository == self,
            BranchMergeProposal.target_git_path.is_in(paths),
            Not(BranchMergeProposal.queue_status.is_in(
                BRANCH_MERGE_PROPOSAL_FINAL_STATES)))

    @property
    def dependent_landings(self):
        """See `IGitRepository`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.prerequisite_git_repository == self,
            Not(BranchMergeProposal.queue_status.is_in(
                BRANCH_MERGE_PROPOSAL_FINAL_STATES)))

    def getMergeProposalByID(self, id):
        """See `IGitRepository`."""
        return self.landing_targets.find(BranchMergeProposal.id == id).one()

    def isRepositoryMergeable(self, other):
        """See `IGitRepository`."""
        return self.namespace.areRepositoriesMergeable(other.namespace)

    @property
    def pending_writes(self):
        """See `IGitRepository`."""
        from lp.code.model.gitjob import (
            GitJob,
            GitJobType,
            )
        jobs = Store.of(self).find(
            GitJob,
            GitJob.repository == self,
            GitJob.job_type == GitJobType.REF_SCAN,
            GitJob.job == Job.id,
            Job._status.is_in([JobStatus.WAITING, JobStatus.RUNNING]))
        return not jobs.is_empty()

    def updateMergeCommitIDs(self, paths):
        """See `IGitRepository`."""
        store = Store.of(self)
        refs = {
            path: commit_sha1 for path, commit_sha1 in store.find(
                (GitRef.path, GitRef.commit_sha1),
                GitRef.repository_id == self.id,
                GitRef.path.is_in(paths))}
        updated = set()
        for kind in ("source", "target", "prerequisite"):
            repository_name = "%s_git_repositoryID" % kind
            path_name = "%s_git_path" % kind
            commit_sha1_name = "%s_git_commit_sha1" % kind
            old_column = partial(getattr, BranchMergeProposal)
            db_kind = "dependent" if kind == "prerequisite" else kind
            column_types = [
                ("%s_git_path" % db_kind, "text"),
                ("%s_git_commit_sha1" % db_kind, "character(40)"),
                ]
            db_values = [(
                bulk.dbify_value(old_column(path_name), path),
                bulk.dbify_value(old_column(commit_sha1_name), commit_sha1)
                ) for path, commit_sha1 in refs.items()]
            new_proposals_expr = Values(
                "new_proposals", column_types, db_values)
            new_proposals = ClassAlias(BranchMergeProposal, "new_proposals")
            new_column = partial(getattr, new_proposals)
            updated_columns = {
                old_column(commit_sha1_name): new_column(commit_sha1_name)}
            update_filter = And(
                old_column(repository_name) == self.id,
                old_column(path_name) == new_column(path_name),
                Not(BranchMergeProposal.queue_status.is_in(
                    BRANCH_MERGE_PROPOSAL_FINAL_STATES)))
            result = store.execute(Returning(BulkUpdate(
                updated_columns, table=BranchMergeProposal,
                values=new_proposals_expr, where=update_filter,
                primary_columns=BranchMergeProposal.id)))
            updated.update(item[0] for item in result)
        if updated:
            # Some existing BranchMergeProposal objects may no longer be
            # valid.  Without knowing which ones we already have, it's
            # safest to just invalidate everything.
            store.invalidate()
        return updated

    def scheduleDiffUpdates(self, paths):
        """See `IGitRepository`."""
        from lp.code.model.branchmergeproposaljob import UpdatePreviewDiffJob
        jobs = []
        for merge_proposal in self.getActiveLandingTargets(paths):
            jobs.append(UpdatePreviewDiffJob.create(merge_proposal))
        return jobs

    def _markProposalMerged(self, proposal, merged_revision_id, logger=None):
        if logger is not None:
            logger.info(
                "Merge detected: %s => %s",
                proposal.source_git_ref.identity,
                proposal.target_git_ref.identity)
        notify_modified(
            proposal, proposal.markAsMerged,
            merged_revision_id=merged_revision_id)

    def detectMerges(self, paths, logger=None):
        """See `IGitRepository`."""
        hosting_client = getUtility(IGitHostingClient)
        all_proposals = self.getActiveLandingCandidates(paths).order_by(
            BranchMergeProposal.target_git_path)
        for _, group in groupby(all_proposals, attrgetter("target_git_path")):
            proposals = list(group)
            merges = hosting_client.detectMerges(
                self.getInternalPath(), proposals[0].target_git_commit_sha1,
                set(proposal.source_git_commit_sha1 for proposal in proposals))
            for proposal in proposals:
                merged_revision_id = merges.get(
                    proposal.source_git_commit_sha1)
                if merged_revision_id is not None:
                    self._markProposalMerged(
                        proposal, merged_revision_id, logger=logger)

    def canBeDeleted(self):
        """See `IGitRepository`."""
        # Can't delete if the repository is associated with anything.
        return len(self.getDeletionRequirements()) == 0

    def _getDeletionRequirements(self):
        """Determine what operations must be performed to delete this branch.

        Two dictionaries are returned, one for items that must be deleted,
        one for items that must be altered.  The item in question is the
        key, and the value is a user-facing string explaining why the item
        is affected.

        As well as the dictionaries, this method returns two list of callables
        that may be called to perform the alterations and deletions needed.
        """
        from lp.snappy.interfaces.snap import ISnapSet

        alteration_operations = []
        deletion_operations = []
        # Merge proposals require their source and target repositories to
        # exist.
        for merge_proposal in self.landing_targets:
            deletion_operations.append(
                DeletionCallable(
                    merge_proposal,
                    msg("This repository is the source repository of this "
                        "merge proposal."),
                    merge_proposal.deleteProposal))
        # Cannot use self.landing_candidates, because it ignores merged
        # merge proposals.
        for merge_proposal in BranchMergeProposal.selectBy(
            target_git_repository=self):
            deletion_operations.append(
                DeletionCallable(
                    merge_proposal,
                    msg("This repository is the target repository of this "
                        "merge proposal."),
                    merge_proposal.deleteProposal))
        for merge_proposal in BranchMergeProposal.selectBy(
            prerequisite_git_repository=self):
            alteration_operations.append(
                ClearPrerequisiteRepository(merge_proposal))
        if not getUtility(ISnapSet).findByContext(self).is_empty():
            alteration_operations.append(DeletionCallable(
                None, msg("Some snap packages build from this repository."),
                getUtility(ISnapSet).detachFromGitRepository, self))

        return (alteration_operations, deletion_operations)

    def getDeletionRequirements(self):
        """See `IGitRepository`."""
        alteration_operations, deletion_operations = (
            self._getDeletionRequirements())
        result = {
            operation.affected_object: ("alter", operation.rationale)
            for operation in alteration_operations}
        # Deletion entries should overwrite alteration entries.
        result.update({
            operation.affected_object: ("delete", operation.rationale)
            for operation in deletion_operations})
        return result

    def _breakReferences(self):
        """Break all external references to this repository.

        NULLable references will be NULLed.  References which are not NULLable
        will cause the item holding the reference to be deleted.

        This function is guaranteed to perform the operations predicted by
        getDeletionRequirements, because it uses the same backing function.
        """
        alteration_operations, deletion_operations = (
            self._getDeletionRequirements())
        for operation in alteration_operations:
            operation()
        for operation in deletion_operations:
            operation()
        Store.of(self).flush()

    def _deleteRepositoryAccessGrants(self):
        """Delete access grants for this repository prior to deleting it."""
        getUtility(IAccessArtifactSource).delete([self])

    def _deleteRepositorySubscriptions(self):
        """Delete subscriptions for this repository prior to deleting it."""
        subscriptions = Store.of(self).find(
            GitSubscription, GitSubscription.repository == self)
        subscriptions.remove()

    def _deleteJobs(self):
        """Delete jobs for this repository prior to deleting it.

        This deletion includes `GitJob`s associated with the branch.
        """
        # Circular import.
        from lp.code.model.gitjob import GitJob

        # Remove GitJobs.
        affected_jobs = Select(
            [GitJob.job_id],
            And(GitJob.job == Job.id, GitJob.repository == self))
        Store.of(self).find(Job, Job.id.is_in(affected_jobs)).remove()

    def destroySelf(self, break_references=False):
        """See `IGitRepository`."""
        # Circular import.
        from lp.code.interfaces.gitjob import (
            IReclaimGitRepositorySpaceJobSource,
            )

        if break_references:
            self._breakReferences()
        if not self.canBeDeleted():
            raise CannotDeleteGitRepository(
                "Cannot delete Git repository: %s" % self.unique_name)

        self.refs.remove()
        self._deleteRepositoryAccessGrants()
        self._deleteRepositorySubscriptions()
        self._deleteJobs()
        getUtility(IWebhookSet).delete(self.webhooks)

        # Now destroy the repository.
        repository_name = self.unique_name
        repository_path = self.getInternalPath()
        Store.of(self).remove(self)
        # And now create a job to remove the repository from storage when
        # it's done.
        getUtility(IReclaimGitRepositorySpaceJobSource).create(
            repository_name, repository_path)


class DeletionOperation:
    """Represent an operation to perform as part of branch deletion."""

    def __init__(self, affected_object, rationale):
        self.affected_object = ProxyFactory(affected_object)
        self.rationale = rationale

    def __call__(self):
        """Perform the deletion operation."""
        raise NotImplementedError(DeletionOperation.__call__)


class DeletionCallable(DeletionOperation):
    """Deletion operation that invokes a callable."""

    def __init__(self, affected_object, rationale, func, *args, **kwargs):
        super(DeletionCallable, self).__init__(affected_object, rationale)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        self.func(*self.args, **self.kwargs)


class ClearPrerequisiteRepository(DeletionOperation):
    """Delete operation that clears a merge proposal's prerequisite
    repository."""

    def __init__(self, merge_proposal):
        DeletionOperation.__init__(
            self, merge_proposal,
            msg("This repository is the prerequisite repository of this merge "
                "proposal."))

    def __call__(self):
        self.affected_object.prerequisite_git_repository = None
        self.affected_object.prerequisite_git_path = None
        self.affected_object.prerequisite_git_commit_sha1 = None


@implementer(IGitRepositorySet)
class GitRepositorySet:
    """See `IGitRepositorySet`."""

    def new(self, registrant, owner, target, name, information_type=None,
            date_created=DEFAULT, description=None):
        """See `IGitRepositorySet`."""
        namespace = get_git_namespace(target, owner)
        return namespace.createRepository(
            registrant, name, information_type=information_type,
            date_created=date_created, description=description)

    def getByPath(self, user, path):
        """See `IGitRepositorySet`."""
        repository, extra_path = getUtility(IGitLookup).getByPath(path)
        if repository is None or extra_path:
            return None
        # removeSecurityProxy is safe here since we're explicitly performing
        # a permission check.
        if removeSecurityProxy(repository).visibleByUser(user):
            return repository
        return None

    def getRepositories(self, user, target):
        """See `IGitRepositorySet`."""
        collection = IGitCollection(target).visibleByUser(user)
        return collection.getRepositories(eager_load=True)

    def getRepositoryVisibilityInfo(self, user, person, repository_names):
        """See `IGitRepositorySet`."""
        if user is None:
            return dict()
        lookup = getUtility(IGitLookup)
        visible_repositories = []
        for name in repository_names:
            repository = lookup.getByUniqueName(name)
            try:
                if (repository is not None
                        and repository.visibleByUser(user)
                        and repository.visibleByUser(person)):
                    visible_repositories.append(repository.unique_name)
            except Unauthorized:
                # We don't include repositories user cannot see.
                pass
        return {
            'person_name': person.displayname,
            'visible_repositories': visible_repositories,
            }

    def getDefaultRepository(self, target):
        """See `IGitRepositorySet`."""
        clauses = [GitRepository.target_default == True]
        if IProduct.providedBy(target):
            clauses.append(GitRepository.project == target)
        elif IDistributionSourcePackage.providedBy(target):
            clauses.append(GitRepository.distribution == target.distribution)
            clauses.append(
                GitRepository.sourcepackagename == target.sourcepackagename)
        else:
            raise GitTargetError(
                "Personal repositories cannot be defaults for any target.")
        return IStore(GitRepository).find(GitRepository, *clauses).one()

    def getDefaultRepositoryForOwner(self, owner, target):
        """See `IGitRepositorySet`."""
        clauses = [
            GitRepository.owner == owner,
            GitRepository.owner_default == True,
            ]
        if IProduct.providedBy(target):
            clauses.append(GitRepository.project == target)
        elif IDistributionSourcePackage.providedBy(target):
            clauses.append(GitRepository.distribution == target.distribution)
            clauses.append(
                GitRepository.sourcepackagename == target.sourcepackagename)
        else:
            raise GitTargetError(
                "Personal repositories cannot be defaults for any target.")
        return IStore(GitRepository).find(GitRepository, *clauses).one()

    @available_with_permission('launchpad.Edit', 'target')
    def setDefaultRepository(self, target, repository):
        """See `IGitRepositorySet`."""
        if IPerson.providedBy(target):
            raise GitTargetError(
                "Cannot set a default Git repository for a person, only "
                "for a project or a package.")
        if repository is not None:
            if repository.target != target:
                raise GitTargetError(
                    "Cannot set default Git repository to one attached to "
                    "another target.")
            repository.setTargetDefault(True)
        else:
            previous = self.getDefaultRepository(target)
            if previous is not None:
                previous.setTargetDefault(False)

    def setDefaultRepositoryForOwner(self, owner, target, repository, user):
        """See `IGitRepositorySet`."""
        if not user.inTeam(owner):
            if owner.is_team:
                raise Unauthorized(
                    "%s is not a member of %s" %
                    (user.displayname, owner.displayname))
            else:
                raise Unauthorized(
                    "%s cannot set a default Git repository for %s" %
                    (user.displayname, owner.displayname))
        if IPerson.providedBy(target):
            raise GitTargetError(
                "Cannot set a default Git repository for a person, only "
                "for a project or a package.")
        if repository is not None:
            if repository.target != target:
                raise GitTargetError(
                    "Cannot set default Git repository to one attached to "
                    "another target.")
            if repository.owner != owner:
                raise GitTargetError(
                    "Cannot set a person's default Git repository to one "
                    "owned by somebody else.")
            repository.setOwnerDefault(True)
        else:
            previous = self.getDefaultRepositoryForOwner(owner, target)
            if previous is not None:
                previous.setOwnerDefault(False)

    def empty_list(self):
        """See `IGitRepositorySet`."""
        return []

    @staticmethod
    def preloadDefaultRepositoriesForProjects(projects):
        repositories = bulk.load_referencing(
            GitRepository, projects, ["project_id"],
            extra_conditions=[GitRepository.target_default == True])
        return {
            repository.project_id: repository for repository in repositories}


def get_git_repository_privacy_filter(user, repository_class=GitRepository):
    public_filter = repository_class.information_type.is_in(
        PUBLIC_INFORMATION_TYPES)

    if user is None:
        return [public_filter]

    artifact_grant_query = Coalesce(
        ArrayIntersects(
            SQL("%s.access_grants" % repository_class.__storm_table__),
            Select(
                ArrayAgg(TeamParticipation.teamID),
                tables=TeamParticipation,
                where=(TeamParticipation.person == user)
            )), False)

    policy_grant_query = Coalesce(
        ArrayIntersects(
            Array(SQL("%s.access_policy" % repository_class.__storm_table__)),
            Select(
                ArrayAgg(AccessPolicyGrant.policy_id),
                tables=(AccessPolicyGrant,
                        Join(TeamParticipation,
                            TeamParticipation.teamID ==
                            AccessPolicyGrant.grantee_id)),
                where=(TeamParticipation.person == user)
            )), False)

    return [Or(public_filter, artifact_grant_query, policy_grant_query)]
