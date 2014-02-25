# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Support for CVS branches."""

__metaclass__ = type
__all__ = ['CVSWorkingTree']

import os

import CVS


class CVSWorkingTree:
    """Represents a CVS working tree."""

    def __init__(self, cvs_root, cvs_module, local_path):
        """Construct a CVSWorkingTree.

        :param cvs_root: The root of the CVS repository.
        :param cvs_module: The module in the CVS repository.
        :param local_path: The local path to check the working tree out to.
        """
        self.root = cvs_root
        self.module = cvs_module
        self.local_path = os.path.abspath(local_path)

    def checkout(self):
        repository = CVS.Repository(self.root, None)
        repository.get(self.module, self.local_path)

    def commit(self):
        tree = CVS.tree(self.local_path)
        tree.commit(log='Log message')

    def update(self):
        tree = CVS.tree(self.local_path)
        tree.update()
