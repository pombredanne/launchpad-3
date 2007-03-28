# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser code for Language table."""

__metaclass__ = type
__all__ = [
    'LanguageContextMenu',
    'LanguageNavigation',
    'LanguageSetView',
    'LanguageSetContextMenu',
    'LanguageSetNavigation',
    ]

import operator

from canonical.launchpad.browser.launchpad import RosettaContextMenu
from canonical.launchpad.interfaces import (
    ILanguageSet, ILanguage)
from canonical.launchpad.webapp import (
    GetitemNavigation, LaunchpadFormView, action)


class LanguageNavigation(GetitemNavigation):
    usedfor = ILanguage


class LanguageSetNavigation(GetitemNavigation):
    usedfor = ILanguageSet


class LanguageSetContextMenu(RosettaContextMenu):
    usedfor = ILanguageSet


class LanguageContextMenu(RosettaContextMenu):
    usedfor = ILanguage


class LanguageSetView:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        form = self.request.form
        self.text = form.get('text')
        self.searchrequested = self.text is not None
        self.results = None
        self.matches = 0

    def searchresults(self):
        if self.results is None:
            self.results = self.context.search(text=self.text)
        if self.results is not None:
            self.matches = self.results.count()
        else:
            self.matches = 0
        return self.results
