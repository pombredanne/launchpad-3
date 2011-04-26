# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for the Jobs system for questions."""

__metaclass__ = type
__all__ = [
    'IQuestionJob',
    'IQuestionJobSource',
    ]

from zope.interface import Attribute
from zope.schema import (
    Field,
    Int,
    Object,
    )

from canonical.launchpad import _
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )


class IQuestionJob(IRunnableJob):
    """A Job related to a question."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this job."))

    job = Object(
        title=_('The common Job attributes'),
        schema=IJob, required=True)

    question = Field(
        title=_("The question related to this job."),
        description=_("An IQuestion."), required=True, readonly=True)

    metadata = Attribute('A dict of data about the job.')


class IQuestionJobSource(IJobSource):
    """An interface for acquiring IQuestionJob."""

    def create(question, metadata):
        """Create a new IQuestionJob."""
