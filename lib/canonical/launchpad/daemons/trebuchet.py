"""HCT XML-RPC Server.

This module provides an XML-RPC server that provides access to an HCT
backend, so the client (HCT) only needs to make XML-RPC requests instead
of (for example) needing directaccess to the database.
"""

import sys
import logging

from StringIO import StringIO
from twisted.web.xmlrpc import XMLRPC
from twisted.internet.threads import deferToThread

import hct.url
import canonical.launchpad.hctapi

from hct.util.log import get_logger
from hct.backends.xmlfiles import ManifestFile


class TrebuchetServer(XMLRPC):
    def __init__(self, backend=None, parent_log=None):
        XMLRPC.__init__(self)

        default_backend = hct.url.backends[hct.url.default_scheme]
        self.backend = backend or default_backend

        self.log = get_logger("trebuchet", parent_log)
        self.log.info("Trebuchet XML-RPC Server started")
        self.log.info("Serving backend %s", self.backend.__name__)

    def xmlrpc_echo(self, *args):
        """Return all arguments unchanged."""
        return args

    def xmlrpc_get_manifest(self, url):
        """Retrieve the manifest with the URL given."""
        self.log.debug("Asked to get manifest %s", url)

        def bottom_half(manifest):
            return pickle_manifest(manifest)

        deferred = deferToThread(self.backend.get_manifest, url)
        deferred.addCallback(bottom_half)
        return deferred

    def xmlrpc_get_release(self, url, version):
        """Return the URL of the release of the product or package given.

        If the release does not exist, this function returns None.
        """
        self.log.debug("Asked to get release %s of %s", version, url)

        def bottom_half(new_url):
            self.log.debug("Found release %s", new_url)

            return pickle_none(new_url)

        deferred = deferToThread(self.backend.get_release, url, version)
        deferred.addCallback(bottom_half)
        return deferred

    def xmlrpc_get_package(self, url, distro_url=None):
        """Return the URL of the package in the given distro.

        Takes the product, source package or release at url and returns the
        equivalent in the distribution or distribution release given.

        If distro_url is ommitted or None, the upstream product is returned.

        Returns URL of equivalent package.
        """
        self.log.debug("Asked to get package of %s in %s", url, distro_url)

        return deferToThread(self.backend.get_package, url, distro_url)

    def xmlrpc_get_branch(self, url):
        """Return branch associated with URL given.

        Returns a Branch object or None if no branch associated.
        """
        self.log.debug("Asked to get branch related to %s", url)

        def bottom_half(branch):
            self.log.debug("Found branch %s", branch)

            return pickle_branch(branch)

        deferred = deferToThread(self.backend.get_branch, url)
        deferred.addCallback(bottom_half)
        return deferred

    def xmlrpc_identify_file(self, ref_url, size, digest, upstream=False):
        """Return URLs and Manifests for a file with the details given.

        Returns a list of tuples of (url, manifest) for each product and
        source package release that include a file with the same size and
        SHA1 digest given.
        """
        self.log.debug("Asked to identify file of size %d and digest %s",
                       size, digest)

        def bottom_half(objs):
            self.log.debug("Found %d objects", len(objs))

            result = []
            for url, manifest in objs:
                result.append((url, pickle_manifest(manifest)))

            return result

        deferred = deferToThread(self.backend.identify_file, size, digest,
                                 upstream=upstream)
        deferred.addCallback(bottom_half)
        return deferred


def pickle_none(value):
    """Pickle a string that could also be None."""
    if value is None:
        return "\0"
    elif value.startswith("\0"):
        return "\0" + value
    else:
        return value

def pickle_manifest(manifest):
    """Pickle a manifest."""
    if manifest is None:
        return pickle_none(manifest)
    else:
        mf = ManifestFile(fileobj=StringIO(), manifests=( manifest, ))
        return pickle_none(mf.file.getvalue())

def pickle_branch(branch):
    """Pickle a branch."""
    if branch is None:
        return pickle_none(branch)
    else:
        mf = ManifestFile(fileobj=StringIO())
        mf.branches.append(branch)
        mf.save()
        return pickle_none(mf.file.getvalue())
