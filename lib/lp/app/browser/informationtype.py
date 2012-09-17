# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'InformationTypePortletMixin',
    ]

from lazr.restful.interfaces import IJSONRequestCache

from lp.app.enums import PRIVATE_INFORMATION_TYPES
from lp.app.utilities import json_dump_information_types


class InformationTypePortletMixin:

    def initialize(self):
        cache = IJSONRequestCache(self.request)
        json_dump_information_types(
            cache,
            self.context.getAllowedInformationTypes(self.user))

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
