# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the 'canonical.lucille.config'
# package. This package is related to managing lucille's configuration
# as stored in the distribution and distrorelease tables

from StringIO import StringIO
from ConfigParser import ConfigParser

class Config(object):
    """Manage a lucille configuration from the database. (Read Only)
    This class provides a useful abstraction so that if we change
    how the database stores configuration then lucille will not
    need to be re-coded to cope"""

    def __init__(self, distribution, distroreleases):
        """Initialise the configuration"""
        self.distroName = distribution.name.encode('utf-8')
        self._distroreleases = {}
        for dr in distroreleases:
            drn = dr.name.encode('utf-8')
            drdrn =  {
                "archtags": []
                }
            self._distroreleases[drn] = drdrn
            for dar in dr.architectures:
                drdrn["archtags"].append(dar.architecturetag.encode('utf-8'))
            strio = StringIO(dr.lucilleconfig.encode('utf-8'))
            drdrn["config"] = ConfigParser()
            drdrn["config"].readfp(strio)
            strio.close()
            drdrn["components"] = drdrn["config"].get("publishing","components").split(" ")

        strio = StringIO(distribution.lucilleconfig.encode('utf-8'))
        self._distroconfig = ConfigParser()
        self._distroconfig.readfp(strio)
        strio.close()

        self._extractConfigInfo()
        
    def distroReleaseNames(self):
        # Because dicts iterate for keys only; this works to get dr names
        return self._distroreleases.keys()

    def archTagsForRelease(self, dr):
        return self._distroreleases[dr]["archtags"]

    def componentsForRelease(self, dr):
        return self._distroreleases[dr]["components"]

    def _extractConfigInfo(self):
        """Extract configuration information into the attributes we use"""
        self.stayofexecution = self._distroconfig.get("publishing",
                                                      "pendingremovalduration",
                                                      5)
        self.stayofexecution = float(self.stayofexecution)
        self.distroroot = self._distroconfig.get("publishing","root")
        self.archiveroot = self._distroconfig.get("publishing","archiveroot")
        self.poolroot = self._distroconfig.get("publishing","poolroot")
        self.distsroot = self._distroconfig.get("publishing","distsroot")
        self.overrideroot = self._distroconfig.get("publishing","overrideroot")
        self.cacheroot = self._distroconfig.get("publishing","cacheroot")
        self.miscroot = self._distroconfig.get("publishing","miscroot")
