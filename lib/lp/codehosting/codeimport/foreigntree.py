# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Support for CVS and Subversion branches."""

__metaclass__ = type
__all__ = ['CVSWorkingTree', 'SubversionWorkingTree']

import os
import subprocess

import CVS
import pysvn


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


class SubversionWorkingTree:
    """Represents a Subversion working tree."""

    def __init__(self, url, path):
        """Construct a `SubversionWorkingTree`.

        :param url: The URL of the branch for this tree.
        :param path: The path to the working tree.
        """
        self.remote_url = url
        self.local_path = path

    def checkout(self):
        # XXX: JonathanLange 2008-02-19: Can't do this with cscvs yet because
        # its Repository class assumes that the repository lives on the local
        # filesystem.
        svn_client = pysvn.Client()
        svn_client.checkout(
            self.remote_url, self.local_path, ignore_externals=True)

    def commit(self):
        client = pysvn.Client()
        client.checkin(self.local_path, 'Log message', recurse=True)

    def update(self):
        # XXX: David Allouche 2006-01-31 bug=82483: A bug in
        # pysvn prevents us from ignoring svn:externals. We work
        # around it by shelling out to svn. When cscvs no longer
        # uses pysvn, we will use the cscvs API again.
        arguments = ['svn', 'update', '--ignore-externals']
        retcode = subprocess.call(
            arguments, cwd=self.local_path, stdout=open('/dev/null', 'w'))
        if retcode != 0:
            raise RuntimeError("svn update failed with code %s" % retcode)
