# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""BugNotificationMailer code, based on `BaseMailer`."""

__metaclass__ = type
__all__ = [
    'BugNotificationMailer',
    ]


from lp.services.mail.basemailer import BaseMailer


class BugNotificationMailer(BaseMailer):
    """A `BaseMailer` subclass for sending `BugNotification`s."""
