# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueNavigation',
    'TranslationImportQueueSetNavigation',
    'TranslationImportQueueSetView',
    'TranslationImportQueueURL',
    'TranslationImportQueueView',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (ITranslationImportQueue,
    ITranslationImportQueueSet, ICanonicalUrlData)
from canonical.launchpad.webapp import GetitemNavigation

class TranslationImportQueueNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueue


class TranslationImportQueueSetNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueueSet


class TranslationImportQueueSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def ready_to_import(self):
        """Return the set of entries that can be imported directly."""
        for entry in self.context:
            if entry.import_into is not None:
                yield entry

    def pending_review(self):
        """Return the set of entries that need manually review."""
        for entry in self.context:
            if entry.import_into is None:
                yield entry


class TranslationImportQueueURL:
    implements(ICanonicalUrlData)

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        translation_import_queue  = self.context
        return str(translation_import_queue.id)

    @property
    def inside(self):
        return getUtility(ITranslationImportQueueSet)


class TranslationImportQueueView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

