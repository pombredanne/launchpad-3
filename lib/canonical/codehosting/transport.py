# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Bazaar transport for the Launchpad code hosting file system."""

__metaclass__ = type
__all__ = ['branch_id_to_path', 'LaunchpadServer', 'LaunchpadTransport']


from bzrlib.errors import BzrError, NoSuchFile, TransportNotPossible
from bzrlib import urlutils
from bzrlib.transport import (
    register_transport,
    Server,
    Transport,
    unregister_transport,
    )


def branch_id_to_path(branch_id):
    """Convert the given branch ID into NN/NN/NN/NN form, where NN is a two
    digit hexadecimal number.
    """
    h = "%08x" % int(branch_id)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])


def split_with_padding(a_string, splitter, num_fields, padding=''):
    """Split the given string into exactly num_fields.

    If the given string doesn't have enough tokens to split into num_fields
    fields, then the resulting list of tokens is padded with 'padding'.
    """
    tokens = a_string.split(splitter, num_fields - 1)
    tokens.extend([padding] * max(0, num_fields - len(tokens)))
    return tokens


def makedirs(base_transport, path, mode=None):
    """Create 'path' on 'base_transport', even if parents of 'path' don't exist
    yet.
    """
    need_to_create = []
    transport = base_transport.clone(path)
    while True:
        try:
            transport.mkdir('.', mode)
        except NoSuchFile:
            need_to_create.append(transport)
        else:
            break
        transport = transport.clone('..')
    while need_to_create:
        transport = need_to_create.pop()
        transport.mkdir('.', mode)


class UntranslatablePath(BzrError):

    _fmt = ("Could not translate %(path)s onto backing transport for "
            "user %(user)r")


class LaunchpadServer(Server):
    """Bazaar Server for Launchpad branches.

    See LaunchpadTransport for more information.
    """

    def __init__(self, authserver, user_id, transport):
        """
        Construct a LaunchpadServer.

        :param authserver: An xmlrpclib.ServerProxy that points to the
            authserver.
        :param user_id: A login ID for the user who is accessing branches.
        :param transport: A Transport pointing to the root of where the
            branches are actually stored.
        """
        self.authserver = authserver
        self.user_id = user_id
        self.backing_transport = transport
        # XXX: JonathanLange 2007-05-29, Instead of fetching branch information
        # as needed, we load it all when the server is started. This mimics the
        # behaviour of the SFTP server, and is the path of least resistance
        # given the authserver's present API. However, in the future, we will
        # want to get branch information as required.
        self._branches = dict(self._iter_branches())

    def _iter_branches(self):
        for team_dict in self.authserver.getUser(self.user_id)['teams']:
            products = self.authserver.getBranchesForUser(team_dict['id'])
            for product_id, product_name, branches in products:
                if product_name == '':
                    product_name = '+junk'
                for branch_id, branch_name in branches:
                    yield ((team_dict['name'], product_name, branch_name),
                           branch_id)

    def mkdir(self, virtual_path):
        """Make a new directory for the given virtual path.

        If the request is to make a user or a product directory, fail with
        NoSuchFile error. If the request is to make a branch directory, create
        the branch in the database then create a matching directory on the
        backing transport.
        """
        path_segments = virtual_path.lstrip('/').split('/')
        if len(path_segments) != 3:
            raise NoSuchFile(virtual_path)
        branch_id = self._make_branch(*path_segments)

        # XXX: JonathanLange 2007-05-29, This should be
        # self.backing_transport.makedirs instead.
        makedirs(self.backing_transport, branch_id_to_path(branch_id))

    def _make_branch(self, user, product, branch):
        """Create a branch in the database for the given user and product.

        :param user: The loginID of the user who owns the new branch.
        :param product: The name of the product to which the new branch
            belongs.
        :param branch: The name of the new branch.
        :return: The database ID of the new branch.
        """
        if not user.startswith('~'):
            raise TransportNotPossible(
                'Path must start with user or team directory: %r' % (user,))
        user = user[1:]
        user_id = self.authserver.getUser(user)['id']
        # If product is '+junk', then product_id will be '', which is XML-RPC's
        # way of saying None.
        product_id = self.authserver.fetchProductID(product)
        branch_id = self.authserver.createBranch(user_id, product_id, branch)
        # Maintain the local cache of branch information. Alternatively, we
        # could do: self._branches = dict(self._iter_branches())
        self._branches[(user, product, branch)] = branch_id
        return branch_id

    def translate_virtual_path(self, virtual_path):
        """Translate an absolute virtual path into the real path on the backing
        transport.

        :raise UntranslatablePath: If path is untranslatable. This could be
            because the path is too short (doesn't include user, product and
            branch), or because the user, product or branch in the path don't
            exist.

        :raise TransportNotPossible: If the path is necessarily invalid. Most
            likely because it didn't begin with a tilde ('~').

        :return: The equivalent real path on the backing transport.
        """
        # XXX: JonathanLange 2007-05-29, We could differentiate between
        # 'branch not found' and 'not enough information in path to figure out
        # a branch'.

        # We can safely pad with '' because we can guarantee that no product or
        # branch name is the empty string. (Mapping '' to '+junk' happens
        # in _iter_branches). 'user' is checked later.
        user, product, branch, path = split_with_padding(
            virtual_path.lstrip('/'), '/', 4)
        if not user.startswith('~'):
            raise TransportNotPossible(
                'Path must start with user or team directory: %r' % (user,))
        user = user[1:]
        try:
            branch_id = self._branches[(user, product, branch)]
        except KeyError:
            raise UntranslatablePath(path=virtual_path, user=self.user_id)
        return '/'.join([branch_id_to_path(branch_id), path])

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

    def tearDown(self):
        """See Server.tearDown."""
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

    def _abspath(self, relpath):
        """Return the absolute path to `relpath` without the schema."""
        return urlutils.joinpath(self.base[len(self.server.scheme)-1:],
                                 relpath)

    def _call(self, methodname, relpath, *args, **kwargs):
        """Call a method on the backing transport, translating relative,
        virtual paths to filesystem paths.
        """
        method = getattr(self.server.backing_transport, methodname)
        return method(self._translate_virtual_path(relpath), *args, **kwargs)

    def _translate_virtual_path(self, relpath):
        """Translate a virtual path into a path on the backing transport."""
        try:
            return self.server.translate_virtual_path(self._abspath(relpath))
        except UntranslatablePath:
            raise NoSuchFile(relpath)

    # Transport methods
    def abspath(self, relpath):
        return urlutils.join(self.server.scheme, relpath)

    def append_file(self, relpath, f, mode=None):
        return self._call('append_file', relpath, f, mode)

    def clone(self, relpath):
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
        backing_transport = self.server.backing_transport.clone(
            self._translate_virtual_path('.'))
        return backing_transport.iter_files_recursive()

    def listable(self):
        return self.server.backing_transport.listable()

    def list_dir(self, relpath):
        return self._call('list_dir', relpath)

    def lock_read(self, relpath):
        return self._call('lock_read', relpath)

    def lock_write(self, relpath):
        return self._call('lock_write', relpath)

    def mkdir(self, relpath, mode=None):
        # XXX: JonathanLange 2007-05-29, ugly and unclear.
        try:
            path = self.server.translate_virtual_path(self._abspath(relpath))
        except UntranslatablePath:
            return self.server.mkdir(self._abspath(relpath))
        else:
            return self.server.backing_transport.mkdir(path, mode)

    def put_file(self, relpath, f, mode=None):
        return self._call('put_file', relpath, f, mode)

    def rename(self, rel_from, rel_to):
        return self._call(
            'rename', rel_from, self._translate_virtual_path(rel_to))

    def rmdir(self, relpath):
        return self._call('rmdir', relpath)

    def stat(self, relpath):
        return self._call('stat', relpath)
