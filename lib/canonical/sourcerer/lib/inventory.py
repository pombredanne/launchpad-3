#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 60a73e8b-81cb-478b-8a07-c3a912672e57
"""Manage inventories.

This modules contains utility classes and functions to aid cataloguing
the inventory of source packages.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os

import canonical.sourcerer.util as util


class InventoryError(Exception): pass

class InventoryItemKind(object):
    """Kinds of inventory item.

    Constants:
      DIR       Directory to be created
      COPY      Copy of a tree
      TAR       Tar file
      PATCH     Patch file

    Note that the definitions of TAR and PATCH deliberately match those
    in util.path.FileFormat.
    """

    DIR    = "DIR"
    COPY   = "COPY"
    TAR    = util.path.FileFormat.TAR
    PATCH  = util.path.FileFormat.PATCH

class Inventory(list):
    """Contents of a source package.

    This class is an iterable list of InventoryItem objects representing
    the inventory of a particular source package.

    Properties:
      package   Name of the source package
      version   Version of the source package
    """

    def __init__(self):
        self.package = None
        self.version = None

class InventoryItem(object):
    """Item in the inventory of a source package.

    This class contains information about a single item in an Inventory.

    Properties:
      kind       Kind of item (InventoryItemKind constant)
      path       Path of item, may be underneath the path of another item
      prefix     Common path prefix of items within this one
      srcprefix  Alternate (original) path prefix of items within this one
      dirname    First component of directory name
      virtual    True if this only contains other InventoryItem objects
      branch     Suggested branch name for this item
      branch_of  Suggested parent branch of this item.
      product    Product name (if known)
    """

    def __init__(self):
        self.kind = None
        self.path = None
        self.prefix = None
        self.srcprefix = None
        self.dirname = None
        self.virtual = False
        self.branch = None
        self.branch_of = None
        self.product = None # FIXME: hacky


def find_parent(patch, inventory):
    """Match an orphaned patch to a possible parent.

    This function uses the common prefix of the files a patch patches
    to match against information about possible parent branches.  If
    a possible match is found the branch_of field of the patch is set
    and True is returned.
    """
    parents = {}
    prefixes = []
    for item in inventory:
        if item.virtual or (item.kind != InventoryItemKind.TAR
                            and item.kind != InventoryItemKind.COPY):
            continue

        # Mine this item for prefix ideas
        ideas = []
        ideas.append(os.path.basename(item.path))
        if item.prefix is not None:
            ideas.append(item.prefix)
        if item.product is not None:
            ideas.append(item.product + "/")

        for idea in ideas:
            idea = util.path.generalise_path(idea)
            if idea not in parents:
                parents[idea] = item
                prefixes.append((len(idea), idea))

    # Sort the prefix ideas
    prefixes.sort()
    prefixes.reverse()

    # Now attempt to match against the patches
    for p_len, prefix in prefixes:
        for tryprefix in (patch.prefix, patch.srcprefix):
            if tryprefix is None:
                continue

            iprefix_w = util.path.generalise_path(tryprefix).split("/")
            for w in range(0, len(iprefix_w)):
                iprefix = "/".join(iprefix_w[w:])
                if iprefix.startswith(prefix):
                    if w > 0:
                        patch.dirname = "/".join(iprefix_w[:w]) + "/" + prefix
                    else:
                        patch.dirname = prefix
                    patch.branch_of = parents[prefix]
                    return True

    return False
