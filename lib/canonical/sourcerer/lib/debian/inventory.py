#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 45df51c9-a8ed-4baa-b3c9-58d0295787c3
"""Debian source inventory.

This module contains a class to produce an inventory of a Debian source
package.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import tarfile

import canonical.sourcerer.deb as deb
import canonical.sourcerer.lib as lib
import canonical.sourcerer.util as util


class DebianInventoryError(lib.inventory.InventoryError): pass

class DebianInventory(lib.inventory.Inventory):
    """Contents of a Debian source package.
    """

    def __init__(self, dsc_filename=None, log_parent=None):
        super(DebianInventory, self).__init__()
        self.log = util.log.get_logger("DebianInventory", log_parent)
        self.lib = util.library.Library(log_parent=self.log)

        if dsc_filename is not None:
            self.open(dsc_filename)

    def open(self, dsc_filename):
        """Open and examine a Debian source control (dsc) file.

        Parses the source control (dsc) filename given and examines the
        companion tar file and diff file (if any) appending interesting
        things found to the inventory.
        """
        self.log.info("Examining '%s'", dsc_filename)
        dirname = os.path.dirname(dsc_filename)
        s = deb.source.SourceControl(dsc_filename)
        self.package = s.source
        self.version = s.version
        self.log.debug("%s %s", self.package, self.version)

        # Get the inventory of the tar file
        tar_debian = lib.inventory.InventoryItem()
        tar_filename = os.path.join(dirname, s.tar.name)
        tar_inventory = self.examineTarfile(tar_filename, s.tar.name,
                                            debian=tar_debian)

        if s.diff is not None:
            # Get the inventory of the diff file
            diff_debian = lib.inventory.InventoryItem()
            diff_filename = os.path.join(dirname, s.diff.name)
            diff_inventory = self.examinePatch(diff_filename, s.diff.name,
                                               apply_path=s.tar.name,
                                               debian=diff_debian)

            # Suggest an "orig" branch name
            if len(tar_inventory):
                tar_inventory[0].branch = "orig"

            # Suggest a "debian" branch name for its content
            if len(diff_inventory) and len(tar_inventory) \
                   and not diff_inventory[0].virtual:
                diff_inventory[0].branch = "debian"
                diff_inventory[0].branch_of = tar_inventory[0]

            # Suggest branch names and relationships for debian directories
            if diff_debian.kind is not None:
                diff_debian.branch = "debian-dir"
                if tar_debian.kind is not None:
                    tar_debian.branch = "orig-debian-dir"
                    diff_debian.branch_of = tar_debian
                else:
                    diff_debian.branch_of = None

            self.extend(tar_inventory)
            self.extend(diff_inventory)

        elif tar_debian.kind is not None:
            # Don't treat the debian directory specially if its a native
            # package with no debian revision
            if self.version.revision is None \
               and len(tar_inventory) and tar_inventory[0] != tar_debian:
                tar_inventory.remove(tar_debian)
            else:
                # Suggest branch name for the debian directory
                tar_debian.branch = "debian-dir"

            self.extend(tar_inventory)

        else:
            self.extend(tar_inventory)

    def examineTarfile(self, tar_filename, tar_name, debian=None):
        """Examine a tar file."""
        self.log.info("Examining tar file '%s'", tar_name)
        try:
            tar = tarfile.open(tar_filename, "r")
        except IOError:
            raise DebianInventoryError, "Missing tar file"
        except tarfile.ReadError:
            raise DebianInventoryError, "Empty or possibly corrupt tar file"

        # Identify the common prefix and directory name of the tarball
        prefix = os.path.commonprefix(tar.getnames())
        if not prefix.endswith("/"):
            prefix = os.path.dirname(prefix) + "/"
        prefix_w = prefix.split("/")
        dirname = prefix_w[0] + "/"
        tar_dirname = dirname

        # Debian-only tarballs should be non-existant, but some bugger's going
        # to try it one day.
        item = lib.inventory.InventoryItem()
        if debian is not None:
            if "debian" in prefix_w:
                self.log.debug("Entire tar file within debian directory")
                item = debian
                dirname = "/".join(prefix_w[:prefix_w.index("debian")+1]) + "/"

        # First item in our inventory is the tarball itself
        i = lib.inventory.Inventory()
        item.kind = lib.inventory.InventoryItemKind.TAR
        item.path = tar_name
        item.prefix = prefix
        item.dirname = dirname
        item.virtual = True
        i.append(item)

        # Unpack it
        try:
            tar_root = self.lib.create(tar_name)
            self.log.info("Unpacking tar file into library")
            util.tarball.unpack(tar_filename, tar_root)
        except util.tarball.TarballUnpackError:
            raise DebianInventoryError, "Unable to unpack tar file"

        # Now iterate the contents
        dirs = []
        content = [ (finfo.name, finfo) for finfo in tar ]
        content.sort()
        content = [ s[-1] for s in content ]
        for finfo in content:
            if len(finfo.name) <= len(item.dirname): continue
            fname = finfo.name[len(item.dirname):]
            fpath = os.path.join(item.path, fname)

            if finfo.isdir():
                # Check for a debian directory and single it out if we need to
                if debian is not None and debian.kind is None:
                    fname_w = fname.split("/")
                    if fname_w[0] == "debian":
                        self.log.debug("Found debian directory")
                        debian.kind = lib.inventory.InventoryItemKind.COPY
                        debian.path = fpath
                        i.append(debian)
                    else:
                        dirs.append(fpath)
                else:
                    dirs.append(fpath)

            elif finfo.isfile():
                # Check for known special file types
                try:
                    fkind = util.path.format(fname)
                    flocal = os.path.join(tar_root,
                                          finfo.name[len(tar_dirname):])

                    if fkind == lib.inventory.InventoryItemKind.TAR:
                        i.extend(self.examineTarfile(flocal, fpath))
                    elif fkind == lib.inventory.InventoryItemKind.PATCH:
                        i.extend(self.examinePatch(flocal, fpath))
                    else:
                        item.virtual = False
                except DebianInventoryError:
                    self.log.warning("Couldn't read '%s' from inside '%s'",
                                     fname, item.path, exc_info=True)
                    item.virtual = False

            else:
                item.virtual = False

        # dirs need to be created if virtual
        if item.virtual:
            ptr = 1
            for dirpath in dirs:
                ditem = lib.inventory.InventoryItem()
                ditem.kind = lib.inventory.InventoryItemKind.DIR
                ditem.path = dirpath
                i.insert(ptr, ditem)
                ptr += 1

        tar.close()
        return i

    def examinePatch(self, patch_filename, patch_name,
                     apply_path=None, debian=None):
        """Examine a patch file."""
        self.log.info("Examining patch file '%s'", patch_name)
        try:
            patch = util.patch.PatchFile(patch_filename)
        except IOError:
            raise DebianInventoryError, "Missing patch file"
        if not len(patch.patched):
            raise DebianInventoryError, "Empty or possibly corrupt patch file"

        # Identify the common prefix and directory name of the patch
        prefix = os.path.commonprefix(patch.patched)
        if not prefix.endswith("/"):
            prefix = os.path.dirname(prefix) + "/"
        srcprefix = os.path.commonprefix(patch.patchsrc)
        if not srcprefix.endswith("/"):
            srcprefix = os.path.dirname(prefix) + "/"
        prefix_w = prefix.split("/")
        dirname = prefix_w[0] + "/"
        patch_dirname = dirname

        # Debian-only patches are sweeeeeeet
        item = lib.inventory.InventoryItem()
        if debian is not None:
            if "debian" in prefix_w:
                self.log.debug("Entire patch file within debian directory")
                item = debian
                dirname = "/".join(prefix_w[:prefix_w.index("debian")+1]) + "/"

        # First item in our inventory is the patch itself
        i = lib.inventory.Inventory()
        item.kind = lib.inventory.InventoryItemKind.PATCH
        item.path = patch_name
        item.prefix = prefix
        item.srcprefix = srcprefix
        item.dirname = dirname
        item.virtual = True
        i.append(item)

        # Apply the patch to a copy of the source it belongs to
        if apply_path is not None:
            try:
                patch_root = self.lib.cloneFrom(self.lib, apply_path,
                                                patch_name)
                self.log.info("Applying patch file to library")
                util.patch.apply(patch_filename, patch_root)
            except util.patch.PatchApplyError:
                raise DebianInventoryError, "Unable to apply patch file"

        # Now iterate the contents
        patch.patched.sort()
        for finfo in patch.patched:
            if len(finfo) <= len(item.dirname): continue
            fname = finfo[len(item.dirname):]
            fpath = os.path.join(item.path, fname)

            fkind = util.path.format(fname)
            if fkind == lib.inventory.InventoryItemKind.PATCH:
                if apply_path is not None:
                    try:
                        flocal = os.path.join(patch_root,
                                              finfo[len(patch_dirname):])
                        i.extend(self.examinePatch(flocal, fpath))
                    except DebianInventoryError:
                        self.log.warning("Couldn't read '%s' from inside '%s'",
                                         fname, item.path, exc_info=True)
                        item.virtual = False
                else:
                    # Special file but we can't examine it
                    fitem = lib.inventory.InventoryItem()
                    fitem.kind = fkind
                    fitem.path = fpath
                    i.append(fitem)

            else:
                # Check if this non-patch file is inside a debian directory,
                # if so create the special debian item
                if debian is not None and debian.kind is None:
                    fname_w = fname.split("/")
                    if fname_w[0] == "debian":
                        self.log.debug("Found file within debian directory")
                        debian.kind = lib.inventory.InventoryItemKind.COPY
                        debian.path = os.path.join(item.path, "debian/")
                        i.insert(1, debian)
                    else:
                        item.virtual = False
                else:
                    item.virtual = False

        return i
