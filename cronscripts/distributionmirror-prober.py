#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

"""Script to probe distribution mirrors and check how up-to-date they are."""

import _pythonpath

import os
from StringIO import StringIO

from twisted.internet import reactor

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import ISOLATION_LEVEL_AUTOCOMMIT
from lp.services.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from lp.registry.interfaces.distributionmirror import (
    IDistributionMirrorSet,
    MirrorContent,
    )
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.webapp import canonical_url
from lp.registry.scripts.distributionmirror_prober import (
    get_expected_cdimage_paths, probe_archive_mirror, probe_cdimage_mirror)


class DistroMirrorProber(LaunchpadCronScript):
    usage = ('%prog --content-type=(archive|cdimage) [--force] '
             '[--no-owner-notification] [--max-mirrors=N]')

    def _sanity_check_mirror(self, mirror):
        """Check that the given mirror is official and has an http_base_url.
        """
        assert mirror.isOfficial(), (
            'Non-official mirrors should not be probed')
        if mirror.base_url is None:
            self.logger.warning(
                "Mirror '%s' of distribution '%s' doesn't have a base URL; "
                "we can't probe it." % (
                    mirror.name, mirror.distribution.name))
            return False
        return True

    def _create_probe_record(self, mirror, logfile):
        """Create a probe record for the given mirror with the given logfile.
        """
        logfile.seek(0)
        filename = '%s-probe-logfile.txt' % mirror.name
        log_file = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(logfile.getvalue()),
            file=logfile, contentType='text/plain')
        mirror.newProbeRecord(log_file)

    def add_my_options(self):
        self.parser.add_option('--content-type',
            dest='content_type', default=None, action='store',
            help='Probe only mirrors of the given type')
        self.parser.add_option('--force',
            dest='force', default=False, action='store_true',
            help='Force the probing of mirrors that were probed recently')
        self.parser.add_option('--no-owner-notification',
            dest='no_owner_notification', default=False, action='store_true',
            help='Do not send failure notification to mirror owners.')
        self.parser.add_option('--no-remote-hosts',
            dest='no_remote_hosts', default=False, action='store_true',
            help='Do not try to connect to any host other than localhost.')
        self.parser.add_option('--max-mirrors',
            dest='max_mirrors', default=None, action='store', type="int",
            help='Only probe N mirrors.')

    def mirror(self, logger, content_type, no_remote_hosts, ignore_last_probe,
               max_mirrors, notify_owner):
        if content_type == MirrorContent.ARCHIVE:
            probe_function = probe_archive_mirror
        elif content_type == MirrorContent.RELEASE:
            probe_function = probe_cdimage_mirror
        else:
            raise ValueError(
                "Unrecognized content_type: %s" % (content_type,))

        self.txn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        self.txn.begin()

        # To me this seems better than passing the no_remote_hosts value
        # through a lot of method/function calls, until it reaches the probe()
        # method. (salgado)
        if no_remote_hosts:
            localhost_only_conf = """
                [distributionmirrorprober]
                localhost_only: True
                """
            config.push('localhost_only_conf', localhost_only_conf)

        logger.info('Probing %s Mirrors' % content_type.title)

        mirror_set = getUtility(IDistributionMirrorSet)
        results = mirror_set.getMirrorsToProbe(
            content_type, ignore_last_probe=ignore_last_probe,
            limit=max_mirrors)
        mirror_ids = [mirror.id for mirror in results]
        unchecked_keys = []
        logfiles = {}
        probed_mirrors = []

        for mirror_id in mirror_ids:
            mirror = mirror_set[mirror_id]
            if not self._sanity_check_mirror(mirror):
                continue

            # XXX: salgado 2006-05-26:
            # Some people registered mirrors on distros other than Ubuntu back
            # in the old times, so now we need to do this small hack here.
            if not mirror.distribution.full_functionality:
                logger.info(
                    "Mirror '%s' of distribution '%s' can't be probed --we "
                    "only probe Ubuntu mirrors."
                    % (mirror.name, mirror.distribution.name))
                continue

            probed_mirrors.append(mirror)
            logfile = StringIO()
            logfiles[mirror_id] = logfile
            probe_function(mirror, logfile, unchecked_keys, self.logger)

        if probed_mirrors:
            reactor.run()
            logger.info('Probed %d mirrors.' % len(probed_mirrors))
        else:
            logger.info('No mirrors to probe.')

        disabled_mirrors = []
        reenabled_mirrors = []
        # Now that we finished probing all mirrors, we check if any of these
        # mirrors appear to have no content mirrored, and, if so, mark them as
        # disabled and notify their owners.
        expected_iso_images_count = len(get_expected_cdimage_paths())
        for mirror in probed_mirrors:
            log = logfiles[mirror.id]
            self._create_probe_record(mirror, log)
            if mirror.shouldDisable(expected_iso_images_count):
                if mirror.enabled:
                    log.seek(0)
                    mirror.disable(notify_owner, log.getvalue())
                    disabled_mirrors.append(canonical_url(mirror))
            else:
                # Ensure the mirror is enabled, so that it shows up on public
                # mirror listings.
                if not mirror.enabled:
                    mirror.enabled = True
                    reenabled_mirrors.append(canonical_url(mirror))

        if disabled_mirrors:
            logger.info(
                'Disabling %s mirror(s): %s'
                % (len(disabled_mirrors), ", ".join(disabled_mirrors)))
        if reenabled_mirrors:
            logger.info(
                'Re-enabling %s mirror(s): %s'
                % (len(reenabled_mirrors), ", ".join(reenabled_mirrors)))
        # XXX: salgado 2007-04-03:
        # This should be done in LaunchpadScript.lock_and_run() when
        # the isolation used is ISOLATION_LEVEL_AUTOCOMMIT. Also note
        # that replacing this with a flush_database_updates() doesn't
        # have the same effect, it seems.
        self.txn.commit()

        logger.info('Done.')


    def main(self):
        if self.options.content_type == 'archive':
            content_type = MirrorContent.ARCHIVE
        elif self.options.content_type == 'cdimage':
            content_type = MirrorContent.RELEASE
        else:
            raise LaunchpadScriptFailure(
                'Wrong value for argument --content-type: %s'
                % self.options.content_type)

        if config.distributionmirrorprober.use_proxy:
            os.environ['http_proxy'] = config.launchpad.http_proxy
            self.logger.debug("Using %s as proxy." % os.environ['http_proxy'])
        else:
            self.logger.debug("Not using any proxy.")

        self.mirror(
            self.logger, content_type, self.options.no_remote_hosts,
            self.options.force, self.options.max_mirrors,
            not self.options.no_owner_notification)



if __name__ == '__main__':
    script = DistroMirrorProber('distributionmirror-prober',
                                dbuser=config.distributionmirrorprober.dbuser)
    script.lock_and_run()

