# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'GitSubscription',
    ]

from storm.locals import (
    Int,
    Reference,
    )
from zope.interface import implementer

from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.interfaces.gitsubscription import IGitSubscription
from lp.code.security import GitSubscriptionEdit
from lp.registry.interfaces.person import validate_person
from lp.registry.interfaces.role import IPersonRoles
from lp.services.database.constants import DEFAULT
from lp.services.database.enumcol import EnumCol
from lp.services.database.stormbase import StormBase


@implementer(IGitSubscription)
class GitSubscription(StormBase):
    """A relationship between a person and a Git repository."""

    __storm_table__ = 'GitSubscription'

    id = Int(primary=True)

    person_id = Int(name='person', allow_none=False, validator=validate_person)
    person = Reference(person_id, 'Person.id')

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    notification_level = EnumCol(
        enum=BranchSubscriptionNotificationLevel, notNull=True,
        default=DEFAULT)
    max_diff_lines = EnumCol(
        enum=BranchSubscriptionDiffSize, notNull=False, default=DEFAULT)
    review_level = EnumCol(
        enum=CodeReviewNotificationLevel, notNull=True, default=DEFAULT)

    subscribed_by_id = Int(
        name='subscribed_by', allow_none=False, validator=validate_person)
    subscribed_by = Reference(subscribed_by_id, 'Person.id')

    def __init__(self, person, repository, notification_level, max_diff_lines,
                 review_level, subscribed_by):
        super(GitSubscription, self).__init__()
        self.person = person
        self.repository = repository
        self.notification_level = notification_level
        self.max_diff_lines = max_diff_lines
        self.review_level = review_level
        self.subscribed_by = subscribed_by

    def canBeUnsubscribedByUser(self, user):
        """See `IBranchSubscription`."""
        if user is None:
            return False
        permission_check = GitSubscriptionEdit(self)
        return permission_check.checkAuthenticated(IPersonRoles(user))
