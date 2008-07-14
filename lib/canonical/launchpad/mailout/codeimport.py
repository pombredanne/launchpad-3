# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to code imports."""

__metaclass__ = type

import textwrap

from zope.component import getUtility

from canonical.launchpad.helpers import (
    contactEmailAddresses, get_email_template)
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeImportReviewStatus,
    ILaunchpadCelebrities)
from canonical.launchpad.interfaces.codeimportevent import (
    CodeImportEventDataType, CodeImportEventType)
from canonical.launchpad.interfaces.productseries import (
    RevisionControlSystems)
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


def make_email_body_for_code_import_update(event):
    """Construct the body of an email describing a MODIFY `CodeImportEvent`.

    :param event: The MODIFY `CodeImportEvent`.
    """
    assert event.event_type == CodeImportEventType.MODIFY, (
        "event type must be MODIFY, not %s" % event.event_type.name)

    code_import = event.code_import
    event_data = dict(event.items())

    body = []

    if CodeImportEventDataType.OLD_REVIEW_STATUS in event_data:
        if code_import.review_status == CodeImportReviewStatus.INVALID:
            body.append("The import has been marked as invalid.")
        elif code_import.review_status == CodeImportReviewStatus.REVIEWED:
            body.append(
                "The import has been approved and an import will start "
                "shortly.")
        elif code_import.review_status == CodeImportReviewStatus.SUSPENDED:
            body.append("The import has been suspended.")
        elif code_import.review_status == CodeImportReviewStatus.FAILING:
            body.append("The import has been marked as failing.")
        else:
            raise AssertionError('Unexpected review status for code import.')

    details_change_prefix = '\n'.join(textwrap.wrap(
        "%s is now being imported from:" % code_import.branch.unique_name))
    if code_import.rcs_type == RevisionControlSystems.CVS:
        if (CodeImportEventDataType.OLD_CVS_ROOT in event_data or
            CodeImportEventDataType.OLD_CVS_MODULE in event_data):
            new_details = '    %s from %s' % (
                code_import.cvs_module, code_import.cvs_root)
            old_root = event_data.get(
                CodeImportEventDataType.OLD_CVS_ROOT,
                code_import.cvs_root)
            old_module = event_data.get(
                CodeImportEventDataType.OLD_CVS_MODULE,
                code_import.cvs_module)
            old_details = '    %s from %s' % (old_module, old_root)
            body.append(
                details_change_prefix + '\n' + new_details +
                "\ninstead of:\n" + old_details)
    elif code_import.rcs_type == RevisionControlSystems.SVN:
        if CodeImportEventDataType.OLD_SVN_BRANCH_URL in event_data:
            old_url = event_data[CodeImportEventDataType.OLD_SVN_BRANCH_URL]
            body.append(
                details_change_prefix + '\n    ' +code_import.svn_branch_url +
                "\ninstead of:\n    " + old_url)
    else:
        raise AssertionError(
            'Unexpected rcs_type %r for code import.' % code_import.rcs_type)

    return '\n\n'.join(body)


def code_import_updated(event):
    """Email the branch subscribers, and the vcs-imports team with new status.

    """
    code_import = event.code_import
    branch = code_import.branch
    recipients = branch.getNotificationRecipients()
    # Add in the vcs-imports user.
    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    recipients.add(
        vcs_imports, None,
        'You are getting this email because you are a member of the '
        'vcs-imports team.')

    headers = {'X-Launchpad-Branch': branch.unique_name}

    subject = 'Code import %s/%s status: %s' % (
        code_import.product.name, branch.name,
        code_import.review_status.title)

    email_template = get_email_template('code-import-status-updated.txt')
    template_params = {
        'body': make_email_body_for_code_import_update(event),
        'branch': canonical_url(code_import.branch)}

    from_address = format_address(
        event.person.displayname, event.person.preferredemail.email)

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
