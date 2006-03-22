# Copyright 2006 Canonical Ltd.  All rights reserved.

import httplib
import urlparse

from twisted.internet import defer, protocol, reactor
from twisted.web.http import HTTPClient
from twisted.python.failure import Failure

from canonical.launchpad.interfaces import IDistroArchRelease, IDistroRelease
from canonical.lp.dbschema import MirrorStatus


PROBER_TIMEOUT = 3


class ProberProtocol(HTTPClient):
    """Simple HTTP client to probe path existence via HEAD."""

    def connectionMade(self):
        """Simply requests path presence."""
        self.makeRequest()
        
    def makeRequest(self):
        """Request path presence via HTTP/1.1 using HEAD.

        Uses factory.host and factory.path
        """
        self.sendCommand('HEAD', self.factory.path)
        self.sendHeader('HOST', self.factory.host)
        self.endHeaders()
        
    def handleStatus(self, version, status, message):
        self.factory.runCallback(status)
        self.transport.loseConnection()

    def handleResponse(self, response):
        # The status is all we need, so we don't need to do anything with 
        # the response
        pass


class ProberTimeout(Exception):
    """The initialized URL did not return in time."""


class ProberFactory(protocol.ClientFactory):
    """Factory using ProberProtocol to probe single URL existence."""

    protocol = ProberProtocol

    def __init__(self, url, timeout=PROBER_TIMEOUT):
        self.deferred = defer.Deferred()
        self.setTimeout(timeout)
        self.setURL(url.encode('ascii'))
        self.timedOut = False

    def startedConnecting(self, connector):
        self.connector = connector

    def setTimeout(self, timeout):
        self.timeoutCall = reactor.callLater(timeout, self.timeOut)

    def timeOut(self):
        self.timedOut = True
        self.deferred.errback(ProberTimeout('TIMEOUT'))
        self.connector.disconnect()

    def _parse(self, url, defaultPort=80):
        scheme, host, path, dummy, dummy, dummy = urlparse.urlparse(url)
        port = defaultPort
        if ':' in host:
            host, port = host.split(':')
            assert port.isdigit()
            port = int(port)
        return scheme, host, port, path

    def setURL(self, url):
        self.url = url
        scheme, host, port, path = self._parse(url)
        if scheme and host:
            self.scheme = scheme
            self.host = host
            self.port = port
        self.path = path

    def runCallback(self, status):
        if self.timeoutCall.active():
            self.timeoutCall.cancel()
        if not self.timedOut:
            # According to http://lists.debian.org/deity/2001/10/msg00046.html,
            # apt intentionally handles only '200 OK' responses, so we do the
            # same here.
            if status == str(httplib.OK):
                self.deferred.callback(status)
            else:
                self.deferred.errback(Failure(BadResponseCode(status)))


class BadResponseCode(Exception):

    def __init__(self, status, *args):
        Exception.__init__(self, *args)
        self.status = status


class MirrorProberCallbacks(object):

    def __init__(self, mirror, release, pocket, component, url, log_file):
        self.mirror = mirror
        self.release = release
        self.pocket = pocket
        self.component = component
        self.url = url
        self.log_file = log_file
        if IDistroArchRelease.providedBy(release):
            self.mirror_class_name = 'MirrorDistroArchRelease'
            self.deleteMethod = self.mirror.deleteMirrorDistroArchRelease
            self.ensureMethod = self.mirror.ensureMirrorDistroArchRelease
        elif IDistroRelease.providedBy(release):
            self.mirror_class_name = 'MirrorDistroRelease'
            self.deleteMethod = self.mirror.deleteMirrorDistroReleaseSource
            self.ensureMethod = self.mirror.ensureMirrorDistroReleaseSource
        else:
            raise AssertionError('release must provide either '
                                 'IDistroArchRelease or IDistroRelease.')

    def deleteMirrorRelease(self, failure):
        """Delete the mirror for self.release, self.pocket and self.component.

        If the failure we get from twisted is not a timeout, then this failure
        is propagated.
        """
        self.deleteMethod(self.release, self.pocket, self.component)
        msg = ('Deleted %s with url %s because of %s.'
               % (self.mirror_class_name, self.url, failure.getErrorMessage()))
        self.log_file.write(msg)
        failure.trap(ProberTimeout, BadResponseCode)

    def ensureMirrorRelease(self, http_status):
        """Make sure we have a mirror for self.release, self.pocket and 
        self.component.
        """
        msg = ('Ensuring %s with url %s exists in the database.'
               % (self.mirror_class_name, self.url))
        mirror = self.ensureMethod(
            self.release, self.pocket, self.component)

        self.log_file.write(msg)
        return mirror

    def updateMirrorStatus(self, arch_or_source_mirror):
        """Update the status of this MirrorDistro{ArchRelease,ReleaseSource}.

        This is done by issuing HTTP HEAD requests on that mirror looking for 
        some packages found in our publishing records. Then, knowing what 
        packages the mirror contains and when these packages were published,
        we can have an idea of when that mirror was last updated.
        """
        # We start setting the status to unknown, and then we move on trying to
        # find one of the recently published packages mirrored there.
        arch_or_source_mirror.status = MirrorStatus.UNKNOWN
        status_url_mapping = arch_or_source_mirror.getURLsToCheckUpdateness()
        for status, url in status_url_mapping.items():
            prober = ProberFactory(url, timeout=PROBER_TIMEOUT)
            prober.deferred.addCallback(
                self.setMirrorStatus, arch_or_source_mirror, status, url)
            prober.deferred.addErrback(self.logError, url)
            reactor.connectTCP(prober.host, prober.port, prober)

    def setMirrorStatus(self, http_status, arch_or_source_mirror, status):
        """Update the status of the given arch or source mirror.

        The status is changed only if the given status refers to a more 
        recent date than the current one.
        """
        if arch_or_source_mirror.status > status:
            arch_or_source_mirror.status = status

    def logError(self, failure, url):
        self.log_file.write("%s on %s" % (failure.getErrorMessage(), url))
        return None

