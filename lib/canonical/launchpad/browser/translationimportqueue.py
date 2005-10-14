# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueSetView',
    'TranslationImportQueueView',
    ]

class TranslationImportQueueSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


class TranslationImportQueueView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
