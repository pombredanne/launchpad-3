# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueNavigation',
    'TranslationImportQueueSetNavigation',
    'TranslationImportQueueSetView',
    'TranslationImportQueueView',
    ]

from canonical.launchpad.interfaces import (ITranslationImportQueue,
    ITranslationImportQueueSet)
from canonical.launchpad.webapp import GetitemNavigation

class TranslationImportQueueNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueue


class TranslationImportQueueSetNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueueSet


class TranslationImportQueueSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


class TranslationImportQueueView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
