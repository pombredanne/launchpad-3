# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Adapters used in the Answer Tracker."""

__metaclass__ = type
__all__ = []

def question_to_questiontarget(question):
    """Adapts an IQuestion to its IQuestionTarget."""
    return question.target


def distrorelease_to_questiontarget(distrorelease):
    """Adapts an IDistroRelease into an IQuestionTarget."""
    return distrorelease.distribution
