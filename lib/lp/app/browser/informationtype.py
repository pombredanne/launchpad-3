# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'InformationTypePortletMixin',
    ]

from lazr.restful.interfaces import IJSONRequestCache

from lp.registry.enums import PRIVATE_INFORMATION_TYPES


class InformationTypePortletMixin:

    def initialize(self):
        cache = IJSONRequestCache(self.request)
        cache.objects['information_type_data'] = [
            {'value': term.name, 'description': term.description,
            'name': term.title,
            'description_css_class': 'choice-description'}
            for term in self.context.getAllowedInformationTypes(self.user)]
        cache.objects['private_types'] = [
            type.name for type in PRIVATE_INFORMATION_TYPES]

    @property
    def information_type(self):
        return self.context.information_type.title

    @property
    def information_type_description(self):
        return self.context.information_type.description

    @property
    def information_type_css(self):
        if self.context.information_type in PRIVATE_INFORMATION_TYPES:
            return 'sprite private'
        else:
            return 'sprite public'
