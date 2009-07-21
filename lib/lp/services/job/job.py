# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type


from lp.services.job.model import job
from lp.services.mail.sendmail import MailController


class Job:

    def __init__(self):
        self.job = job.Job()

    def getOopsRecipients(self):
        return self.oops_recipients

    def getOopsMailController(self, oops):
        recipients = self.getOopsRecipients()
        if len(recipients) == 0:
            return None
        body = (
            'Launchpad encountered an internal error during the following'
            ' operation: %s.  It was logged with id %s.  Sorry for the'
            ' inconvenience.' % (self.getOperationDescription(), oops.id))
        return MailController('noreply@launchpad.net', recipients,
                              'NullJob failed.', body)

    def notifyOops(self, oops):
        ctrl = self.getOopsMailController(oops)
        if ctrl is None:
            return
        ctrl.send()
