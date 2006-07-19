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

MAX_REDIRECTS = 3


class ProberProtocol(HTTPClient):
    """Simple HTTP client to probe path existence via HEAD."""

    def connectionMade(self):
        """Simply requests path presence."""
        self.makeRequest()
        self.headers = {}
        
    def makeRequest(self):
        """Request path presence via HTTP/1.1 using HEAD.

        Uses factory.host and factory.path
        """
        self.sendCommand('HEAD', self.factory.path)
        self.sendHeader('HOST', self.factory.host)
        self.endHeaders()
        
    def handleStatus(self, version, status, message):
        # According to http://lists.debian.org/deity/2001/10/msg00046.html,
        # apt intentionally handles only '200 OK' responses, so we do the
        # same here.
        if status == str(httplib.OK):
            self.factory.succeeded(status)
        else:
            self.factory.failed(Failure(BadResponseCode(status)))
        self.transport.loseConnection()

    def handleResponse(self, response):
        # The status is all we need, so we don't need to do anything with 
        # the response
        pass


class RedirectAwareProberProtocol(ProberProtocol):
    """A specialized version of ProberProtocol that follows HTTP redirects."""

    redirected_to_location = False

    # The different redirect statuses that I handle.
    handled_redirect_statuses = (
        httplib.MOVED_PERMANENTLY, httplib.FOUND, httplib.SEE_OTHER)

    def handleHeader(self, key, value):
        key = key.lower()
        l = self.headers.setdefault(key, [])
        l.append(value)

    def handleStatus(self, version, status, message):
        if int(status) in self.handled_redirect_statuses:
            # We need to redirect to the location specified in the headers.
            self.redirected_to_location = True
        else:
            # We have the result immediately.
            ProberProtocol.handleStatus(self, version, status, message)

    def handleEndHeaders(self):
        if self.redirected_to_location:
            # Server responded redirecting us to another location.
            location = self.headers.get('location')
            url = location[0]
            self.factory.redirect(url)
            self.transport.loseConnection()
        else:
            # XXX: Maybe move this to an 
            # assert self.redirected_to_location at the beginning of the
            # method?
            raise AssertionError(
                'All headers received but failed to find a result.')


class ProberFactory(protocol.ClientFactory):
    """Factory using ProberProtocol to probe single URL existence."""

    protocol = ProberProtocol

    def __init__(self, url, timeout=config.distributionmirrorprober.timeout):
        self.deferred = defer.Deferred()
        self.timeout = timeout
        self.setURL(url.encode('ascii'))
        # self.waiting is a variable that must be checked (and set to True)
        # whenever we callback or errback. We do this because it's
        # theoretically possible that succeeded() and/or failed() are
        # called more than once per probe, in case a response is received at
        # the same time it times out.
        self.waiting = True

    def probe(self):
        reactor.connectTCP(self.host, self.port, self)
        self.timeoutCall = reactor.callLater(
            self.timeout, self.failWithTimeoutError)
        self.deferred.addBoth(self._cancelTimeout)
        return self.deferred

    def failWithTimeoutError(self):
        self.failed(ProberTimeout(self.url, self.timeout))
        self.connector.disconnect()

    def startedConnecting(self, connector):
        self.connector = connector

    def succeeded(self, status):
        if self.waiting:
            self.waiting = False
            self.deferred.callback(status)

    def failed(self, reason):
        if self.waiting:
            self.waiting = False
            self.deferred.errback(reason)

    def _cancelTimeout(self, result):
        if self.timeoutCall.active():
            self.timeoutCall.cancel()
        return result

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
        proxy = os.getenv('http_proxy')
        if proxy:
            scheme, host, port, path = self._parse(proxy)
            path = url
        else:
            scheme, host, port, path = self._parse(url)
        if scheme != 'http':
            raise UnknownURLScheme(scheme)
        if scheme and host:
            self.scheme = scheme
            self.host = host
            self.port = port
        self.path = path


class RedirectAwareProberFactory(ProberFactory):

    protocol = RedirectAwareProberProtocol
    redirection_count = 0

    def redirect(self, url):
        self.timeoutCall.reset(self.timeout)
        if not self.waiting:
            # Somebody already called failed()/succeeded() on this factory
            return

        try:
            if self.redirection_count >= MAX_REDIRECTS:
                raise InfiniteLoopDetected()
            self.redirection_count += 1

            self.setURL(url)
        except (InfiniteLoopDetected, UnknownURLScheme), e:
            self.failed(e)
        else:
            reactor.connectTCP(self.host, self.port, self)


class ProberError(Exception):
    """A generic prober error.

    This class should be used as a base for more specific prober errors.
    """


class ProberTimeout(ProberError):
    """The initialized URL did not return in time."""

    def __init__(self, url, timeout, *args):
        self.url = url
        self.timeout = timeout
        ProberError.__init__(self, *args)

    def __str__(self):
        return ("Getting %s took longer than %s seconds"
                % (self.url, self.timeout))


class BadResponseCode(ProberError):

    def __init__(self, status, *args):
        ProberError.__init__(self, *args)
        self.status = status

    def __str__(self):
        return "Bad response code: %s" % self.status


class InfiniteLoopDetected(ProberError):

    def __str__(self):
        return "Infinite loop detected"


class UnknownURLScheme(ProberError):

    def __init__(self, scheme, *args):
        ProberError.__init__(self, *args)
        self.scheme = scheme

    def __str__(self):
        return ("The mirror prober doesn't know how to check URLs with an "
                "'%s' scheme." % self.scheme)


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
        msg = ('Deleted %s of %s with url %s because: %s.\n'
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
        # return None if it gets a ProberTimeout or BadResponseCode error,
        # so we need to check that here.
        if arch_or_source_mirror is None:
            return

        status_url_mapping = arch_or_source_mirror.getURLsToCheckUpdateness()
        if not status_url_mapping:
            # We have no publishing records for self.release, self.pocket and
            # self.component, so it's better to delete this
            # MirrorDistroArchRelease/MirrorDistroReleaseSource than to keep
            # it with an UNKNOWN status.
            self.deleteMethod(self.release, self.pocket, self.component)
            return

        deferredList = []
        # We start setting the status to unknown, and then we move on trying to
        # find one of the recently published packages mirrored there.
        arch_or_source_mirror.status = MirrorStatus.UNKNOWN
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


class MirrorCDImageProberCallbacks(object):

    def __init__(self, mirror, distrorelease, flavour, log_file):
        self.mirror = mirror
        self.distrorelease = distrorelease
        self.flavour = flavour
        self.log_file = log_file

    def ensureOrDeleteMirrorCDImageRelease(self, result):
        """Check if the result of the deferredList contains only success and
        then ensure we have a MirrorCDImageRelease for self.distrorelease and
        self.flavour.

        If result contains one or more failures, then we ensure that
        MirrorCDImageRelease is deleted.
        """
        for success_or_failure, response in result:
            if success_or_failure == defer.FAILURE:
                self.mirror.deleteMirrorCDImageRelease(
                    self.distrorelease, self.flavour)
                response.trap(ProberTimeout, BadResponseCode)
                return None

        mirror = self.mirror.ensureMirrorCDImageRelease(
            self.distrorelease, self.flavour)
        self.log_file.write(
            "Found all ISO images for release %s and flavour %s.\n"
            % (self.distrorelease.title, self.flavour))
        return mirror

    def logMissingURL(self, failure, url):
        self.log_file.write(
            "Failed %s: %s\n" % (url, failure.getErrorMessage()))
        return failure
