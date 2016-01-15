# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event subscribers for Git repositories."""

__metaclass__ = type


def refs_updated(repository, event):
    """Some references in a Git repository have been updated."""
    repository.updateMergeCommitIDs(event.paths)
    repository.scheduleDiffUpdates(event.paths)
    repository.markRecipesStale(event.paths)
    repository.detectMerges(event.paths, logger=event.logger)
