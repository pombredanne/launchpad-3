# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Safe branch opening."""

__metaclass__ = type

from bzrlib import urlutils
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir

__all__ = [
    'AcceptAnythingPolicy',
    'BadUrl',
    'BlacklistPolicy',
    'BranchLoopError',
    'BranchReferenceForbidden',
    'SafeBranchOpener',
    'WhitelistPolicy',
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


class BranchPolicy:
    """Policy on how to mirror branches.

    In particular, a policy determines which branches are safe to mirror by
    checking their URLs and deciding whether or not to follow branch
    references. A policy also determines how the mirrors of branches should be
    stacked.
    """

    def getStackedOnURLForDestinationBranch(self, source_branch,
                                            destination_url):
        """Get the stacked on URL for `source_branch`.

        In particular, the URL it should be stacked on when it is mirrored to
        `destination_url`.
        """
        return None

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


class BlacklistPolicy(BranchPolicy):
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
        """See `BranchPolicy.transformFallbackLocation`.

        This class is not used for testing our smarter stacking features so we
        just do the simplest thing: return the URL that would be used anyway
        and don't check it.
        """
        return urlutils.join(branch.base, url), False


class AcceptAnythingPolicy(BlacklistPolicy):
    """Accept anything, to make testing easier."""

    def __init__(self):
        super(AcceptAnythingPolicy, self).__init__(True, set())


class WhitelistPolicy(BranchPolicy):
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
        """See `BranchPolicy.transformFallbackLocation`.

        Here we return the URL that would be used anyway and optionally check
        it.
        """
        return urlutils.join(branch.base, url), self.check


class SafeBranchOpener(object):
    """Safe branch opener.

    The policy object is expected to have the following methods:
    * checkOneURL
    * shouldFollowReferences
    * transformFallbackLocation
    """

    def __init__(self, policy):
        self.policy = policy
        self._seen_urls = set()

    def checkAndFollowBranchReference(self, url):
        """Check URL (and possibly the referenced URL) for safety.

        This method checks that `url` passes the policy's `checkOneURL`
        method, and if `url` refers to a branch reference, it checks whether
        references are allowed and whether the reference's URL passes muster
        also -- recursively, until a real branch is found.

        :raise BranchLoopError: If the branch references form a loop.
        :raise BranchReferenceForbidden: If this opener forbids branch
            references.
        """
        while True:
            if url in self._seen_urls:
                raise BranchLoopError()
            self._seen_urls.add(url)
            self.policy.checkOneURL(url)
            next_url = self.followReference(url)
            if next_url is None:
                return url
            url = next_url
            if not self.policy.shouldFollowReferences():
                raise BranchReferenceForbidden(url)

    def transformFallbackLocationHook(self, branch, url):
        """Installed as the 'transform_fallback_location' Branch hook.

        This method calls `transformFallbackLocation` on the policy object and
        either returns the url it provides or passes it back to
        checkAndFollowBranchReference.
        """
        new_url, check = self.policy.transformFallbackLocation(branch, url)
        if check:
            return self.checkAndFollowBranchReference(new_url)
        else:
            return new_url

    def runWithTransformFallbackLocationHookInstalled(
            self, callable, *args, **kw):
        Branch.hooks.install_named_hook(
            'transform_fallback_location', self.transformFallbackLocationHook,
            'SafeBranchOpener.transformFallbackLocationHook')
        try:
            return callable(*args, **kw)
        finally:
            # XXX 2008-11-24 MichaelHudson, bug=301472: This is the hacky way
            # to remove a hook.  The linked bug report asks for an API to do
            # it.
            Branch.hooks['transform_fallback_location'].remove(
                self.transformFallbackLocationHook)
            # We reset _seen_urls here to avoid multiple calls to open giving
            # spurious loop exceptions.
            self._seen_urls = set()

    def followReference(self, url):
        """Get the branch-reference value at the specified url.

        This exists as a separate method only to be overriden in unit tests.
        """
        bzrdir = BzrDir.open(url)
        return bzrdir.get_branch_reference()

    def open(self, url):
        """Open the Bazaar branch at url, first checking for safety.

        What safety means is defined by a subclasses `followReference` and
        `checkOneURL` methods.
        """
        url = self.checkAndFollowBranchReference(url)
        return self.runWithTransformFallbackLocationHookInstalled(
            Branch.open, url)
