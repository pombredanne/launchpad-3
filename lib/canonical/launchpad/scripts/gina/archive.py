# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Archive pool classes.

This module has the classes resposable for locate and extract the package
information from an archive pool.
"""

__all__ = ['ArchiveFilesystemInfo', 'ArchiveComponentItems', 'PackagesMap']

import apt_pkg, tempfile, os
from string import split


class ArchiveFilesystemInfo:
    """Archive information files holder

 
    This class gets and holds the Packages.gz and Source.gz files
    from a Package Archive and holds them as internal attributes
    to be used for other classes.
    """

    def __init__(self, root, distrorelease, component, arch):

        # Holds the distribution informations
        self.distrorelease = distrorelease
        self.component = component
        self.arch = arch

        # Search and get the files with full path
        sources_zipped = os.path.join(root, "dists", distrorelease,
                                      component, "source", "Sources.gz")
        binaries_zipped = os.path.join(root, "dists", distrorelease,
                                       component, "binary-%s" % arch,
                                       "Packages.gz")
        di_zipped = os.path.join(root, "dists", distrorelease, component,
                                 "debian-installer", "binary-%s" % arch,
                                 "Packages.gz")
        

        # Extract the files
        srcfd, sources_tagfile = tempfile.mkstemp()
        os.system("gzip -dc %s > %s" % (sources_zipped, sources_tagfile))
        srcfile = os.fdopen(srcfd)
        
        binfd, binaries_tagfile = tempfile.mkstemp()
        os.system("gzip -dc %s > %s" % (binaries_zipped, binaries_tagfile))
        binfile = os.fdopen(binfd)
    
        difd, di_tagfile = tempfile.mkstemp()
        os.system("gzip -dc %s > %s" % (di_zipped, di_tagfile))
        difile = os.fdopen(difd)

        # Holds the opened files and its names.
        self.sources_tagfile = sources_tagfile
        self.srcfile = srcfile
        self.binaries_tagfile = binaries_tagfile
        self.binfile = binfile
        self.di_tagfile = di_tagfile
        self.difile = difile
        

class ArchiveComponentItems:
    """Package Archive Items holder

    This class holds ArchiveFilesystemInfo instances
    for each architecture/component pair that will be imported
    """
    def __init__(self, package_root, distrorelease, components, archs):

        # Runs through architectures.
        archive_archs = []
        for arch in archs:
            # Runs through components.
            for component in components:
                # Create the ArchiveFilesystemInfo instance.
                archive_info = ArchiveFilesystemInfo(package_root,
                                                     distrorelease,
                                                     component, arch)
                # Hold it in a list.
                archive_archs.append(archive_info)

        self._archive_archs = archive_archs

    def __iter__(self):
        # Iterate over the ArchiveFilesystemInfo instances.
        return iter(self._archive_archs)


class PackagesMap:
    """Archive Package Map class

    This class goes through the archive files held by an
    ArchComponentItems instance and create maps for sources
    and binary packages.  These are stored in the src_map and bin_map
    attributes.
    
    The sources map is a dict where the sourcepackage name is the key and a
    dict with some other package information (Version, Maintainer, etc) is
    the value.
    
    The binary is also a dict but has the architecturetag as the keys, and
    the values are a dict that holds the same information as on source map.
    """
    def __init__(self, arch_component_items):

        # Create the maps
        self.src_map = {}
        self.bin_map = {}

        # Create an orphan map to track binarypackages with no source
        # package.
        self.orphans ={}

        # Iterate over ArchComponentItems instance to cover
        # all components in all architectures.
        for info_set in arch_component_items:
            # Create a tmp map for binaries for one arch/component pair
            if self.bin_map.has_key(info_set.arch):
                tmpbin_map = self.bin_map[info_set.arch]
            else:
                tmpbin_map = {}           
            # Get a apt_pkg handler for the binaries
            binaries = apt_pkg.ParseTagFile(info_set.binfile)

            # Run over the handler and store info in tmp_bin_map.
            while binaries.Step():
                bin_tmp = dict(binaries.Section)
                # Add in the dict the component
                bin_tmp['Component']=info_set.component
                bin_name = bin_tmp['Package']
                tmpbin_map[bin_name] = bin_tmp


            # Get a apt_pkg handler for the debian installer binaries
            dibinaries = apt_pkg.ParseTagFile(info_set.binfile)
            
            # Run over the handler and store info in tmp_bin_map.
            while dibinaries.Step():
                dibin_tmp = dict(dibinaries.Section)
                dibin_tmp['Component']=info_set.component
                dibin_name = dibin_tmp['Package']
                tmpbin_map[bin_name] = dibin_tmp

            # Get a apt_pkg handler for the sources
            sources = apt_pkg.ParseTagFile(info_set.srcfile)

            # Run over the handler and store info in src_map
            # We make just one source map because most of then are the same
            # for all architectures, but we go over it to cover also source
            # packages that only compiles for one architecture.
            while sources.Step():
                src_tmp = dict(sources.Section)
                src_tmp['Component']=info_set.component
                src_name = src_tmp['Package']

                # Check if the is a binary with the same package name.
                if src_name in tmpbin_map.keys():
                    # If so, grabe the binary description for this source.
                    description = tmpbin_map[src_name]['Description']
                    src_tmp['Description'] = description
                    # Also, store on the binary a reference for this source
                    tmpbin_map[src_name]['SourceRef'] = src_tmp

                # insert into src_map
                self.src_map[src_name] = src_tmp

            # Store the tmpbin_map in bin_map, mapped by architecture.
            self.bin_map[info_set.arch] = tmpbin_map

            # Check the binaries for this arch that does not have an
            # source on archive.
            self._checkSources(info_set.arch)

    def _checkSources(self, arch):
        """Search for binaries with no sources available"""
        orphans ={}

        # Go over the bin_map of an given arch.
        for name, pack in self.bin_map[arch].iteritems():            
            if 'SourceRef' in pack.keys():
                # If SourceRef exists it has a source related.
                continue
                
            # Check if the Key Source is available on its binary info
            elif 'Source' in pack.keys():
                # If so, Check if it is available in the archive.
                if pack['Source'] not in self.src_map.keys():
                    # if not, check if Source: is in <name> (<version>) format
                    try:
                        sname, sversion = split(pack['Source'])
                    except ValueError:
                        # If it is not, the bin package is orphan
                        orphans[name] = pack
                    else:
                        pack['Source'] = sname
                        pack['SVersion'] = sversion[1:-1]
                        if sname not in self.src_map.keys():
                            # If it is but the source name is not in src_map
                            # this bin package is orphan
                            orphans[name] = pack

        # Orphan binary packages can't be imported because it needs a build
        # and build needs a sourcepackagerelease. So, delete them.
        for name in orphans.keys():
            del self.bin_map[arch][name]

        # Store the orphans to do not lost this info.
        self.orphans[arch]=orphans
