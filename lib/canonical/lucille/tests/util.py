# Copyright 2004 Canonical Ltd.  All rights reserved.
#

# Utility functions/classes for testing Lucille.

from canonical.lucille.tests import datadir

class FakeDistribution(object):
    def __init__(self,name,conf):
        self.name = name.decode('utf-8')
        self.lucilleconfig = conf.decode('utf-8')

class FakeDistroRelease(object):
    def __init__(self,name,conf,distro):
        self.name = name.decode('utf-8')
        self.lucilleconfig = conf.decode('utf-8')
        self.distribution = distro
        self.architectures = [ FakeDistroArchRelease(self, "i386"),
                               FakeDistroArchRelease(self, "powerpc") ]

class FakeDistroArchRelease(object):
    def __init__(self,dr,archtag):
        self.distrorelease = dr
        self.architecturetag = archtag

class FakeSource(object):
    def __init__(self,version,status,name=""):
        self.version = version.decode('utf-8')
        self.status = status
        self.sourcepackagename = name.decode('utf-8')
    def _deepCopy(self):
        return FakeSource(self.version.encode('utf-8'),
                          self.status,
                          self.sourcepackagename.encode('utf-8')
                          )

class FakeBinary(object):
    def __init__(self,version,status,name=""):
        self.version = version.decode('utf-8')
        self.status = status
        self.packagename = name.decode('utf-8')
    def _deepCopy(self):
        return FakeBinary(self.version.encode('utf-8'),
                          self.status,
                          self.packagename.encode('utf-8')
                          )

class FakeSourcePublishing(object):
    def __init__(self,source,component,filename,alias,section="",dr=""):
        self.sourcepackagename = source.decode('utf-8')
        self.componentname = component.decode('utf-8')
        self.libraryfilealiasfilename = filename.decode('utf-8')
        self.libraryfilealias = alias
        self.sourcepackagepublishing = FakeSource("",0)
        self.sectionname = section.decode('utf-8')
        self.distroreleasename = dr.decode('utf-8')
        
    def _deepCopy(self):
        return FakeSourcePublishing( self.sourcepackagename.encode('utf-8'),
                                     self.componentname.encode('utf-8'),
                                     self.libraryfilealiasfilename.encode('utf-8'),
                                     self.libraryfilealias,
                                     self.sectionname.encode('utf-8'),
                                     self.distroreleasename.encode('utf-8')
                                     )
class FakeBinaryPublishing(object):
    def __init__(self,source,component,filename,alias,
                 section="",dr="",prio=0, archtag = ""):
        self.sourcepackagename = source.decode('utf-8')
        self.binarypackagename = source.decode('utf-8')
        self.componentname = component.decode('utf-8')
        self.libraryfilealiasfilename = filename.decode('utf-8')
        self.libraryfilealias = alias
        self.packagepublishing = FakeBinary("",0)
        self.sectionname = section.decode('utf-8')
        self.distroreleasename = dr.decode('utf-8')
        self.priority = prio
        self.architecturetag = archtag.decode('utf-8')
        
    def _deepCopy(self):
        return FakeBinaryPublishing( self.sourcepackagename.encode('utf-8'),
                                     self.componentname.encode('utf-8'),
                                     self.libraryfilealiasfilename.encode('utf-8'),
                                     self.libraryfilealias,
                                     self.sectionname.encode('utf-8'),
                                     self.distroreleasename.encode('utf-8'),
                                     self.priority,
                                     self.architecturetag.encode('utf-8')
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


class FakeDownloadClient(object):
    """Fake up a FileDownloadClient for the tests"""
    def __init__(self):
        pass

    def getFileByAlias(self, alias):
        """Fake this up by returning data/aliases/alias"""
        return file("%s/%s" % (datadir("aliases"), alias), "r")

    def getPathForAlias(self, alias):
        """Fake this up by returning the PATH 'alias/alias/alias'"""
        return "/%s/%s/%s" % (alias, alias, alias)


class FakeUploadClient(object):
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
dist = FakeDistribution("ubuntu",
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

drs = [
    FakeDistroRelease("warty",
                      """
[publishing]
components = main restricted universe
                      """, dist),
    FakeDistroRelease("hoary",
                      """
[publishing]
components = main restricted universe
                      """, dist)
    ]

