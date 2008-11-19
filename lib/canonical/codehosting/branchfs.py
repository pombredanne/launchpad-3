# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""The Launchpad code hosting file system.

The way Launchpad presents branches is very different from the way it stores
them. Externally, branches are reached using URLs that look like
<schema>://launchpad.net/~owner/product/branch-name. Internally, they are
stored by branch ID. Branch 1 is stored at 00/00/00/01 and branch 10 is stored
at 00/00/00/0A. Further, these branches might not be stored on the same
physical machine.

This means that our services need to translate the external paths into
internal paths.

We also want to let users create new branches on Launchpad simply by pushing
them up. We want Launchpad to detect when a branch has been changed and update
our internal mirror.

This means our services must detect events like "make directory" and "unlock
branch", translate them into Launchpad operations like "create branch" and
"request mirror" and then actually perform those operations.

So, we have a `LaunchpadServer` which implements the core operations --
translate a path, make a branch and request a mirror -- in terms of virtual
paths.

This server does most of its work by delegating to a `LaunchpadBranch` object.
This object can be constructed from a virtual path and then operated on. It in
turn delegates to the "authserver", an internal XML-RPC server that actually
talks to the database. We cache requests to the authserver using
`CachingAuthserverClient`, in order to speed things up a bit.

We hook the `LaunchpadServer` into Bazaar by implementing a
`AsyncVirtualTransport`, a `bzrlib.transport.Transport` that wraps all of its
operations so that they are translated by an object that implements
`translateVirtualPath`.  See transport.py for more information.

This virtual transport isn't quite enough, since it only does dumb path
translation. We also need to be able to interpret filesystem events in terms
of Launchpad branches. To do this, we provide a `LaunchpadTransport` that
hooks into operations like `mkdir` and ask the `LaunchpadServer` to make a
branch if appropriate.
"""


__metaclass__ = type
__all__ = [
    'AsyncLaunchpadTransport',
    'get_puller_server',
    'get_scanner_server',
    'LaunchpadInternalServer',
    'LaunchpadServer',
    ]

import xmlrpclib

from bzrlib.bzrdir import BzrDirFormat
from bzrlib.errors import (
    BzrError, NoSuchFile, PermissionDenied, TransportNotPossible)
from bzrlib import urlutils
from bzrlib.transport import (
    get_transport, register_transport, Server, unregister_transport)
from bzrlib.transport.memory import MemoryServer

from twisted.internet import defer
from twisted.python import failure

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.branchfsclient import (
    BlockingProxy, CachingAuthserverClient, trap_fault)
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.transport import (
    AsyncVirtualTransport, _MultiServer, get_chrooted_transport,
    get_readonly_transport, SynchronousAdapter, TranslationError)
from canonical.config import config
from canonical.launchpad.interfaces.codehosting import (
    BRANCH_TRANSPORT, CONTROL_TRANSPORT, LAUNCHPAD_SERVICES,
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE)
from canonical.launchpad.xmlrpc import faults


# The directories allowed directly beneath a branch directory. These are the
# directories that Bazaar creates as part of regular operation.
ALLOWED_DIRECTORIES = ('.bzr', '.bzr.backup', 'backup.bzr')
FORBIDDEN_DIRECTORY_ERROR = (
    "Cannot create '%s'. Only Bazaar branches are allowed.")


def get_path_segments(path, maximum_segments=-1):
    """Break up the given path into segments.

    If 'path' ends with a trailing slash, then the final empty segment is
    ignored.
    """
    return path.strip('/').split('/', maximum_segments)


def is_lock_directory(absolute_path):
    """Is 'absolute_path' a Bazaar branch lock directory?"""
    return absolute_path.endswith('/.bzr/branch/lock/held')


class TransportFactory:

    def __init__(self, hosted_transport, mirrored_transport):
        self.hosted_transport = hosted_transport
        self.mirrored_transport = mirrored_transport
        self._transport_factories = {
            BRANCH_TRANSPORT: self.make_branch_transport,
            CONTROL_TRANSPORT: self.make_control_transport,
            }

    def make_transport(self, transport_tuple):
        transport_type, data, trailing_path = transport_tuple
        factory = self._transport_factories[transport_type]
        return factory(**data), trailing_path

    def make_branch_transport(self, id, writable):
        if writable:
            transport = self.hosted_transport
        else:
            transport = self.mirrored_transport
        transport = transport.clone(branch_id_to_path(id))
        ensure_base(transport)
        if not writable:
            transport = get_transport('readonly+' + transport.base)
        return transport

    def make_control_transport(self, default_stack_on):
        memory_server = MemoryServer()
        memory_server.setUp()
        transport = get_transport(memory_server.get_url())
        if default_stack_on == '':
            return transport
        format = BzrDirFormat.get_default_format()
        bzrdir = format.initialize_on_transport(transport)
        bzrdir.get_config().set_default_stack_on(default_stack_on)
        return get_transport('readonly+' + transport.base)


class BranchNotFound(BzrError):
    """Raised when on translating a virtual path for a non-existent branch."""

    _fmt = ("Could not find id for branch ~%(owner)s/%(product)s/%(name)s.")


class NotABranchPath(TranslationError):
    """Raised when we cannot translate a virtual URL fragment to a branch.

    In particular, this is raised when there is some intrinsic deficiency in
    the path itself.
    """

    _fmt = ("Could not translate %(virtual_url_fragment)r to branch. "
            "%(reason)s")


class NotEnoughInformation(NotABranchPath):
    """Raised when there's not enough information in the path."""

    reason = "Not enough information."


class InvalidOwnerDirectory(NotABranchPath):
    """Raised when the owner directory is invalid.

    This generally means that it doesn't start with a tilde (~).
    """

    reason = "Path must start with a user or team directory."


class InvalidControlDirectory(BzrError):
    """Raised when we try to parse an invalid control directory."""


class LaunchpadBranch:
    """A branch on Launchpad.

    This abstractly represents a branch on Launchpad without exposing details
    of the naming of Launchpad branches. It contains and maintains the
    knowledge of how a virtual path, such as '~owner/product/branch' is
    translated into the underlying storage systems.

    It also exposes operations on Launchpad branches that we in turn expose
    via the codehosting system. Namely, creating a branch and requesting that
    a branch be mirrored.

    :ivar can_write: Whether or not the current user can write to the branch.
    :type can_write: bool
    """

    @classmethod
    def from_virtual_path(cls, authserver, virtual_url_fragment):
        """Construct a LaunchpadBranch from a virtual URL fragment.

        :param authserver: An XML-RPC client to the Launchpad authserver.
            This is used to get information about the branch and to perform
            database operations on the branch. This XML-RPC client should
            implement 'callRemote'.
        :param virtual_path: A public path to a branch, or to a file or
            directory within a branch. This path is required to be URL
            escaped.

        :raise NotABranchPath: If `virtual_path` cannot be translated into a
            (potential) path to a branch. See also `NotEnoughInformation`
            and `InvalidOwnerDirectory`.

        :return: (launchpad_branch, rest_of_path), where `launchpad_branch`
            is an instance of LaunchpadBranch that represents the branch at
            the virtual path, and `rest_of_path` is a URL fragment within
            that branch.
        """
        deferred = authserver.translatePath('/' + virtual_url_fragment)

        def path_translated(result):
            (transport_type, data, trailing_path) = result
            if transport_type != BRANCH_TRANSPORT:
                raise NotEnoughInformation(virtual_url_fragment)
            return (
                cls(authserver, virtual_url_fragment, data['id'],
                    data['writable']),
                trailing_path)

        def path_not_translated(failure):
            trap_fault(failure, faults.PathTranslationError.error_code)
            raise BranchNotFound(virtual_url_fragment)

        return deferred.addCallbacks(path_translated, path_not_translated)

    def __init__(self, authserver, branch_path, branch_id, can_write):
        """Construct a LaunchpadBranch object.

        In general, don't call this directly, use
        `LaunchpadBranch.from_virtual_path` instead. This prevents assumptions
        about branch naming spreading throughout the code.

        :param authserver: An XML-RPC client to the Launchpad authserver.
            This is used to get information about the branch and to perform
            database operations on the branch. The client should implement
            `callRemote`.
        :param owner: The owner of the branch. A string that is the name of a
            Launchpad `IPerson`.
        :param product: The project that the branch belongs to. A string that
            is either '+junk' or the name of a Launchpad `IProduct`.
        :param branch: The name of the branch.
        """
        self._authserver = authserver
        self._branch_path = branch_path
        self._branch_id = branch_id
        self.can_write = can_write

    def _checkPath(self, path_on_branch):
        """Raise an error if `path_on_branch` is not valid.

        This allows us to enforce a certain level of policy about what goes
        into a branch directory on Launchpad. Specifically, we do not allow
        arbitrary files at the top-level, we only allow Bazaar control
        directories, and backups of same.

        :raise PermissionDenied: if `path_on_branch` is forbidden.
        """
        if path_on_branch == '':
            return
        segments = get_path_segments(path_on_branch)
        if segments[0] not in ALLOWED_DIRECTORIES:
            raise PermissionDenied(
                FORBIDDEN_DIRECTORY_ERROR % (segments[0],))

    def create(self):
        """Create a branch in the database.

        :raise TransportNotPossible: If the branch owner or product does not
            exist.
        :raise PermissionDenied: If the branch cannot be created in the
            database. This might indicate that the branch already exists, or
            that its creation is forbidden by a policy.
        """
        deferred = self._authserver.createBranch(self._branch_path)

        def translate_fault(failure):
            # One might think that it would make sense to raise NoSuchFile
            # here, but that makes the client do "clever" things like say
            # "Parent directory of
            # bzr+ssh://bazaar.launchpad.dev/~noone/firefox/branch does not
            # exist. You may supply --create-prefix to create all leading
            # parent directories." Which is just misleading.
            fault = trap_fault(
                failure, NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE)
            raise PermissionDenied(fault.faultString)

        return deferred.addErrback(translate_fault)

    def ensureUnderlyingPath(self, transport):
        """Ensure that the directory for the branch exists on the transport.
        """
        try:
            real_path = self.getRealPath('')
        except BranchNotFound:
            pass
        ensure_base(transport.clone(real_path))

    def getRealPath(self, url_fragment_on_branch):
        """Return the 'real' URL-escaped path to a path within this branch.

        :param path_on_branch: A URL fragment referring to a path within this
             branch.

        :raise BranchNotFound: if the branch does not exist.
        :raise PermissionDenied: if `url_fragment_on_branch` is forbidden.

        :return: A path relative to the base directory where all branches
            are stored. This path will look like '00/AB/02/43/.bzr/foo', where
            'AB0243' is the database ID of the branch expressed in hex and
            '.bzr/foo' is `path_on_branch`.
        """
        self._checkPath(url_fragment_on_branch)
        branch_path = branch_id_to_path(self._branch_id)
        return '/'.join([branch_path, url_fragment_on_branch])

    def requestMirror(self):
        """Request that the branch be mirrored as soon as possible.

        :raise BranchNotFound: if the branch does not exist.
        """
        return self._authserver.requestMirror(self._branch_id)


class _BaseLaunchpadServer(Server):
    """Bazaar Server for Launchpad branches.

    This server provides facilities for transports that use a virtual
    filesystem, backed by an XML-RPC server.

    For more information, see the module docstring.
    """

    asyncTransportFactory = None

    def __init__(self, scheme, authserver, user_id):
        """Construct a LaunchpadServer.

        :param scheme: The URL scheme to use.
        :param authserver: An XML-RPC client that implements callRemote.
        :param user_id: The database ID for the user who is accessing
            branches.
        """
        # bzrlib's Server class does not have a constructor, so we cannot
        # safely upcall it.
        # pylint: disable-msg=W0231
        self._scheme = scheme
        self._authserver = CachingAuthserverClient(authserver, user_id)
        self._is_set_up = False

    def _transportFactory(self, url):
        """Create a transport for this server pointing at `url`.

        Override this in subclasses.
        """
        assert url.startswith(self.get_url())
        return SynchronousAdapter(self.asyncTransportFactory(self, url))

    def _getLaunchpadBranch(self, virtual_path):
        return LaunchpadBranch.from_virtual_path(
            self._authserver, virtual_path)

    def _getTransportForLaunchpadBranch(self, lp_branch):
        """Return the transport for accessing `lp_branch`."""
        raise NotImplementedError("Override this in subclasses.")

    def translateVirtualPath(self, virtual_url_fragment):
        """Translate 'virtual_url_fragment' into a transport and sub-fragment.

        :param virtual_url_fragment: A virtual URL fragment to be translated.

        :raise NotABranchPath: If `virtual_url_fragment` does not have at
            least a valid path to a branch.
        :raise BranchNotFound: If `virtual_path` looks like a path to a
            branch, but there is no branch in the database that matches.
        :raise NoSuchFile: If `virtual_path` is *inside* a non-existing
            branch.
        :raise PermissionDenied: if the path on the branch is forbidden.

        :return: (transport, path_on_transport)
        """
        deferred = self._getLaunchpadBranch(virtual_url_fragment)

        def branch_not_found(failure):
            failure.trap(BranchNotFound)
            raise NoSuchFile(virtual_url_fragment)

        deferred.addErrback(branch_not_found)

        def got_branch((lp_branch, path)):
            real_path = lp_branch.getRealPath(path)
            transport = self._getTransportForLaunchpadBranch(lp_branch)
            return transport, real_path

        return deferred.addCallback(got_branch)

    def get_url(self):
        """Return the URL of this server."""
        return self._scheme

    def setUp(self):
        """See Server.setUp."""
        register_transport(self.get_url(), self._transportFactory)
        self._is_set_up = True

    def tearDown(self):
        """See Server.tearDown."""
        if not self._is_set_up:
            return
        self._is_set_up = False
        unregister_transport(self.get_url(), self._transportFactory)


class LaunchpadServer(_BaseLaunchpadServer):
    """The Server used for codehosting services.

    This server provides a VFS that backs onto two transports: a 'hosted'
    transport and a 'mirrored' transport. When users push up 'hosted'
    branches, the branches are written to the hosted transport. Similarly,
    whenever users access branches that they can write to, they are accessed
    from the hosted transport. The mirrored transport is used for branches
    that the user can only read.

    In addition to basic VFS operations, this server provides operations for
    creating a branch and requesting for a branch to be mirrored. The
    associated transport, `AsyncLaunchpadTransport`, has hooks in certain
    filesystem-level operations to trigger these.
    """

    def __init__(self, authserver, user_id, hosted_transport,
                 mirror_transport):
        scheme = 'lp-%d:///' % id(self)
        super(LaunchpadServer, self).__init__(scheme, authserver, user_id)
        self.asyncTransportFactory = AsyncLaunchpadTransport
        self._hosted_transport = hosted_transport
        self._mirror_transport = get_transport(
            'readonly+' + mirror_transport.base)

    def _buildControlDirectory(self, stack_on_url):
        """Return a MemoryTransport that has '.bzr/control.conf' in it."""
        return TransportFactory(
            None, None).make_control_transport(stack_on_url)

    def _parseProductControlDirectory(self, virtual_path):
        """Parse `virtual_path` and return a product and path in that product.

        If we can't parse `virtual_path`, raise `InvalidControlDirectory`.
        """
        segments = get_path_segments(virtual_path, 3)
        if len(segments) < 3:
            raise InvalidControlDirectory(virtual_path)
        user, product, control = segments[:3]
        if not user.startswith('~'):
            raise InvalidControlDirectory(virtual_path)
        if control != '.bzr':
            raise InvalidControlDirectory(virtual_path)
        return product, '/'.join([control] + segments[3:])

    def _translateControlPath(self, virtual_url_fragment):
        virtual_path = urlutils.unescape(virtual_url_fragment).encode('utf-8')
        product, path = self._parseProductControlDirectory(virtual_path)
        deferred = self._authserver.getDefaultStackedOnBranch(product)
        deferred.addCallback(self._buildControlDirectory)
        return deferred.addCallback(
            lambda transport: (transport, urlutils.escape(path)))

    def _getTransportForLaunchpadBranch(self, lp_branch):
        """Return the transport for accessing `lp_branch`."""
        if not lp_branch.can_write:
            return self._mirror_transport
        lp_branch.ensureUnderlyingPath(self._hosted_transport)
        return self._hosted_transport

    def translateVirtualPath(self, virtual_url_fragment):
        deferred = super(LaunchpadServer, self).translateVirtualPath(
            virtual_url_fragment)

        def not_a_branch(failure):
            """Called when the path simply could not point to a branch."""
            failure.trap(NotEnoughInformation)
            deferred = defer.maybeDeferred(
                self._translateControlPath, virtual_url_fragment)
            deferred.addErrback(lambda ignored: failure)
            return deferred

        return deferred.addErrback(not_a_branch)

    def createBranch(self, virtual_url_fragment):
        """Make a new directory for the given virtual URL fragment.

        If `virtual_url_fragment` is a branch directory, create the branch in
        the database, then create a matching directory on the backing
        transport.

        :param virtual_url_fragment: A virtual path to be translated.

        :raise NotABranchPath: If `virtual_path` does not have at least a
            valid path to a branch.
        :raise TransportNotPossible: If the branch owner or product does not
            exist.
        :raise PermissionDenied: If the branch cannot be created in the
            database. This might indicate that the branch already exists, or
            that its creation is forbidden by a policy.
        """
        lp_branch = LaunchpadBranch(
            self._authserver, virtual_url_fragment, None, None)
        return lp_branch.create()

    def requestMirror(self, virtual_url_fragment):
        """Mirror the branch that owns 'virtual_url_fragment'.

        :param virtual_path: A virtual URL fragment to be translated.

        :raise NotABranchPath: If `virtual_url_fragment` does not have at
            least a valid path to a branch.
        """
        deferred = self._getLaunchpadBranch(virtual_url_fragment)

        def got_branch((lp_branch, ignored)):
            return lp_branch.requestMirror()

        return deferred.addCallback(got_branch)


class LaunchpadInternalServer(_BaseLaunchpadServer):
    """Server for Launchpad internal services.

    This server provides access to a transport using the Launchpad virtual
    filesystem. Unlike the `LaunchpadServer`, it backs onto a single transport
    and doesn't do any permissions work.

    Intended for use with the branch puller and scanner.
    """

    def __init__(self, scheme, authserver, branch_transport):
        super(LaunchpadInternalServer, self).__init__(
            scheme, authserver, LAUNCHPAD_SERVICES)
        self.asyncTransportFactory = AsyncVirtualTransport
        self._branch_transport = branch_transport

    def _getTransportForLaunchpadBranch(self, lp_branch):
        """Return the transport for accessing `lp_branch`."""
        try:
            lp_branch.ensureUnderlyingPath(self._branch_transport)
        except TransportNotPossible:
            # We try to make the branch's directory on the underlying
            # transport. If the transport is read-only, then we just continue
            # silently.
            pass
        return self._branch_transport


def get_scanner_server():
    """Get a Launchpad internal server for scanning branches."""
    proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
    authserver = BlockingProxy(proxy)
    branch_transport = get_transport(
        'readonly+' + config.supermirror.warehouse_root_url)
    return LaunchpadInternalServer(
        'lp-mirrored:///', authserver, branch_transport)


def get_puller_server():
    """Get a server for the Launchpad branch puller.

    The server wraps up two `LaunchpadInternalServer`s. One of them points to
    the hosted branch area and is read-only, the other points to the mirrored
    area and is read/write.
    """
    proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
    authserver = BlockingProxy(proxy)
    hosted_transport = get_readonly_transport(
        get_chrooted_transport(config.codehosting.branches_root))
    mirrored_transport = get_chrooted_transport(
        config.supermirror.branchesdest)
    hosted_server = LaunchpadInternalServer(
        'lp-hosted:///', authserver,
        get_readonly_transport(hosted_transport))
    mirrored_server = LaunchpadInternalServer(
        'lp-mirrored:///', authserver, mirrored_transport)
    return _MultiServer(hosted_server, mirrored_server)


class AsyncLaunchpadTransport(AsyncVirtualTransport):
    """Virtual transport to implement the Launchpad VFS for branches.

    This implements a few hooks to translate filesystem operations (such as
    making a certain kind of directory) into Launchpad operations (such as
    creating a branch in the database).

    It also converts the Launchpad-specific translation errors (such as 'not a
    valid branch path') into Bazaar errors (such as 'no such file').
    """

    def _getUnderylingTransportAndPath(self, relpath):
        """Return the underlying transport and path for `relpath`."""
        deferred = AsyncVirtualTransport._getUnderylingTransportAndPath(
            self, relpath)
        def convert_failure(failure):
            failure.trap(NotABranchPath)
            # If a virtual path doesn't point to a branch, then we cannot
            # translate it to an underlying transport. For almost all
            # purposes, this is as good as not existing at all.
            exception = failure.value
            raise NoSuchFile(
                exception.virtual_url_fragment, exception.reason)
        return deferred.addErrback(convert_failure)

    def mkdir(self, relpath, mode=None):
        # We hook into mkdir so that we can request the creation of a branch
        # and so that we can provide useful errors in the special case where
        # the user tries to make a directory like "~foo/bar". That is, a
        # directory that has too little information to be translated into a
        # Launchpad branch.
        deferred = AsyncVirtualTransport._getUnderylingTransportAndPath(
            self, relpath)
        def maybe_make_branch_in_db(failure):
            # Looks like we are trying to make a branch.
            failure.trap(NoSuchFile)
            return self.server.createBranch(self._abspath(relpath))
        def check_permission_denied(failure):
            # You can't ever create a directory that's not even a valid branch
            # name. That's strictly forbidden.
            failure.trap(NotABranchPath)
            exc_object = failure.value
            raise PermissionDenied(
                exc_object.virtual_url_fragment, exc_object.reason)
        def real_mkdir((transport, path)):
            return getattr(transport, 'mkdir')(path, mode)

        deferred.addCallback(real_mkdir)
        deferred.addErrback(maybe_make_branch_in_db)
        deferred.addErrback(check_permission_denied)
        return deferred

    def rename(self, rel_from, rel_to):
        # We hook into rename to catch the "unlock branch" event, so that we
        # can request a mirror once a branch is unlocked.
        abs_from = self._abspath(rel_from)
        if is_lock_directory(abs_from):
            deferred = self.server.requestMirror(abs_from)
        else:
            deferred = defer.succeed(None)
        deferred = deferred.addCallback(
            lambda ignored: AsyncVirtualTransport.rename(
                self, rel_from, rel_to))
        return deferred

    def rmdir(self, relpath):
        # We hook into rmdir in order to prevent users from deleting branches,
        # products and people from the VFS.
        virtual_url_fragment = self._abspath(relpath)
        path_segments = virtual_url_fragment.lstrip('/').split('/')
        if len(path_segments) <= 3:
            return defer.fail(
                failure.Failure(PermissionDenied(virtual_url_fragment)))
        return AsyncVirtualTransport.rmdir(self, relpath)
