# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Adapters used in the Answer Tracker."""

__metaclass__ = type
__all__ = []


from canonical.launchpad.interfaces import IFAQTarget


def question_to_questiontarget(question):
    """Adapts an IQuestion to its IQuestionTarget."""
    return question.target


def series_to_questiontarget(series):
    """Adapts an IDistroSeries or IProductSeries into an IQuestionTarget."""
    return series.parent


def sourcepackagerelease_to_questiontarget(sourcepackagerelease):
    """Adapts an ISourcePackageRelease into an IQuestionTarget."""
    return sourcepackagerelease.distrosourcepackage


def question_to_faqtarget(question):
    """Adapt an IQuestion into an IFAQTarget.

    It adapts the question's target to IFAQTarget.
    """
    return IFAQTarget(question.target)


def distrosourcepackage_to_faqtarget(distrosourcepackage):
    """Adapts an `IDistributionSourcePackage` into an `IFAQTarget`."""
    return distrosourcepackage.distribution


def sourcepackage_to_faqtarget(sourcepackage):
    """Adapts an `ISourcePackage` into an `IFAQTarget`."""
    return sourcepackage.distribution


def faq_to_faqtarget(faq):
    """Adapts an `IFAQ` into an `IFAQTarget`."""
    return faq.target

