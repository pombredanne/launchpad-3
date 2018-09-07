# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Components related to Git repositories."""

__metaclass__ = type
__all__ = [
    "GitRepositoryDelta",
    ]

from lazr.lifecycle.objectdelta import ObjectDelta
from zope.interface import implementer

from lp.code.interfaces.gitrepository import (
    IGitRepository,
    IGitRepositoryDelta,
    )


@implementer(IGitRepositoryDelta)
class GitRepositoryDelta:
    """See `IGitRepositoryDelta`."""

    delta_values = ('name', 'git_identity')

    new_values = ()

    interface = IGitRepository

    def __init__(self, repository, user, name=None, git_identity=None,
                 activities=None):
        self.repository = repository
        self.user = user

        self.name = name
        self.git_identity = git_identity
        self.activities = activities

    @classmethod
    def construct(klass, old_repository, new_repository, user):
        """Return a GitRepositoryDelta instance that encapsulates the changes.

        This method is primarily used by event subscription code to
        determine what has changed during an ObjectModifiedEvent.
        """
        delta = ObjectDelta(old_repository, new_repository)
        delta.recordNewAndOld(klass.delta_values)
        activities = new_repository.getActivity(
            changed_after=old_repository.date_last_modified)
        if delta.changes or activities:
            changes = delta.changes
            changes["repository"] = new_repository
            changes["user"] = user
            changes["activities"] = activities

            return GitRepositoryDelta(**changes)
        else:
            return None
