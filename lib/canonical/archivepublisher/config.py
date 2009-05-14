# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the
# 'canonical.archivepublisher.config' package. This package is related
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
        for distroseries in pubconf._distroserieses.keys():
            pubconf._distroserieses[
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
    else:
        raise AssertionError(
            "Unknown archive purpose %s when getting publisher config.",
            archive.purpose)

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
        self._distroserieses = {}
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

            if not dr.lucilleconfig:
                raise LucilleConfigError(
                    'No Lucille configuration section for %s' % dr.name)

            strio = StringIO(dr.lucilleconfig.encode('utf-8'))
            config_segment["config"] = ConfigParser()
            config_segment["config"].readfp(strio)
            strio.close()
            config_segment["components"] = config_segment["config"].get(
                "publishing", "components").split(" ")

            self._distroserieses[distroseries_name] = config_segment

        strio = StringIO(distribution.lucilleconfig.encode('utf-8'))
        self._distroconfig = ConfigParser()
        self._distroconfig.readfp(strio)
        strio.close()

        self._extractConfigInfo()

    def distroSeriesNames(self):
        # Because dicts iterate for keys only; this works to get dr names
        return self._distroserieses.keys()

    def archTagsForSeries(self, dr):
        return self._distroserieses[dr]["archtags"]

    def componentsForSeries(self, dr):
        return self._distroserieses[dr]["components"]

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
