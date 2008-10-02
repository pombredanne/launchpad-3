# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Database objects for CodeMailJob"""

__metaclass__ = type
__all__ = ['CodeMailJob', 'CodeMailJobSource']


from calendar import timegm
from email.Message import Message
from email.Header import Header
from email.Utils import formatdate

from sqlobject import ForeignKey, IntCol, StringCol
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.database.job import Job
from canonical.launchpad.interfaces import (
    ICodeMailJob, ICodeMailJobSource, JobStatus)
from canonical.launchpad.mailout import append_footer
from canonical.launchpad.mail.sendmail import sendmail
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class CodeMailJob(SQLBase):

    implements(ICodeMailJob)

    _table = 'CodeMailJob'

    id = IntCol(notNull=True)

    job = ForeignKey(foreignKey='Job', notNull=True)

    rfc822msgid = StringCol(notNull=True)

    in_reply_to = StringCol()

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    from_address = StringCol(notNull=True)

    reply_to_address = StringCol()

    to_address = StringCol(notNull=True)

    subject = StringCol(notNull=True)

    body = StringCol(notNull=True)

    footer = StringCol()

    rationale = StringCol()

    branch_url = StringCol()

    branch_project_name = StringCol()

    def __init__(self, **kwargs):
        kwargs['job'] = Job()
        SQLBase.__init__(self, **kwargs)

    static_diff = ForeignKey(foreignKey='StaticDiff')
    max_diff_lines = IntCol()

    def toMessage(self):
        mail = Message()
        mail['Message-Id'] = self.rfc822msgid
        if self.in_reply_to is not None:
            mail['In-Reply-To'] = self.in_reply_to
        mail['To'] = Header(self.to_address, 'iso-8859-1')
        mail['From'] = Header(self.from_address, 'iso-8859-1')
        if self.reply_to_address is not None:
            mail['Reply-To'] = Header(self.reply_to_address, 'iso-8859-1')
        mail['X-Launchpad-Message-Rationale'] = Header(self.rationale,
            'iso-8859-1')
        mail['X-Launchpad-Branch'] = self.branch_url
        if self.branch_project_name is not None:
            mail['X-Launchpad-Project'] = Header(self.branch_project_name,
                'iso-8859-1')
        mail['Subject'] = Header(self.subject, 'iso-8859-1')
        mail['Date'] = formatdate(timegm(self.date_created.utctimetuple()))
        mail.set_payload(self.get_body(), 'utf-8')
        return mail

    def get_body(self):
        body = self.body % {'diff': self._diffText()}
        return append_footer(body, self.footer)

    def _diffText(self):
        if self.max_diff_lines == 0 or self.static_diff is None:
            return ''
        lfa = self.static_diff.diff.diff_text
        lfa.open()
        diff = lfa.read().decode('utf8', 'replace')
        diff_size = diff.count('\n') + 1
        if diff_size > self.max_diff_lines:
            return (
                '\nThe size of the diff (%d lines) is larger than your '
                'specified limit of %d lines' % (
                diff_size, self.max_diff_lines))
        else:
            return '\n' + diff

    def run(self):
        self.job.start()
        sendmail(self.toMessage(), [self.to_address])
        self.job.complete()


class CodeMailJobSource:

    implements(ICodeMailJobSource)

    def create(self, from_address, reply_to_address, to_address, rationale,
               branch_url, branch_project_name, subject, body, footer,
               message_id, in_reply_to, max_diff_lines):
        """See `ICodeMailJobSource`"""
        return CodeMailJob(from_address=from_address,
            reply_to_address=reply_to_address, to_address=to_address,
            rationale=rationale, branch_url=branch_url,
            branch_project_name=branch_project_name, subject=subject,
            body=body, footer=footer, rfc822msgid=message_id,
            in_reply_to=in_reply_to, max_diff_lines=max_diff_lines)

    @staticmethod
    def findRunnableJobs():
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(CodeMailJob, CodeMailJob.job == Job.id,
                          Job.id.is_in(Job.ready_jobs))
