# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bzr back-end for importd."""

__metaclass__ = type

__all__ = ['BzrManager']


class BzrManager:
    """Manage a bzr branch in importd.

    This class encapsulate all the bzr-specific code in importd.
    """

    def createMaster(self):
       """Do nothing. For compatibility with ArchiveManager."""

    def createMirror(self):
       """Do nothing. For compatibility with ArchiveManager."""

    def nukeMaster(self):
       """Do nothing. For compatibility with ArchiveManager."""

    def rollbackToMirror(self):
        """Do nothing. For compatibility with ArchiveManager."""

    # def createImportTarget(self, working_dir):
    # fail if there is a mirror

    # def getSyncTarget(self, working_dir):
    # fail if there is no mirror

    # def mirrorBranch(self, logger):
    # fail if there is divergence
