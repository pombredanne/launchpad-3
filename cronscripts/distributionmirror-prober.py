#!/usr/bin/python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Script to probe distribution mirrors and check how up-to-date they are."""

import _pythonpath

import sys
import optparse
import itertools
from StringIO import StringIO

from twisted.internet import reactor
from twisted.internet.defer import DeferredSemaphore

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import (
    IDistributionMirrorSet, ILibraryFileAliasSet)
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, MirrorProberCallbacks)


def checkComplete(result, url, unchecked_urls):
    """Check if we finished probing all mirrors, and call reactor.stop()."""
    unchecked_urls.remove(url)
    if not len(unchecked_urls):
        reactor.callLater(0, reactor.stop)
    # This is added to the deferred with addBoth(), which means it'll be
    # called if something goes wrong in the end of the callback chain, and in
    # that case we shouldn't swallow the error.
    return result


def main(argv):
    parser = optparse.OptionParser()
    # Add the verbose/quiet options.
    logger_options(parser)

    options, args = parser.parse_args(argv[1:])
    logger_obj = logger(options, 'distributionmirror-prober')
    logger_obj.info('Probing Distribution Mirrors')

    ztm = initZopeless(
        implicitBegin=False, dbuser=config.distributionmirrorprober.dbuser)
    execute_zcml_for_scripts()

    mirror_set = getUtility(IDistributionMirrorSet)

    ztm.begin()

    mirror_ids = [mirror.id for mirror in mirror_set.getMirrorsToProbe()]
    unchecked_urls = []
    logfiles = {}
    probed_mirrors = []

    semaphore = DeferredSemaphore(50)
    for mirror_id in mirror_ids:
        mirror = mirror_set[mirror_id]
        if mirror.http_base_url is None:
            logger_obj.warning(
                "Mirror '%s' of distribution '%s' doesn't have an http base "
                "URL, we can't probe it."
                % (mirror.name, mirror.distribution.name))
            continue

        probed_mirrors.append(mirror)
        logfiles[mirror_id] = StringIO()
        packages_paths = mirror.guessPackagesPaths()
        sources_paths = mirror.guessSourcesPaths()
        all_paths = itertools.chain(packages_paths, sources_paths)
        for release, pocket, component, path in all_paths:
            url = '%s/%s' % (mirror.http_base_url, path)
            callbacks = MirrorProberCallbacks(
                mirror, release, pocket, component, url, logfiles[mirror_id])
            unchecked_urls.append(url)
            prober = ProberFactory(url)

            prober.deferred.addCallbacks(
                callbacks.ensureMirrorRelease, callbacks.deleteMirrorRelease)

            prober.deferred.addCallback(callbacks.updateMirrorStatus)
            prober.deferred.addErrback(logger_obj.error)

            prober.deferred.addBoth(checkComplete, url, unchecked_urls)
            semaphore.run(prober.probe)

    if mirror_ids:
        reactor.run()
        logger_obj.info('Probed %d mirrors.' % len(mirror_ids))
    else:
        logger_obj.info('No mirrors to probe.')
    ztm.commit()

    # Now that we finished probing all mirrors, we check if any of these
    # mirrors appear to have no content mirrored, and, if so, mark them as
    # disabled and notify their owners.
    ztm.begin()
    for mirror in probed_mirrors:
        logfile = logfiles[mirror.id]
        logfile.seek(0)
        filename = '%s-probe-logfile.txt' % mirror.name
        log_file = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(logfile.getvalue()),
            file=logfile, contentType='text/plain')
        probe_record = mirror.newProbeRecord(log_file)
        if not (mirror.source_releases or mirror.arch_releases):
            mirror.disableAndNotifyOwner()

    ztm.commit()

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

