#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: f936066e-8236-4cde-8abd-01a0b7fd6a4a
"""Import source packages.

This module contains the code to take a manifest and use it to import
a source package into arch.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import shutil

import arch
import inventory
import manifest
import canonical.sourcerer.util as util
from canonical.sourcerer.lib import __path__ as lib_path


class ImporterError(Exception): pass

class Importer(object):
    """Import manager.

    This is the class that takes a manifest and imports the code into
    arch.  It's implemented as a class to wrap the library and common
    variables inside.
    """

    def __init__(self, dirname, manifest, log_parent=None, rollback=None):
        self.log = util.log.get_logger("Importer", log_parent)
        self.lib = util.library.Library(log_parent=self.log)
        self.arch_lib = util.library.Library(log_parent=self.log)
        self.dir = dirname
        self.manifest = manifest

        self.unpackManifest()
        self.runImport(rollback=rollback)

    def unpackManifest(self):
        """Unpack the manifest entries into the library."""
        for entry in self.manifest:
            path = self.findPath(entry.path)
            if path is None:
                raise ImporterError, ("Unable to find file for entry: "
                                      + entry.path)

            if entry.kind == inventory.InventoryItemKind.COPY:
                self.log.info("Moving copied tree '%s' into library",
                              entry.path)
                try:
                    root = self.lib.create(entry.path)
                    for item in os.listdir(path):
                        os.rename(os.path.join(path, item),
                                  os.path.join(root, item))
                    os.rmdir(path)
                except OSError:
                    raise ImporterError, "Unable to move copied tree"

            elif entry.kind == inventory.InventoryItemKind.TAR:
                self.log.info("Unpacking tar file '%s' into library",
                              entry.path)
                try:
                    root = self.lib.create(entry.path)
                    util.tarball.unpack(path, root)
                except util.tarball.TarballUnpackError:
                    raise ImporterError, "Unable to unpack tar file"

                if not path.startswith(self.dir):
                    os.unlink(path)

            elif entry.kind == inventory.InventoryItemKind.PATCH:
                if entry.branch:
                    branches = entry.branch.getRelations("tracked")
                else:
                    branches = []
                if len(branches):
                    # Find the parent
                    for branch in branches:
                        self.log.debug("Found tracked parent branch '%s'",
                                       branch.repository)
                        parent = manifest.entry_on_branch(branch,
                                                              self.manifest)
                        if parent:
                            break
                    else:
                        raise ImporterError, "Unable to determine parent of " \
                              "patch file"

                    self.log.info("Creating copy of '%s' parent in library",
                                  entry.path)
                    if not self.lib.contains(parent.path):
                        raise ImporterError, "Parent hasn't been placed in " \
                              "library"
                    root = self.lib.cloneFrom(self.lib, parent.path,
                                              entry.path)
                else:
                    # Apply the patch to a blank directory
                    root = self.lib.create(entry.path)

                try:
                    prune = len(entry.dirname.split("/"))
                    self.log.info("Applying patch '%s' to library with -p%d",
                                  entry.path, prune)
                    util.patch.apply(path, root, prune=prune)
                except util.patch.PatchApplyError:
                    raise ImporterError, "Unable to apply patch file"

                if not path.startswith(self.dir):
                    os.unlink(path)

    def findPath(self, path):
        """Find the item specified by path.

        Looks for the item specified by path in the directory, if it doesn't
        exist there then it looks in the library by assuming part of the
        directory specification refers to a library entry.

        Given 'foo.tar.gz/tarballs/bar.tar.gz', if 'foo.tar.gz' is unpacked
        in the library with that name and contains 'tarballs/bar.tar.gz'
        then the path to that tar file will be returned.

        Returns the on-disk path of the item or None if the item could
        not be found.
        """
        if os.path.exists(os.path.join(self.dir, path)):
            return os.path.join(self.dir, path)

        dirname = os.path.dirname(path)
        path = os.path.basename(path)
        while len(dirname):
            if self.lib.contains(dirname):
                libpath = self.lib.getPath(dirname)
                if os.path.exists(os.path.join(libpath, path)):
                    return os.path.join(libpath, path)
                else:
                    return None
            else:
                path = os.path.join(os.path.basename(dirname), path)
                dirname = os.path.dirname(dirname)

        return None

    def runImport(self, rollback=None):
        """Run the import, placing the code into arch."""
        for entry in self.manifest:
            if entry.branch is None:
                continue

            # Locate the item in the library and create an entry in the
            # arch library for it
            root = self.lib.getPath(entry.path)
            arch_root = self.arch_lib.create(entry.path)

            # See if there are parents of this branch
            parents = entry.branch.getRelations("tracked")
            do_import = False

            # Get the working tree, creating the archive or tag if we need to
            arch_ver = arch.Version(entry.branch.repository)
            if rollback is not None:
                self.log.info("Rolling back local changes to '%s'", arch_ver)
                rollback(arch_ver)
            if arch_ver.exists():
                self.log.info("Getting arch tree for '%s'", arch_ver)
                os.rmdir(arch_root) # Naughty!
                tree = arch.get(arch_ver, arch_root)
            elif len(parents):
                self.log.info("Tagging '%s' to create new arch tree for '%s'",
                              parents[0].repository, arch_ver)
                arch.make_continuation(parents[0].repository, arch_ver)
                os.rmdir(arch_root) # Naughty!
                tree = arch.get(arch_ver, arch_root)
                tla_naming_reset(tree)
            else:
                self.log.info("Creating new arch tree for '%s'", arch_ver)
                do_import = True
                arch_ver.setup()
                tree = arch.init_tree(arch_root, arch_ver, nested=True)
                tla_naming_reset(tree)

            # Merge changes from parents, it doesn't matter if these
            # don't work too much as the local changes will include
            # them if all else fails
            for parent in parents:
                try:
                    tree.star_merge(parent.repository)

                    if do_import or tree.has_changes():
                        log = tree.log_message()
                        log["Summary"] = "merge from %s" % parent.repository
                        log.description = tree.log_for_merge()
                        if do_import:
                            tree.import_(log)
                            do_import = False
                        else:
                            tree.commit(log)
                except arch.util.ExecProblem:
                    self.log.warning("Merge failed from '%s'",
                                     parent.repository, exc_info=True)
                    tree.undo(throw_away=True)

            # Copy local changes and commit
            self.copyChanges(root, tree)
            if do_import or tree.has_changes():
                log = tree.log_message()
                log["Summary"] = "updated from %s" \
                                 % os.path.basename(entry.path)
                log.description = tree.log_for_merge()
                if do_import:
                    tree.import_(log)
                else:
                    tree.commit(log)

    def fileDelete(self, tree, filename):
        """Perform deletion of a file."""
        self.log.debug("Deleting '%s'", filename)
        tree.delete(filename)

    def fileMove(self, tree, srcfile, dstfile):
        """Perform move of a file."""
        self.log.debug("Moving '%s' to '%s'", srcfile, dstfile)
        tree.move_tag(srcfile, dstfile)

        srcpath = os.path.join(tree.realpath(), srcfile)
        dstpath = os.path.join(tree.realpath(), dstfile)
        os.rename(srcpath, dstpath)

    def fileUpdate(self, tree, root, filename):
        """Perform update of a file."""
        self.log.debug("Updating '%s'", filename)
        srcpath = os.path.join(root, filename)
        dstpath = os.path.join(tree.realpath(), filename)

        os.unlink(dstpath)
        if os.path.islink(srcpath):
            linkdest = os.readlink(srcpath)
            os.symlink(linkdest, dstpath)
        else:
            shutil.copy2(srcpath, dstpath)

    def fileAdd(self, tree, root, filename, exclude):
        """Perform add of a file."""
        parentdir = os.path.basename(os.path.dirname(filename))
        if parentdir == "{arch}" and os.path.basename(filename)[:1] in "+,.":
            # Special file in the {arch} directory, we already have
            # these so don't want to add them
            exclude.append(filename)
            return

        # Check this isn't under a directory we excluded above
        for baddir in exclude:
            if filename.startswith(baddir):
                return

        self.log.debug("Adding '%s'", filename)
        srcpath = os.path.join(root, filename)
        dstpath = os.path.join(tree.realpath(), filename)
        if os.path.isdir(srcpath):
            if not os.path.isdir(dstpath):
                os.mkdir(dstpath)
        elif os.path.islink(srcpath):
            linkdest = os.readlink(srcpath)
            os.symlink(linkdest, dstpath)
        else:
            shutil.copy2(srcpath, dstpath)

        if not tree.get_tag(filename) and parentdir != ".arch-ids":
            # Note that get_tag returns something for stuff under {arch}
            tree.add_tag(filename)

    def copyChanges(self, root, tree):
        """Copy changes from the path given to the arch working tree."""
        architer = tree.iter_inventory(source=True, both=True)
        archsums = util.dirsums.calculate_from(tree.realpath(), architer)

        sums = util.dirsums.calculate(root)
        (changed, new, gone, moved) = util.dirsums.diff(archsums, sums)

        for filename in changed:
            self.fileUpdate(tree, root, filename)

        for filename in gone:
            # Process any affected moved
            for srcfile, dstfile in moved:
                if srcfile.startswith(filename + "/"):
                    self.fileMove(tree, srcfile, dstfile)

            self.fileDelete(tree, filename)

        exclude = []
        for filename in new:
            self.fileAdd(tree, root, filename, exclude)

        for srcfile, dstfile in moved:
            if os.path.islink(srcfile) or os.path.exists(srcfile):
                self.fileMove(tree, srcfile, dstfile)


def tla_naming_reset(path):
    """Set tla naming conventions to something a little more sensible."""
    our_tagging_method = os.path.join(lib_path[0], "tagging-method.in")
    tagging_method = os.path.join(path, "{arch}", "=tagging-method")
    shutil.copy2(our_tagging_method, tagging_method)
