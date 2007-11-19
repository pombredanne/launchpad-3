# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Question message interface."""

__metaclass__ = type

__all__ = [
    'IQuestionMessage',
    ]

from zope.schema import Choice, Field

from canonical.launchpad import _
from canonical.launchpad.interfaces.message import IMessage
from canonical.launchpad.interfaces.questionenums import (
    QuestionAction, QuestionStatus)


class IQuestionMessage(IMessage):
    """A message part of a question.

    It adds attributes to the IMessage interface.
    """
    # This is really an Object field with schema=IQuestion, but that
    # would create a circular dependency between IQuestion
    # and IQuestionMessage
    question = Field(
        title=_("The question related to this message."),
        description=_("An IQuestion object."), required=True, readonly=True)

    action = Choice(
        title=_("Action operated on the question by this message."),
        required=True, readonly=True, default=QuestionAction.COMMENT,
        vocabulary=QuestionAction)

    new_status = Choice(
        title=_("Question status after message"),
        description=_("The status of the question after the transition "
        "related the action operated by this message."), required=True,
        readonly=True, default=QuestionStatus.OPEN,
        vocabulary=QuestionStatus)

