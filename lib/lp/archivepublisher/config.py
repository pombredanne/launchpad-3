# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# This is the python package that defines the
# 'lp.archivepublisher.config' package. This package is related
# to managing the archive publisher's configuration as stored in the
# distribution and distroseries tables

from ConfigParser import ConfigParser
import os
from StringIO import StringIO

from canonical.config import config
from lp.soyuz.enums import ArchivePurpose


def update_pub_config(pubconf):
    """Update dependent `PubConfig` fields.

    Update fields dependending on 'archiveroot'.
    """
    pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
    pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')
    pubconf.overrideroot = None
    pubconf.cacheroot = None
    pubconf.miscroot = None


def getPubConfig(archive):
    """Return an overridden Publisher Configuration instance.

    The original publisher configuration based on the distribution is
    modified according local context, it basically fixes the archive
    paths to cope with non-primary and PPA archives publication workflow.
    """
    pubconf = Config(archive.distribution)
    ppa_config = config.personalpackagearchive

    pubconf.temproot = os.path.join(
        config.archivepublisher.root, '%s-temp' % archive.distribution.name)

    if archive.is_ppa:
        if archive.private:
            pubconf.distroroot = ppa_config.private_root
            pubconf.htaccessroot = os.path.join(
                pubconf.distroroot, archive.owner.name, archive.name)
        else:
            pubconf.distroroot = ppa_config.root
            pubconf.htaccessroot = None
        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, archive.owner.name, archive.name,
            archive.distribution.name)
    elif archive.is_main:
        pubconf.distroroot = config.archivepublisher.root
        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, archive.distribution.name)
        if archive.purpose == ArchivePurpose.PARTNER:
            pubconf.archiveroot += '-partner'
        elif archive.purpose == ArchivePurpose.DEBUG:
            pubconf.archiveroot += '-debug'
    elif archive.is_copy:
        pubconf.distroroot = config.archivepublisher.root
        pubconf.archiveroot = os.path.join(
            pubconf.distroroot,
            archive.distribution.name + '-' + archive.name,
            archive.distribution.name)
    else:
        raise AssertionError(
            "Unknown archive purpose %s when getting publisher config.",
            archive.purpose)

    update_pub_config(pubconf)

    # There can be multiple copy archives, so the temp dir needs to be
    # within the archive.
    if archive.is_copy:
        pubconf.temproot = pubconf.archiveroot + '-temp'

    apt_ftparchive_purposes = (ArchivePurpose.PRIMARY, ArchivePurpose.COPY)
    if archive.purpose in apt_ftparchive_purposes:
        pubconf.overrideroot = pubconf.archiveroot + '-overrides'
        pubconf.cacheroot = pubconf.archiveroot + '-cache'
        pubconf.miscroot = pubconf.archiveroot + '-misc'

    meta_root = os.path.join(
        pubconf.distroroot, archive.owner.name)
    pubconf.metaroot = os.path.join(
        meta_root, "meta", archive.name)

    return pubconf


class LucilleConfigError(Exception):
    """Lucille configuration was not present."""


class Config(object):
    """Manage a publisher configuration from the database. (Read Only)
    This class provides a useful abstraction so that if we change
    how the database stores configuration then the publisher will not
    need to be re-coded to cope"""

    def __init__(self, distribution):
        """Initialise the configuration"""
        self.publishable_series = set()
        if not distribution.lucilleconfig:
            raise LucilleConfigError(
                'No Lucille config section for %s' % distribution.name)

        for dr in distribution:
            distroseries_name = dr.name.encode('utf-8')

            # We now just use lucilleconfig's nullness to determine if
            # the series is initialised and publishable.
            if dr.lucilleconfig is not None:
                self.publishable_series.add(distroseries_name)

    def setupArchiveDirs(self):
        """Create missing required directories in archive."""
        required_directories = [
            self.distroroot,
            self.poolroot,
            self.distsroot,
            self.archiveroot,
            self.cacheroot,
            self.overrideroot,
            self.miscroot,
            self.temproot,
            ]

        for directory in required_directories:
            if directory is None:
                continue
            if not os.path.exists(directory):
                os.makedirs(directory, 0755)
