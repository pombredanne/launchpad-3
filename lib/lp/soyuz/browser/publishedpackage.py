# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'PkgBuild',
    'PkgVersion',
    'DistroSeriesVersions',
    'BinPackage',
    ]

class PkgBuild:

    def __init__(self, id, processorfamilyname,
                 distroarchseries):
        self.id = id
        self.processorfamilyname = processorfamilyname
        self.distroarchseries = distroarchseries

    def html(self):
        return (
            '<a href="/soyuz/packages/%s">%s</a>'
            % (self.id, self.processorfamilyname))

class PkgVersion:

    def __init__(self, version):
        self.version = version
        self.builds = []

    def buildlisthtml(self):
        return ', '.join([ build.html() for build in self.builds ])

class DistroSeriesVersions:

    def __init__(self, distroseriesname):
        self.distroseriesname = distroseriesname
        self.versions = {}

class BinPackage:

    def __init__(self, name, summary, description):
        self.name = name
        self.summary = summary
        self.description = description
        self.distroseriess = {}


