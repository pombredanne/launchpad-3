# Copyright 2006 Canonical Ltd.  All rights reserved.

import httplib
import logging
import os
import urlparse

from twisted.internet import defer, protocol, reactor
from twisted.web.http import HTTPClient
from twisted.python.failure import Failure

from canonical.config import config
from canonical.launchpad.interfaces import IDistroArchRelease, IDistroRelease
from canonical.lp.dbschema import MirrorStatus


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

    def __init__(self, host, port, *args):
        self.host = host
        self.port = port
        Exception.__init__(self, *args)

    def __str__(self):
        return 'Time out on host %s, port %s' % (self.host, self.port)


class ProberFactory(protocol.ClientFactory):
    """Factory using ProberProtocol to probe single URL existence."""

    protocol = ProberProtocol

    def __init__(self, url, timeout=config.distributionmirrorprober.timeout):
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
        self.deferred.errback(ProberTimeout(self.host, self.port))
        self.connector.disconnect()

    def _parse(self, url, defaultPort=80):
        scheme, host, path, dummy, dummy, dummy = urlparse.urlparse(url)
        port = defaultPort
        if ':' in host:
            host, port = host.split(':')
            assert port.isdigit()
            port = int(port)
        return scheme, host, port, path

    def probe(self):
        reactor.connectTCP(self.host, self.port, self)
        return self.deferred

    def setURL(self, url):
        self.url = url
        proxy = os.getenv('http_proxy')
        if proxy is not None:
            scheme, host, port, path = self._parse(proxy)
            path = url
        else:
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

    def __str__(self):
        return "Bad response code: %s" % self.status


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
        msg = ('Deleted %s of %s with url %s because of %s.\n'
               % (self.mirror_class_name,
                  self._getReleasePocketAndComponentDescription(), self.url,
                  failure.getErrorMessage()))
        self.log_file.write(msg)
        failure.trap(ProberTimeout, BadResponseCode)

    def ensureMirrorRelease(self, http_status):
        """Make sure we have a mirror for self.release, self.pocket and 
        self.component.
        """
        msg = ('Ensuring %s of %s with url %s exists in the database.\n'
               % (self.mirror_class_name,
                  self._getReleasePocketAndComponentDescription(),
                  self.url))
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
        # The errback that's one level before this callback in the chain will
        # return None if it gets a ProberTimeout or BadResponseCode error, so
        # we need to check that here.
        if arch_or_source_mirror is None:
            return

        deferredList = []
        # We start setting the status to unknown, and then we move on trying to
        # find one of the recently published packages mirrored there.
        arch_or_source_mirror.status = MirrorStatus.UNKNOWN
        status_url_mapping = arch_or_source_mirror.getURLsToCheckUpdateness()
        for status, url in status_url_mapping.items():
            prober = ProberFactory(url)
            prober.deferred.addCallback(
                self.setMirrorStatus, arch_or_source_mirror, status, url)
            prober.deferred.addErrback(self.logError, url)
            deferredList.append(prober.deferred)
            reactor.connectTCP(prober.host, prober.port, prober)
        return defer.DeferredList(deferredList)

    def setMirrorStatus(self, http_status, arch_or_source_mirror, status, url):
        """Update the status of the given arch or source mirror.

        The status is changed only if the given status refers to a more 
        recent date than the current one.
        """
        if status < arch_or_source_mirror.status:
            msg = ('Found that %s exists. Updating %s of %s status to %s.\n'
                   % (url, self.mirror_class_name,
                      self._getReleasePocketAndComponentDescription(), 
                      status.title))
            self.log_file.write(msg)
            arch_or_source_mirror.status = status

    def _getReleasePocketAndComponentDescription(self):
        """Return a string containing the name of the release, pocket and
        component.

        This is meant to be used in the logs, to help us identify if this is a
        MirrorDistroReleaseSource or a MirrorDistroArchRelease.
        """
        if IDistroArchRelease.providedBy(self.release):
            text = ("Distro Release %s, Architecture %s" %
                    (self.release.distrorelease.title,
                     self.release.architecturetag))
        else:
            text = "Distro Release %s" % self.release.title
        text += (", Component %s and Pocket %s" % 
                 (self.component.name, self.pocket.title))
        return text

    def logError(self, failure, url):
        msg = ("%s on %s of %s\n" 
               % (failure.getErrorMessage(), url,
                  self._getReleasePocketAndComponentDescription()))
        if failure.check(ProberTimeout, BadResponseCode) is not None:
            self.log_file.write(msg)
        else:
            # This is not an error we expect from an HTTP server, so we log it
            # using the cronscript's logger and wait for kiko to complain
            # about it.
            logger = logging.getLogger('distributionmirror-prober')
            logger.error(msg)
        return None

