# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for dealing with Bazaar.

Much of the code in here should be submitted upstream. The rest is code that
integrates between Bazaar's infrastructure and Launchpad's infrastructure.
"""

__metaclass__ = type
__all__ = [
    'add_exception_logging_hook',
    'BranchLoopDetected',
    'DenyingServer',
    'get_branch_stacked_on_url',
    'get_vfs_format_classes',
    'HttpAsLocalTransport',
    'identical_formats',
    'install_oops_handler',
    'is_branch_stackable',
    'remove_exception_logging_hook',
    'safe_open',
    'SafeOpenFailed',
    'UnsafeUrlSeen',
    ]

import os
import sys
import threading

from bzrlib import config, trace
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.errors import (
    NotStacked, UnstackableBranchFormat, UnstackableRepositoryFormat)
from bzrlib.remote import RemoteBranch, RemoteBzrDir, RemoteRepository
from bzrlib.transport import register_transport, unregister_transport
from bzrlib.transport.local import LocalTransport

from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility, ScriptRequest)

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


_exception_logging_hooks = []

_original_log_exception_quietly = trace.log_exception_quietly


def _hooked_log_exception_quietly():
    """Wrapper around `trace.log_exception_quietly` that calls hooks."""
    _original_log_exception_quietly()
    for hook in _exception_logging_hooks:
        hook()


def add_exception_logging_hook(hook_function):
    """Call 'hook_function' when bzr logs an exception.

    :param hook_function: A nullary callable that relies on sys.exc_info()
        for exception information.
    """
    if trace.log_exception_quietly == _original_log_exception_quietly:
        trace.log_exception_quietly = _hooked_log_exception_quietly
    _exception_logging_hooks.append(hook_function)


def remove_exception_logging_hook(hook_function):
    """Cease calling 'hook_function' whenever bzr logs an exception.

    :param hook_function: A nullary callable that relies on sys.exc_info()
        for exception information. It will be removed from the exception
        logging hooks.
    """
    _exception_logging_hooks.remove(hook_function)
    if len(_exception_logging_hooks) == 0:
        trace.log_exception_quietly == _original_log_exception_quietly


def make_oops_logging_exception_hook(error_utility, request):
    """Make a hook for logging OOPSes."""
    def log_oops():
        error_utility.raising(sys.exc_info(), request)
    return log_oops


class BazaarOopsRequest(ScriptRequest):
    """An OOPS request specific to bzr."""

    def __init__(self, user_id):
        """Construct a `BazaarOopsRequest`.

        :param user_id: The database ID of the user doing this.
        """
        data = [('user_id', user_id)]
        super(BazaarOopsRequest, self).__init__(data, URL=None)


def make_error_utility(pid=None):
    """Make an error utility for logging errors from bzr."""
    if pid is None:
        pid = os.getpid()
    error_utility = ErrorReportingUtility()
    error_utility.configure('bzr_lpserve')
    error_utility.setOopsToken(str(pid))
    return error_utility


def install_oops_handler(user_id):
    """Install an OOPS handler for a bzr process.

    When installed, logs any exception passed to `log_exception_quietly`.

    :param user_id: The database ID of the user the process is running as.
    """
    error_utility = make_error_utility()
    request = BazaarOopsRequest(user_id)
    hook = make_oops_logging_exception_hook(error_utility, request)
    add_exception_logging_hook(hook)


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

    def start_server(self):
        """Prevent transports being created for specified schemes."""
        for scheme in self.schemes:
            register_transport(scheme, self._deny)
        self._is_set_up = True

    def stop_server(self):
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


def get_vfs_format_classes(branch):
    """Return the vfs classes of the branch, repo and bzrdir formats.

    'vfs' here means that it will return the underlying format classes of a
    remote branch.
    """
    if isinstance(branch, RemoteBranch):
        branch._ensure_real()
        branch = branch._real_branch
    repository = branch.repository
    if isinstance(repository, RemoteRepository):
        repository._ensure_real()
        repository = repository._real_repository
    bzrdir = branch.bzrdir
    if isinstance(bzrdir, RemoteBzrDir):
        bzrdir._ensure_real()
        bzrdir = bzrdir._real_bzrdir
    return (
        branch._format.__class__,
        repository._format.__class__,
        bzrdir._format.__class__,
        )


def identical_formats(branch_one, branch_two):
    """Check if two branches have the same bzrdir, repo, and branch formats.
    """
    return (get_vfs_format_classes(branch_one) ==
            get_vfs_format_classes(branch_two))


safe_open_data = threading.local()


def _install_hook():
    """Install `_safe_open_pre_open_hook` as a pre_open hook.

    This is called at module import time, but _safe_open_pre_open_hook doesn't
    do anything unless the `safe_open_data` threading.Local object has a
    'safe_opener' attribute in this thread.
    """
    BzrDir.hooks.install_named_hook(
        'pre_open', _safe_open_pre_open_hook, 'safe open')


def _safe_open_pre_open_hook(transport):
    """If a safe_opener is present in this thread, check `transport` is safe.
    """
    safe_opener = getattr(safe_open_data, 'safe_opener', None)
    if safe_opener is None:
        return
    abspath = transport.base
    safe_opener.checkURL(abspath)


_install_hook()


class SafeOpenFailed(Exception):
    """`safe_open` found a URL it refused to open."""


class UnsafeUrlSeen(SafeOpenFailed):
    """`safe_open` found a URL that was not on the configured scheme."""


class BranchLoopDetected(SafeOpenFailed):
    """`safe_open` detected a recursive branch loop.

    `Branch.open` traverses branch references and stacked-on locations.
    `safe_open` raises this exception if either traversal finds a URL that has
    been seen earlier in the opening process.
    """


class _SafeOpener:
    """A `_SafeOpener` knows which URLs are safe to open."""

    def __init__(self, allowed_scheme):
        self.seen_urls = set()
        self.allowed_scheme = allowed_scheme

    def checkURL(self, url):
        """Check that `url` is safe to open."""
        if url in self.seen_urls:
            raise BranchLoopDetected()
        self.seen_urls.add(url)
        if URI(url).scheme != self.allowed_scheme:
            raise UnsafeUrlSeen(
                "Attempt to open %r which is not a %s URL" % (
                    url, self.allowed_scheme))


def safe_open(allowed_scheme, url):
    """Open the branch at `url`, only accessing URLs on `allowed_scheme`.

    :raises BranchLoopDetected: If a stacked-on location or the target of a
        branch reference turns out to be a URL we've already seen in this open
        attempt.
    :raises UnsafeUrlSeen: An attempt was made to open a URL that was not on
        `allowed_scheme`.
    """
    if hasattr(safe_open_data, 'safe_opener'):
        raise AssertionError("safe_open called recursively")
    safe_open_data.safe_opener = _SafeOpener(allowed_scheme)
    try:
        return Branch.open(url)
    finally:
        del safe_open_data.safe_opener
