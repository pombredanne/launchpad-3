#!/usr/bin/python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Script to probe distribution mirrors and check how up-to-date they are."""

import _pythonpath

import optparse
import sys

from twisted.internet import reactor
from twisted.python import failure

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import MirrorStatus
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import IDistributionMirrorSet
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, ProberTimeout)


PROBER_TIMEOUT = 3


def logError(failure, url, logger):
    # XXX: I'm not sure it's worth having this errback which will simply log
    # the error and then propagate it. -- Guilherme Salgado, 2006-02-15
    logger.error("%s on %s" % (failure, url))
    return failure


def setMirrorStatus(result, arch_or_source_mirror, status):
    if '200 OK' not in result:
        return
    if arch_or_source_mirror.status > status:
        arch_or_source_mirror.status = status


def updateMirrorDistroArchReleaseStatus(mirror_distro_arch_release, logger):
    """Update the status of this MirrorDistroArchRelease.

    This is done by issuing HTTP HEAD requests on that mirror looking for 
    some binary packages found in our publishing records. Then, knowing what
    packages the mirror contains and when these packages were published, we
    can have an idea of when that mirror was last updated.
    """
    if not mirror_distro_arch_release:
        return
    # We start setting the status to unknown, and then we move on trying to
    # find one of the recently published packages mirrored there.
    mirror_distro_arch_release.status = MirrorStatus.UNKNOWN
    status_url_mapping = mirror_distro_arch_release.getURLsToCheckUpdateness()
    for status, url in status_url_mapping.items():
        prober = ProberFactory(url, timeout=PROBER_TIMEOUT)
        prober.deferred.addCallback(
            setMirrorStatus, mirror_distro_arch_release, status)
        prober.deferred.addErrback(logError, url, logger)
        reactor.connectTCP(prober.host, prober.port, prober)


def updateMirrorDistroReleaseSourceStatus(mirror_distro_release_source, logger):
    """Update the status of this MirrorDistroReleaseSource.

    This is done by issuing HTTP HEAD requests on that mirror looking for 
    some source packages found in our publishing records. Then, knowing what
    packages the mirror contains and when these packages were published, we
    can have an idea of when that mirror was last updated.
    """
    # The previous callback might return None in case we got a 404, so we need
    # to check that here.
    if not mirror_distro_release_source:
        return
    # We start setting the status to unknown, and then we move on trying to
    # find one of the recently published packages mirrored there.
    mirror_distro_release_source.status = MirrorStatus.UNKNOWN
    status_url_mapping = mirror_distro_release_source.getURLsToCheckUpdateness()
    for status, url in status_url_mapping.items():
        prober = ProberFactory(url, timeout=PROBER_TIMEOUT)
        prober.deferred.addCallback(
            setMirrorStatus, mirror_distro_release_source, status)
        prober.deferred.addErrback(logError, url, logger)
        reactor.connectTCP(prober.host, prober.port, prober)


def checkComplete(result, url, UNCHECKED_URLS):
    """Check if we finished probing all mirrors, and call reactor.stop()."""
    UNCHECKED_URLS.remove(url)
    if not len(UNCHECKED_URLS):
        reactor.callLater(0, reactor.stop)
    # This is added to the deferred with addBoth(), which means it'll be
    # called if something goes wrong in the end of the callback chain, and in
    # that case we shouldn't swallow the error, so we always return the result
    # we get from the deferred.
    return result


def ensureMirrorDistroArchRelease(result, mirror, arch_release, pocket,
                                  component, url):
    if '200 OK' in result:
        return mirror.ensureMirrorDistroArchRelease(
            arch_release, pocket, component)
    else:
        mirror.deleteMirrorDistroArchRelease(arch_release, pocket, component)
        return None


def deleteMirrorDistroArchRelease(reason, mirror, arch_release, pocket,
                                  component, url, logger):
    mirror.deleteMirrorDistroArchRelease(arch_release, pocket, component)
    if reason.type != ProberTimeout:
        return reason
    logger.info("Timeout on %s" % url)
    return None


def ensureMirrorDistroReleaseSource(result, mirror, release, pocket,
                                    component, url):
    if '200 OK' in result:
        return mirror.ensureMirrorDistroReleaseSource(
            release, pocket, component)
    else:
        mirror.deleteMirrorDistroReleaseSource(release, pocket, component)
        return None


def deleteMirrorDistroReleaseSource(reason, mirror, release, pocket,
                                    component, url, logger):
    mirror.deleteMirrorDistroReleaseSource(release, pocket, component)
    if reason.type != ProberTimeout:
        return reason
    logger.info("Timeout on %s" % url)
    return None


def main(argv):
    parser = optparse.OptionParser()
    # Add the verbose/quiet options.
    logger_options(parser)

    options, args = parser.parse_args(argv[1:])
    logger_obj = logger(options, 'distributionmirror-prober')
    logger_obj.info('Probing Distribution Mirrors')

    ztm = initZopeless(implicitBegin=False)
    execute_zcml_for_scripts()

    mirror_set = getUtility(IDistributionMirrorSet)

    ztm.begin()

    mirror_ids = [mirror.id for mirror in mirror_set.getMirrorsToProbe()]
    UNCHECKED_URLS = []

    for mirror_id in mirror_ids:
        mirror = mirror_set[mirror_id]
        packages_paths = mirror.guessPackagesPaths()
        for arch_release, pocket, component, path in packages_paths:
            url = '%s/%s' % (mirror.http_base_url, path)
            UNCHECKED_URLS.append(url)
            prober = ProberFactory(url, timeout=PROBER_TIMEOUT)

            prober.deferred.addCallback(
                ensureMirrorDistroArchRelease, mirror, arch_release, pocket,
                component, url)
            prober.deferred.addErrback(
                deleteMirrorDistroArchRelease, mirror, arch_release, pocket,
                component, url, logger_obj)

            prober.deferred.addCallback(
                updateMirrorDistroArchReleaseStatus, logger_obj)

            prober.deferred.addBoth(checkComplete, url, UNCHECKED_URLS)
            reactor.connectTCP(prober.host, prober.port, prober)

        for release, pocket, component, path in mirror.guessSourcesPaths():
            url = '%s/%s' % (mirror.http_base_url, path)
            UNCHECKED_URLS.append(url)
            prober = ProberFactory(url, timeout=PROBER_TIMEOUT)

            prober.deferred.addCallback(
                ensureMirrorDistroReleaseSource, mirror, release, pocket,
                component, url)
            prober.deferred.addErrback(
                deleteMirrorDistroReleaseSource, mirror, release, pocket,
                component, url, logger_obj)

            prober.deferred.addCallback(
                updateMirrorDistroReleaseSourceStatus, logger_obj)

            prober.deferred.addBoth(checkComplete, url, UNCHECKED_URLS)
            reactor.connectTCP(prober.host, prober.port, prober)

    if mirror_ids:
        reactor.run()
    ztm.commit()

    # Now that we finished probing all mirrors, we check if any of these
    # mirrors appear to have no content mirrored, and, if so, mark them as
    # disabled and notify their owners.
    ztm.begin()
    for mirror_id in mirror_ids:
        mirror = mirror_set[mirror_id]
        mirror.newProbeRecord()
        if not (mirror.source_releases or mirror.arch_releases):
            mirror.disableAndNotifyOwner()

    ztm.commit()

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

