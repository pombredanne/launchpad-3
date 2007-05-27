# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Adapters used in the Answer Tracker."""

__metaclass__ = type
__all__ = []

def question_to_questiontarget(question):
    """Adapts an IQuestion to its IQuestionTarget."""
    return question.target


def distroseries_to_questiontarget(distroseries):
    """Adapts an IDistroSeries into an IQuestionTarget."""
    return distroseries.distribution

def sourcepackagerelease_to_questiontarget(sourcepackagerelease):
    """Adapts an ISourcePackageRelease into an IQuestionTarget."""
    return sourcepackagerelease.distrosourcepackage