# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Utilities for dealing with Bazaar.

Everything in here should be submitted upstream.
"""

__metaclass__ = type
__all__ = [
    'DenyingServer',
    'ensure_base',
    'get_branch_stacked_on_url',
    'HttpAsLocalTransport',
    'is_branch_stackable',
    ]

from bzrlib.builtins import _create_prefix as create_prefix
from bzrlib import config
from bzrlib.errors import (
    NoSuchFile, NotStacked, UnstackableBranchFormat,
    UnstackableRepositoryFormat)
from bzrlib.remote import RemoteBzrDir
from bzrlib.transport import register_transport, unregister_transport
from bzrlib.transport.local import LocalTransport

from lazr.uri import URI


def is_branch_stackable(bzr_branch):
    """Return True if the bzr_branch is able to be stacked."""
    try:
        bzr_branch.get_stacked_on_url()
    except (UnstackableBranchFormat, UnstackableRepositoryFormat):
        return False
    except NotStacked:
        # This is fine.
        return True
    else:
        # If nothing is raised, then stackable (and stacked even).
        return True


def get_branch_stacked_on_url(a_bzrdir):
    """Return the stacked-on URL for the branch in this bzrdir.

    This method lets you figure out the stacked-on URL of a branch without
    opening the stacked-on branch. This lets us check for pathologically
    stacked branches.

    :raises NotBranchError: If there is no Branch.
    :raises NotStacked: If the Branch is not stacked.
    :raises UnstackableBranchFormat: If the Branch is of an unstackable
        format.
    :return: the stacked-on URL for the branch in this bzrdir.
    """
    # XXX: JonathanLange 2008-09-04: In a better world, this method would live
    # on BzrDir. Unfortunately, Bazaar lacks the configuration APIs to make
    # this possible (see below). Alternatively, Bazaar could provide us with a
    # way to open a Branch without opening the stacked-on branch.

    # XXX: MichaelHudson 2008-09-19, bug=271924:
    # RemoteBzrDir.find_branch_format opens the branch, which defeats the
    # purpose of this helper.
    if isinstance(a_bzrdir, RemoteBzrDir):
        a_bzrdir._ensure_real()
        a_bzrdir = a_bzrdir._real_bzrdir

    # XXX: JonathanLange 2008-09-04: In Bazaar 1.6, there's no way to get the
    # format of a branch from a generic BzrDir. Here, we just assume that if
    # you can't get the branch format using the newer API (i.e.
    # BzrDir.find_branch_format()), then the branch is not stackable. Bazaar
    # post-1.6 has added 'get_branch_format' to the pre-split-out formats,
    # which we could use instead.
    find_branch_format = getattr(a_bzrdir, 'find_branch_format', None)
    if find_branch_format is None:
        raise UnstackableBranchFormat(
            a_bzrdir._format, a_bzrdir.root_transport.base)
    format = find_branch_format()
    if not format.supports_stacking():
        raise UnstackableBranchFormat(format, a_bzrdir.root_transport.base)
    branch_transport = a_bzrdir.get_branch_transport(None)
    # XXX: JonathanLange 2008-09-04: We should be using BranchConfig here, but
    # that requires opening the Branch. Bazaar should grow APIs to let us
    # safely access the branch configuration without opening the branch. Here
    # we read the 'branch.conf' and don't bother with the locations.conf or
    # bazaar.conf. This is OK for Launchpad since we don't ever want to have
    # local client configuration. It's not OK for Bazaar in general.
    branch_config = config.TransportConfig(
        branch_transport, 'branch.conf')
    stacked_on_url = branch_config.get_option('stacked_on_location')
    if not stacked_on_url:
        raise NotStacked(a_bzrdir.root_transport.base)
    return stacked_on_url


# XXX: JonathanLange 2007-06-13 bugs=120135:
# This should probably be part of bzrlib.
def ensure_base(transport):
    """Make sure that the base directory of `transport` exists.

    If the base directory does not exist, try to make it. If the parent of the
    base directory doesn't exist, try to make that, and so on.
    """
    try:
        transport.ensure_base()
    except NoSuchFile:
        create_prefix(transport)


class HttpAsLocalTransport(LocalTransport):
    """A LocalTransport that works using http URLs.

    We have this because the Launchpad database has constraints on URLs for
    branches, disallowing file:/// URLs. bzrlib itself disallows
    file://localhost/ URLs.
    """

    def __init__(self, http_url):
        file_url = URI(
            scheme='file', host='', path=URI(http_url).path)
        return super(HttpAsLocalTransport, self).__init__(
            str(file_url))

    @classmethod
    def register(cls):
        """Register this transport."""
        register_transport('http://', cls)

    @classmethod
    def unregister(cls):
        """Unregister this transport."""
        unregister_transport('http://', cls)


class DenyingServer:
    """Temporarily prevent creation of transports for certain URL schemes."""

    _is_set_up = False

    def __init__(self, schemes):
        """Set up the instance.

        :param schemes: The schemes to disallow creation of transports for.
        """
        self.schemes = schemes

    def setUp(self):
        """Prevent transports being created for specified schemes."""
        for scheme in self.schemes:
            register_transport(scheme, self._deny)
        self._is_set_up = True

    def tearDown(self):
        """Re-enable creation of transports for specified schemes."""
        if not self._is_set_up:
            return
        self._is_set_up = False
        for scheme in self.schemes:
            unregister_transport(scheme, self._deny)

    def _deny(self, url):
        """Prevent creation of transport for 'url'."""
        raise AssertionError(
            "Creation of transport for %r is currently forbidden" % url)

