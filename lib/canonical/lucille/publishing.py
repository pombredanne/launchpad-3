# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: 9503b5c7-7f87-48ee-a617-2a23b567d7a9

import os
from canonical.lucille.pool import Poolifier

from canonical.lp.dbschema import PackagePublishingStatus, \
                                  PackagePublishingPriority

from StringIO import StringIO

class Publisher(object):
    """Publisher is the class used to provide the facility to publish
    files in the pool of a Distribution. The publisher objects will be
    instantiated by the archive build scripts and will be used throughout
    the processing of each DistroRelease and DistroArchRelease in question
    """
    
    def __init__(self, poolroot, librarian):
        """Initialise a publisher. Publishers need the pool root dir
        and a canonical.librarian.FileDownloadClient"""
        if poolroot is None:
            raise ValueError, "Publisher expects a pool root directory"
        self._root = poolroot
        if not os.path.isdir(self._root):
            raise ValueError, "Root %s is not a directory or does not exist" % self._root
        self._poolifier = Poolifier()
        self._library = librarian

    def _pathfor(self, source, component, filename = None):
        if filename is None:
            return "%s/%s" % \
                   (self._root, self._poolifier.poolify(source,component))
        else:
            return "%s/%s/%s" % \
                   (self._root, self._poolifier.poolify(source,component), \
                    filename)


    def _preparedir(self, source, component):
        """Prepare the directories leading to this component/source
        combination. This uses os.makedirs to great effect"""
        if os.path.exists(self._pathfor(source,component)):
            return
        os.makedirs( self._pathfor(source, component) )

    def _publish(self, source, component, filename, alias):
        """Extract the given file from the librarian, construct the
        path to it in the pool and store the file. (assuming it's not already
        there)"""
        if os.path.exists(self._pathfor(source,component,filename)):
            print "%s/%s/%s: Already present" % (component,source,filename)
            return
        self._preparedir(source,component)
        print "%s/%s/%s: Publish from %d" % (component,source,filename,alias)
        # Dir is ready, extract from the librarian...
        # self._library should be a client for fetching from the library...
        # We're going to assume here that we'll eventually be allowed to
        # fetch from the library purely by aliasid (since that utterly
        # unambiguously identifies the file that we want)
        inf = self._library.getFileByAlias(alias)
        outf = open(self._pathfor(source,component,filename),'wb')
        while True:
            s = inf.read(4096)
            if s:
                outf.write(s)
            else:
                break
        outf.close()
        inf.close()

    def publish(self, records):
        """records should be an iterable of indexables which provide the
        following attributes:

               pp : PackagePublishing record
          pfalias : LibraryFileAlias.id
          lfaname : LibraryFileAlias.filename
           spname : SourcePackageName.name
            cname : Component.name
        """
        for pubrec in records:
            source = pubrec.spname.encode('utf-8')
            component = pubrec.cname.encode('utf-8')
            filename = pubrec.lfaname.encode('utf-8')
            self._publish( source, component, filename, pubrec.pfalias )
            pubrec.pp.status = PackagePublishingStatus.PUBLISHED.value

    def publishOverrides(self, sourceoverrides, binaryoverrides, \
                         overrideroot, defaultcomponent = "main"):
        """Given the provided sourceoverrides and binaryoverrides, output
        a set of override files for use in apt-ftparchive.

        The files will be written to overrideroot with filenames of the form:
        override.<distrorelease>.<component>[.src]

        Attributes which must be present in sourceoverrides are:
        drname, spname, cname, sname

        Attributes which must be present in binaryoverrides are:
        drname, spname, cname, sname, priority

        The binary priority will be mapped via the values in dbschema.py
        """

        # overrides[distrorelease][component][src/bin] = list of lists
        overrides = {}

        prio = {}
        for p in PackagePublishingPriority._items:
            prio[p] = PackagePublishingPriority._items[p].title.lower()

        for so in sourceoverrides:
            distrorelease = so.drname.encode('utf-8')
            component = so.cname.encode('utf-8')
            section = so.sname.encode('utf-8')
            sourcepackagename = so.spname.encode('utf-8')
            if component != defaultcomponent:
                section = "%s/%s" % (component,section)
            overrides.setdefault(distrorelease, {})
            overrides[distrorelease].setdefault(component, {})
            overrides[distrorelease][component].setdefault('src', [])
            overrides[distrorelease][component]['src'].append( (sourcepackagename,section) )

        for bo in binaryoverrides:
            distrorelease = bo.drname.encode('utf-8')
            component = bo.cname.encode('utf-8')
            section = bo.sname.encode('utf-8')
            binarypackagename = bo.bpname.encode('utf-8')
            priority = bo.priority
            if priority not in prio:
                raise ValueError, "Unknown priority value %d" % priority
            priority = prio[priority]
            if component != defaultcomponent:
                section = "%s/%s" % (component,section)
            overrides.setdefault(distrorelease, {})
            overrides[distrorelease].setdefault(component, {})
            overrides[distrorelease][component].setdefault('bin', [])
            overrides[distrorelease][component]['bin'].append( (binarypackagename,priority,section) )

        # Now generate the files on disk...
        for distrorelease in overrides:
            for component in overrides[distrorelease]:
                f = open("%s/override.%s.%s" % (overrideroot, distrorelease, component), "w")
                for tup in overrides[distrorelease][component]['bin']:
                    f.write("\t".join(tup))
                    f.write("\n")
                    
                f.close()

                f = open("%s/override.%s.%s.src" % (overrideroot, distrorelease, component), "w")
                for tup in overrides[distrorelease][component]['src']:
                    f.write("\t".join(tup))
                    f.write("\n")
                f.close()
                
