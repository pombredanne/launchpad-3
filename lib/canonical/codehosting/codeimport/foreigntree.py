# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Support for CVS and Subversion branches."""

__metaclass__ = type
__all__ = ['CVSWorkingTree', 'SubversionWorkingTree']

import os

import CVS
import pysvn
import svn_oo


class CVSWorkingTree:
    """A foreign branch object that represents a CVS branch."""

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


class SubversionWorkingTree:
    """A foreign branch object that represents a Subversion branch."""

    def __init__(self, url, path):
        """Construct a `SubversionWorkingTree`.

        :param url: The URL of the branch for this tree.
        :param path: The path to the working tree.
        """
        self.remote_url = url
        self.local_path = path

    def checkout(self):
        # XXX: Can't do this with cscvs yet because its Repository class
        # assumes that the repository lives on the local filesystem.
        svn_client = pysvn.Client()
        svn_client.checkout(
            self.remote_url, self.local_path, ignore_externals=True)

    def update(self):
        tree = svn_oo.WorkingTree(self.local_path)
        tree.update()
