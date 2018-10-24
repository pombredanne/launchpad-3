# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of the XML-RPC APIs for Git."""

__metaclass__ = type
__all__ = [
    'GitAPI',
    ]

from collections import defaultdict
from fnmatch import fnmatch
import sys

from pymacaroons import Macaroon
from storm.store import Store
import transaction
from zope.component import (
    ComponentLookupError,
    getUtility,
    )
from zope.error.interfaces import IErrorReportingUtility
from zope.interface import implementer
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NameLookupFailed
from lp.app.validators import LaunchpadValidationError
from lp.code.enums import (
    GitGranteeType,
    GitPermissionType,
    GitRepositoryType,
    )
from lp.code.errors import (
    GitRepositoryCreationException,
    GitRepositoryCreationFault,
    GitRepositoryCreationForbidden,
    GitRepositoryExists,
    GitTargetError,
    InvalidNamespace,
    )
from lp.code.interfaces.codehosting import LAUNCHPAD_ANONYMOUS
from lp.code.interfaces.codeimport import ICodeImportSet
from lp.code.interfaces.gitapi import IGitAPI
from lp.code.interfaces.githosting import IGitHostingClient
from lp.code.interfaces.gitjob import IGitRefScanJobSource
from lp.code.interfaces.gitlookup import (
    IGitLookup,
    IGitTraverser,
    )
from lp.code.interfaces.gitnamespace import (
    get_git_namespace,
    split_git_unique_name,
    )
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.xmlrpc.codehosting import run_with_login
from lp.registry.errors import (
    InvalidName,
    NoSuchSourcePackageName,
    )
from lp.registry.interfaces.person import NoSuchPerson
from lp.registry.interfaces.product import (
    InvalidProductName,
    NoSuchProduct,
    )
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.services.macaroons.interfaces import IMacaroonIssuer
from lp.services.webapp import LaunchpadXMLRPCView
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.errorlog import ScriptRequest
from lp.xmlrpc import faults
from lp.xmlrpc.helpers import return_fault


@implementer(IGitAPI)
class GitAPI(LaunchpadXMLRPCView):
    """See `IGitAPI`."""

    def __init__(self, *args, **kwargs):
        super(GitAPI, self).__init__(*args, **kwargs)
        self.repository_set = getUtility(IGitRepositorySet)

    def _verifyMacaroon(self, macaroon_raw, repository=None):
        try:
            macaroon = Macaroon.deserialize(macaroon_raw)
        except Exception:
            return False
        try:
            issuer = getUtility(IMacaroonIssuer, macaroon.identifier)
        except ComponentLookupError:
            return False
        if repository is not None:
            if repository.repository_type != GitRepositoryType.IMPORTED:
                return False
            code_import = getUtility(ICodeImportSet).getByGitRepository(
                repository)
            if code_import is None:
                return False
            job = code_import.import_job
            if job is None:
                return False
            return issuer.verifyMacaroon(macaroon, job)
        else:
            return issuer.checkMacaroonIssuer(macaroon)

    def _performLookup(self, requester, path, auth_params):
        repository, extra_path = getUtility(IGitLookup).getByPath(path)
        if repository is None:
            return None
        macaroon_raw = auth_params.get("macaroon")
        naked_repository = removeSecurityProxy(repository)
        if (macaroon_raw is not None and
                self._verifyMacaroon(macaroon_raw, naked_repository)):
            # The authentication parameters specifically grant access to
            # this repository, so we can bypass other checks.
            # For the time being, this only works for code imports.
            assert (
                naked_repository.repository_type == GitRepositoryType.IMPORTED)
            hosting_path = naked_repository.getInternalPath()
            writable = True
            private = naked_repository.private
        else:
            try:
                hosting_path = repository.getInternalPath()
            except Unauthorized:
                return None
            writable = (
                repository.repository_type == GitRepositoryType.HOSTED and
                check_permission("launchpad.Edit", repository))
            # If we have any grants to this user, they are declared to have
            # write access at this point. `_checkRefPermissions` will
            # sort out access to individual refs at a later point in the push.
            if not writable:
                grants = naked_repository.findRuleGrantsByGrantee(requester)
                if not grants.is_empty():
                    writable = True
            private = repository.private
        return {
            "path": hosting_path,
            "writable": writable,
            "trailing": extra_path,
            "private": private,
            }

    def _getGitNamespaceExtras(self, path, requester):
        """Get the namespace, repository name, and callback for the path.

        If the path defines a full Git repository path including the owner
        and repository name, then the namespace that is returned is the
        namespace for the owner and the repository target specified.

        If the path uses a shortcut name, then we only allow the requester
        to create a repository if they have permission to make the newly
        created repository the default for the shortcut target.  If there is
        an existing default repository, then GitRepositoryExists is raised.
        The repository name that is used is determined by the namespace as
        the first unused name starting with the leaf part of the namespace
        name.  In this case, the repository owner will be set to the
        namespace owner, and distribution source package namespaces are
        currently disallowed due to the complexities of ownership there.
        """
        try:
            namespace_name, repository_name = split_git_unique_name(path)
        except InvalidNamespace:
            namespace_name = path
            repository_name = None
        owner, target, repository = getUtility(IGitTraverser).traverse_path(
            namespace_name)
        # split_git_unique_name should have left us without a repository name.
        assert repository is None
        if owner is None:
            if not get_git_namespace(target, None).allow_push_to_set_default:
                raise GitRepositoryCreationForbidden(
                    "Cannot automatically set the default repository for this "
                    "target; push to a named repository instead.")
            repository_owner = target.owner
        else:
            repository_owner = owner
        namespace = get_git_namespace(target, repository_owner)
        if repository_name is None and not namespace.has_defaults:
            raise InvalidNamespace(path)
        if repository_name is None:
            def default_func(new_repository):
                if owner is None:
                    self.repository_set.setDefaultRepository(
                        target, new_repository)
                if (owner is not None or
                    self.repository_set.getDefaultRepositoryForOwner(
                        repository_owner, target) is None):
                    self.repository_set.setDefaultRepositoryForOwner(
                        repository_owner, target, new_repository, requester)

            repository_name = namespace.findUnusedName(target.name)
            return namespace, repository_name, default_func
        else:
            return namespace, repository_name, None

    def _reportError(self, path, exception, hosting_path=None):
        properties = [
            ("path", path),
            ("error-explanation", unicode(exception)),
            ]
        if hosting_path is not None:
            properties.append(("hosting_path", hosting_path))
        request = ScriptRequest(properties)
        getUtility(IErrorReportingUtility).raising(sys.exc_info(), request)
        raise faults.OopsOccurred("creating a Git repository", request.oopsid)

    def _createRepository(self, requester, path, clone_from=None):
        try:
            namespace, repository_name, default_func = (
                self._getGitNamespaceExtras(path, requester))
        except InvalidNamespace:
            raise faults.PermissionDenied(
                "'%s' is not a valid Git repository path." % path)
        except NoSuchPerson as e:
            raise faults.NotFound("User/team '%s' does not exist." % e.name)
        except (NoSuchProduct, InvalidProductName) as e:
            raise faults.NotFound("Project '%s' does not exist." % e.name)
        except NoSuchSourcePackageName as e:
            try:
                getUtility(ISourcePackageNameSet).new(e.name)
            except InvalidName:
                raise faults.InvalidSourcePackageName(e.name)
            return self._createRepository(requester, path)
        except NameLookupFailed as e:
            raise faults.NotFound(unicode(e))
        except GitRepositoryCreationForbidden as e:
            raise faults.PermissionDenied(unicode(e))

        try:
            repository = namespace.createRepository(
                GitRepositoryType.HOSTED, requester, repository_name)
        except LaunchpadValidationError as e:
            # Despite the fault name, this just passes through the exception
            # text so there's no need for a new Git-specific fault.
            raise faults.InvalidBranchName(e)
        except GitRepositoryExists as e:
            # We should never get here, as we just tried to translate the
            # path and found nothing (not even an inaccessible private
            # repository).  Log an OOPS for investigation.
            self._reportError(path, e)
        except GitRepositoryCreationException as e:
            raise faults.PermissionDenied(unicode(e))

        try:
            if default_func:
                try:
                    default_func(repository)
                except Unauthorized:
                    raise faults.PermissionDenied(
                        "You cannot set the default Git repository for '%s'." %
                        path)

            # Flush to make sure that repository.id is populated.
            Store.of(repository).flush()
            assert repository.id is not None

            # If repository has target_default, clone from default.
            target_path = None
            try:
                default = self.repository_set.getDefaultRepository(
                    repository.target)
                if default is not None and default.visibleByUser(requester):
                    target_path = default.getInternalPath()
                else:
                    default = self.repository_set.getDefaultRepositoryForOwner(
                        repository.owner, repository.target)
                    if (default is not None and
                            default.visibleByUser(requester)):
                        target_path = default.getInternalPath()
            except GitTargetError:
                pass  # Ignore Personal repositories.

            hosting_path = repository.getInternalPath()
            try:
                getUtility(IGitHostingClient).create(
                    hosting_path, clone_from=target_path)
            except GitRepositoryCreationFault as e:
                # The hosting service failed.  Log an OOPS for investigation.
                self._reportError(path, e, hosting_path=hosting_path)
        except Exception:
            # We don't want to keep the repository we created.
            transaction.abort()
            raise

    @return_fault
    def _translatePath(self, requester, path, permission, auth_params):
        if requester == LAUNCHPAD_ANONYMOUS:
            requester = None
        try:
            result = self._performLookup(requester, path, auth_params)
            if (result is None and requester is not None and
                permission == "write"):
                self._createRepository(requester, path)
                result = self._performLookup(requester, path, auth_params)
            if result is None:
                raise faults.GitRepositoryNotFound(path)
            if permission != "read" and not result["writable"]:
                raise faults.PermissionDenied()
            return result
        except (faults.PermissionDenied, faults.GitRepositoryNotFound):
            # Turn lookup errors for anonymous HTTP requests into
            # "authorisation required", so that the user-agent has a
            # chance to try HTTP basic auth.
            can_authenticate = auth_params.get("can-authenticate", False)
            if can_authenticate and requester is None:
                raise faults.Unauthorized()
            else:
                raise

    def translatePath(self, path, permission, auth_params):
        """See `IGitAPI`."""
        requester_id = auth_params.get("uid")
        if requester_id is None:
            requester_id = LAUNCHPAD_ANONYMOUS
        if isinstance(path, str):
            path = path.decode('utf-8')
        return run_with_login(
            requester_id, self._translatePath,
            path.strip("/"), permission, auth_params)

    def notify(self, translated_path):
        """See `IGitAPI`."""
        repository = getUtility(IGitLookup).getByHostingPath(translated_path)
        if repository is None:
            return faults.NotFound(
                "No repository found for '%s'." % translated_path)
        getUtility(IGitRefScanJobSource).create(
            removeSecurityProxy(repository))

    def authenticateWithPassword(self, username, password):
        """See `IGitAPI`."""
        # XXX cjwatson 2016-10-06: We only support free-floating macaroons
        # at the moment, not ones bound to a user.
        if not username and self._verifyMacaroon(password):
            return {"macaroon": password}
        else:
            # Only macaroons are supported for password authentication.
            return faults.Unauthorized()

    def _renderPermissions(self, set_of_permissions):
        """Render a set of permission strings for XML-RPC output."""
        permissions = []
        if GitPermissionType.CAN_CREATE in set_of_permissions:
            permissions.append('create')
        if GitPermissionType.CAN_PUSH in set_of_permissions:
            permissions.append('push')
        if GitPermissionType.CAN_FORCE_PUSH in set_of_permissions:
            permissions.append('force_push')
        return permissions

    def _buildPermissions(self, grant):
        """Build a set of the available permissions from a GitRuleGrant"""
        permissions = set(grant.permissions)
        if GitPermissionType.CAN_FORCE_PUSH in permissions:
            # Permission to force-push implies permission to push.
            permissions.add(GitPermissionType.CAN_PUSH)
        return permissions

    def _findMatchingRules(self, repository, ref_path):
        """Find all matching rules for a given ref path"""
        matching_rules = []
        for rule in repository.rules:
            if fnmatch(ref_path, rule.ref_pattern):
                matching_rules.append(rule)
        return matching_rules

    def _checkRefPermissions(self, requester, translated_path, ref_paths,
                             auth_params):
        if requester == LAUNCHPAD_ANONYMOUS:
            requester = None
        repository = removeSecurityProxy(
            getUtility(IGitLookup).getByHostingPath(translated_path))
        result = {}

        grants_for_user = defaultdict(list)
        macaroon_raw = auth_params.get("macaroon")
        if (macaroon_raw is not None and
                self._verifyMacaroon(macaroon_raw, repository)):
            # The authentication parameters grant access as an anonymous
            # repository owner.
            # For the time being, this only works for code imports.
            assert repository.repository_type == GitRepositoryType.IMPORTED
            is_owner = True
            grants = repository.findRuleGrantsByGrantee(
                GitGranteeType.REPOSITORY_OWNER)
        elif requester is None:
            is_owner = False
            grants = []
        else:
            is_owner = requester.inTeam(repository.owner)
            grants = repository.findRuleGrantsByGrantee(requester)
            if is_owner:
                owner_grants = repository.findRuleGrantsByGrantee(
                    GitGranteeType.REPOSITORY_OWNER)
                grants = grants.union(owner_grants)
        for grant in grants:
            grants_for_user[grant.rule].append(grant)

        for ref in ref_paths:
            matching_rules = self._findMatchingRules(repository, ref)
            if is_owner and not matching_rules:
                result[ref] = ['create', 'push', 'force_push']
                continue
            seen_grantees = set()
            union_permissions = set()
            for rule in matching_rules:
                for grant in grants_for_user[rule]:
                    if (grant.grantee, grant.grantee_type) in seen_grantees:
                        continue
                    permissions = self._buildPermissions(grant)
                    union_permissions.update(permissions)
                    seen_grantees.add((grant.grantee, grant.grantee_type))

            owner_type = (None, GitGranteeType.REPOSITORY_OWNER)
            if is_owner and owner_type not in seen_grantees:
                union_permissions.update(
                    [GitPermissionType.CAN_CREATE, GitPermissionType.CAN_PUSH])

            result[ref] = self._renderPermissions(union_permissions)
        return result

    def checkRefPermissions(self, translated_path, ref_paths, auth_params):
        """ See `IGitAPI`"""
        requester_id = auth_params.get("uid")
        if requester_id is None:
            requester_id = LAUNCHPAD_ANONYMOUS
        return run_with_login(
            requester_id,
            self._checkRefPermissions,
            translated_path,
            ref_paths,
            auth_params)
