Linked Bug Status Changed Notification
======================================

While a bug is linked to a question , its subscribers will be notified
of changes to the bug status:

    >>> from lp.answers.tests.test_question_notifications import (
    ...     pop_questionemailjobs)
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.webapp.snapshot import notify_modified

    >>> no_priv = getUtility(IPersonSet).getByName('no-priv')
    >>> bugtask = get_bugtask_linked_to_question()
    >>> with notify_modified(bugtask, ['status'], user=no_priv):
    ...     bugtask.transitionToStatus(BugTaskStatus.CONFIRMED, no_priv)
    ...     ignore = pop_questionemailjobs()

    >>> notifications = pop_questionemailjobs()
    >>> len(notifications)
    1

    >>> print(notifications[0].metadata['recipient_set'])
    ASKER_SUBSCRIBER

    >>> print(notifications[0].subject)
    [Question #...]: Status of bug #... changed to 'Confirmed' in Ubuntu

    >>> print(notifications[0].body)
    Bug #... status changed in Ubuntu:
    <BLANKLINE>
        New => Confirmed
    <BLANKLINE>
    http://.../ubuntu/+bug/...
    "Installer fails on a Mac PPC"
    <BLANKLINE>
    This bug is linked to #...
    Can't install Ubuntu
    http://.../ubuntu/+question/...

Only a change in status triggers a notification.

    >>> from lp.testing import login_person
    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     'test@canonical.com')
    >>> ignored = login_person(sample_person)
    >>> with notify_modified(
    ...         bugtask, ['assignee', 'dateassigned'], user=sample_person):
    ...     bugtask.transitionToAssignee(sample_person)

    >>> len(pop_questionemailjobs())
    0
