# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# This is the python package that defines the
# 'lp.archivepublisher.config' package. This package is related
# to managing the archive publisher's configuration as stored in the
# distribution and distroseries tables

import os
from StringIO import StringIO
from ConfigParser import ConfigParser

from canonical.config import config
from lp.soyuz.interfaces.archive import ArchivePurpose


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

    if archive.purpose == ArchivePurpose.PRIMARY:
        pass
    elif archive.is_ppa:
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
        update_pub_config(pubconf)
    elif archive.purpose == ArchivePurpose.PARTNER:
        # Reset the list of components to partner only.  This prevents
        # any publisher runs from generating components not related to
        # the partner archive.
        for distroseries in pubconf._distroseries.keys():
            pubconf._distroseries[
                distroseries]['components'] = ['partner']
        pubconf.distroroot = config.archivepublisher.root
        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, archive.distribution.name + '-partner')
        update_pub_config(pubconf)
    elif archive.purpose == ArchivePurpose.DEBUG:
        pubconf.distroroot = config.archivepublisher.root
        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, archive.distribution.name + '-debug')
        update_pub_config(pubconf)
    elif archive.is_copy:
        pubconf.distroroot = config.archivepublisher.root
        pubconf.archiveroot = os.path.join(
            pubconf.distroroot,
            archive.distribution.name + '-' + archive.name,
            archive.distribution.name)
        # Multiple copy archives can exist on the same machine so the
        # temp areas need to be unique also.
        pubconf.temproot = pubconf.archiveroot + '-temp'
        update_pub_config(pubconf)
        pubconf.overrideroot = pubconf.archiveroot + '-overrides'
        pubconf.cacheroot = pubconf.archiveroot + '-cache'
        pubconf.miscroot = pubconf.archiveroot + '-misc'
    else:
        raise AssertionError(
            "Unknown archive purpose %s when getting publisher config.",
            archive.purpose)

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
        self.distroName = distribution.name.encode('utf-8')
        self._distroseries = {}
        if not distribution.lucilleconfig:
            raise LucilleConfigError(
                'No Lucille config section for %s' % distribution.name)

        for dr in distribution:
            distroseries_name = dr.name.encode('utf-8')
            config_segment =  {
                "archtags": []
                }

            for dar in dr.architectures:
                config_segment["archtags"].append(
                    dar.architecturetag.encode('utf-8'))

            if dr.lucilleconfig:
                strio = StringIO(dr.lucilleconfig.encode('utf-8'))
                config_segment["config"] = ConfigParser()
                config_segment["config"].readfp(strio)
                strio.close()
                config_segment["components"] = config_segment["config"].get(
                    "publishing", "components").split(" ")

                self._distroseries[distroseries_name] = config_segment

        strio = StringIO(distribution.lucilleconfig.encode('utf-8'))
        self._distroconfig = ConfigParser()
        self._distroconfig.readfp(strio)
        strio.close()

        self._extractConfigInfo()

    def distroSeriesNames(self):
        # Because dicts iterate for keys only; this works to get dr names
        return self._distroseries.keys()

    def series(self, dr):
        try:
            return self._distroseries[dr]
        except KeyError:
            raise LucilleConfigError(
                'No Lucille config section for %s in %s' %
                    (dr, self.distroName))

    def archTagsForSeries(self, dr):
        return self.series(dr)["archtags"]

    def componentsForSeries(self, dr):
        return self.series(dr)["components"]

    def _extractConfigInfo(self):
        """Extract configuration information into the attributes we use"""
        self.stayofexecution = self._distroconfig.get(
            "publishing", "pendingremovalduration", 5)
        self.stayofexecution = float(self.stayofexecution)
        self.distroroot = self._distroconfig.get("publishing","root")
        self.archiveroot = self._distroconfig.get("publishing","archiveroot")
        self.poolroot = self._distroconfig.get("publishing","poolroot")
        self.distsroot = self._distroconfig.get("publishing","distsroot")
        self.overrideroot = self._distroconfig.get(
            "publishing","overrideroot")
        self.cacheroot = self._distroconfig.get("publishing","cacheroot")
        self.miscroot = self._distroconfig.get("publishing","miscroot")
        # XXX cprov 2007-04-26 bug=45270:
        # We should build all the previous attributes
        # dynamically like this. It would reduce the configuration complexity.
        # Even before we have it properly modeled in LPDB.
        self.temproot = os.path.join(
            self.distroroot, '%s-temp' % self.distroName)

    def setupArchiveDirs(self):
        """Create missing required directories in archive.

        For PPA publication path are overriden after instantiation
        and empty locations should not be considered for creation.
        """
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
