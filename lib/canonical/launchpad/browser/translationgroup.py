# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import operator

from zope.event import notify
from zope.exceptions import NotFoundError
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope.app.form.browser.add import AddView
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
import zope.security.interfaces

from canonical.launchpad.interfaces import ITranslationGroup, \
    ITranslationGroupSet, IPerson, ILanguageSet, IPersonSet

from canonical.launchpad.database import TranslationGroup

ow = CustomWidgetFactory(ObjectWidget, TranslationGroup)
sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)

__all__ = ['TranslationGroupView',
           'TranslationGroupAddTranslatorView',
           'TranslationGroupSetAddView']

class TranslationGroupView:

    relatedsPortlet = ViewPageTemplateFile(
        '../templates/portlet-translationgroup-relateds.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.notices = []

        self.parseUrlNotices()

    def parseUrlNotices(self):
        """Parse any notice message as an argument to the page."""

        # Check if we have the 'removed' key as an argument. This argument is
        # used by the +rm form to tell us 'who' was removed from 'where'.
        if (self.request.form.has_key('removed') and
            '-' in self.request.form['removed']):
            # The key exists and follows the format we expect:
            # languagecode-personame
            code, name = self.request.form['removed'].split('-', 1)

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
        if self.request.form.has_key('remove'):
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

    options_widget = sw

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def nextURL(self):
        return self._nextURL


class TranslationGroupSetAddView(AddView):

    __used_for__ = ITranslationGroupSet

    options_widget = sw

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the bounty
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized, "Need an authenticated group owner"
        kw = {}
        for item in data.items():
            kw[str(item[0])] = item[1]
        kw['ownerID'] = owner.id
        group = TranslationGroup(**kw)
        notify(ObjectCreatedEvent(group))
        self._nextURL = kw['name']
        return group

    def nextURL(self):
        return self._nextURL

