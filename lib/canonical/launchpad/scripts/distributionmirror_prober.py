# Copyright 2006 Canonical Ltd.  All rights reserved.

import httplib
import itertools
import logging
import os
import urllib2
import urlparse

from zope.component import getUtility

from twisted.internet import defer, protocol, reactor
from twisted.internet.defer import DeferredSemaphore
from twisted.web.http import HTTPClient
from twisted.python.failure import Failure

from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistroArchRelease, IDistroRelease, ILaunchpadCelebrities,
    UnableToFetchCDImageFileList)
from canonical.lp.dbschema import MirrorStatus


# The requests/timeouts ratio has to be at least 3 for us to keep issuing
# requests on a given host. (This ratio is per run, rather than held long
# term)
# IMPORTANT: Changing these values can cause lots of false negatives when
# probing mirrors, so please don't change them unless you know what you're
# doing.
MIN_REQUEST_TIMEOUT_RATIO = 3
MIN_REQUESTS_TO_CONSIDER_RATIO = 30

# XXX: We need to get rid of these global dicts in this module. See
# https://launchpad.net/launchpad/+bug/82201 for more details.
# -- Guilherme Salgado, 2007-01-30
host_requests = {}
host_timeouts = {}
host_semaphores = {}

MAX_REDIRECTS = 3

# Number of simultaneous connections we issue on a given host
# IMPORTANT: Don't change this unless you really know what you're doing. Using
# a to big value can cause spurious failures on lots of mirrors and a to small
# one can cause the prober to run for hours.
PER_HOST_REQUESTS = 2


class ProberProtocol(HTTPClient):
    """Simple HTTP client to probe path existence via HEAD."""

    def connectionMade(self):
        """Simply requests path presence."""
        self.makeRequest()
        self.headers = {}
        
    def makeRequest(self):
        """Request path presence via HTTP/1.1 using HEAD.

        Uses factory.connect_host and factory.connect_path
        """
        self.sendCommand('HEAD', self.factory.connect_path)
        self.sendHeader('HOST', self.factory.connect_host)
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
        assert self.redirected_to_location, (
            'All headers received but failed to find a result.')

        # Server responded redirecting us to another location.
        location = self.headers.get('location')
        url = location[0]
        self.factory.redirect(url)
        self.transport.loseConnection()


class ProberFactory(protocol.ClientFactory):
    """Factory using ProberProtocol to probe single URL existence."""

    protocol = ProberProtocol

    # Details of the URL of the host in which we actually want to request the
    # confirmation from.
    request_scheme = None
    request_host = None
    request_port = None
    request_path = None

    # Details of the URL of the host in which we'll connect, which will only
    # be different from request_* in case we have an http_proxy environment
    # variable --in that case the scheme, host and port will be the ones
    # extracted from http_proxy and the path will be self.url
    connect_scheme = None
    connect_host = None
    connect_port = None
    connect_path = None

    def __init__(self, url, timeout=config.distributionmirrorprober.timeout):
        # We want the deferred to be a private attribute (_deferred) to make
        # sure our clients will only use the deferred returned by the probe()
        # method; this is to ensure self._cancelTimeout is always the first
        # callback in the chain.
        self._deferred = defer.Deferred()
        self.timeout = timeout
        self.setURL(url.encode('ascii'))
        self.connector = None

    def probe(self):
        logger = logging.getLogger('distributionmirror-prober')
        # NOTE: We don't want to issue connections to any outside host when
        # running the mirror prober in a development machine, so we do this
        # hack here.
        if (self.connect_host != 'localhost' 
            and config.distributionmirrorprober.localhost_only):
            reactor.callLater(0, self.succeeded, '200')
            logger.debug("Forging a successful response on %s as we've been "
                         "told to probe only local URLs." % self.url)
            return self._deferred

        if should_skip_host(self.request_host):
            reactor.callLater(0, self.failed, ConnectionSkipped(self.url))
            logger.debug("Skipping %s as we've had too many timeouts on this "
                         "host already." % self.url)
            return self._deferred

        self.connect()
        self.timeoutCall = reactor.callLater(
            self.timeout, self.failWithTimeoutError)
        self._deferred.addBoth(self._cancelTimeout)
        logger.debug('Probing %s' % self.url)
        return self._deferred

    def connect(self):
        host_requests[self.request_host] += 1
        reactor.connectTCP(self.connect_host, self.connect_port, self)

    def failWithTimeoutError(self):
        host_timeouts[self.request_host] += 1
        self.failed(ProberTimeout(self.url, self.timeout))
        if self.connector:
            self.connector.disconnect()

    def startedConnecting(self, connector):
        self.connector = connector

    def succeeded(self, status):
        self._deferred.callback(status)

    def failed(self, reason):
        self._deferred.errback(reason)

    def _cancelTimeout(self, result):
        if self.timeoutCall.active():
            self.timeoutCall.cancel()
        return result

    def setURL(self, url):
        self.url = url
        scheme, host, port, path = _parse(url)
        # XXX: We don't actually know how to handle FTP responses, but we
        # expect to be behind a squid HTTP proxy with the patch at
        # http://www.squid-cache.org/bugs/show_bug.cgi?id=1758 applied. So, if
        # you encounter any problems with FTP URLs you'll probably have to nag
        # the sysadmins to fix squid for you.
        # -- Guilherme Salgado, 2006-09-19
        if scheme not in ('http', 'ftp'):
            raise UnknownURLScheme(url)

        if scheme and host:
            self.request_scheme = scheme
            self.request_host = host
            self.request_port = port
            self.request_path = path

        if self.request_host not in host_requests:
            host_requests[self.request_host] = 0
        if self.request_host not in host_timeouts:
            host_timeouts[self.request_host] = 0

        # If the http_proxy variable is set, we want to use it as the host
        # we're going to connect to.
        proxy = os.getenv('http_proxy')
        if proxy:
            scheme, host, port, dummy = _parse(proxy)
            path = url

        self.connect_scheme = scheme
        self.connect_host = host
        self.connect_port = port
        self.connect_path = path


class RedirectAwareProberFactory(ProberFactory):

    protocol = RedirectAwareProberProtocol
    redirection_count = 0

    def redirect(self, url):
        self.timeoutCall.reset(self.timeout)

        try:
            if self.redirection_count >= MAX_REDIRECTS:
                raise InfiniteLoopDetected()
            self.redirection_count += 1

            logger = logging.getLogger('distributionmirror-prober')
            logger.debug('Got redirected from %s to %s' % (self.url, url))
            # XXX: We can't assume url to be absolute here. See
            # https://bugs.launchpad.net/launchpad/+bug/109223 for more
            # details.  -- Guilherme Salgado, 2007-04-23
            self.setURL(url)
        except (InfiniteLoopDetected, UnknownURLScheme), e:
            self.failed(e)
        else:
            self.connect()


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
        return ("HEAD request on %s took longer than %s seconds"
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


class ConnectionSkipped(ProberError):

    def __str__(self):
        return ("Connection skipped because of too many timeouts on this "
                "host. It will be retried on the next probing run.")


class UnknownURLScheme(ProberError):

    def __init__(self, url, *args):
        ProberError.__init__(self, *args)
        self.url = url

    def __str__(self):
        return ("The mirror prober doesn't know how to check this kind of "
                "URLs: %s" % self.url)


class ArchiveMirrorProberCallbacks(object):

    expected_failures = (BadResponseCode, ProberTimeout, ConnectionSkipped)

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

        If the failure we get from twisted is not a timeout, a bad response
        code or a connection skipped, then this failure is propagated.
        """
        self.deleteMethod(self.release, self.pocket, self.component)
        msg = ('Deleted %s of %s with url %s because: %s.\n'
               % (self.mirror_class_name,
                  self._getReleasePocketAndComponentDescription(), self.url,
                  failure.getErrorMessage()))
        self.log_file.write(msg)
        failure.trap(*self.expected_failures)

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
        # return None if it gets any of self.expected_failures as the error,
        # so we need to check that here.
        if arch_or_source_mirror is None:
            return

        scheme, host, port, path = _parse(self.url)
        status_url_mapping = arch_or_source_mirror.getURLsToCheckUpdateness()
        if not status_url_mapping or should_skip_host(host):
            # Either we have no publishing records for self.release,
            # self.pocket and self.component or we got too may timeouts from
            # this host and thus should skip it, so it's better to delete this
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
            # Use one semaphore per host, to limit the numbers of simultaneous
            # connections on a given host. Note that we don't have an overall
            # limit of connections, since the per-host limit should be enough.
            # If we ever need an overall limit, we can use Andrew's suggestion
            # on https://launchpad.net/bugs/54791 to implement it.
            semaphore = host_semaphores.setdefault(
                prober.request_host, DeferredSemaphore(PER_HOST_REQUESTS))
            deferred = semaphore.run(prober.probe)
            deferred.addCallback(
                self.setMirrorStatus, arch_or_source_mirror, status, url)
            deferred.addErrback(self.logError, url)
            deferredList.append(deferred)
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
        if failure.check(*self.expected_failures) is not None:
            self.log_file.write(msg)
        else:
            # This is not an error we expect from an HTTP server, so we log it
            # using the cronscript's logger and wait for kiko to complain
            # about it.
            logger = logging.getLogger('distributionmirror-prober')
            logger.error(msg)
        return None


class MirrorCDImageProberCallbacks(object):

    expected_failures = (BadResponseCode, ProberTimeout, ConnectionSkipped)

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
                if response.check(*self.expected_failures) is None:
                    msg = ("%s on mirror %s. Check its logfile for more "
                           "details.\n" 
                           % (response.getErrorMessage(), self.mirror.name))
                    # This is not an error we expect from an HTTP server, so 
                    # we log it using the cronscript's logger and wait for 
                    # kiko to complain about it.
                    logger = logging.getLogger('distributionmirror-prober')
                    logger.error(msg)
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


def _build_request_for_cdimage_file_list(url):
    headers = {'Pragma': 'no-cache', 'Cache-control': 'no-cache'}
    return urllib2.Request(url, headers=headers)


def _get_cdimage_file_list():
    url = config.distributionmirrorprober.releases_file_list_url
    try:
        return urllib2.urlopen(_build_request_for_cdimage_file_list(url))
    except urllib2.URLError, e:
        raise UnableToFetchCDImageFileList(
            'Unable to fetch %s: %s' % (url, e))


def restore_http_proxy(http_proxy):
    """Restore the http_proxy environment variable to the given value."""
    if http_proxy is None:
        try:
            del os.environ['http_proxy']
        except KeyError:
            pass
    else:
        os.environ['http_proxy'] = http_proxy


def get_expected_cdimage_paths():
    """Get all paths where we can find CD image files on a release mirror.

    Return a list containing, for each Ubuntu DistroRelease and flavour, a
    list of CD image file paths for that DistroRelease and flavour.

    This list is read from a file located at http://releases.ubuntu.com,
    so if something goes wrong while reading that file, an
    UnableToFetchCDImageFileList exception will be raised.
    """
    d = {}
    for line in _get_cdimage_file_list().readlines():
        flavour, releasename, path, size = line.split('\t')
        paths = d.setdefault((flavour, releasename), [])
        paths.append(path)

    ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    paths = []
    for key, value in d.items():
        flavour, releasename = key
        release = ubuntu.getRelease(releasename)
        paths.append((release, flavour, value))
    return paths


def checkComplete(result, key, unchecked_keys):
    """Check if we finished probing all mirrors, and call reactor.stop()."""
    unchecked_keys.remove(key)
    if not len(unchecked_keys):
        reactor.callLater(0, reactor.stop)
    # This is added to the deferred with addBoth(), which means it'll be
    # called if something goes wrong in the end of the callback chain, and in
    # that case we shouldn't swallow the error.
    return result


def probe_archive_mirror(mirror, logfile, unchecked_keys, logger,
                         host_semaphores=host_semaphores):
    """Probe an archive mirror for its contents and freshness.

    First we issue a set of HTTP HEAD requests on some key files to find out
    what is mirrored there, then we check if some packages that we know the
    publishing time are available on that mirror, giving us an idea of when it
    was last synced to the main archive.
    """
    packages_paths = mirror.getExpectedPackagesPaths()
    sources_paths = mirror.getExpectedSourcesPaths()
    all_paths = itertools.chain(packages_paths, sources_paths)
    for release, pocket, component, path in all_paths:
        url = "%s/%s" % (mirror.base_url, path)
        callbacks = ArchiveMirrorProberCallbacks(
            mirror, release, pocket, component, url, logfile)
        unchecked_keys.append(url)
        prober = ProberFactory(url)

        # Use one semaphore per host, to limit the numbers of simultaneous
        # connections on a given host. Note that we don't have an overall
        # limit of connections, since the per-host limit should be enough.
        # If we ever need an overall limit, we can use Andrews's suggestion
        # on https://launchpad.net/bugs/54791 to implement it.
        semaphore = host_semaphores.setdefault(
            prober.request_host, DeferredSemaphore(PER_HOST_REQUESTS))
        deferred = semaphore.run(prober.probe)
        deferred.addCallbacks(
            callbacks.ensureMirrorRelease, callbacks.deleteMirrorRelease)

        deferred.addCallback(callbacks.updateMirrorStatus)
        deferred.addErrback(logger.error)

        deferred.addBoth(checkComplete, url, unchecked_keys)


def probe_release_mirror(mirror, logfile, unchecked_keys, logger,
                         host_semaphores=host_semaphores):
    """Probe a release mirror for its contents.
    
    This is done by checking the list of files for each flavour and release
    returned by get_expected_cdimage_paths(). If a mirror contains all
    files for a given release and flavour, then we consider that mirror is
    actually mirroring that release and flavour.
    """
    # The list of files a mirror should contain will change over time and we
    # don't want to keep records for files a mirror doesn't need to have
    # anymore, so we delete all records before start probing. This also fixes
    # https://launchpad.net/bugs/46662
    mirror.deleteAllMirrorCDImageReleases()
    try:
        cdimage_paths = get_expected_cdimage_paths()
    except UnableToFetchCDImageFileList, e:
        logger.error(e)
        return

    for release, flavour, paths in cdimage_paths:
        callbacks = MirrorCDImageProberCallbacks(
            mirror, release, flavour, logfile)

        mirror_key = (release, flavour)
        unchecked_keys.append(mirror_key)
        deferredList = []
        for path in paths:
            url = '%s/%s' % (mirror.base_url, path)
            # Use a RedirectAwareProberFactory because CD mirrors are allowed
            # to redirect, and we need to cope with that.
            prober = RedirectAwareProberFactory(url)
            # Use one semaphore per host, to limit the numbers of simultaneous
            # connections on a given host. Note that we don't have an overall
            # limit of connections, since the per-host limit should be enough.
            # If we ever need an overall limit, we can use Andrews's
            # suggestion on https://launchpad.net/bugs/54791 to implement it.
            semaphore = host_semaphores.setdefault(
                prober.request_host, DeferredSemaphore(PER_HOST_REQUESTS))
            deferred = semaphore.run(prober.probe)
            deferred.addErrback(callbacks.logMissingURL, url)
            deferredList.append(deferred)

        deferredList = defer.DeferredList(deferredList, consumeErrors=True)
        deferredList.addCallback(callbacks.ensureOrDeleteMirrorCDImageRelease)
        deferredList.addCallback(checkComplete, mirror_key, unchecked_keys)


def should_skip_host(host):
    """Return True if the requests/timeouts ratio on this host is too low."""
    requests = host_requests[host]
    timeouts = host_timeouts[host]
    if timeouts == 0 or requests < MIN_REQUESTS_TO_CONSIDER_RATIO:
        return False
    else:
        ratio = float(requests) / timeouts
        return ratio < MIN_REQUEST_TIMEOUT_RATIO


def _parse(url, defaultPort=80):
    """Parse the given URL returning the scheme, host, port and path."""
    scheme, host, path, dummy, dummy, dummy = urlparse.urlparse(url)
    port = defaultPort
    if ':' in host:
        host, port = host.split(':')
        assert port.isdigit()
        port = int(port)
    return scheme, host, port, path

