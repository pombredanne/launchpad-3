# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Bazaar transport for the Launchpad code hosting file system."""

__metaclass__ = type
__all__ = ['branch_id_to_path', 'LaunchpadServer', 'LaunchpadTransport']


from bzrlib.errors import NoSuchFile, TransportNotPossible
from bzrlib import urlutils
from bzrlib.transport import (
    register_transport,
    Server,
    Transport,
    unregister_transport,
    )


def branch_id_to_path(branch_id):
    h = "%08x" % int(branch_id)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])


def split(string, splitter, num_fields):
    tokens = string.split(splitter, num_fields - 1)
    tokens.extend([''] * max(0, num_fields - len(tokens)))
    return tokens


class LaunchpadServer(Server):

    def __init__(self, authserver, user_id, transport):
        self.authserver = authserver
        self.user_id = user_id
        self.backing_transport = transport
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
        path_segments = virtual_path.strip('/').split('/')
        if len(path_segments) != 3:
            raise NoSuchFile(virtual_path)
        branch_id = self._make_branch(*path_segments)
        self.backing_transport.mkdir(branch_id_to_path(branch_id))

    def _make_branch(self, user, product, branch):
        if not user.startswith('~'):
            raise TransportNotPossible(
                'Path must start with user or team directory: %r' % (user,))
        user = user[1:]
        user_id = self.authserver.getUser(self.user_id)['id']
        product_id = self.authserver.fetchProductID(product)
        branch_id = self.authserver.createBranch(user_id, product_id, branch)
        self._branches[(user, product, branch)] = branch_id
        return branch_id

    def translate_virtual_path(self, virtual_path):
        user, product, branch, path = split(virtual_path.lstrip('/'), '/', 4)
        if not user.startswith('~'):
            raise TransportNotPossible(
                'Path must start with user or team directory: %r' % (user,))
        user = user[1:]
        branch_id = self._branches[(user, product, branch)]
        return '/'.join([branch_id_to_path(branch_id), path])

    def _factory(self, url):
        assert url.startswith(self.scheme)
        return LaunchpadTransport(self, url)

    def get_url(self):
        return self.scheme

    def setUp(self):
        self.scheme = 'lp-%d:///' % id(self)
        register_transport(self.scheme, self._factory)

    def tearDown(self):
        unregister_transport(self.scheme, self._factory)


class LaunchpadTransport(Transport):

    def __init__(self, server, url):
        self.server = server
        Transport.__init__(self, url)

    def _abspath(self, relpath):
        """Return the absolute path to `relpath` without the schema."""
        return urlutils.joinpath(self.base[len(self.server.scheme)-1:],
                                 relpath)

    def _call(self, methodname, relpath, *args, **kwargs):
        method = getattr(self.server.backing_transport, methodname)
        return method(self._translate_virtual_path(relpath), *args, **kwargs)

    def _translate_virtual_path(self, relpath):
        try:
            return self.server.translate_virtual_path(self._abspath(relpath))
        except KeyError:
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
        try:
            path = self.server.translate_virtual_path(self._abspath(relpath))
        except KeyError:
            return self.server.mkdir(self._abspath(relpath))
        else:
            return self.backing_transport.mkdir(path, mode)

    def put_file(self, relpath, f, mode=None):
        return self._call('put_file', relpath, f, mode)

    def rename(self, rel_from, rel_to):
        return self._call(
            'rename', rel_from, self._translate_virtual_path(rel_to))

    def rmdir(self, relpath):
        return self._call('rmdir', relpath)

    def stat(self, relpath):
        return self._call('stat', relpath)
