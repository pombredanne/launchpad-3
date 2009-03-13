# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Views which export vocabularies as JSON for widgets."""

__metaclass__ = type

__all__ = [
    'VocabularySet',
    'VocabularySetNavigation',
    ]

import simplejson

from zope.schema.interfaces import IVocabulary
from zope.schema.vocabulary import getVocabularyRegistry
from zope.app.form.interfaces import MissingInputError

from canonical.config import config
from canonical.launchpad.interfaces.launchpad import IHasIcon
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.webapp.tales import ObjectImageDisplayAPI

class VocabularyJSONView:
    DEFAULT_BATCH_SIZE = 10

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        name = self.request.form.get('name')
        if name is None:
            raise MissingInputError('name', '')
        registry = getVocabularyRegistry()
        vocabulary = registry.get(IVocabulary, name)
        search_text = self.request.form.get('search_text')
        batch_size = int(self.request.form.get('size',
                                               self.DEFAULT_BATCH_SIZE))
        offset = int(self.request.form.get('offset', 0))
        if search_text is None:
            matches = [term for term in vocabulary]
            total_size = len(matches)
        else:
            matches = vocabulary.searchForTerms(search_text)
            total_size = matches.count()

        result = []
        for term in matches[offset:offset+batch_size]:
            entry = dict(value=term.token, title=term.title)
            # Set image url.
            if (IHasIcon.providedBy(term.value)
                and term.value.icon is not None):
                image_url = term.value.icon.getURL()
            else:
                display_api = ObjectImageDisplayAPI(term.value)
                image_url = display_api.default_icon_resource(term.value)
            if image_url is not None:
                entry['image'] = image_url
            # Set description.
            if (IPerson.providedBy(term.value)
                and term.value.preferredemail is not None):
                entry['description'] = term.value.preferredemail.email
            elif hasattr(term.value, 'summary'):
                entry['description'] = term.value.summary
            result.append(entry)
        if config.devmode:
            if len(result) < batch_size and len(result) != 0:
                result.append(dict(
                    value='bad-value-for-testing-errors-on-dev-system',
                    title='Bad Value for Testing on Dev System',
                    description='Intential bad value.',
                    image='/@@/bug-critical'))

        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(dict(total_size=total_size, entries=result))
