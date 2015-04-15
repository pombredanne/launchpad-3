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
from itertools import chain

from bzrlib import urlutils
import pytz
from storm.databases.postgres import Returning
from storm.expr import (
    And,
    Coalesce,
    Insert,
    Join,
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
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

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
from lp.app.interfaces.launchpad import IPrivacy
from lp.app.interfaces.services import IService
from lp.code.enums import GitObjectType
from lp.code.errors import (
    GitDefaultConflict,
    GitFeatureDisabled,
    GitTargetError,
    )
from lp.code.interfaces.gitcollection import (
    IAllGitRepositories,
    IGitCollection,
    )
from lp.code.interfaces.gitlookup import IGitLookup
from lp.code.interfaces.gitnamespace import (
    get_git_namespace,
    IGitNamespacePolicy,
    )
from lp.code.interfaces.gitrepository import (
    GIT_FEATURE_FLAG,
    GitIdentityMixin,
    IGitRepository,
    IGitRepositorySet,
    user_has_special_git_repository_access,
    )
from lp.code.interfaces.revision import IRevisionSet
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
from lp.services.features import getFeatureFlag
from lp.services.propertycache import cachedproperty
from lp.services.webapp.authorization import available_with_permission


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
    repository.date_last_modified = UTC_NOW


class GitRepository(StormBase, GitIdentityMixin):
    """See `IGitRepository`."""

    __storm_table__ = 'GitRepository'

    implements(IGitRepository, IHasOwner, IPrivacy, IInformationType)

    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    owner_id = Int(name='owner', allow_none=False)
    owner = Reference(owner_id, 'Person.id')

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

    def __init__(self, registrant, owner, target, name, information_type,
                 date_created, description=None):
        if not getFeatureFlag(GIT_FEATURE_FLAG):
            raise GitFeatureDisabled
        super(GitRepository, self).__init__()
        self.registrant = registrant
        self.owner = owner
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

    def setTarget(self, target, user):
        """See `IGitRepository`."""
        if IPerson.providedBy(target):
            owner = IPerson(target)
            if (self.information_type in PRIVATE_INFORMATION_TYPES and
                (not owner.is_team or
                 owner.visibility != PersonVisibility.PRIVATE)):
                raise GitTargetError(
                    "Only private teams may have personal private "
                    "repositories.")
        namespace = get_git_namespace(target, self.owner)
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
            if existing is not None:
                raise GitDefaultConflict(
                    existing, self.target, owner=self.owner)
        self.owner_default = value

    def setTargetDefault(self, value):
        """See `IGitRepository`."""
        if value:
            # Check for an existing target default.
            existing = getUtility(IGitRepositorySet).getDefaultRepository(
                self.target)
            if existing is not None:
                raise GitDefaultConflict(existing, self.target)
        self.target_default = value

    @property
    def display_name(self):
        return self.git_identity

    def getInternalPath(self):
        """See `IGitRepository`."""
        # This may need to change later to improve support for sharding.
        # See also `IGitLookup.getByHostingPath`.
        return str(self.id)

    def getCodebrowseUrl(self):
        """See `IGitRepository`."""
        return urlutils.join(
            config.codehosting.git_browse_root, self.unique_name)

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

    def getRefByPath(self, path):
        return Store.of(self).find(
            GitRef,
            GitRef.repository_id == self.id,
            GitRef.path == path).one()

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

    def createOrUpdateRefs(self, refs_info, get_objects=False):
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

        if get_objects:
            return bulk.load(GitRef, updated + created)

    def removeRefs(self, paths):
        """See `IGitRepository`."""
        Store.of(self).find(
            GitRef,
            GitRef.repository == self, GitRef.path.is_in(paths)).remove()

    def planRefChanges(self, hosting_client, hosting_path, logger=None):
        """See `IGitRepository`."""
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
    def fetchRefCommits(hosting_client, hosting_path, refs, logger=None):
        """See `IGitRepository`."""
        oids = sorted(set(info["sha1"] for info in refs.values()))
        commits = {
            commit.get("sha1"): commit
            for commit in hosting_client.getCommits(
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

    def synchroniseRefs(self, refs_to_upsert, refs_to_remove):
        """See `IGitRepository`."""
        if refs_to_upsert:
            self.createOrUpdateRefs(refs_to_upsert)
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
        if information_type in PRIVATE_INFORMATION_TYPES and self.subscribers:
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

    def setOwner(self, new_owner, user):
        """See `IGitRepository`."""
        new_namespace = get_git_namespace(self.target, new_owner)
        new_namespace.moveRepository(self, user, rename_if_necessary=True)

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

    def destroySelf(self):
        raise NotImplementedError


class GitRepositorySet:
    """See `IGitRepositorySet`."""

    implements(IGitRepositorySet)

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

    @available_with_permission('launchpad.Edit', 'owner')
    def setDefaultRepositoryForOwner(self, owner, target, repository):
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


def get_git_repository_privacy_filter(user):
    public_filter = GitRepository.information_type.is_in(
        PUBLIC_INFORMATION_TYPES)

    if user is None:
        return [public_filter]

    artifact_grant_query = Coalesce(
        ArrayIntersects(
            SQL("GitRepository.access_grants"),
            Select(
                ArrayAgg(TeamParticipation.teamID),
                tables=TeamParticipation,
                where=(TeamParticipation.person == user)
            )), False)

    policy_grant_query = Coalesce(
        ArrayIntersects(
            Array(SQL("GitRepository.access_policy")),
            Select(
                ArrayAgg(AccessPolicyGrant.policy_id),
                tables=(AccessPolicyGrant,
                        Join(TeamParticipation,
                            TeamParticipation.teamID ==
                            AccessPolicyGrant.grantee_id)),
                where=(TeamParticipation.person == user)
            )), False)

    return [Or(public_filter, artifact_grant_query, policy_grant_query)]
