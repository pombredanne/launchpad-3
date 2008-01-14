# Copyright 2004 Canonical Ltd.  All rights reserved.
#

"""Utilities to aid testing archivepublisher."""

__metaclass__ = type

# Utility functions/classes for testing the archive publisher.

from canonical.archivepublisher.tests import datadir
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, PackagePublishingPocket, PackagePublishingStatus)

__all__ = ['FakeLogger']

class FakeLogger:
    def debug(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class FakeDistribution:
    def __init__(self, name, conf):
        self.name = name.decode('utf-8')
        self.lucilleconfig = conf.decode('utf-8')
        self.serieses = []

    def registerSeries(self, series):
        self.serieses.append(series)

    def __getitem__(self, name):
        for series in self.serieses:
            if series.name == name:
                return series
        return None


class FakeDistroSeries:
    def __init__(self, name, conf, distro):
        self.name = name.decode('utf-8')
        self.lucilleconfig = conf.decode('utf-8')
        self.distribution = distro
        self.architectures = [FakeDistroArchSeries(self, "i386"),
                              FakeDistroArchSeries(self, "powerpc")]
        self.status = DistroSeriesStatus.DEVELOPMENT
        self.distribution.registerSeries(self)


class FakeDistroArchSeries:
    def __init__(self, series, archtag):
        self.distroseries = series
        self.architecturetag = archtag


class FakeSource:
    def __init__(self, version, status, name=""):
        self.version = version.decode('utf-8')
        self.status = status
        self.datepublished = None
        self.sourcepackagename = name.decode('utf-8')

    def _deepCopy(self):
        return FakeSource(
            self.version.encode('utf-8'),
            self.status,
            self.sourcepackagename.encode('utf-8')
            )


class FakeBinary:
    def __init__(self, version, status, name=""):
        self.version = version.decode('utf-8')
        self.status = status
        self.datepublished = None
        self.packagename = name.decode('utf-8')

    def _deepCopy(self):
        return FakeBinary(
            self.version.encode('utf-8'),
            self.status,
            self.packagename.encode('utf-8')
            )


class FakeSourcePublishing:
    """Mocks a SourcePackagePublishingHistory object."""
    id = 1

    def __init__(self, source, component, alias, section, ds):
        class Dummy: id = 1
        self.sourcepackagerelease = Dummy()
        self.sourcepackagerelease.name = source
        self.component = Dummy()
        self.component.name = component
        self.libraryfilealias = alias
        self.section = Dummy()
        self.section.name = section
        self.distroseries = Dummy()
        self.distroseries.name = ds
        self.pocket = PackagePublishingPocket.RELEASE

    def _deepCopy(self):
        return FakeSourcePublishing(
            self.sourcepackage.name,
            self.component.name,
            self.libraryfilealias,
            self.section.name,
            self.distroseries.name,
            )

class FakeBinaryPublishing:
    """Mocks a BinaryPackagePublishingHistory object."""
    id = 1

    def __init__(self, binary, source, component, alias,
                 section, ds, prio, archtag):
        class Dummy: id = 1
        self.binarypackagerelease = Dummy()
        self.binarypackagerelease.name = source
        self.sourcepackagerelease = Dummy()
        self.sourcepackagerelease.name = source
        self.binarypackage = Dummy()
        self.binarypackage.name = source
        self.component = Dummy()
        self.component.name = component
        self.section = Dummy()
        self.section.name = section
        self.distroarchseries = Dummy()
        self.distroarchseries.distroseries = Dummy()
        self.distroarchseries.distroseries.name = ds
        self.libraryfilealias = alias
        self.priority = prio
        self.architecturetag = archtag
        self.pocket = PackagePublishingPocket.RELEASE

    def _deepCopy(self):
        return FakeBinaryPublishing(
            self.binarypackagerelease.name,
            self.sourcepackagerelease.name,
            self.component.name,
            self.libraryfilealias,
            self.section.name,
            self.distroseries.name,
            self.priority,
            self.architecturetag,
            )


class FakeSourceFilePublishing:
    """Mocks a SourcePackageFilePublishing object."""
    def __init__(self, source, component, leafname, alias, section, ds):
        self.sourcepackagename = source
        self.componentname = component
        self.libraryfilealiasfilename = leafname
        self.libraryfilealias = alias
        self.sectionname = section
        self.distroseriesname = ds
        self.pocket = PackagePublishingPocket.RELEASE

    def _deepCopy(self):
        return FakeSourceFilePublishing(
            self.sourcepackagename,
            self.componentname,
            self.libraryfilealiasfilename,
            self.libraryfilealias,
            self.sectionname,
            self.distroseriesname,
            )

class FakeBinaryFilePublishing:
    """Mocks a BinaryPackageFilePublishing object."""
    def __init__(self, source, component, leafname, alias, section, ds, archtag):
        self.sourcepackagename = source
        self.componentname = component
        self.libraryfilealiasfilename = leafname
        self.libraryfilealias = alias
        self.sectionname = section
        self.distroseriesname = ds
        self.architecturetag = archtag
        self.pocket = PackagePublishingPocket.RELEASE

    def _deepCopy(self):
        return FakeBinaryFilePublishing(
            self.sourcepackagename,
            self.componentname,
            self.libraryfilealiasfilename,
            self.libraryfilealias,
            self.sectionname,
            self.distroseriesname,
            self.architecturetag,
            )

sentinel = object()


def _deepCopy(thing):
    if type(thing) == dict:
        ret = {}
        for key in thing:
            ret[key] = _deepCopy(thing[key])
        return ret
    if type(thing) == list:
        ret = []
        for val in thing:
            ret.append(_deepCopy(val))
        return ret
    if type(thing) == tuple:
        ret = []
        for val in thing:
            ret.append(_deepCopy(val))
        return tuple(ret)
    if getattr(thing,"_deepCopy",sentinel) != sentinel:
        return thing._deepCopy()
    return thing # Assume we can't copy it deeply


class FakeDownloadClient:
    """Fake up a FileDownloadClient for the tests"""
    def __init__(self):
        pass

    def getFileByAlias(self, alias):
        """Fake this up by returning data/aliases/alias"""
        return file("%s/%s" % (datadir("aliases"), alias), "r")

    def getPathForAlias(self, alias):
        """Fake this up by returning the PATH 'alias/alias/alias'"""
        return "/%s/%s/%s" % (alias, alias, alias)


class FakeUploadClient:
    """Fake up a FileUploadClient for the tests"""
    def __init__(self):
        pass

    def connect(self, host, port):
        pass

    def addFile(self, name, size, fileobj, contentType, digest):
        fileid = '1'
        filealias = '1'
        return fileid, filealias


# NOTE: If you alter the configs here remember to add tests in test_config.py
fake_ubuntu = FakeDistribution("ubuntu",
                        """
[publishing]
pendingremovalduration=5
root=FOO
archiveroot=FOO/BAR
poolroot=FOO/BAR/pool
distsroot=FOO/BAR/dists
overrideroot=FOO/overrides
cacheroot=FOO/cache
miscroot=FOO/misc
                        """.replace("FOO",datadir("distro")).replace("BAR","ubuntu"));

fake_ubuntu_serieses = [
    FakeDistroSeries("warty",
                      """
[publishing]
components = main restricted universe
                      """, fake_ubuntu),
    FakeDistroSeries("hoary",
                      """
[publishing]
components = main restricted universe
                      """, fake_ubuntu)
    ]

