# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Archive pool classes.

This module has the classes resposable for locate and extract the package
information from an archive pool.
"""

__metaclass__ = type

__all__ = [
    'ArchiveFilesystemInfo',
    'ArchiveComponentItems',
    'MangledArchiveError',
    'PackagesMap',
    ]

from collections import defaultdict
import os
import shutil
import tempfile

import apt_pkg

from lp.services.scripts import log
from lp.soyuz.scripts.gina import call


class MangledArchiveError(Exception):
    """Raised when the archive is found to be grossly incomplete"""


class NoBinaryArchive(Exception):
    """Raised when the archive is found to be grossly incomplete"""


class ArchiveFilesystemInfo:
    """Archive information files holder

    This class gets and holds the Packages and Sources files
    from a Package Archive and holds them as internal attributes
    to be used for other classes.
    """
    sources_tagfile = None
    srcfile = None
    binaries_tagfile = None
    binfile = None
    di_tagfile = None
    difile = None

    def __init__(self, root, distroseries, component, arch=None,
                 source_only=False):

        # Holds the distribution informations
        self.distroseries = distroseries
        self.component = component
        self.arch = arch
        self.source_only = source_only

        dist_dir = os.path.join(root, "dists", distroseries, component)
        if not os.path.exists(dist_dir):
            raise MangledArchiveError("No archive directory for %s/%s" %
                                      (distroseries, component))

        # Extract Sources index.
        sources_prefix = os.path.join(
            root, "dists", distroseries, component, "source", "Sources")
        self.srcfile, self.sources_tagfile = self.openTagFile(sources_prefix)

        # Detect source-only mode and skip binary index parsing.
        if source_only:
            return

        # Extract binary indexes.
        dist_bin_dir = os.path.join(dist_dir, "binary-%s" % arch)
        if not os.path.exists(dist_bin_dir):
            raise NoBinaryArchive

        self.binfile, self.binaries_tagfile = self.openTagFile(
            os.path.join(dist_bin_dir, "Packages"))

        try:
            self.difile, self.di_tagfile = self.openTagFile(
                os.path.join(
                    root, "dists", distroseries, component,
                    "debian-installer", "binary-%s" % arch, "Packages"))
        except MangledArchiveError:
            # d-i binary indexes may be missing.  Put something empty in
            # place so that PackagesMap doesn't need to care.
            difd, self.di_tagfile = tempfile.mkstemp()
            self.difile = os.fdopen(difd)

    def openTagFile(self, prefix):
        for suffix in (".xz", ".bz2", ".gz", ""):
            if os.path.exists(prefix + suffix):
                # Extract index.
                fd, tagfile = tempfile.mkstemp()
                if suffix == ".xz":
                    call("xz -dc %s > %s" % (prefix + suffix, tagfile))
                elif suffix == ".bz2":
                    call("bzip2 -dc %s > %s" % (prefix + suffix, tagfile))
                elif suffix == ".gz":
                    call("gzip -dc %s > %s" % (prefix + suffix, tagfile))
                elif suffix == "":
                    shutil.copy(prefix + suffix, tagfile)
                else:
                    raise AssertionError("Unknown suffix '%s'" % suffix)
                return os.fdopen(fd), tagfile
        else:
            raise MangledArchiveError(
                "Archive missing any variant of %s" % prefix)

    def cleanup(self):
        os.unlink(self.sources_tagfile)
        if self.source_only:
            return
        os.unlink(self.binaries_tagfile)
        os.unlink(self.di_tagfile)


class ArchiveComponentItems:
    """Package Archive Items holder

    This class holds ArchiveFilesystemInfo instances
    for each architecture/component pair that will be imported
    """

    def __init__(self, archive_root, distroseries, components, archs,
                 source_only=False):
        # Store ArchiveFilesystemInfo objects built in this context.
        self._archive_archs = []

        # Detect source-only mode and store only the ArchiveFilesystemInfo
        # object for the given components.
        if source_only:
            for component in components:
                self._buildArchiveFilesystemInfo(
                    archive_root, distroseries, component,
                    source_only=source_only)
            return

        # Run through components and architectures.
        for component in components:
            for arch in archs:
                self._buildArchiveFilesystemInfo(
                    archive_root, distroseries, component, arch)

    def _buildArchiveFilesystemInfo(self, archive_root, distroseries,
                                    component, arch=None, source_only=False):
        """Create and store the ArchiveFilesystemInfo objects."""
        try:
            archive_info = ArchiveFilesystemInfo(
                archive_root, distroseries, component, arch, source_only)
        except NoBinaryArchive:
            log.warn("The archive for %s/%s doesn't contain "
                     "a directory for %s, skipping" %
                     (distroseries, component, arch))
            return
        self._archive_archs.append(archive_info)

    def __iter__(self):
        # Iterate over the ArchiveFilesystemInfo instances.
        return iter(self._archive_archs)

    def cleanup(self):
        for ai in self._archive_archs:
            ai.cleanup()


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
        self.create_maps(arch_component_items)
        arch_component_items.cleanup()

    def create_maps(self, arch_component_items):
        # Create the maps
        self.src_map = defaultdict(list)
        self.bin_map = {}

        # Iterate over ArchComponentItems instance to cover
        # all components in all architectures.
        for info_set in arch_component_items:

            # Run over the source stanzas and store info in src_map. We
            # make just one source map (instead of one per architecture)
            # because most of them are the same for all architectures,
            # but we go over it to also cover source packages that only
            # compile for one architecture.
            sources = apt_pkg.TagFile(info_set.srcfile)
            for section in sources:
                try:
                    src_tmp = dict(section)
                    src_tmp['Component'] = info_set.component
                    src_name = src_tmp['Package']
                except KeyError:
                    log.exception(
                        "Invalid Sources stanza in %s",
                        info_set.sources_tagfile)
                    continue
                self.src_map[src_name].append(src_tmp)

            # Check if it's in source-only mode.  If so, skip binary index
            # mapping.
            if info_set.source_only:
                continue

            # Create a tmp map for binaries for one arch/component pair.
            self.bin_map.setdefault(info_set.arch, {})

            tmpbin_map = self.bin_map[info_set.arch]

            binaries = apt_pkg.TagFile(info_set.binfile)
            for section in binaries:
                try:
                    bin_tmp = dict(section)
                    # The component isn't listed in the tagfile.
                    bin_tmp['Component'] = info_set.component
                    bin_name = bin_tmp['Package']
                except KeyError:
                    log.exception(
                        "Invalid Releases stanza in %s",
                        info_set.binaries_tagfile)
                    continue
                tmpbin_map[bin_name] = bin_tmp

            # Run over the D-I stanzas and store info in tmp_bin_map.
            dibinaries = apt_pkg.TagFile(info_set.difile)
            for section in dibinaries:
                try:
                    dibin_tmp = dict(section)
                    dibin_tmp['Component'] = info_set.component
                    dibin_name = dibin_tmp['Package']
                except KeyError:
                    log.exception("Invalid D-I Releases stanza in %s" %
                                  info_set.difile)
                    continue
                tmpbin_map[dibin_name] = dibin_tmp
