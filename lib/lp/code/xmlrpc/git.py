# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of the XML-RPC APIs for Git."""

__metaclass__ = type
__all__ = [
    'GitAPI',
    ]

from storm.store import Store
import transaction
from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from lp.app.errors import NameLookupFailed
from lp.app.validators import LaunchpadValidationError
from lp.code.errors import (
    GitRepositoryCreationException,
    GitRepositoryCreationForbidden,
    InvalidNamespace,
    )
from lp.code.githosting import GitHostingClient
from lp.code.interfaces.codehosting import LAUNCHPAD_ANONYMOUS
from lp.code.interfaces.gitapi import IGitAPI
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
from lp.services.config import config
from lp.services.webapp import LaunchpadXMLRPCView
from lp.services.webapp.authorization import check_permission
from lp.xmlrpc import faults
from lp.xmlrpc.helpers import return_fault


class GitAPI(LaunchpadXMLRPCView):
    """See `IGitAPI`."""

    implements(IGitAPI)

    def __init__(self, *args, **kwargs):
        super(GitAPI, self).__init__(*args, **kwargs)
        self.hosting_client = GitHostingClient(
            config.codehosting.internal_git_api_endpoint)

    def _performLookup(self, path):
        repository = getUtility(IGitLookup).getByPath(path)
        if repository is None:
            return None
        try:
            hosting_path = repository.getInternalPath()
        except Unauthorized:
            raise faults.PermissionDenied()
        writable = check_permission("launchpad.Edit", repository)
        return {"path": hosting_path, "writable": writable}

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
            repository_owner = requester
        else:
            repository_owner = owner
        namespace = get_git_namespace(target, repository_owner)
        if repository_name is None and not namespace.has_defaults:
            raise InvalidNamespace(path)
        if owner is None and not namespace.allow_push_to_set_default:
            raise GitRepositoryCreationForbidden(
                "Cannot automatically set the default repository for this "
                "target; push to a named repository instead.")
        if repository_name is None:
            def default_func(new_repository):
                repository_set = getUtility(IGitRepositorySet)
                if owner is None:
                    repository_set.setDefaultRepository(
                        target, new_repository)
                else:
                    repository_set.setDefaultRepositoryForOwner(
                        owner, target, new_repository)

            repository_name = namespace.findUnusedName(target.name)
            return namespace, repository_name, default_func
        else:
            return namespace, repository_name, None

    def _createRepository(self, requester, path):
        try:
            namespace, repository_name, default_func = (
                self._getGitNamespaceExtras(path, requester))
        except (ValueError, InvalidNamespace):
            raise faults.PermissionDenied(
                "Cannot create Git repository at '%s'" % path)
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
            raise faults.NotFound(str(e))
        except GitRepositoryCreationForbidden as e:
            raise faults.PermissionDenied(str(e))

        try:
            repository = namespace.createRepository(
                requester, repository_name)
        except LaunchpadValidationError as e:
            msg = e.args[0]
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8')
            raise faults.PermissionDenied(msg)
        except GitRepositoryCreationException as e:
            raise faults.PermissionDenied(str(e))

        try:
            if default_func:
                try:
                    default_func(repository)
                except Unauthorized:
                    raise faults.PermissionDenied(
                        "You cannot set the default Git repository for '%s'." %
                        path)

            # The transaction hasn't been committed yet (and shouldn't be
            # until the non-transactional work is complete), so
            # repository.id will not yet have been filled in, but we need it
            # to create the hosting path.
            store = Store.of(repository)
            repository_id = store.execute(
                """SELECT currval('gitrepository_id_seq')""").get_one()[0]

            hosting_path = repository.getInternalPathForID(repository_id)
            # XXX cjwatson 2015-02-27: Turn any exceptions into proper faults.
            self.hosting_client.create(hosting_path)
        except Exception:
            # We don't want to keep the repository we created.
            transaction.abort()
            raise

    @return_fault
    def _translatePath(self, requester, path, permission, can_authenticate):
        if requester == LAUNCHPAD_ANONYMOUS:
            requester = None
        try:
            result = self._performLookup(path)
            if (result is None and requester is not None and
                permission == "write"):
                self._createRepository(requester, path)
                result = self._performLookup(path)
            if result is None:
                raise faults.PathTranslationError(path)
            if permission != "read" and not result["writable"]:
                raise faults.PermissionDenied()
            return result
        except faults.PermissionDenied:
            # Turn "permission denied" for anonymous HTTP requests into
            # "authorisation required", so that the user-agent has a chance
            # to try HTTP basic auth.
            if can_authenticate and requester is None:
                raise faults.Unauthorized()
            raise

    def translatePath(self, path, permission, requester_id, can_authenticate):
        """See `IGitAPI`."""
        if requester_id is None:
            requester_id = LAUNCHPAD_ANONYMOUS
        return run_with_login(
            requester_id, self._translatePath,
            path.strip("/"), permission, can_authenticate)
