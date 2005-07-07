# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser code for translation groups."""

__metaclass__ = type

import operator

from zope.event import notify
from zope.exceptions import NotFoundError
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ITranslationGroup, ITranslationGroupSet, ILanguageSet,
    IPersonSet, ILaunchBag)

__all__ = ['TranslationGroupView',
           'TranslationGroupAddTranslatorView',
           'TranslationGroupSetAddView']

class TranslationGroupView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.notices = []

        self.parseUrlNotices()

    def parseUrlNotices(self):
        """Parse any notice message as an argument to the page."""

        # Check if we have the 'removed' key as an argument. This argument is
        # used by the +rm form to tell us 'who' was removed from 'where'.
        form_removed = self.request.form.get('removed', '')
        if '-' in form_removed:
            # The key exists and follows the format we expect:
            # languagecode-personame
            code, name = form_removed.split('-', 1)

            try:
                language = getUtility(ILanguageSet)[code]
            except NotFoundError:
                # We got a non valid language code.
                language = None

            translator = getUtility(IPersonSet).getByName(name)

            if language is not None and translator is not None:
                # The language and the person got as arguments are valid in
                # our system, so we should show the message:
                self.notices.append(
                    '%s removed as translator for %s.' % (
                        translator.browsername, language.displayname))

    def removals(self):
        """Remove a translator/team for a concrete language."""
        if 'remove' in self.request.form:
            code = self.request.form['remove']
            try:
                translator = self.context[code]
            except NotFoundError:
                translator = None

            new_url = '.'
            if translator is not None:
                new_url = '%s?removed=%s-%s' % (
                            new_url, translator.language.code,
                            translator.translator.name)

                self.context.remove_translator(translator)

            self.request.response.redirect(new_url)

    def translator_list(self):
        result = []
        for item in self.context.translators:
            result.append({'lang': item.language.englishname,
                           'person': item.translator,
                           'code': item.language.code,
                           'datecreated': item.datecreated})
        result.sort(key=operator.itemgetter('lang'))
        return result


class TranslationGroupAddTranslatorView(AddView):

    __used_for__ = ITranslationGroup

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def nextURL(self):
        return self._nextURL


class TranslationGroupSetAddView(AddView):

    __used_for__ = ITranslationGroupSet

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # Add the owner information for the new translation group.
        owner = getUtility(ILaunchBag).user
        if not owner:
            raise AssertionError(
                "User must be authenticated to create a translation group")

        group = getUtility(ITranslationGroupSet).new(
            name=data['name'],
            title=data['title'],
            summary=data['summary'],
            owner=owner)
        notify(ObjectCreatedEvent(group))
        self._nextURL = group.name
        return group

    def nextURL(self):
        return self._nextURL

