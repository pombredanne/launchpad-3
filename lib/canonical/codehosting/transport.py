# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0702

"""Bazaar transport for the Launchpad code hosting file system."""

__metaclass__ = type
__all__ = [
    'LaunchpadServer',
    'LaunchpadTransport',
    'set_up_logging',
    'UntranslatablePath',
    ]

import logging
import os

from bzrlib.errors import (
    BzrError, FileExists, InProcessTransport, NoSuchFile, PermissionDenied,
    TransportNotPossible)
from bzrlib import trace, urlutils
from bzrlib.transport import (
    get_transport,
    register_transport,
    Server,
    Transport,
    unregister_transport,
    )

from twisted.web.xmlrpc import Fault

from canonical.authserver.interfaces import (
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE, READ_ONLY)

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.bazaarfs import (
    ALLOWED_DIRECTORIES, FORBIDDEN_DIRECTORY_ERROR, is_lock_directory)
from canonical.config import config
from canonical.twistedsupport.loggingsupport import set_up_oops_reporting


def split_with_padding(a_string, splitter, num_fields, padding=None):
    """Split the given string into exactly num_fields.

    If the given string doesn't have enough tokens to split into num_fields
    fields, then the resulting list of tokens is padded with 'padding'.
    """
    tokens = a_string.split(splitter, num_fields - 1)
    tokens.extend([padding] * max(0, num_fields - len(tokens)))
    return tokens


# XXX: JonathanLange 2007-06-13 bugs=120135:
# This should probably be part of bzrlib.
def makedirs(base_transport, path, mode=None):
    """Create 'path' on 'base_transport', even if parents of 'path' don't
    exist yet.
    """
    need_to_create = []
    transport = base_transport.clone(path)
    while True:
        try:
            transport.mkdir('.', mode)
        except NoSuchFile:
            need_to_create.append(transport)
        except FileExists:
            # Nothing to do. Directory made.
            return
        else:
            break
        transport = transport.clone('..')
    while need_to_create:
        transport = need_to_create.pop()
        transport.mkdir('.', mode)


def get_path_segments(path):
    """Break up the given path into segments.

    If 'path' ends with a trailing slash, then the final empty segment is
    ignored.
    """
    return path.strip('/').split('/')


class _NotFilter(logging.Filter):
    """A Filter that only allows records that do *not* match.

    A _NotFilter initialized with "A.B" will allow "C", "A.BB" but not allow
    "A.B", "A.B.C" etc.
    """

    def filter(self, record):
        return not logging.Filter.filter(self, record)


def set_up_logging(configure_oops_reporting=False):
    """Set up logging for the smart server.

    This sets up a debugging handler on the 'codehosting' logger, makes sure
    that things logged there won't go to stderr (necessary because of
    bzrlib.trace shenanigans) and then returns the 'codehosting' logger.

    In addition, if configure_oops_reporting is True, install a
    Twisted log observer that ensures unhandled exceptions get
    reported as OOPSes.
    """
    log = logging.getLogger('codehosting')

    if config.codehosting.debug_logfile is not None:
        # Create the directory that contains the debug logfile.
        parent_dir = os.path.dirname(config.codehosting.debug_logfile)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        assert os.path.isdir(parent_dir), (
            "%r should be a directory" % parent_dir)

        # Messages logged to 'codehosting' are stored in the debug_logfile.
        handler = logging.FileHandler(config.codehosting.debug_logfile)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s %(levelname)-8s %(name)s\t%(message)s'))
        handler.setLevel(logging.DEBUG)
        log.addHandler(handler)

    # Don't log 'codehosting' messages to stderr.
    if getattr(trace, '_stderr_handler', None) is not None:
        trace._stderr_handler.addFilter(_NotFilter('codehosting'))

    log.setLevel(logging.DEBUG)

    if configure_oops_reporting:
        set_up_oops_reporting('codehosting')

    return log


class UntranslatablePath(BzrError):

    _fmt = ("Could not translate %(path)s onto backing transport for "
            "user %(user)r")


class LaunchpadServer(Server):
    """Bazaar Server for Launchpad branches.

    See LaunchpadTransport for more information.
    """

    def __init__(self, authserver, user_id, hosting_transport,
                 mirror_transport):
        """
        Construct a LaunchpadServer.

        :param authserver: An xmlrpclib.ServerProxy that points to the
            authserver.
        :param user_id: A login ID for the user who is accessing branches.
        :param hosting_transport: A Transport pointing to the root of where
            the branches are actually stored.
        :param mirror_transport: A Transport pointing to the root of where
            branches are mirrored to.
        """
        # bzrlib's Server class does not have a constructor, so we cannot
        # safely upcall it.
        # pylint: disable-msg=W0231

        # Cache for authserver responses to getBranchInformation(). This maps
        # from (user, product, branch) tuples to whatever
        # getBranchInformation() returns. To clear an individual tuple, set
        # its value in the cache to None, or delete it from the cache.
        self._branch_info_cache = {}
        self.authserver = authserver
        self.user_dict = self.authserver.getUser(user_id)
        self.user_id = self.user_dict['id']
        self.user_name = self.user_dict['name']
        self.backing_transport = hosting_transport
        self.mirror_transport = get_transport(
            'readonly+' + mirror_transport.base)
        self._is_set_up = False
        self.logger = logging.getLogger(
            'codehosting.lpserve.%s' % self.user_name)

    def requestMirror(self, virtual_path):
        """Request that the branch that owns 'virtual_path' be mirrored."""
        branch_id, ignored, path = self._translate_path(virtual_path)
        self.logger.info('Requesting mirror for: %r', branch_id)
        self.authserver.requestMirror(self.user_id, branch_id)

    def make_branch_dir(self, virtual_path):
        """Make a new directory for the given virtual path.

        If the request is to make a user or a product directory, fail
        with PermissionDenied error. If the request is to make a
        branch directory, create the branch in the database then
        create a matching directory on the backing transport.
        """
        self.logger.info('mkdir(%r)', virtual_path)
        path_segments = get_path_segments(virtual_path)
        if len(path_segments) != 3:
            raise PermissionDenied(
                'This method is only for creating branches: %s'
                % (virtual_path,))
        branch_id = self._make_branch(*path_segments)
        if branch_id == '':
            raise PermissionDenied(
                'Cannot create branch: %s' % (virtual_path,))
        makedirs(self.backing_transport, branch_id_to_path(branch_id))

    def _make_branch(self, user, product, branch):
        """Create a branch in the database for the given user and product.

        :param user: The loginID of the user who owns the new branch.
        :param product: The name of the product to which the new branch
            belongs.
        :param branch: The name of the new branch.

        :raise PermissionDenied: If 'user' does not begin with a '~' or if
            'product' is not the name of an existing product.
        :return: The database ID of the new branch.
        """
        self.logger.debug('_make_branch(%r, %r, %r)', user, product, branch)
        if not user.startswith('~'):
            raise PermissionDenied(
                'Path must start with user or team directory: %r' % (user,))
        user = user[1:]
        branch_id, permissions = self._get_branch_information(
            user, product, branch)
        if branch_id != '':
            self.logger.debug('Branch (%r, %r, %r) already exists ')
            return branch_id
        else:
            try:
                return self._create_branch(user, product, branch)
            except Fault, f:
                if f.faultCode == NOT_FOUND_FAULT_CODE:
                    # One might think that it would make sense to raise
                    # NoSuchFile here, but that makes the client do "clever"
                    # things like say "Parent directory of
                    # bzr+ssh://bazaar.launchpad.dev/~noone/firefox/branch
                    # does not exist.  You may supply --create-prefix to
                    # create all leading parent directories."  Which is just
                    # misleading.
                    raise TransportNotPossible(f.faultString)
                elif f.faultCode == PERMISSION_DENIED_FAULT_CODE:
                    raise PermissionDenied(f.faultString)
                else:
                    raise

    def _create_branch(self, user, product, branch):
        """Create a branch on the authserver."""
        branch_id = self.authserver.createBranch(
            self.user_id, user, product, branch)
        # Clear the cache for this branch. We *could* populate it with
        # (branch_id, 'w'), but then we'd be building in more assumptions
        # about the authserver.
        self._branch_info_cache[(user, product, branch)] = None
        return branch_id

    def _get_branch_information(self, user, product, branch):
        """Get branch information from the authserver."""
        branch_info = self._branch_info_cache.get((user, product, branch))
        if branch_info is None:
            branch_info = self.authserver.getBranchInformation(
                self.user_id, user, product, branch)
            self._branch_info_cache[(user, product, branch)] = branch_info
        return branch_info

    def _translate_path(self, virtual_path):
        """Translate a virtual path into an internal branch id, permissions
        and relative path.

        'virtual_path' is a path that points to a branch or a path within a
        branch. This method returns the id of the branch, the permissions that
        the user running the server has for that branch and the path relative
        to that branch. In short, everything you need to be able to access a
        file in a branch.
        """
        # We can safely pad with '' because we can guarantee that no product
        # or branch name is the empty string. (Mapping '' to '+junk' happens
        # in _iter_branches). 'user' is checked later.
        user_dir, product, branch, path = split_with_padding(
            virtual_path.lstrip('/'), '/', 4, padding='')
        if not user_dir.startswith('~'):
            raise TransportNotPossible(
                'Path must start with user or team directory: %r'
                % (user_dir,))
        user = user_dir[1:]
        branch_id, permissions = self._get_branch_information(
            user, product, branch)
        return branch_id, permissions, path

    def translate_virtual_path(self, virtual_path):
        """Translate an absolute virtual path into the real path on the
        backing transport.

        :raise UntranslatablePath: If path is untranslatable. This could be
            because the path is too short (doesn't include user, product and
            branch), or because the user, product or branch in the path don't
            exist.

        :raise TransportNotPossible: If the path is necessarily invalid. Most
            likely because it didn't begin with a tilde ('~').

        :return: The equivalent real path on the backing transport.
        """
        self.logger.debug('translate_virtual_path(%r)', virtual_path)
        segments = get_path_segments(virtual_path)
        # XXX: JamesHenstridge 2007-10-09
        # We trim the segments list so that we don't raise
        # PermissionDenied when the client tries to read
        # /~user/project/.bzr/branch-format when checking for a shared
        # repository (instead, we'll fail to look up the branch, and
        # return UntranslatablePath).  This whole function will
        # probably need refactoring when we move to actually
        # supporting shared repos.
        if '.bzr' in segments:
            segments = segments[:segments.index('.bzr')]
        if (len(segments) == 4 and segments[-1] not in ALLOWED_DIRECTORIES):
            raise PermissionDenied(
                FORBIDDEN_DIRECTORY_ERROR % (segments[-1],))

        # XXX: JonathanLange 2007-05-29, We could differentiate between
        # 'branch not found' and 'not enough information in path to figure out
        # a branch'.
        branch_id, permissions, path = self._translate_path(virtual_path)
        self.logger.debug(
            'Translated %r => %r', virtual_path,
            (branch_id, permissions, path))
        if branch_id == '':
            raise UntranslatablePath(path=virtual_path, user=self.user_name)
        return '/'.join([branch_id_to_path(branch_id), path]), permissions

    def _factory(self, url):
        """Construct a transport for the given URL. Used by the registry."""
        assert url.startswith(self.scheme)
        return LaunchpadTransport(self, url)

    def get_url(self):
        """Return the URL of this server.

        The URL is of the form 'lp-<object_id>:///', where 'object_id' is
        id(self). This ensures that we can have LaunchpadServer objects for
        different users, different backing transports and, theoretically,
        different authservers.

        See Server.get_url.
        """
        return self.scheme

    def setUp(self):
        """See Server.setUp."""
        self.scheme = 'lp-%d:///' % id(self)
        register_transport(self.scheme, self._factory)
        self._is_set_up = True

    def tearDown(self):
        """See Server.tearDown."""
        if not self._is_set_up:
            return
        self._is_set_up = False
        self._branch_info_cache.clear()
        unregister_transport(self.scheme, self._factory)


class LaunchpadTransport(Transport):
    """Transport to map from ~user/product/branch paths to codehosting paths.

    Launchpad serves its branches from URLs that look like
    bzr+ssh://launchpad/~user/product/branch. On the filesystem, the branches
    are stored by their id.

    This transport maps from the external, 'virtual' paths to the internal
    filesystem paths. The internal filesystem is represented by a backing
    transport.
    """

    def __init__(self, server, url):
        self.server = server
        Transport.__init__(self, url)

    def external_url(self):
        # There's no real external URL to this transport. It's heavily
        # dependent on the process.
        raise InProcessTransport(self)

    def _abspath(self, relpath):
        """Return the absolute path to `relpath` without the schema."""
        return urlutils.joinpath(self.base[len(self.server.scheme)-1:],
                                 relpath)

    def _call(self, methodname, relpath, *args, **kwargs):
        """Call a method on the backing transport, translating relative,
        virtual paths to filesystem paths.

        If 'relpath' translates to a path that we only have read-access to,
        then the method will be called on the backing transport decorated with
        'readonly+'.

        :raise NoSuchFile: If the path cannot be translated.
        :raise TransportNotPossible: If trying to do a write operation on a
            read-only path.
        """
        transport, path, permissions = self._get_transport_and_path(relpath)
        self.server.logger.info(
            '%s(%r -> %r, args=%r, kwargs=%r)',
            methodname, relpath, (path, permissions), args, kwargs)
        method = getattr(transport, methodname)
        return method(path, *args, **kwargs)

    def _get_transport_and_path(self, relpath):
        path, permissions = self._translate_virtual_path(relpath)
        if permissions == READ_ONLY:
            transport = self.server.mirror_transport
        else:
            transport = self.server.backing_transport
        return transport, path, permissions

    def _translate_virtual_path(self, relpath):
        """Translate a virtual path into a path on the backing transport.

        :raise NoSuchFile: If there is not way to map the given relpath to the
            backing transport.

        :return: A valid path on the backing transport.
        """
        try:
            return self.server.translate_virtual_path(self._abspath(relpath))
        except (UntranslatablePath, TransportNotPossible):
            raise NoSuchFile(relpath)

    # Transport methods
    def abspath(self, relpath):
        self.server.logger.debug('abspath(%s)', relpath)
        return urlutils.join(self.server.scheme, relpath)

    def append_file(self, relpath, f, mode=None):
        return self._call('append_file', relpath, f, mode)

    def clone(self, relpath=None):
        self.server.logger.debug('clone(%s)', relpath)
        if relpath is None:
            return LaunchpadTransport(self.server, self.base)
        else:
            return LaunchpadTransport(
                self.server, urlutils.join(self.base, relpath))

    def delete(self, relpath):
        return self._call('delete', relpath)

    def delete_tree(self, relpath):
        return self._call('delete_tree', relpath)

    def get(self, relpath):
        return self._call('get', relpath)

    def has(self, relpath):
        return self._call('has', relpath)

    def iter_files_recursive(self):
        self.server.logger.debug('iter_files_recursive()')
        transport, path, permissions = self._get_transport_and_path('.')
        return transport.clone(path).iter_files_recursive()

    def listable(self):
        self.server.logger.debug('listable()')
        transport, path, permissions = self._get_transport_and_path('.')
        return transport.listable()

    def list_dir(self, relpath):
        return self._call('list_dir', relpath)

    def lock_read(self, relpath):
        return self._call('lock_read', relpath)

    def lock_write(self, relpath):
        return self._call('lock_write', relpath)

    def mkdir(self, relpath, mode=None):
        # If we can't translate the path, then perhaps we are being asked to
        # create a new branch directory. Delegate to the server, as it knows
        # how to deal with absolute virtual paths.
        try:
            return self._call('mkdir', relpath, mode)
        except NoSuchFile:
            return self.server.make_branch_dir(self._abspath(relpath))

    def put_file(self, relpath, f, mode=None):
        return self._call('put_file', relpath, f, mode)

    def rename(self, rel_from, rel_to):
        path, permissions = self._translate_virtual_path(rel_to)
        if permissions == READ_ONLY:
            raise TransportNotPossible('readonly transport')
        abs_from = self._abspath(rel_from)
        if is_lock_directory(abs_from):
            self.server.requestMirror(abs_from)
        return self._call('rename', rel_from, path)

    def rmdir(self, relpath):
        virtual_path = self._abspath(relpath)
        path_segments = path = virtual_path.lstrip('/').split('/')
        if len(path_segments) <= 3:
            raise PermissionDenied(virtual_path)
        return self._call('rmdir', relpath)

    def stat(self, relpath):
        return self._call('stat', relpath)
