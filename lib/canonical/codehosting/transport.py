# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Bazaar transport for the Launchpad code hosting file system."""

__metaclass__ = type
__all__ = ['LaunchpadServer', 'LaunchpadTransport']

from bzrlib.transport import (
    get_transport,
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
                for branch_id, branch_name in branches:
                    yield ((team_dict['name'], product_name, branch_name),
                           branch_id)

    def translate_virtual_path(self, virtual_path):
        user, product, branch, path = split(virtual_path.lstrip('/'), '/', 4)
        assert user[0] == '~', "Temporary assertion"
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

