"""HCT XML-RPC Server.

This module provides an XML-RPC server that provides access to an HCT
backend, so the client (HCT) only needs to make XML-RPC requests instead
of (for example) needing directaccess to the database.
"""

import sys
import logging
import xmlrpclib

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

    def errorHandler(self, error):
        """Handle exceptions that occur during deferred processing."""
        if issubclass(error.type, canonical.launchpad.hctapi.LaunchpadError):
            raise xmlrpclib.Fault(8003, str(error.value))
        else:
            raise error.value

    def pickleBranch(self, branch):
        """Return a pickled branch."""
        if branch is None:
            return "None"
        else:
            mf = ManifestFile(fileobj=StringIO())
            mf.branches.append(branch)
            mf.save()
            return mf.file.getvalue()

    def pickleManifest(self, manifest):
        """Return a pickled manifest."""
        if manifest is None:
            return "None"
        else:
            mf = ManifestFile(fileobj=StringIO(), manifests=(manifest,))
            return mf.file.getvalue()

    def pickleString(self, string):
        """Return a pickled string."""
        if value is None:
            return "None"
        elif value.startswith("None"):
            return "\\" + value
        elif value.startswith("\\"):
            return "\\" + value
        else:
            return value

    def picklePair(self, pair):
        """Return a pickled pair."""
        if pair is None:
            return "None"
        else:
            return (pickle_string(pair[0]), pickle_manifest(pair[1]))

    def picklePairs(self, pairs):
        """Return pickled list of pairs."""
        return [self.picklePair(pair) for pair in pairs]

    def xmlrpc_echo(self, *args):
        """Return all arguments unchanged."""
        return args

    def xmlrpc_get_manifest(self, url):
        """Retrieve the manifest with the URL given."""
        self.log.debug("Asked to get manifest %s", url)
        deferred = deferToThread(self.backend.get_manifest, url)
        deferred.addCallback(self.pickleManifest)
        deferred.addErrback(self.errorHandler)
        return deferred

    def xmlrpc_get_release(self, url, version):
        """Return the URL of the release of the product or package given.

        If the release does not exist, this function returns None.
        """
        self.log.debug("Asked to get release %s of %s", version, url)
        deferred = deferToThread(self.backend.get_release, url, version)
        deferred.addCallback(self.pickleString)
        deferred.addErrback(self.errorHandler)
        return deferred

    def xmlrpc_get_package(self, url, distro_url=None):
        """Return the URL of the package in the given distro.

        Takes the product, source package or release at url and returns the
        equivalent in the distribution or distribution release given.

        If distro_url is ommitted or None, the upstream product is returned.

        Returns URL of equivalent package.
        """
        self.log.debug("Asked to get package of %s in %s", url, distro_url)
        deferred = deferToThread(self.backend.get_package, url, distro_url)
        deferred.addCallback(self.pickleString)
        deferred.addErrback(self.errorHandler)
        return deferred

    def xmlrpc_get_branch(self, url):
        """Return branch associated with URL given.

        Returns a Branch object or None if no branch associated.
        """
        self.log.debug("Asked to get branch related to %s", url)
        deferred = deferToThread(self.backend.get_branch, url)
        deferred.addCallback(self.pickleBranch)
        deferred.addErrback(self.errorHandler)
        return deferred

    def xmlrpc_identify_file(self, ref_url, size, digest, upstream=False):
        """Return URLs and Manifests for a file with the details given.

        Returns a list of tuples of (url, manifest) for each product and
        source package release that include a file with the same size and
        SHA1 digest given.
        """
        self.log.debug("Asked to identify file of size %d and digest %s",
                       size, digest)
        deferred = deferToThread(self.backend.identify_file, size, digest,
                                 upstream=upstream)
        deferred.addCallback(self.picklePairs)
        deferred.addErrback(self.errorHandler)
        return deferred
