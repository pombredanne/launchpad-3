# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to QuestionJob."""

__metaclass__ = type
__all__ = [
    'QuestionJob',
    ]

import simplejson
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.interface import (
    implements,
    )

from canonical.database.enumcol import EnumCol
from lp.answers.enums import QuestionJobType
from lp.answers.interfaces.questionjob import (
    IQuestionJob,
    )
from lp.answers.model.question import Question
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import Job


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
        return simplejson.loads(self._json_data)
