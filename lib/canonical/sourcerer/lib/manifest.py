#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: b1c115b6-59cd-40c7-955c-bfdb82c8bc03
"""Manage manifests.

This module provides various utility classes for taking inventories
(as provided in the inventory module) and matching them with the
manifests we store in the Soyuz database, and manipulating those
manifests.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import re

import inventory
import canonical.sourcerer.util as util
import canonical.sourcerer.soyuzwrapper as soyuz


# FIXME: I still have no idea how to do this properly
ARCHIVE = "sourcerer-imports@canonical.com"


class ManifestError(Exception): pass


def matches_entry(entry, item):
    """Compare the inventory item with the manifest entry."""
    # FIXME: Is this enough?
    if entry.kind != item.kind:
        return False

    # Compare generalised paths
    epath = util.path.generalise_path(entry.path)
    while epath.endswith("/"): epath = epath[:-1]
    ipath = util.path.generalise_path(item.path)
    while ipath.endswith("/"): ipath = ipath[:-1]
    if epath != ipath:
        return False

    # Compare lengths of directory names
    # (generally indicates a layout change)
    if entry.dirname is not None and item.dirname is not None:
        entry_w = entry.dirname.split("/")
        item_w = item.dirname.split("/")
        while item_w[-1] == None or item_w[-1] == "":
            item_w = item_w[:-1]
        if len(entry_w) != len(item_w):
            return False
    elif entry.dirname != item.dirname:
        return False

    return True


def entry_on_branch(branch, manifest):
    """Find the manifest entry on the branch given."""
    for entry in manifest:
        if entry.branch is None:
            continue
        if entry.branch.repository == branch.repository:
            return entry
    else:
        return None

def move_entry(entry, manifest, new_manifest, new_path=None):
    """Move manifest entry between manifests.

    If new_path is not None then this is assigned as the new path for
    the manifest.

    Returns the entry which is the same object as passed.
    """
    manifest.remove(entry)
    if new_path is not None:
        entry.path = new_path
    new_manifest.append(entry)

    # FIXME: This doesn't handle possible changes in the version of the
    #        manifest entry.
    # FIXME: This doesn't handle children elements.
    return entry

def copy_entry(entry, manifest, new_path=None):
    """Copy the manifest entry into the new manifest.

    This creates an identical copy of the manifest entry with the same
    branch and changeset information, be careful that you don't use this
    when you really want branch_entry().

    If new_path is not None then this is assigned as the new path for
    the manifest.

    Returns the new entry object.
    """
    new_entry = manifest.createEntry()
    new_entry.seq = entry.seq
    new_entry.kind = entry.kind
    if new_path is not None:
        new_entry.path = new_path
    else:
        new_entry.path = entry.path
    new_entry.dirname = entry.dirname
    new_entry.branch = entry.branch
    new_entry.changeset = entry.changeset
#    manifest.append(new_entry)

    # FIXME: This doesn't handle children elements.
    return new_entry

def branch_entry(entry, manifest, inventory_, new_path=None):
    """Create a branch of the manifest entry in the new manifest.

    This creates a copy of the manifest entry with different branch
    information, the new branch record is created as a branch of the old
    one.

    If new_path is not None then this is assigned as the new path for
    the manifest.

    Returns the new entry object.
    """
    new_entry = copy_entry(entry, manifest, new_path=new_path)
    if new_entry.branch is not None:
        # FIXME: Probably bogus name invention (human involvement?)
        branch = entry.branch.repository.split("/", 1)[1].replace("--", "-", 1)
    else:
        # FIXME: this is purely bogus and to get around my hacky http thing
        name = os.path.basename(new_entry.path)
        name = util.path.generalise_path(name)
        branch = tla_sanitise(name)

    category = tla_sanitise(inventory_.package)
    repository = "%s/%s--%s" % (ARCHIVE, category, branch)
    new_entry.branch = soyuz.createBranch(repository)
    new_entry.changeset = None

    # FIXME: Different branch styles?
    if entry.branch is not None:
        new_entry.branch.createRelationship(entry.branch, "tracked")

    # FIXME: This doesn't handle children elements.
    return new_entry

def update_manifest(manifest, inventory_, log_parent=None):
    """Update the manifest using the inventory.

    Matches inventory items up to manifest entries retiring any manifest
    entries not in the new inventory and adding any new inventory items
    to the manifest.
    """
    old_manifest = list(manifest)
    while len(manifest):
        manifest.pop()

    log = util.log.get_logger("ManifestUpdate", log_parent)

    matched = {}
    branches = {}
    for item in inventory_:
        for entry in old_manifest:
            if matches_entry(entry, item):
                if entry in matched:
                    log.warning("Ignoring duplicate manifest match "
                                "('%s' and '%s' to '%s')",
                                matched[entry.patch], item.path, entry.path)
                    continue

                log.info("Found manifest match for '%s'", item.path)
                move_entry(entry, old_manifest, manifest, new_path=item.path)
                item.manifest = entry
                matched[entry] = item

                if item.branch is not None:
                    if item.branch in branches:
                        log.warning("Struck down duplicate branch name "
                                    "('%s' because '%s' wants '%s')",
                                    branches[item.branch].path,
                                    item.path, item.branch)

                        # FIXME: Abuse of item.kind
                        branches[item.branch].kind = "IGNORE"

                    branches[item.branch] = item
                break
        else:
            log.info("Found new item '%s'", item.path)
            if item.virtual:
                # Virtual tars and patches never need more information
                item.branch = None
                item.branch_of = None

            elif item.kind == inventory.InventoryItemKind.TAR:
                pass
                # Tarballs might be upstream releases just dropped into
                # place, if so we can steal their manifest
#                prefix = util.path.name(item.path)
#                prefix = util.path.patched_ext.sub("", prefix)
#                prefix = prefix.replace("_", "-")
#                # FIXME: Check in the File table, not UpstreamRelease?
#                urelease = soyuz.getUpstreamRelease(prefix)
#                if urelease is not None:
#                    # FIXME: Whole manifest, not first entry?
#                    log.info("Found upstream release for '%s'", item.path)
#                    item.manifest = branch_entry(urelease.getManifest()[0],
#                                                 manifest, inventory_,
#                                                 new_path=item.path)
#
#                    # Store product name to make patch matching easier
#                    item.product = urelease.product.name
#                    continue
#                else:
#                    # FIXME: Ask the user what to do?
#                    log.warning("Importing orphaned tar file '%s'", item.path)

            elif item.kind == inventory.InventoryItemKind.PATCH:
                # Try to find a parent for this patch branch
                if item.branch is None and item.branch_of is None:
                    if inventory_.find_parent(item, inventory_):
                        log.info("Found parent '%s' for patch '%s'",
                                 item.branch_of.path, item.path)
                    else:
                        # FIXME: *MUST* ask the user what to do!
                        log.warning("Ignoring orphaned patch file '%s'",
                                    item.path)
                        # FIXME: Abuse of item.kind
                        item.kind = "IGNORE"

            # Invent a name if we haven't got one
            if ( item.branch is None
                 and not item.virtual
                 and item.kind != inventory.InventoryItemKind.DIR
                 and item.kind != "IGNORE" ):
                # FIXME: almost certainly bogus
                name = os.path.basename(item.path)
                name = util.path.generalise_path(name)
                item.branch = tla_sanitise(name)
                if item.branch is None:
                    log.warning("Unable to construct branch name for '%s'",
                                item.path)
                    # FIXME: Abuse of item.kind
                    item.kind = "IGNORE"

            # Create the new manifest entry
            entry = manifest.createEntry()
            entry.kind = item.kind
            entry.path = item.path
            while entry.path.endswith("/"):
                entry.path = entry.path[:-1]
            entry.dirname = item.dirname
            while entry.dirname is not None and entry.dirname.endswith("/"):
                entry.dirname = entry.dirname[:-1]
#            manifest.append(entry)
            item.manifest = entry

            # Create the branch and relationships
            if item.branch is not None:
                if item.branch in branches:
                    log.warning("Duplicate branch name, ignored '%s' "
                                "(because '%s' wants '%s')", item.path,
                                branches[item.branch].path, item.branch)
                    # FIXME: Almost abuse of entry.kind ?
                    entry.kind = "IGNORE"
                    continue
                else:
                    branches[item.branch] = item

                # FIXME: utterly bogus, need to manage archives and components
                #        better, I'm just not sure how.
                category = tla_sanitise(inventory_.package)
                repository = "%s/%s--%s--0" % (ARCHIVE, category, item.branch)
                entry.branch = soyuz.createBranch(repository)

                # Branch relationships are a little tricky, we may be
                # able to create the relationship now or we might have
                # to delay it until that item is processed
                if item.branch_of is not None:
                    if hasattr(item.branch_of, "manifest"):
                        parent = item.branch_of.manifest.branch
                        if parent is not None:
                            entry.branch.createRelationship(parent, "tracked")
                    else:
                        # Leave it in the item for processing later
                        if not hasattr(item.branch_of, "relations"):
                            item.branch_of.relations = []
                        item.branch_of.relations.append(entry.branch)

                # Process any earlier items that are branched from us
                if hasattr(item, "relations"):
                    for relation in item.relations:
                        relation.createRelationship(entry.branch, "tracked")

    # Retire old manifest entries that are no longer relevant from the table
    for entry in old_manifest:
        log.info("Deleting retired manifest entry '%s'", entry.path)
        entry.deleteRecord()

#    # Update the sequence ids of the new manifest
#    seq = 0
#    for entry in manifest:
#        seq += 1
#        entry.seq = seq

def tla_sanitise(text):
    """Turn the text into something suitable for a tla category or branch."""
    text = re.sub('[^A-Za-z0-9]+', '-', text)
    text = re.sub('^[0-9-]*', '', text)
    text = re.sub('-*$', '', text)
    if len(text):
        return text
    else:
        return None
