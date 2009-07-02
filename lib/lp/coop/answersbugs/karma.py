# Copyright 2006-2009 Canonical Ltd.  All rights reserved.

"""Karma for the Answer Tracker / Bugs extension."""

__metaclass__ = type
__all__ = []

from canonical.database.sqlbase import block_implicit_flushes

from lp.registry.interfaces.person import IPerson
from lp.answers.karma import assignKarmaUsingQuestionContext

@block_implicit_flushes
def question_bug_added(questionbug, event):
    """Assign karma to the user which added <questionbug>."""
    question = questionbug.question
    assignKarmaUsingQuestionContext(
        IPerson(event.user), question, 'questionlinkedtobug')

