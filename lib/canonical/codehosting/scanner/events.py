# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Events generated by the scanner."""

__metaclass__ = type
__all__ = [
    'DatabaseBranchLoaded',
    'NewRevision',
    'RevisionsRemoved',
    'TipChanged',
    ]


class ScannerEvent:
    """Base scanner event."""

    def __init__(self, db_branch, bzr_branch):
        """"Construct a scanner event.

        :param db_branch: The database IBranch.
        :param bzr_branch: The Bazaar branch being scanned.
        """
        self.db_branch = db_branch
        self.bzr_branch = bzr_branch


class DatabaseBranchLoaded(ScannerEvent):
    """The old branch ancestry has been loaded from the database."""

    def __init__(self, db_branch, bzr_branch, db_ancestry, db_history,
                 db_branch_revision_map):
        """Construct a `DatabaseBranchLoaded` event.

        :param db_branch: The database IBranch.
        :param bzr_branch: The Bazaar branch being scanned.
        :param db_ancestry: ???
        :param db_history: ???
        :param db_branch_revision_map: None
        """
        super(DatabaseBranchLoaded, self).__init__(db_branch, bzr_branch)
        self.db_ancestry = db_ancestry
        self.db_history = db_history
        self.db_branch_revision_map = db_branch_revision_map


class NewRevision(ScannerEvent):
    """A new revision has been found in the branch."""

    def __init__(self, db_branch, bzr_branch, db_revision, bzr_revision,
                 revno):
        """Construct a `NewRevision` event.

        :param db_branch: The database branch.
        :param bzr_branch: The Bazaar branch.
        :param db_revision: An `IRevision` for the new revision.
        :param bzr_revision: The new Bazaar revision.
        :param revno: The revision number of the new revision, None if not
            mainline.
        """
        super(NewRevision, self).__init__(db_branch, bzr_branch)
        self.db_revision = db_revision
        self.bzr_revision = bzr_revision
        self.revno = revno

    def isMainline(self):
        """Is the new revision a mainline one?"""
        return self.revno is not None


class TipChanged(ScannerEvent):
    """The tip of the branch has changed."""

    def __init__(self, db_branch, bzr_branch, initial_scan):
        """Construct a `TipChanged` event.

        :param db_branch: The database branch.
        :param bzr_branch: The Bazaar branch.
        :param initial_scan: Is this the first scan of the branch?
        """
        super(TipChanged, self).__init__(db_branch, bzr_branch)
        self.initial_scan = initial_scan


class RevisionsRemoved(ScannerEvent):
    """Revisions have been removed from the branch."""

    def __init__(self, db_branch, bzr_branch, removed_history):
        super(RevisionsRemoved, self).__init__(db_branch, bzr_branch)
        self.removed_history = removed_history


# XXX: Other possible events:
# class BazaarBranchLoaded(ScannerEvent):
#     bzr_ancestry = None
#     bzr_revision = None
# class MergeDetected:
#     source_db_branch = None
#     target_db_branch = None
#     proposal = None
