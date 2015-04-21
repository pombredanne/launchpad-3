# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'GitRef',
    'GitRefFrozen',
    ]

import pytz
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Unicode,
    )
from zope.interface import implements

from lp.app.errors import NotFoundError
from lp.code.enums import GitObjectType
from lp.code.interfaces.gitref import IGitRef
from lp.services.database.enumcol import EnumCol
from lp.services.database.stormbase import StormBase


class GitRefMixin:
    """Methods and properties common to GitRef and GitRefFrozen.

    These can be derived solely from the repository and path, and so do not
    require a database record.
    """

    @property
    def display_name(self):
        """See `IGitRef`."""
        return self.identity

    @property
    def name(self):
        """See `IGitRef`."""
        if self.path.startswith("refs/heads/"):
            return self.path[len("refs/heads/"):]
        else:
            return self.path

    @property
    def identity(self):
        """See `IGitRef`."""
        return "%s:%s" % (self.repository.shortened_path, self.name)

    @property
    def unique_name(self):
        """See `IGitRef`."""
        return "%s:%s" % (self.repository.unique_name, self.name)

    @property
    def owner(self):
        """See `IGitRef`."""
        return self.repository.owner

    @property
    def target(self):
        """See `IGitRef`."""
        return self.repository.target

    @property
    def subscribers(self):
        """See `IGitRef`."""
        return self.repository.subscribers

    def subscribe(self, person, notification_level, max_diff_lines,
                  code_review_level, subscribed_by):
        """See `IGitRef`."""
        return self.repository.subscribe(
            person, notification_level, max_diff_lines, code_review_level,
            subscribed_by)

    def getSubscription(self, person):
        """See `IGitRef`."""
        return self.repository.getSubscription(person)

    def getNotificationRecipients(self):
        """See `IGitRef`."""
        return self.repository.getNotificationRecipients()


class GitRef(StormBase, GitRefMixin):
    """See `IGitRef`."""

    __storm_table__ = 'GitRef'
    __storm_primary__ = ('repository_id', 'path')

    implements(IGitRef)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    path = Unicode(name='path', allow_none=False)

    commit_sha1 = Unicode(name='commit_sha1', allow_none=False)

    object_type = EnumCol(enum=GitObjectType, notNull=True)

    author_id = Int(name='author', allow_none=True)
    author = Reference(author_id, 'RevisionAuthor.id')
    author_date = DateTime(
        name='author_date', tzinfo=pytz.UTC, allow_none=True)

    committer_id = Int(name='committer', allow_none=True)
    committer = Reference(committer_id, 'RevisionAuthor.id')
    committer_date = DateTime(
        name='committer_date', tzinfo=pytz.UTC, allow_none=True)

    commit_message = Unicode(name='commit_message', allow_none=True)

    @property
    def commit_message_first_line(self):
        return self.commit_message.split("\n", 1)[0]


class GitRefFrozen(GitRefMixin):
    """A frozen Git reference.

    This is like a GitRef, but is frozen at a particular commit, even if the
    real reference has moved on or has been deleted.  It isn't necessarily
    backed by a real database object, and will retrieve columns from the
    database when required.  Use this when you have a
    repository/path/commit_sha1 that you want to pass around as a single
    object, but don't necessarily know that the ref still exists.
    """

    implements(IGitRef)

    def __init__(self, repository, path, commit_sha1):
        self.repository_id = repository.id
        self.repository = repository
        self.path = path
        self.commit_sha1 = commit_sha1

    @property
    def _self_in_database(self):
        """Return the equivalent database-backed record of self."""
        ref = IStore(GitRef).get(GitRef, (self.repository_id, self.path))
        if ref is None:
            raise NotFoundError(
                "Repository '%s' does not currently contain a reference named "
                "'%s'" % (self.repository, self.path))
        return ref

    def __getattr__(self, name):
        return getattr(self._self_in_database, name)

    def __setattr__(self, name, value):
        if name in ("repository_id", "repository", "path", "commit_sha1"):
            self.__dict__[name] = value
        else:
            setattr(self._self_in_database, name, value)

    def __eq__(self, other):
        return (
            self.repository == other.repository and
            self.path == other.path and
            self.commit_sha1 == other.commit_sha1)

    def __ne__(self, other):
        return not self == other
