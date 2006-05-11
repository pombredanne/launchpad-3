#!/usr/bin/python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Script to probe distribution mirrors and check how up-to-date they are."""

import _pythonpath

import sys
import optparse
import itertools
from StringIO import StringIO

from twisted.internet import defer, reactor
from twisted.internet.defer import DeferredSemaphore

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import MirrorContent
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import (
    IDistributionMirrorSet, ILibraryFileAliasSet)
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, MirrorProberCallbacks, MirrorCDImageProberCallbacks)


BATCH_SIZE = 50


def checkComplete(result, key, unchecked_keys):
    """Check if we finished probing all mirrors, and call reactor.stop()."""
    unchecked_keys.remove(key)
    if not len(unchecked_keys):
        reactor.callLater(0, reactor.stop)
    # This is added to the deferred with addBoth(), which means it'll be
    # called if something goes wrong in the end of the callback chain, and in
    # that case we shouldn't swallow the error.
    return result


def probe_archive_mirror(mirror, logfile, unchecked_mirrors, logger):
    """Probe an archive mirror for its contents and freshness.

    First we issue a set of HTTP HEAD requests on some key files to find out
    what is mirrored there, then we check if some packages that we know the
    publishing time are available on that mirror, giving us an idea of when it
    was last synced to the main archive.
    """
    semaphore = DeferredSemaphore(BATCH_SIZE)
    packages_paths = mirror.guessPackagesPaths()
    sources_paths = mirror.guessSourcesPaths()
    all_paths = itertools.chain(packages_paths, sources_paths)
    for release, pocket, component, path in all_paths:
        url = '%s/%s' % (mirror.http_base_url, path)
        callbacks = MirrorProberCallbacks(
            mirror, release, pocket, component, url, logfile)
        unchecked_mirrors.append(url)
        prober = ProberFactory(url)

        prober.deferred.addCallbacks(
            callbacks.ensureMirrorRelease, callbacks.deleteMirrorRelease)

        prober.deferred.addCallback(callbacks.updateMirrorStatus)
        prober.deferred.addErrback(logger.error)

        prober.deferred.addBoth(checkComplete, url, unchecked_mirrors)
        semaphore.run(prober.probe)


def probe_release_mirror(mirror, logfile, unchecked_mirrors, logger):
    """Probe a release or release mirror for its contents.
    
    This is done by checking the list of files for each flavour and release
    returned by mirror.guessCDImagePaths(). If a mirror contains all files for
    a given release and flavour, then we consider that mirror is actually
    mirroring that release and flavour.
    """
    semaphore = DeferredSemaphore(BATCH_SIZE)
    try:
        cdimage_paths = mirror.guessCDImagePaths()
    except UnableToFetchCDImageFileList, e:
        logger.error(e)
        return

    for release, flavour, paths in cdimage_paths:
        callbacks = MirrorCDImageProberCallbacks(
            mirror, release, flavour, logfile)

        mirror_key = (release, flavour)
        unchecked_mirrors.append(mirror_key)
        deferredList = []
        for path in paths:
            url = '%s/%s' % (mirror.http_base_url, path)
            prober = ProberFactory(url)
            prober.deferred.addErrback(callbacks.logMissingURL, url)
            d = semaphore.run(prober.probe)
            deferredList.append(d)

        deferredList = defer.DeferredList(deferredList, consumeErrors=True)
        deferredList.addCallback(callbacks.ensureOrDeleteMirrorCDImageRelease)
        deferredList.addCallback(checkComplete, mirror_key, unchecked_mirrors)


def parse_options(args):
    parser = optparse.OptionParser(usage='%prog --content-type=archive|release')
    parser.add_option(
        '--content-type',
        dest='content_type',
        default=None,
        action='store',
        help='Probe only mirrors of the given type'
        )

    # Add the verbose/quiet options.
    logger_options(parser)
    options, args = parser.parse_args(args)
    return options


def main(argv):
    options = parse_options(argv[1:])
    logger_obj = logger(options, 'distributionmirror-prober')
    logger_obj.info('Probing Distribution Mirrors')

    if options.content_type == 'archive':
        probe_function = probe_archive_mirror
        content_type = MirrorContent.ARCHIVE
    elif options.content_type == 'release':
        probe_function = probe_release_mirror
        content_type = MirrorContent.RELEASE
    else:
        logger_obj.error('Wrong value for argument --content-type: %s'
                         % options.content_type)
        return 1

    ztm = initZopeless(
        implicitBegin=False, dbuser=config.distributionmirrorprober.dbuser)
    execute_zcml_for_scripts()

    mirror_set = getUtility(IDistributionMirrorSet)

    ztm.begin()

    results = mirror_set.getMirrorsToProbe(content_type)
    mirror_ids = [mirror.id for mirror in results]
    unchecked_mirrors = []
    logfiles = {}
    probed_mirrors = []

    for mirror_id in mirror_ids:
        mirror = mirror_set[mirror_id]
        if mirror.http_base_url is None:
            logger_obj.warning(
                "Mirror '%s' of distribution '%s' doesn't have an http base "
                "URL, we can't probe it."
                % (mirror.name, mirror.distribution.name))
            continue

        probed_mirrors.append(mirror)
        logfile = StringIO()
        logfiles[mirror_id] = logfile
        probe_function(mirror, logfile, unchecked_mirrors, logger_obj)

    if mirror_ids:
        reactor.run()
        logger_obj.info('Probed %d mirrors.' % len(mirror_ids))
    else:
        logger_obj.info('No mirrors to probe.')
    ztm.commit()

    # Now that we finished probing all mirrors, we check if any of these
    # mirrors appear to have no content mirrored, and, if so, mark them as
    # disabled and notify their owners.
    disabled_mirrors_count = 0
    ztm.begin()
    for mirror in probed_mirrors:
        logfile = logfiles[mirror.id]
        logfile.seek(0)
        filename = '%s-probe-logfile.txt' % mirror.name
        log_file = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(logfile.getvalue()),
            file=logfile, contentType='text/plain')
        probe_record = mirror.newProbeRecord(log_file)
        if not mirror.hasContent():
            disabled_mirrors_count += 1
            mirror.disableAndNotifyOwner()

    ztm.commit()

    if disabled_mirrors_count:
        logger_obj.info(
            'Disabled %d mirrors because no content was found on them.'
            % disabled_mirrors_count)
    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

