# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions to detect if intltool can be used to generate a POT file for the
package in the current directory."""

from __future__ import with_statement

__metaclass__ = type
__all__ = [
    'is_intltool_structure',
    ]

class ReadLockTree(object):
    """Context manager to claim a read lock on a bzr tree."""

    def __init__(self, tree):
        self.tree = tree

    def __enter__(self):
        self.tree.lock_read()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tree.unlock()
        return False


def is_intltool_structure(tree):
    """Does this source tree look like it's set up for intltool?

    Currently this just checks for the existence of POTFILES.in.

    :param tree: A bzrlib.Tree object to search for the intltool structure.
    :returns: True if signs of an intltool structure were found.
    """
    with ReadLockTree(tree):
        for thedir, files in tree.walkdirs():
            for afile in files:
                file_path, file_name, file_type = afile[:3]
                if file_type != 'file':
                    continue
                if file_name == "POTFILES.in":
                    return True
    return False
