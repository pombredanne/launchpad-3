# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Safe branch opening."""

__metaclass__ = type

from bzrlib import urlutils
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir

from lazr.uri import URI

import threading

__all__ = [
    'AcceptAnythingPolicy',
    'BadUrl',
    'BlacklistPolicy',
    'BranchLoopError',
    'BranchOpenPolicy',
    'BranchReferenceForbidden',
    'SafeBranchOpener',
    'WhitelistPolicy',
    'safe_open',
    ]


# TODO JelmerVernooij 2011-08-06: This module is generic enough to be
# in bzrlib, and may be of use to others.


class BadUrl(Exception):
    """Tried to access a branch from a bad URL."""


class BranchReferenceForbidden(Exception):
    """Trying to mirror a branch reference and the branch type does not allow
    references.
    """


class BranchLoopError(Exception):
    """Encountered a branch cycle.

    A URL may point to a branch reference or it may point to a stacked branch.
    In either case, it's possible for there to be a cycle in these references,
    and this exception is raised when we detect such a cycle.
    """


class BranchOpenPolicy:
    """Policy on how to open branches.

    In particular, a policy determines which branches are safe to open by
    checking their URLs and deciding whether or not to follow branch
    references.
    """

    def shouldFollowReferences(self):
        """Whether we traverse references when mirroring.

        Subclasses must override this method.

        If we encounter a branch reference and this returns false, an error is
        raised.

        :returns: A boolean to indicate whether to follow a branch reference.
        """
        raise NotImplementedError(self.shouldFollowReferences)

    def transformFallbackLocation(self, branch, url):
        """Validate, maybe modify, 'url' to be used as a stacked-on location.

        :param branch:  The branch that is being opened.
        :param url: The URL that the branch provides for its stacked-on
            location.
        :return: (new_url, check) where 'new_url' is the URL of the branch to
            actually open and 'check' is true if 'new_url' needs to be
            validated by checkAndFollowBranchReference.
        """
        raise NotImplementedError(self.transformFallbackLocation)

    def checkOneURL(self, url):
        """Check the safety of the source URL.

        Subclasses must override this method.

        :param url: The source URL to check.
        :raise BadUrl: subclasses are expected to raise this or a subclass
            when it finds a URL it deems to be unsafe.
        """
        raise NotImplementedError(self.checkOneURL)


class BlacklistPolicy(BranchOpenPolicy):
    """Branch policy that forbids certain URLs."""

    def __init__(self, should_follow_references, unsafe_urls=None):
        if unsafe_urls is None:
            unsafe_urls = set()
        self._unsafe_urls = unsafe_urls
        self._should_follow_references = should_follow_references

    def shouldFollowReferences(self):
        return self._should_follow_references

    def checkOneURL(self, url):
        if url in self._unsafe_urls:
            raise BadUrl(url)

    def transformFallbackLocation(self, branch, url):
        """See `BranchOpenPolicy.transformFallbackLocation`.

        This class is not used for testing our smarter stacking features so we
        just do the simplest thing: return the URL that would be used anyway
        and don't check it.
        """
        return urlutils.join(branch.base, url), False


class AcceptAnythingPolicy(BlacklistPolicy):
    """Accept anything, to make testing easier."""

    def __init__(self):
        super(AcceptAnythingPolicy, self).__init__(True, set())


class WhitelistPolicy(BranchOpenPolicy):
    """Branch policy that only allows certain URLs."""

    def __init__(self, should_follow_references, allowed_urls=None,
                 check=False):
        if allowed_urls is None:
            allowed_urls = []
        self.allowed_urls = set(url.rstrip('/') for url in allowed_urls)
        self.check = check

    def shouldFollowReferences(self):
        return self._should_follow_references

    def checkOneURL(self, url):
        if url.rstrip('/') not in self.allowed_urls:
            raise BadUrl(url)

    def transformFallbackLocation(self, branch, url):
        """See `BranchOpenPolicy.transformFallbackLocation`.

        Here we return the URL that would be used anyway and optionally check
        it.
        """
        return urlutils.join(branch.base, url), self.check


class SingleSchemePolicy(BranchOpenPolicy):
    """Branch open policy that rejects URLs not on the given scheme."""

    def __init__(self, allowed_scheme):
        self.allowed_scheme = allowed_scheme

    def shouldFollowReferences(self):
        return True

    def transformFallbackLocation(self, branch, url):
        return urlutils.join(branch.base, url), True

    def checkOneURL(self, url):
        """Check that `url` is safe to open."""
        if URI(url).scheme != self.allowed_scheme:
            raise BadUrl(url)


class SafeBranchOpener(object):
    """Safe branch opener.

    All locations that are opened (stacked-on branches, references) are checked
    against a policy object.

    The policy object is expected to have the following methods:
    * checkOneURL
    * shouldFollowReferences
    * transformFallbackLocation
    """

    _threading_data = threading.local()

    def __init__(self, policy):
        self.policy = policy
        self._seen_urls = set()

    @classmethod
    def install_hook(cls):
        """Install the ``transformFallbackLocation`` hook.

        This is done at module import time, but transformFallbackLocationHook
        doesn't do anything unless the `_active_openers` threading.Local object
        has a 'opener' attribute in this thread.

        This is in a module-level function rather than performed at module level
        so that it can be called in setUp for testing `SafeBranchOpener` as
        bzrlib.tests.TestCase.setUp clears hooks.
        """
        Branch.hooks.install_named_hook(
            'transform_fallback_location',
            cls.transformFallbackLocationHook,
            'SafeBranchOpener.transformFallbackLocationHook')

    def checkAndFollowBranchReference(self, url, open_dir=None):
        """Check URL (and possibly the referenced URL) for safety.

        This method checks that `url` passes the policy's `checkOneURL`
        method, and if `url` refers to a branch reference, it checks whether
        references are allowed and whether the reference's URL passes muster
        also -- recursively, until a real branch is found.

        :param url: URL to check
        :param open_dir: Optional function to use for opening control
            directories (defaults to BzrDir.open)
        :raise BranchLoopError: If the branch references form a loop.
        :raise BranchReferenceForbidden: If this opener forbids branch
            references.
        """
        while True:
            if url in self._seen_urls:
                raise BranchLoopError()
            self._seen_urls.add(url)
            self.policy.checkOneURL(url)
            next_url = self.followReference(url, open_dir=open_dir)
            if next_url is None:
                return url
            url = next_url
            if not self.policy.shouldFollowReferences():
                raise BranchReferenceForbidden(url)

    @classmethod
    def transformFallbackLocationHook(cls, branch, url):
        """Installed as the 'transform_fallback_location' Branch hook.

        This method calls `transformFallbackLocation` on the policy object and
        either returns the url it provides or passes it back to
        checkAndFollowBranchReference.
        """
        try:
            opener = getattr(cls._threading_data, "opener")
        except AttributeError:
            return url
        new_url, check = opener.policy.transformFallbackLocation(branch, url)
        if check:
            return opener.checkAndFollowBranchReference(new_url,
                getattr(cls._threading_data, "open_dir"))
        else:
            return new_url

    def runWithTransformFallbackLocationHookInstalled(
            self, open_dir, callable, *args, **kw):
        assert (self.transformFallbackLocationHook in
                Branch.hooks['transform_fallback_location'])
        self._threading_data.opener = self
        self._threading_data.open_dir = open_dir
        try:
            return callable(*args, **kw)
        finally:
            del self._threading_data.open_dir
            del self._threading_data.opener
            # We reset _seen_urls here to avoid multiple calls to open giving
            # spurious loop exceptions.
            self._seen_urls = set()

    def followReference(self, url, open_dir=None):
        """Get the branch-reference value at the specified url.

        This exists as a separate method only to be overriden in unit tests.
        """
        if open_dir is None:
            open_dir = BzrDir.open
        bzrdir = open_dir(url)
        return bzrdir.get_branch_reference()

    def open(self, url, open_dir=None):
        """Open the Bazaar branch at url, first checking for safety.

        What safety means is defined by a subclasses `followReference` and
        `checkOneURL` methods.

        :param open_dir: Optional function to use for opening control
            directories (defaults to BzrDir.open)
        """
        url = self.checkAndFollowBranchReference(url, open_dir=open_dir)
        if open_dir is None:
            open_dir = BzrDir.open
        def open_branch(url):
            dir = open_dir(url)
            return dir.open_branch()
        return self.runWithTransformFallbackLocationHookInstalled(
            open_dir, open_branch, url)


def safe_open(allowed_scheme, url):
    """Open the branch at `url`, only accessing URLs on `allowed_scheme`.

    :raises BadUrl: An attempt was made to open a URL that was not on
        `allowed_scheme`.
    """
    return SafeBranchOpener(SingleSchemePolicy(allowed_scheme)).open(url)


SafeBranchOpener.install_hook()
