#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Move a python module in the tree.

It uses bzr mv to rename the module and will try to find all imports.

rename-module.py src_file+ target

Both files must be under lib/.

If more than one src files is given, target must be a directory.
"""

__metaclass__ = type

__all__ = [
    'bzr_add',
    'bzr_has_filename',
    'bzr_move_file',
    'bzr_remove_file',
    'rename_module',
    'update_references',
    ]

import os
import sys

from bzrlib import workingtree
from find import find_matches
from utils import fail, log


def file2module(module_file):
    """From a filename, return the python module name."""
    start_path = 'lib' + os.path.sep
    assert module_file.startswith(start_path), (
        "File should start with lib: %s" % module_file)
    assert module_file.endswith('.py'), (
        "File should end with .py: %s" % module_file)
    return module_file[len(start_path):-3].replace(os.path.sep, '.')


# Cache the working tree for speed.
_wt = workingtree.WorkingTree.open('.')

def bzr_move_file(src_file, target):
    """Move or rename a versioned file or directory."""
    if os.path.isdir(target):
        _wt.move([src_file], target)
    else:
        _wt.rename_one(src_file, target)
    log('    Renamed %s => %s', src_file, target)


def bzr_add(paths):
    "Version a list of paths."
    _wt.add(paths)

def bzr_remove_file(filename):
    """Remove a versioned file."""
    _wt.remove([filename], keep_files=False, force=True)


def bzr_has_filename(file_path):
    """Is the file versioned?"""
    _wt.has_filename(file_path)


def rename_module(src_file, target_file):
    """Renamed  a versioned module and update all references to it."""
    # Move the file using bzr.
    bzr_move_file(src_file, target_file)
    if not src_file.endswith('.py'):
        # It's not a module, so don't try to update imports of it.
        return
    source_module = file2module(src_file)
    target_module = file2module(target_file)
    update_references(source_module, target_module)


def update_references(source_module, target_module):
    """Update references to the source module.

    :param src_module: a string describing the old module name. May contain
        RE patterns
    :param target_module: a string representing the new module name. May
        contain RE groups.
    """
    source = r'\b%s\b' % source_module.replace('.', '\\.')
    target = target_module
    root_dirs = ['cronscripts', 'lib/canonical', 'lib/lp']
    file_pattern = '\.(py|txt|zcml)$'
    print "    Updating references:"
    for root_dir in root_dirs:
        for summary in find_matches(
            root_dir, file_pattern, source, substitution=target):
            print "        * %(file_path)s" % summary


def main():
    """Rename a module and update all references to it."""
    if len(sys.argv) < 3:
        fail('Usage: %s src_file+ target', os.path.basename(sys.argv[0]))
    src_files = sys.argv[1:-1]
    target = sys.argv[-1]

    if os.path.exists(target) and not os.path.isdir(target):
        fail('Destination file "%s" already exists.', target)
    if not target.startswith('lib'):
        fail('Destination file "%s" must be under lib.', target)
    if len(src_files) > 1 and not os.path.isdir(target):
        fail('Destination must be a directory.')

    for src_file in src_files:
        if not os.path.exists(src_file):
            log('Source file "%s" doesn\'t exists. Skipping', src_file)
            continue
        if not src_file.startswith('lib'):
            log('Source file "%s" must be under lib. Skipping', src_file)
            continue

        if os.path.isdir(target):
            target_file = os.path.join(target, os.path.basename(src_file))
        else:
            target_file = target

        rename_module(src_file, target_file)


if __name__ == '__main__':
    main()
