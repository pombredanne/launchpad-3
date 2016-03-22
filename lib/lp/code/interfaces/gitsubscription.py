# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository subscription interfaces."""

__metaclass__ = type

__all__ = [
    'IGitSubscription',
    ]

from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_read_operation,
    exported,
    operation_for_version,
    REQUEST_USER,
    )
from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Choice,
    Int,
    )

from lp import _
from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.fields import PersonChoice


class IGitSubscription(Interface):
    """The relationship between a person and a Git repository."""

    # XXX cjwatson 2015-01-19 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(as_of="beta")

    id = Int(title=_("ID"), readonly=True, required=True)
    person_id = Int(title=_("Person ID"), required=True, readonly=True)
    person = exported(
        PersonChoice(
            title=_("Person"), required=True, vocabulary="ValidPersonOrTeam",
            readonly=True,
            description=_(
                'Enter the launchpad id, or email address of the person you '
                'wish to subscribe to this repository. If you are unsure, use '
                'the "Choose..." option to find the person in Launchpad. You '
                'can only subscribe someone who is a registered user of the '
                'system.')))
    repository = exported(
        Reference(
            title=_("Repository ID"), required=True, readonly=True,
            schema=IGitRepository))
    notification_level = exported(
        Choice(
            title=_("Notification Level"), required=True,
            vocabulary=BranchSubscriptionNotificationLevel,
            default=BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
            description=_(
                "Attribute notifications are sent when repository details are "
                "changed such as lifecycle status and name.  Revision "
                "notifications are generated when new revisions are found.")))
    max_diff_lines = exported(
        Choice(
            title=_("Generated Diff Size Limit"), required=True,
            vocabulary=BranchSubscriptionDiffSize,
            default=BranchSubscriptionDiffSize.ONEKLINES,
            description=_(
                "Diffs greater than the specified number of lines will not "
                "be sent to the subscriber.  The subscriber will still "
                "receive an email with the new revision details even if the "
                "diff is larger than the specified number of lines.")))
    review_level = exported(
        Choice(
            title=_("Code review Level"), required=True,
            vocabulary=CodeReviewNotificationLevel,
            default=CodeReviewNotificationLevel.FULL,
            description=_(
                "Control the kind of review activity that triggers "
                "notifications."
                )))

    subscribed_by = exported(PersonChoice(
        title=_("Subscribed by"), required=True,
        vocabulary="ValidPersonOrTeam", readonly=True,
        description=_("The person who created this subscription.")))

    @call_with(user=REQUEST_USER)
    @export_read_operation()
    @operation_for_version("devel")
    def canBeUnsubscribedByUser(user):
        """Can the user unsubscribe the subscriber from the repository?"""
