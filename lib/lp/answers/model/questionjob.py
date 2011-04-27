# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to QuestionJob."""

__metaclass__ = type
__all__ = [
    'QuestionJob',
    ]

import simplejson
from storm.expr import (
    And,
    )
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from lazr.delegates import delegates

from canonical.database.enumcol import EnumCol
from canonical.launchpad.helpers import (
    get_contact_email_addresses,
    )
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    )
from canonical.launchpad.mail import (
    format_address,
    simple_sendmail,
    )
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.scripts import log
from canonical.launchpad.webapp import canonical_url
from lp.answers.enums import QuestionJobType
from lp.answers.interfaces.questionjob import (
    IQuestionJob,
    IQuestionEmailJob,
    IQuestionEmailJobSource,
    )
from lp.answers.model.question import Question
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.mail.sendmail import format_address_for_person
from lp.services.propertycache import cachedproperty


class QuestionJob(StormBase):
    """A Job for queued question emails."""

    implements(IQuestionJob)

    __storm_table__ = 'QuestionJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    job_type = EnumCol(enum=QuestionJobType, notNull=True)

    question_id = Int(name='question')
    question = Reference(question_id, Question.id)

    _json_data = Unicode('json_data')

    def __init__(self, question, job_type, metadata):
        """Constructor.

        :param question: The question related to this job.
        :param job_type: The specific job being performed for the question.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(QuestionJob, self).__init__()
        self.job = Job()
        self.job_type = job_type
        self.question = question
        json_data = simplejson.dumps(metadata)
        self._json_data = json_data.decode('utf-8')

    def __repr__(self):
        return (
            "<{self.__class__.__name__} for question {self.question.id}; "
            "status={self.job.status}>").format(self=self)

    @property
    def metadata(self):
        """See `IQuestionJob`."""
        return simplejson.loads(self._json_data)


class QuestionEmailJob(BaseRunnableJob):
    """Intermediate class for deriving from QuestionJob."""
    delegates(IQuestionJob)
    implements(IQuestionEmailJob)
    classProvides(IQuestionEmailJobSource)

    def __init__(self, job):
        self.context = job

    class_job_type = QuestionJobType.EMAIL

    @classmethod
    def create(cls, question, user, subject, body, headers):
        """See `IQuestionJob`."""
        metadata = {
            'user': user.id,
            'subject': subject,
            'body': body,
            'headers': headers,
            }
        job = QuestionJob(
            question=question, job_type=cls.class_job_type, metadata=metadata)
        return cls(job)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        store = IMasterStore(QuestionJob)
        jobs = store.find(
            QuestionJob,
            And(QuestionJob.job_type == cls.class_job_type,
                QuestionJob.job_id.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    @cachedproperty
    def user(self):
        """See `IQuestionEmailJob`."""
        return getUtility(IPersonSet).get(self.metadata['user'])

    @property
    def subject(self):
        """See `IQuestionEmailJob`."""
        return self.metadata['subject']

    @property
    def body(self):
        """See `IQuestionEmailJob`."""
        return self.metadata['body']

    @property
    def headers(self):
        """See `IQuestionEmailJob`."""
        return self.metadata['headers']

    @property
    def log_name(self):
        """See `IRunnableJob`."""
        return self.__class__.__name__

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('question', self.question.id),
            ('user', self.user.name),
            ])
        return vars

    def getErrorRecipients(self):
        """See `IRunnableJob`."""
        return self.user
