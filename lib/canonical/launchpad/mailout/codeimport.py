# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to code imports."""

__metaclass__ = type


from zope.component import getUtility

from canonical.launchpad.helpers import (
    contactEmailAddresses, get_email_template)
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeImportReviewStatus,
    ILaunchpadCelebrities)
from canonical.launchpad.mail import format_address, simple_sendmail
from canonical.launchpad.webapp import canonical_url


def new_import(code_import, event):
    """Email the vcs-imports team about a new code import."""
    if event.user is None:
        # If there is no logged in user, then we are most likely in a
        # test.
        return

    headers = {'X-Launchpad-Branch': code_import.branch.unique_name}
    subject = 'New code import: %s/%s' % (
        code_import.product.name, code_import.branch.name)
    body = get_email_template('new-code-import.txt') % {
        'person': code_import.registrant.displayname,
        'branch': canonical_url(code_import.branch)}

    from_address = format_address(
        event.user.displayname, event.user.preferredemail.email)

    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    for address in contactEmailAddresses(vcs_imports):
        simple_sendmail(from_address, address, subject, body, headers)


def code_import_status_updated(code_import, user):
    """Email the branch subscribers, and the vcs-imports team with new status.

    """
    branch = code_import.branch
    recipients = branch.getNotificationRecipients()
    # Add in the vcs-imports user.
    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    recipients.add(
        vcs_imports, None,
        'You are getting this email because you are a member of the '
        'vcs-imports team.')

    headers = {'X-Launchpad-Branch': code_import.branch.unique_name}

    subject = 'Code import %s/%s status: %s' % (
        code_import.product.name, code_import.branch.name,
        code_import.review_status.title)

    if code_import.review_status == CodeImportReviewStatus.INVALID:
        status = "The import has been marked as invalid."
    elif code_import.review_status == CodeImportReviewStatus.REVIEWED:
        status = (
            "The import has been approved and an import will start shortly.")
    elif code_import.review_status == CodeImportReviewStatus.SUSPENDED:
        status = "The import has been suspended."
    else:
        raise AssertionError('Unexpected review status for code import.')

    email_template = get_email_template('code-import-status-updated.txt')
    template_params = {
        'status': status,
        'branch': canonical_url(branch)}

    from_address = format_address(user.displayname, user.preferredemail.email)

    interested_levels = (
        BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
        BranchSubscriptionNotificationLevel.FULL)

    for email_address in recipients.getEmails():
        subscription, rationale = recipients.getReason(email_address)

        if subscription is None:
            template_params['rationale'] = rationale
            template_params['unsubscribe'] = ''
        else:
            if subscription.notification_level in interested_levels:
                template_params['rationale'] = (
                    'You are receiving this email as you are subscribed '
                    'to the branch.')
                if not subscription.person.isTeam():
                    # Give the users a link to unsubscribe.
                    template_params['unsubscribe'] = (
                        "\nTo unsubscribe from this branch go to "
                        "%s/+edit-subscription." % canonical_url(branch))
                else:
                    template_params['unsubscribe'] = ''
            else:
                # Don't send email to this subscriber.
                continue

        headers['X-Launchpad-Message-Rationale'] = rationale
        body = email_template % template_params
        simple_sendmail(from_address, email_address, subject, body, headers)
