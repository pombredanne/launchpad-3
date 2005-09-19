# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: 9503b5c7-7f87-48ee-a617-2a23b567d7a9

import os

from canonical.lp.dbschema import PackagePublishingStatus, \
                                  PackagePublishingPriority, \
                                  PackagePublishingPocket

from StringIO import StringIO
from sets import Set

from canonical.librarian.client import LibrarianClient
from canonical.archivepublisher.pool import AlreadyInPool
from canonical.database.constants import nowUTC

__all__ = [ 'Publisher', 'pocketsuffix', 'suffixpocket' ]

pocketsuffix = {
    PackagePublishingPocket.RELEASE: "",
    PackagePublishingPocket.SECURITY: "-security",
    PackagePublishingPocket.UPDATES: "-updates",
    PackagePublishingPocket.PROPOSED: "-proposed"
    }
suffixpocket = dict((v,k) for (k,v) in pocketsuffix.items())

class Publisher(object):
    """Publisher is the class used to provide the facility to publish
    files in the pool of a Distribution. The publisher objects will be
    instantiated by the archive build scripts and will be used throughout
    the processing of each DistroRelease and DistroArchRelease in question
    """
    
    def __init__(self, logger, config, diskpool):
        """Initialise a publisher. Publishers need the pool root dir
        and a DiskPool object"""
        self._config = config
        self._root = config.poolroot
        if not os.path.isdir(self._root):
            raise ValueError, "Root %s is not a directory or does not exist" % self._root
        self._diskpool = diskpool
        self._library = LibrarianClient()
        self._logger = logger
        self._pathfor = diskpool.pathFor

        # We need somewhere to note down where the debian-installer
        # components came from. in _di_release_components we store
        # sets, keyed by distrorelease name of the component names
        # which contain debian-installer binaries.  This is filled out
        # when generating overrides and file lists, and then consumed
        # when generating apt-ftparchive configuration.
        self._di_release_components = {}

    def debug(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def _publish(self, source, component, filename, alias):
        """Extract the given file from the librarian, construct the
        path to it in the pool and store the file. (assuming it's not already
        there)"""
        #print "%s/%s/%s: Publish from %d" % (component,source,filename,alias)
        # Dir is ready, extract from the librarian...
        # self._library should be a client for fetching from the library...
        # We're going to assume here that we'll eventually be allowed to
        # fetch from the library purely by aliasid (since that utterly
        # unambiguously identifies the file that we want)
        try:
            outf = self._diskpool.openForAdd(component, source, filename)
        except AlreadyInPool:
            pass
        else:
            self.debug("Adding %s %s/%s from library" %
                       (component, source, filename))
            inf = self._library.getFileByAlias(alias)
            while True:
                s = inf.read(4096)
                if s:
                    outf.write(s)
                else:
                    break
            outf.close()
            inf.close()

    def publish(self, records, isSource = True):
        """records should be an iterable of indexables which provide the
        following attributes:

               packagepublishing : {Source,}PackagePublishing record
                libraryfilealias : LibraryFileAlias.id
        libraryfilealiasfilename : LibraryFileAlias.filename
               sourcepackagename : SourcePackageName.name
                   componentname : Component.name
        """

        for pubrec in records:
            source = pubrec.sourcepackagename.encode('utf-8')
            component = pubrec.componentname.encode('utf-8')
            filename = pubrec.libraryfilealiasfilename.encode('utf-8')
            self._publish( source, component, filename,
                           pubrec.libraryfilealias )
            if isSource:
                if pubrec.sourcepackagepublishing.status == \
                   PackagePublishingStatus.PENDING:
                    pubrec.sourcepackagepublishing.status = \
                        PackagePublishingStatus.PUBLISHED
                    pubrec.sourcepackagepublishing.datepublished = nowUTC
            else:
                if pubrec.binarypackagepublishing.status == \
                   PackagePublishingStatus.PENDING:
                    pubrec.binarypackagepublishing.status = \
                        PackagePublishingStatus.PUBLISHED
                    pubrec.binarypackagepublishing.datepublished = nowUTC

    def publishOverrides(self, sourceoverrides, binaryoverrides, \
                         defaultcomponent = "main"):
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
            self.debug("Recording priority %d with name %s", p, prio[p])

        for so in sourceoverrides:
            distrorelease = so.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[so.pocket]
            component = so.componentname.encode('utf-8')
            section = so.sectionname.encode('utf-8')
            sourcepackagename = so.sourcepackagename.encode('utf-8')
            if component != defaultcomponent:
                section = "%s/%s" % (component,section)
            overrides.setdefault(distrorelease, {})
            overrides[distrorelease].setdefault(component, {})
            overrides[distrorelease][component].setdefault('src', [])
            overrides[distrorelease][component]['src'].append( (sourcepackagename,section) )

        for bo in binaryoverrides:
            distrorelease = bo.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[bo.pocket]
            component = bo.componentname.encode('utf-8')
            section = bo.sectionname.encode('utf-8')
            binarypackagename = bo.binarypackagename.encode('utf-8')
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
            self.debug("Generating overrides for %s..." % distrorelease)
            for component in overrides[distrorelease]:
                di_overrides = []
                f = open("%s/override.%s.%s" % (self._config.overrideroot,
                                                distrorelease, component), "w")
                for tup in overrides[distrorelease][component]['bin']:
                    if tup[2].endswith("debian-installer"):
                        # Note in _di_release_components that this
                        # distrorelease has d-i contents in this component.
                        self._di_release_components.setdefault(distrorelease,
                                                Set()).add(component)
                        # And record the tuple for later output in the d-i
                        # override file instead
                        di_overrides.append(tup)
                    else:
                        f.write("\t".join(tup))
                        f.write("\n")
                f.close()

                if len(di_overrides):
                    # We managed to find some d-i bits in these binaries,
                    # so we output a magical "component"-ish "section"-y sort
                    # of thing.
                    # Elmo informs me that the technical term for the d-i stuff
                    # is "horrible f***ing bodge"
                    f = open("%s/override.%s.%s.debian-installer" % (
                        self._config.overrideroot, distrorelease, component),
                             "w")
                    for tup in di_overrides:
                        f.write("\t".join(tup))
                        f.write("\n")
                    f.close()
                    
                f = open("%s/override.%s.%s.src" % (self._config.overrideroot,
                                                    distrorelease,
                                                    component), "w")
                for tup in overrides[distrorelease][component]['src']:
                    f.write("\t".join(tup))
                    f.write("\n")
                f.close()
                
    def publishFileLists(self, sourcefiles, binaryfiles):
        """Collate the set of source files and binary files provided and
        write out all the file list files for them.

        listroot/distrorelease_component_source
        listroot/distrorelease_component_binary-archname
        """
        filelist = {}
        self.debug("Collating lists of source files...")
        for f in sourcefiles:
            distrorelease = f.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[f.pocket]
            component = f.componentname.encode('utf-8')
            sourcepackagename = f.sourcepackagename.encode('utf-8')
            filename = f.libraryfilealiasfilename.encode('utf-8')
            ondiskname = self._pathfor(component,sourcepackagename,filename)

            filelist.setdefault(distrorelease, {})
            filelist[distrorelease].setdefault(component,{})
            filelist[distrorelease][component].setdefault('source',[])
            filelist[distrorelease][component]['source'].append(ondiskname)

        self.debug("Collating lists of binary files...")
        for f in binaryfiles:
            distrorelease = f.distroreleasename.encode('utf-8')
            distrorelease += pocketsuffix[f.pocket]
            component = f.componentname.encode('utf-8')
            sourcepackagename = f.sourcepackagename.encode('utf-8')
            filename = f.libraryfilealiasfilename.encode('utf-8')
            architecturetag = f.architecturetag.encode('utf-8')
            architecturetag = "binary-%s" % architecturetag
            
            ondiskname = self._pathfor(component,sourcepackagename,filename)

            filelist.setdefault(distrorelease, {})
            filelist[distrorelease].setdefault(component,{})
            filelist[distrorelease][component].setdefault(architecturetag,[])
            filelist[distrorelease][component][architecturetag].append(ondiskname)

        # Now write them out...
        for distrorelease, components in filelist.items():
            self.debug("Writing file lists for %s" % distrorelease)
            for component, architectures in components.items():
                for architecture, file_names in architectures.items():
                    di_files = []
                    f = open("%s/%s_%s_%s" % (self._config.overrideroot,
                                              distrorelease, component,
                                              architecture), "w")
                    for name in file_names:
                        if name.endswith(".udeb"):
                            # Once again, note that this componentonent in this
                            # distrorelease has d-i elements
                            self._di_release_components.setdefault(
                                distrorelease, Set()).add(component)
                            # And note the name for output later
                            di_files.append(name)
                        else:
                            f.write("%s\n" % name)
                    f.close()
                    if len(di_files):
                        # Once again, some d-i stuff to write out...
                        self.debug("Writing d-i file list for %s/%s/%s" % (
                            distrorelease, component, architecture))
                        f = open("%s/%s_%s_debian-installer_%s" % (
                            self._config.overrideroot, distrorelease,
                            component, architecture), "w")
                        f.write("\n".join(di_files))
                        f.write("\n")
                        f.close()
    

    def generateAptFTPConfig(self):
        """Generate an APT FTPArchive configuration from the provided
        config object and the paths we either know or have given to us"""
        cnf = StringIO()
        cnf.write("""
Dir
{
  ArchiveDir "%s";
  OverrideDir "%s";
  CacheDir "%s";
};
  
Default
{
  Packages::Compress ". gzip";
  Sources::Compress "gzip";
  Contents::Compress "gzip";
  DeLinkLimit 0;
  MaxContentsChange 12000;
  FileMode 0644;
}

TreeDefault
{
   Contents::Header "%s/contents.header";
};

        
        """ % (
        self._config.archiveroot,
        self._config.overrideroot,
        self._config.cacheroot,
        self._config.miscroot
        ))

        stanza_template = """
tree "dists/%(DISTRORELEASEONDISK)s"
{
  FileList "%(LISTPATH)s/%(DISTRORELEASEBYFILE)s_$(SECTION)_binary-$(ARCH)";
  SourceFileList "%(LISTPATH)s/%(DISTRORELEASE)s_$(SECTION)_source";
  Sections "%(SECTIONS)s";
  Architectures "%(ARCHITECTURES)s";
  BinOverride "override.%(DISTRORELEASE)s.$(SECTION)";
  SrcOverride "override.%(DISTRORELEASE)s.$(SECTION).src";
  Packages::Extensions "%(EXTENSIONS)s";
  BinCacheDB "packages-%(CACHEINSERT)s$(ARCH).db";
  Contents " ";
}

"""
        # cnf now contains a basic header. Add a dists entry for each
        # of the distroreleases
        for dr in self._config.distroReleaseNames():
            for pocket in pocketsuffix:
                oarchs = self._config.archTagsForRelease(dr)
                ocomps = self._config.componentsForRelease(dr)
                # Firstly, pare comps down to the ones we've output
                comps = []
                for comp in ocomps:
                    if os.path.exists(os.path.join(
                        self._config.overrideroot,
                        "_".join([dr + pocketsuffix[pocket],
                                 comp, "source"]))):
                        comps.append(comp)
                if len(comps) == 0:
                    self.debug("Did not find any components to create config "
                               "for %s%s" % (dr, pocketsuffix[pocket]))
                    continue
                # Second up, pare archs down as appropriate
                archs = []
                for arch in oarchs:
                    if os.path.exists(os.path.join(
                        self._config.overrideroot,
                        "_".join([dr + pocketsuffix[pocket],
                                 comps[0],
                                 "binary-"+arch]))):
                        archs.append(arch)
                if len(archs) == 0:
                    self.debug("Didn't find any archs to include in config "
                               "for %s%s" % (dr, pocketsuffix[pocket]))
                    continue
                self.debug("Generating apt config for %s%s" % (
                    dr, pocketsuffix[pocket]))
                # Replace those tokens

                cnf.write(stanza_template % {
                    "LISTPATH": self._config.overrideroot,
                    "DISTRORELEASE": dr + pocketsuffix[pocket],
                    "DISTRORELEASEBYFILE": dr + pocketsuffix[pocket],
                    "DISTRORELEASEONDISK": dr + pocketsuffix[pocket],
                    "ARCHITECTURES": " ".join(archs),
                    "SECTIONS": " ".join(comps),
                    "EXTENSIONS": ".deb",
                    "CACHEINSERT": ""
                    })
                dr_full_name = dr + pocketsuffix[pocket]
                if dr_full_name in self._di_release_components:
                    for component in self._di_release_components[dr_full_name]:
                        cnf.write(stanza_template % {
                            "LISTPATH": self._config.overrideroot,
                            "DISTRORELEASEONDISK": "%s%s/%s" % (dr,
                                                          pocketsuffix[pocket],
                                                          component),
                            "DISTRORELEASEBYFILE": "%s%s_%s" % (dr,
                                                          pocketsuffix[pocket],
                                                          component),
                            "DISTRORELEASE": "%s%s.%s" % (dr,
                                                          pocketsuffix[pocket],
                                                          component),
                            "ARCHITECTURES": " ".join(archs),
                            "SECTIONS": "debian-installer",
                            "EXTENSIONS": ".udeb",
                            "CACHEINSERT": "debian-installer-"
                            })

                def safe_mkdir(path):
                    if not os.path.exists(path):
                        os.makedirs(path)

                
                for comp in comps:
                    component_path = os.path.join(self._config.distsroot,
                                                  dr+pocketsuffix[pocket],
                                                  comp)
                    base_paths = [component_path]
                    if dr_full_name in self._di_release_components:
                        if comp in self._di_release_components[dr_full_name]:
                            base_paths.append(os.path.join(component_path,
                                                           "debian-installer"))
                    for base_path in base_paths:
                        if "debian-installer" not in base_path:
                            safe_mkdir(os.path.join(base_path, "source"))
                        for arch in archs:
                            safe_mkdir(os.path.join(base_path, "binary-"+arch))
        # And now return that string.
        s = cnf.getvalue()
        cnf.close()

        return s

    def unpublishDeathRow(self, condemnedsources, condemnedbinaries,
                          livesources, livebinaries):
        """Take the list of publishing records provided and unpublish them.
        You should only pass in entries you want to be unpublished because
        this will result in the files being removed if they're not otherwise
        in use"""
        livefiles = Set()
        condemnedfiles = Set()
        details = {}
        
        for p in livesources:
            fn = p.libraryfilealiasfilename.encode('utf-8')
            sn = p.sourcepackagename.encode('utf-8')
            cn = p.componentname.encode('utf-8')
            filename = self._pathfor(cn, sn, fn)
            details.setdefault(filename,[cn,sn,fn])
            livefiles.add(filename)
        for p in livebinaries:
            fn = p.libraryfilealiasfilename.encode('utf-8')
            sn = p.sourcepackagename.encode('utf-8')
            cn = p.componentname.encode('utf-8')
            filename = self._pathfor(cn, sn, fn)
            details.setdefault(filename,[cn,sn,fn])
            livefiles.add(filename)

        for p in condemnedsources:
            fn = p.libraryfilealiasfilename.encode('utf-8')
            sn = p.sourcepackagename.encode('utf-8')
            cn = p.componentname.encode('utf-8')
            filename = self._pathfor(cn, sn, fn)
            details.setdefault(filename,[cn,sn,fn])
            condemnedfiles.add(filename)

        for p in condemnedbinaries:
            fn = p.libraryfilealiasfilename.encode('utf-8')
            sn = p.sourcepackagename.encode('utf-8')
            cn = p.componentname.encode('utf-8')
            filename = self._pathfor(cn, sn, fn)
            details.setdefault(filename,[cn,sn,fn])
            condemnedfiles.add(filename)

        for f in condemnedfiles - livefiles:
            try:
                self._diskpool.removeFile(details[f][0],
                                          details[f][1],
                                          details[f][2])
            except:
                # XXX dsilvers 2004-11-16: This depends on a logging
                # infrastructure. I need to decide on one...
                # Do something to log the failure to remove
                self.logger.logexception("Removing file generated exception")
                pass
        
