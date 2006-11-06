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
from canonical.launchpad.interfaces import UnableToFetchCDImageFileList
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import (
    IDistributionMirrorSet, ILibraryFileAliasSet)
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, MirrorProberCallbacks, MirrorCDImageProberCallbacks,
    RedirectAwareProberFactory, get_expected_cdimage_paths)


# Keep this number smaller than 1024 if running on python-2.3.4, as there's a
# bug (https://launchpad.net/bugs/48301) on this specific version which would
# break this script if BATCH_SIZE is higher than 1024.
BATCH_SIZE = 50
semaphore = DeferredSemaphore(BATCH_SIZE)


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
    packages_paths = mirror.getExpectedPackagesPaths()
    sources_paths = mirror.getExpectedSourcesPaths()
    all_paths = itertools.chain(packages_paths, sources_paths)
    for release, pocket, component, path in all_paths:
        url = "%s/%s" % (mirror.base_url, path)
        callbacks = MirrorProberCallbacks(
            mirror, release, pocket, component, url, logfile)
        unchecked_mirrors.append(url)
        prober = ProberFactory(url)

        deferred = semaphore.run(prober.probe)
        deferred.addCallbacks(
            callbacks.ensureMirrorRelease, callbacks.deleteMirrorRelease)

        deferred.addCallback(callbacks.updateMirrorStatus)
        deferred.addErrback(logger.error)

        deferred.addBoth(checkComplete, url, unchecked_mirrors)


def probe_release_mirror(mirror, logfile, unchecked_mirrors, logger):
    """Probe a release or release mirror for its contents.
    
    This is done by checking the list of files for each flavour and release
    returned by get_expected_cdimage_paths(). If a mirror contains all
    files for a given release and flavour, then we consider that mirror is
    actually mirroring that release and flavour.
    """
    # The list of files a mirror should contain will change over time and we
    # don't want to keep records for files a mirror once had but doesn't have
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
        unchecked_mirrors.append(mirror_key)
        deferredList = []
        for path in paths:
            url = '%s/%s' % (mirror.base_url, path)
            # Use a RedirectAwareProberFactory because CD mirrors are allowed
            # to redirect, and we need to cope with that.
            prober = RedirectAwareProberFactory(url)
            deferred = semaphore.run(prober.probe)
            deferred.addErrback(callbacks.logMissingURL, url)
            deferredList.append(deferred)

        deferredList = defer.DeferredList(deferredList, consumeErrors=True)
        deferredList.addCallback(callbacks.ensureOrDeleteMirrorCDImageRelease)
        deferredList.addCallback(checkComplete, mirror_key, unchecked_mirrors)


def parse_options(args):
    parser = optparse.OptionParser(
        usage='%prog --content-type=(archive|release) [--force]')
    parser.add_option(
        '--content-type',
        dest='content_type',
        default=None,
        action='store',
        help='Probe only mirrors of the given type'
        )

    parser.add_option(
        '--force',
        dest='force',
        default=False,
        action='store_true',
        help='Force the probing of mirrors that have been probed recently'
        )

    # Add the verbose/quiet options.
    logger_options(parser)
    options, args = parser.parse_args(args)
    return options


def _sanity_check_mirror(mirror, logger):
    """Check that the given mirror is official and has an http_base_url."""
    assert mirror.isOfficial(), 'Non-official mirrors should not be probed'
    if mirror.base_url is None:
        logger.warning(
            "Mirror '%s' of distribution '%s' doesn't have a base URL; "
            "we can't probe it." % (mirror.name, mirror.distribution.name))
        return False
    return True


def _create_probe_record(mirror, logfile):
    """Create a probe record for the given mirror with the given logfile."""
    logfile.seek(0)
    filename = '%s-probe-logfile.txt' % mirror.name
    log_file = getUtility(ILibraryFileAliasSet).create(
        name=filename, size=len(logfile.getvalue()),
        file=logfile, contentType='text/plain')
    mirror.newProbeRecord(log_file)


def main(argv):
    options = parse_options(argv[1:])
    logger_obj = logger(options, 'distributionmirror-prober')

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

    logger_obj.info('Probing %s Mirrors' % content_type.title)

    ztm = initZopeless(
        implicitBegin=False, dbuser=config.distributionmirrorprober.dbuser)
    execute_zcml_for_scripts()

    mirror_set = getUtility(IDistributionMirrorSet)

    ztm.begin()

    results = mirror_set.getMirrorsToProbe(
        content_type, ignore_last_probe=options.force)
    mirror_ids = [mirror.id for mirror in results]
    unchecked_mirrors = []
    logfiles = {}
    probed_mirrors = []

    for mirror_id in mirror_ids:
        mirror = mirror_set[mirror_id]
        if not _sanity_check_mirror(mirror, logger_obj):
            continue

        # XXX: Some people registered mirrors on distros other than Ubuntu
        # back in the old times, so now we need to do this small hack here.
        # Guilherme Salgado, 2006-05-26
        if not mirror.distribution.full_functionality:
            logger_obj.info(
                "Mirror '%s' of distribution '%s' can't be probed --we only "
                "probe Ubuntu mirrors." 
                % (mirror.name, mirror.distribution.name))
            continue

        probed_mirrors.append(mirror)
        logfile = StringIO()
        logfiles[mirror_id] = logfile
        probe_function(mirror, logfile, unchecked_mirrors, logger_obj)

    if probed_mirrors:
        reactor.run()
        logger_obj.info('Probed %d mirrors.' % len(probed_mirrors))
    else:
        logger_obj.info('No mirrors to probe.')
    ztm.commit()

    # Now that we finished probing all mirrors, we check if any of these
    # mirrors appear to have no content mirrored, and, if so, mark them as
    # disabled and notify their owners.
    disabled_mirrors_count = 0
    reenabled_mirrors_count = 0
    ztm.begin()
    expected_iso_images_count = len(get_expected_cdimage_paths())
    for mirror in probed_mirrors:
        _create_probe_record(mirror, logfiles[mirror.id])
        if mirror.shouldDisable(expected_iso_images_count):
            if mirror.enabled:
                disabled_mirrors_count += 1
            mirror.disableAndNotifyOwner()
        else:
            # Ensure the mirror is enabled, so that it shows up on public
            # mirror listings.
            if not mirror.enabled:
                mirror.enabled = True
                reenabled_mirrors_count += 1

    ztm.commit()

    if disabled_mirrors_count > 0:
        logger_obj.info(
            'Disabled %d mirror(s) that were previously enabled.'
            % disabled_mirrors_count)
    if reenabled_mirrors_count > 0:
        logger_obj.info(
            'Enabled %d mirror(s) that were previously disabled.'
            % reenabled_mirrors_count)
    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

