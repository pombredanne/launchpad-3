# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Adapters used in the Answer Tracker."""

__metaclass__ = type
__all__ = []

def question_to_questiontarget(question):
    """Adapts an IQuestion to its IQuestionTarget."""
    return question.target


def series_to_questiontarget(series):
    """Adapts an IDistroSeries or IProductSeries into an IQuestionTarget."""
    return series.parent

def sourcepackagerelease_to_questiontarget(sourcepackagerelease):
    """Adapts an ISourcePackageRelease into an IQuestionTarget."""
    return sourcepackagerelease.distrosourcepackage
