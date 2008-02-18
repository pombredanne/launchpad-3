# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Support for CVS and Subversion branches."""

__metaclass__ = type
__all__ = ['CVSWorkingTree', 'SubversionWorkingTree']

import os

import CVS
import pysvn


# Importer
# - Checkout
# - Update

# - Need to be able to modify the branch for testing
# - Need to be able to make up branches for testing


class ForeignWorkingTree:
    """The working tree of a Subversion or CVS branch."""

    def checkout(self):
        """Check out the branch."""

    def update(self):
        """Update the working tree with the latest changes from the branch."""


class CVSWorkingTree(ForeignWorkingTree):

    def __init__(self, cvs_root, cvs_module, local_path):
        """
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


class SubversionWorkingTree(ForeignWorkingTree):
    """A foreign branch object that represents a Subversion branch."""

    def __init__(self, url, path):
        """Construct a `ForeignWorkingTree`.

        :param url: The URL of the branch for this tree.
        :param path: The path to the working tree.
        """
        self.remote_url = url
        self.local_path = path

    def checkout(self):
        svn_client = pysvn.Client()
        svn_client.checkout(
            self.remote_url, self.local_path, ignore_externals=True)

    def update(self):
        svn_client = pysvn.Client()
        svn_client.update(self.local_path)
