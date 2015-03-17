# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of `IGitNamespace`."""

__metaclass__ = type
__all__ = [
    'GitNamespaceSet',
    'PackageGitNamespace',
    'PersonalGitNamespace',
    'ProjectGitNamespace',
    ]

from lazr.lifecycle.event import ObjectCreatedEvent
from storm.locals import And
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import (
    FREE_INFORMATION_TYPES,
    InformationType,
    NON_EMBARGOED_INFORMATION_TYPES,
    PUBLIC_INFORMATION_TYPES,
    )
from lp.app.interfaces.services import IService
from lp.code.errors import (
    GitRepositoryCreationForbidden,
    GitRepositoryCreatorNotMemberOfOwnerTeam,
    GitRepositoryCreatorNotOwner,
    GitRepositoryExists,
    )
from lp.code.interfaces.gitnamespace import (
    IGitNamespace,
    IGitNamespacePolicy,
    IGitNamespaceSet,
    )
from lp.code.interfaces.gitrepository import (
    IGitRepository,
    user_has_special_git_repository_access,
    )
from lp.code.interfaces.hasgitrepositories import IHasGitRepositories
from lp.code.model.branchnamespace import (
    BRANCH_POLICY_ALLOWED_TYPES,
    BRANCH_POLICY_DEFAULT_TYPES,
    BRANCH_POLICY_REQUIRED_GRANTS,
    )
from lp.code.model.gitrepository import GitRepository
from lp.registry.enums import PersonVisibility
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.services.database.constants import DEFAULT
from lp.services.database.interfaces import IStore
from lp.services.propertycache import get_property_cache


class _BaseGitNamespace:
    """Common code for Git repository namespaces."""

    def createRepository(self, registrant, name, information_type=None,
                         date_created=DEFAULT, description=None):
        """See `IGitNamespace`."""

        self.validateRegistrant(registrant)
        self.validateRepositoryName(name)

        if information_type is None:
            information_type = self.getDefaultInformationType(registrant)
            if information_type is None:
                raise GitRepositoryCreationForbidden()

        repository = GitRepository(
            registrant, self.owner, self.target, name, information_type,
            date_created, description=description)
        repository._reconcileAccess()

        notify(ObjectCreatedEvent(repository))

        return repository

    def isNameUsed(self, repository_name):
        """See `IGitNamespace`."""
        return self.getByName(repository_name) is not None

    def findUnusedName(self, prefix):
        """See `IGitNamespace`."""
        name = prefix
        count = 0
        while self.isNameUsed(name):
            count += 1
            name = "%s-%s" % (prefix, count)
        return name

    def validateRegistrant(self, registrant):
        """See `IGitNamespace`."""
        if user_has_special_git_repository_access(registrant):
            return
        owner = self.owner
        if not registrant.inTeam(owner):
            if owner.is_team:
                raise GitRepositoryCreatorNotMemberOfOwnerTeam(
                    "%s is not a member of %s"
                    % (registrant.displayname, owner.displayname))
            else:
                raise GitRepositoryCreatorNotOwner(
                    "%s cannot create Git repositories owned by %s"
                    % (registrant.displayname, owner.displayname))

        if not self.getAllowedInformationTypes(registrant):
            raise GitRepositoryCreationForbidden(
                'You cannot create Git repositories in "%s"' % self.name)

    def validateRepositoryName(self, name):
        """See `IGitNamespace`."""
        existing_repository = self.getByName(name)
        if existing_repository is not None:
            raise GitRepositoryExists(existing_repository)

        # Not all code paths that lead to Git repository creation go via a
        # schema-validated form, so we validate the repository name here to
        # give a nicer error message than 'ERROR: new row for relation
        # "gitrepository" violates check constraint "valid_name"...'.
        IGitRepository['name'].validate(unicode(name))

    def validateMove(self, repository, mover, name=None):
        """See `IGitNamespace`."""
        if name is None:
            name = repository.name
        self.validateRepositoryName(name)
        self.validateRegistrant(mover)

    def moveRepository(self, repository, mover, new_name=None,
                       rename_if_necessary=False):
        """See `IGitNamespace`."""
        # Check to see if the repository is already in this namespace.
        old_namespace = repository.namespace
        if self.name == old_namespace.name:
            return
        if new_name is None:
            new_name = repository.name
        if rename_if_necessary:
            new_name = self.findUnusedName(new_name)
        self.validateMove(repository, mover, new_name)
        # Remove the security proxy of the repository as the owner and
        # target attributes are read-only through the interface.
        naked_repository = removeSecurityProxy(repository)
        naked_repository.owner = self.owner
        self._retargetRepository(naked_repository)
        del get_property_cache(naked_repository).target
        naked_repository.name = new_name

    def getRepositories(self):
        """See `IGitNamespace`."""
        return IStore(GitRepository).find(
            GitRepository, self._getRepositoriesClause())

    def getByName(self, repository_name, default=None):
        """See `IGitNamespace`."""
        match = IStore(GitRepository).find(
            GitRepository, self._getRepositoriesClause(),
            GitRepository.name == repository_name).one()
        if match is None:
            match = default
        return match

    def getAllowedInformationTypes(self, who=None):
        """See `IGitNamespace`."""
        raise NotImplementedError

    def getDefaultInformationType(self, who=None):
        """See `IGitNamespace`."""
        raise NotImplementedError

    def __eq__(self, other):
        """See `IGitNamespace`."""
        return self.target == other.target

    def __ne__(self, other):
        """See `IGitNamespace`."""
        return not self == other


class PersonalGitNamespace(_BaseGitNamespace):
    """A namespace for personal repositories.

    Repositories in this namespace have names like "~foo/+git/bar".
    """

    implements(IGitNamespace, IGitNamespacePolicy)

    has_defaults = False
    allow_push_to_set_default = False

    def __init__(self, person):
        self.owner = person

    def _getRepositoriesClause(self):
        return And(
            GitRepository.owner == self.owner,
            GitRepository.project == None,
            GitRepository.distribution == None,
            GitRepository.sourcepackagename == None)

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    @property
    def name(self):
        """See `IGitNamespace`."""
        return "~%s" % self.owner.name

    @property
    def target(self):
        """See `IGitNamespace`."""
        return IHasGitRepositories(self.owner)

    def _retargetRepository(self, repository):
        repository.project = None
        repository.distribution = None
        repository.sourcepackagename = None

    @property
    def _is_private_team(self):
        return (
            self.owner.is_team
            and self.owner.visibility == PersonVisibility.PRIVATE)

    def getAllowedInformationTypes(self, who=None):
        """See `IGitNamespace`."""
        # Private teams get private branches, everyone else gets public ones.
        if self._is_private_team:
            return NON_EMBARGOED_INFORMATION_TYPES
        else:
            return FREE_INFORMATION_TYPES

    def getDefaultInformationType(self, who=None):
        """See `IGitNamespace`."""
        if self._is_private_team:
            return InformationType.PROPRIETARY
        else:
            return InformationType.PUBLIC


class ProjectGitNamespace(_BaseGitNamespace):
    """A namespace for project repositories.

    This namespace is for all the repositories owned by a particular person
    in a particular project.
    """

    implements(IGitNamespace, IGitNamespacePolicy)

    has_defaults = True
    allow_push_to_set_default = True

    def __init__(self, person, project):
        self.owner = person
        self.project = project

    def _getRepositoriesClause(self):
        return And(
            GitRepository.owner == self.owner,
            GitRepository.project == self.project)

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    @property
    def name(self):
        """See `IGitNamespace`."""
        return '~%s/%s' % (self.owner.name, self.project.name)

    @property
    def target(self):
        """See `IGitNamespace`."""
        return IHasGitRepositories(self.project)

    def _retargetRepository(self, repository):
        repository.project = self.project
        repository.distribution = None
        repository.sourcepackagename = None

    def getAllowedInformationTypes(self, who=None):
        """See `IGitNamespace`."""
        # Some policies require that the repository owner or current user
        # have full access to an information type.  If it's required and the
        # user doesn't hold it, no information types are legal.
        required_grant = BRANCH_POLICY_REQUIRED_GRANTS[
            self.project.branch_sharing_policy]
        if (required_grant is not None
            and not getUtility(IService, 'sharing').checkPillarAccess(
                [self.project], required_grant, self.owner)
            and (who is None
                or not getUtility(IService, 'sharing').checkPillarAccess(
                    [self.project], required_grant, who))):
            return []

        return BRANCH_POLICY_ALLOWED_TYPES[self.project.branch_sharing_policy]

    def getDefaultInformationType(self, who=None):
        """See `IGitNamespace`."""
        default_type = BRANCH_POLICY_DEFAULT_TYPES[
            self.project.branch_sharing_policy]
        if default_type not in self.getAllowedInformationTypes(who):
            return None
        return default_type


class PackageGitNamespace(_BaseGitNamespace):
    """A namespace for distribution source package repositories.

    This namespace is for all the repositories owned by a particular person
    in a particular source package in a particular distribution.
    """

    implements(IGitNamespace, IGitNamespacePolicy)

    has_defaults = True
    allow_push_to_set_default = False

    def __init__(self, person, distro_source_package):
        self.owner = person
        self.distro_source_package = distro_source_package

    def _getRepositoriesClause(self):
        dsp = self.distro_source_package
        return And(
            GitRepository.owner == self.owner,
            GitRepository.distribution == dsp.distribution,
            GitRepository.sourcepackagename == dsp.sourcepackagename)

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    @property
    def name(self):
        """See `IGitNamespace`."""
        dsp = self.distro_source_package
        return '~%s/%s/+source/%s' % (
            self.owner.name, dsp.distribution.name, dsp.sourcepackagename.name)

    @property
    def target(self):
        """See `IGitNamespace`."""
        return IHasGitRepositories(self.distro_source_package)

    def _retargetRepository(self, repository):
        dsp = self.distro_source_package
        repository.project = None
        repository.distribution = dsp.distribution
        repository.sourcepackagename = dsp.sourcepackagename

    def getAllowedInformationTypes(self, who=None):
        """See `IGitNamespace`."""
        return PUBLIC_INFORMATION_TYPES

    def getDefaultInformationType(self, who=None):
        """See `IGitNamespace`."""
        return InformationType.PUBLIC

    def __eq__(self, other):
        """See `IGitNamespace`."""
        # We may have different DSP objects that are functionally the same.
        self_dsp = self.distro_source_package
        other_dsp = IDistributionSourcePackage(other.target)
        return (
            self_dsp.distribution == other_dsp.distribution and
            self_dsp.sourcepackagename == other_dsp.sourcepackagename)


class GitNamespaceSet:
    """Only implementation of `IGitNamespaceSet`."""

    implements(IGitNamespaceSet)

    def get(self, person, project=None, distribution=None,
            sourcepackagename=None):
        """See `IGitNamespaceSet`."""
        if project is not None:
            assert distribution is None and sourcepackagename is None, (
                "project implies no distribution or sourcepackagename. "
                "Got %r, %r, %r."
                % (project, distribution, sourcepackagename))
            return ProjectGitNamespace(person, project)
        elif distribution is not None:
            assert sourcepackagename is not None, (
                "distribution implies sourcepackagename. Got %r, %r"
                % (distribution, sourcepackagename))
            return PackageGitNamespace(
                person, distribution.getSourcePackage(sourcepackagename))
        else:
            return PersonalGitNamespace(person)
