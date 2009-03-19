# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

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
talks to the database.

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
    'branch_id_to_path',
    'get_lp_server',
    'get_multi_server',
    'get_puller_server',
    'get_scanner_server',
    'LaunchpadInternalServer',
    'LaunchpadServer',
    ]

import xmlrpclib

from bzrlib.bzrdir import BzrDirFormat
from bzrlib.errors import (
    NoSuchFile, PermissionDenied, TransportNotPossible)
from bzrlib.transport import get_transport
from bzrlib.transport.memory import MemoryServer
from bzrlib.urlutils import unescape

from twisted.internet import defer
from twisted.python import failure

from zope.interface import implements, Interface

from canonical.codehosting.vfs.branchfsclient import (
    BlockingProxy, BranchFileSystemClient, trap_fault)
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.vfs.transport import (
    AsyncVirtualServer, AsyncVirtualTransport, _MultiServer,
    get_chrooted_transport, get_readonly_transport, TranslationError)
from canonical.config import config
from canonical.launchpad.interfaces.codehosting import (
    BRANCH_TRANSPORT, CONTROL_TRANSPORT, LAUNCHPAD_SERVICES)
from canonical.launchpad.xmlrpc import faults


# The directories allowed directly beneath a branch directory. These are the
# directories that Bazaar creates as part of regular operation.
ALLOWED_DIRECTORIES = ('.bzr', '.bzr.backup', 'backup.bzr')
FORBIDDEN_DIRECTORY_ERROR = (
    "Cannot create '%s'. Only Bazaar branches are allowed.")


class NotABranchPath(TranslationError):
    """Raised when we cannot translate a virtual URL fragment to a branch.

    In particular, this is raised when there is some intrinsic deficiency in
    the path itself.
    """

    _fmt = ("Could not translate %(virtual_url_fragment)r to branch. "
            "%(reason)s")


class UnknownTransportType(Exception):
    """Raised when we don't know the transport type."""


def branch_id_to_path(branch_id):
    """Convert the given branch ID into NN/NN/NN/NN form, where NN is a two
    digit hexadecimal number.

    Some filesystems are not capable of dealing with large numbers of inodes.
    The codehosting system has tens of thousands of branches and thus splits
    the branches into several directories. The Launchpad id is used in order
    to determine the splitting.
    """
    h = "%08x" % int(branch_id)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])


def get_path_segments(path, maximum_segments=-1):
    """Break up the given path into segments.

    If 'path' ends with a trailing slash, then the final empty segment is
    ignored.
    """
    return path.strip('/').split('/', maximum_segments)


def is_lock_directory(absolute_path):
    """Is 'absolute_path' a Bazaar branch lock directory?"""
    return absolute_path.endswith('/.bzr/branch/lock/held')


def get_scanner_server():
    """Get a Launchpad internal server for scanning branches."""
    proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
    branchfs_endpoint = BlockingProxy(proxy)
    branch_transport = get_readonly_transport(
        get_transport(config.codehosting.internal_branch_by_id_root))
    return LaunchpadInternalServer(
        'lp-mirrored:///', branchfs_endpoint, branch_transport)


def get_puller_server():
    """Get a server for the Launchpad branch puller.

    The server wraps up two `LaunchpadInternalServer`s. One of them points to
    the hosted branch area and is read-only, the other points to the mirrored
    area and is read/write.
    """
    return get_multi_server(write_mirrored=True)


def get_multi_server(write_hosted=False, write_mirrored=False):
    """Get a server with access to both mirrored and hosted areas.

    The server wraps up two `LaunchpadInternalServer`s. One of them points to
    the hosted branch area, the other points to the mirrored area.

    Write permision defaults to False, but can be overridden.
    :param write_hosted: if True, lp-hosted URLs are writeable.  Otherwise,
        they are read-only.
    :param write_mirrored: if True, lp-mirrored URLs are writeable.
        Otherwise, they are read-only.
    """
    proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
    branchfs_endpoint = BlockingProxy(proxy)
    hosted_transport = get_chrooted_transport(
        config.codehosting.hosted_branches_root, mkdir=True)
    if not write_hosted:
        hosted_transport = get_readonly_transport(hosted_transport)
    mirrored_transport = get_chrooted_transport(
        config.codehosting.mirrored_branches_root, mkdir=True)
    if not write_mirrored:
        mirrored_transport = get_readonly_transport(mirrored_transport)
    hosted_server = LaunchpadInternalServer(
        'lp-hosted:///', branchfs_endpoint, hosted_transport)
    mirrored_server = LaunchpadInternalServer(
        'lp-mirrored:///', branchfs_endpoint, mirrored_transport)
    return _MultiServer(hosted_server, mirrored_server)


class ITransportDispatch(Interface):
    """Turns descriptions of transports into transports."""

    def makeTransport(transport_tuple):
        """Return a transport and trailing path for 'transport_tuple'.

        :param transport_tuple: a tuple of (transport_type, transport_data,
            trailing_path), as returned by IBranchFileSystem['translatePath'].

        :return: A transport and a path on that transport that point to a
            place that matches the one described in transport_tuple.
        :rtype: (`bzrlib.transport.Transport`, str)
        """


class BranchTransportDispatch:
    """Turns BRANCH_TRANSPORT tuples into transports that point to branches.

    This transport dispatch knows how branches are laid out on the disk in a
    particular "area". It doesn't know anything about the "hosted" or
    "mirrored" areas.

    This is used directly by our internal services (puller and scanner).
    """
    implements(ITransportDispatch)

    def __init__(self, base_transport):
        self.base_transport = base_transport

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

    def makeTransport(self, transport_tuple):
        """See `ITransportDispatch`.

        :raise PermissionDenied: If the path on the branch's transport is
            forbidden because it's not in ALLOWED_DIRECTORIES.
        """
        transport_type, data, trailing_path = transport_tuple
        if transport_type != BRANCH_TRANSPORT:
            raise UnknownTransportType(transport_type)
        self._checkPath(trailing_path)
        transport = self.base_transport.clone(branch_id_to_path(data['id']))
        try:
            ensure_base(transport)
        except TransportNotPossible:
            # Silently ignore TransportNotPossible. This is raised when the
            # base transport is read-only.
            pass
        return transport, trailing_path


class TransportDispatch:
    """Make transports for hosted, mirrored areas and virtual control dirs.

    This transport dispatch knows about whether a particular branch should be
    served from the hosted or mirrored area. It also knows how to serve .bzr
    control directories for products (to enable default stacking).

    This is used for the rich codehosting VFS that we serve publically.
    """
    implements(ITransportDispatch)

    def __init__(self, hosted_transport, mirrored_transport):
        self._hosted_dispatch = BranchTransportDispatch(hosted_transport)
        self._mirrored_dispatch = BranchTransportDispatch(mirrored_transport)
        self._transport_factories = {
            BRANCH_TRANSPORT: self._makeBranchTransport,
            CONTROL_TRANSPORT: self._makeControlTransport,
            }

    def makeTransport(self, transport_tuple):
        transport_type, data, trailing_path = transport_tuple
        factory = self._transport_factories[transport_type]
        data['trailing_path'] = trailing_path
        return factory(**data), trailing_path

    def _makeBranchTransport(self, id, writable, trailing_path=''):
        if writable:
            dispatch = self._hosted_dispatch
        else:
            dispatch = self._mirrored_dispatch
        transport, ignored = dispatch.makeTransport(
            (BRANCH_TRANSPORT, dict(id=id), trailing_path))
        if not writable:
            transport = get_readonly_transport(transport)
        return transport

    def _makeControlTransport(self, default_stack_on, trailing_path=None):
        """Make a transport that points to a control directory.

        A control directory is a .bzr directory containing a 'control.conf'
        file. This is used to specify configuration for branches created
        underneath the directory that contains the control directory.

        :param default_stack_on: The default stacked-on branch URL for
            branches that respect this control directory. If empty, then
            we'll return an empty memory transport.
        :return: A read-only `MemoryTransport` containing a working BzrDir,
            configured to use the given default stacked-on location.
        """
        memory_server = MemoryServer()
        memory_server.setUp()
        transport = get_transport(memory_server.get_url())
        if default_stack_on == '':
            return transport
        format = BzrDirFormat.get_default_format()
        bzrdir = format.initialize_on_transport(transport)
        bzrdir.get_config().set_default_stack_on(unescape(default_stack_on))
        return get_readonly_transport(transport)


class _BaseLaunchpadServer(AsyncVirtualServer):
    """Bazaar `Server` for translating Lanuchpad paths via XML-RPC.

    This server provides facilities for transports that use a virtual
    filesystem, backed by an XML-RPC server.

    For more information, see the module docstring.

    :ivar _authserver: An object that has a method 'translatePath' that
        returns a Deferred that fires information about how a path can be
        translated into a transport. See `IBranchFilesystem['translatePath']`.

    :ivar _transport_dispatch: An `ITransportDispatch` provider used to
        convert the data from the authserver into an actual transport and
        path on that transport.
    """

    def __init__(self, scheme, authserver, user_id):
        """Construct a LaunchpadServer.

        :param scheme: The URL scheme to use.
        :param authserver: An XML-RPC client that implements callRemote.
        :param user_id: The database ID for the user who is accessing
            branches.
        """
        AsyncVirtualServer.__init__(self, scheme)
        self._authserver = BranchFileSystemClient(authserver, user_id)
        self._is_set_up = False

    def translateVirtualPath(self, virtual_url_fragment):
        """See `AsyncVirtualServer.translateVirtualPath`.

        Call 'translatePath' on the authserver with the fragment and then use
        'makeTransport' on the _transport_dispatch to translate that result
        into a transport and trailing path.
        """
        deferred = self._authserver.translatePath('/' + virtual_url_fragment)

        def path_not_translated(failure):
            trap_fault(
                failure, faults.PathTranslationError, faults.PermissionDenied)
            raise NoSuchFile(virtual_url_fragment)

        def unknown_transport_type(failure):
            failure.trap(UnknownTransportType)
            raise NoSuchFile(virtual_url_fragment)

        deferred.addCallbacks(
            self._transport_dispatch.makeTransport, path_not_translated)
        deferred.addErrback(unknown_transport_type)
        return deferred


class LaunchpadInternalServer(_BaseLaunchpadServer):
    """Server for Launchpad internal services.

    This server provides access to a transport using the Launchpad virtual
    filesystem. Unlike the `LaunchpadServer`, it backs onto a single transport
    and doesn't do any permissions work.

    Intended for use with the branch puller and scanner.
    """

    def __init__(self, scheme, authserver, branch_transport):
        """Construct a `LaunchpadInternalServer`.

        :param scheme: The URL scheme to use.

        :param authserver: An object that provides a 'translatePath' method.

        :param branch_transport: A Bazaar `Transport` that refers to an
            area where Launchpad branches are stored, generally either the
            hosted or mirrored areas.
        """
        super(LaunchpadInternalServer, self).__init__(
            scheme, authserver, LAUNCHPAD_SERVICES)
        self._transport_dispatch = BranchTransportDispatch(branch_transport)

    def setUp(self):
        super(LaunchpadInternalServer, self).setUp()
        try:
            self._transport_dispatch.base_transport.ensure_base()
        except TransportNotPossible:
            pass

    def destroy(self):
        """Delete the on-disk branches and tear down."""
        self._transport_dispatch.base_transport.delete_tree('.')
        self.tearDown()


class AsyncLaunchpadTransport(AsyncVirtualTransport):
    """Virtual transport to implement the Launchpad VFS for branches.

    This implements a few hooks to translate filesystem operations (such as
    making a certain kind of directory) into Launchpad operations (such as
    creating a branch in the database).

    It also converts the Launchpad-specific translation errors (such as 'not a
    valid branch path') into Bazaar errors (such as 'no such file').
    """

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
        def real_mkdir((transport, path)):
            return getattr(transport, 'mkdir')(path, mode)

        deferred.addCallback(real_mkdir)
        deferred.addErrback(maybe_make_branch_in_db)
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
        # XXX: JonathanLange 2008-11-19 bug=300551: This code assumes stuff
        # about the VFS! We need to figure out the best way to delegate the
        # decision about permission-to-delete to the XML-RPC server.
        if len(path_segments) <= 3:
            return defer.fail(
                failure.Failure(PermissionDenied(virtual_url_fragment)))
        return AsyncVirtualTransport.rmdir(self, relpath)


class LaunchpadServer(_BaseLaunchpadServer):
    """The Server used for the public SSH codehosting service.

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

    asyncTransportFactory = AsyncLaunchpadTransport

    def __init__(self, authserver, user_id, hosted_transport,
                 mirror_transport):
        """Construct a `LaunchpadServer`.

        See `_BaseLaunchpadServer` for more information.

        :param authserver: An object that has 'createBranch' and
            'requestMirror' methods in addition to a 'translatePath' method.
            These methods should return Deferreds.
            XXX: JonathanLange 2008-11-19: Specify this interface better.

        :param user_id: The database ID of the user to connect as.

        :param hosted_transport: A Bazaar `Transport` that points to the
            "hosted" area of Launchpad. See module docstring for more
            information.

        :param mirror_transport: A Bazaar `Transport` that points to the
            "mirrored" area of Launchpad. See module docstring for more
            information.
        """
        scheme = 'lp-%d:///' % id(self)
        super(LaunchpadServer, self).__init__(scheme, authserver, user_id)
        mirror_transport = get_readonly_transport(mirror_transport)
        self._transport_dispatch = TransportDispatch(
            hosted_transport, mirror_transport)

    def createBranch(self, virtual_url_fragment):
        """Make a new directory for the given virtual URL fragment.

        If `virtual_url_fragment` is a branch directory, create the branch in
        the database, then create a matching directory on the backing
        transport.

        :param virtual_url_fragment: A virtual path to be translated.

        :raise NotABranchPath: If `virtual_path` does not have at least a
            valid path to a branch.
        :raise NotEnoughInformation: If `virtual_path` does not map to a
            branch.
        :raise PermissionDenied: If the branch cannot be created in the
            database. This might indicate that the branch already exists, or
            that its creation is forbidden by a policy.
        :raise Fault: If the XML-RPC server raises errors.
        """
        deferred = self._authserver.createBranch(virtual_url_fragment)

        def translate_fault(failure):
            # We turn faults.NotFound into a PermissionDenied, even
            # though one might think that it would make sense to raise
            # NoSuchFile. Sadly, raising that makes the client do "clever"
            # things like say "Parent directory of
            # bzr+ssh://bazaar.launchpad.dev/~noone/firefox/branch does not
            # exist. You may supply --create-prefix to create all leading
            # parent directories", which is just misleading.
            fault = trap_fault(
                failure, faults.NotFound, faults.PermissionDenied)
            raise PermissionDenied(virtual_url_fragment, fault.faultString)

        return deferred.addErrback(translate_fault)

    def requestMirror(self, virtual_url_fragment):
        """Mirror the branch that owns 'virtual_url_fragment'.

        :param virtual_path: A virtual URL fragment to be translated.

        :raise NotABranchPath: If `virtual_url_fragment` points to a path
            that's not a branch.
        :raise NotEnoughInformation: If `virtual_url_fragment` cannot be
            translated to a branch.
        :raise Fault: If the XML-RPC server raises errors.
        """
        deferred = self._authserver.translatePath('/' + virtual_url_fragment)

        def got_path_info((transport_type, data, trailing_path)):
            if transport_type != BRANCH_TRANSPORT:
                raise NotABranchPath(virtual_url_fragment)
            return self._authserver.requestMirror(data['id'])

        return deferred.addCallback(got_path_info)


def get_lp_server(branchfs_client, user_id, hosted_url, mirror_url):
    """Create a Launchpad server.

    :param branchfs_client: An `xmlrpclib.ServerProxy` (or equivalent) for the
        branch file system end-point.
    :param user_id: A unique database ID of the user whose branches are
        being served.
    :param hosted_url: Where the branches are uploaded to.
    :param mirror_url: Where all Launchpad branches are mirrored.
    :return: A `LaunchpadServer`.
    """
    # XXX: JonathanLange 2007-05-29: The 'chroot' lines lack unit tests.
    hosted_transport = get_chrooted_transport(hosted_url)
    mirror_transport = get_chrooted_transport(mirror_url)
    lp_server = LaunchpadServer(
        BlockingProxy(branchfs_client), user_id,
        hosted_transport, mirror_transport)
    return lp_server
