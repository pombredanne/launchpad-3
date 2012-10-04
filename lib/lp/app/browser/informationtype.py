# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'InformationTypePortletMixin',
    ]

from lazr.restful.interfaces import IJSONRequestCache

from lp.app.enums import PRIVATE_INFORMATION_TYPES
from lp.app.interfaces.informationtype import IInformationType
from lp.app.utilities import json_dump_information_types


class InformationTypePortletMixin:

    def initialize(self):
        information_typed = IInformationType(self.context, None)
        if information_typed is None:
            information_typed = self.context
        cache = IJSONRequestCache(self.request)
        json_dump_information_types(
            cache,
            information_typed.getAllowedInformationTypes(self.user))

    @property
    def information_type(self):
        information_typed = IInformationType(self.context, None)
        if information_typed is None:
            information_typed = self.context
        return information_typed.information_type.title

    @property
    def information_type_description(self):
        information_typed = IInformationType(self.context, None)
        if information_typed is None:
            information_typed = self.context
        return information_typed.information_type.description

    @property
    def information_type_css(self):
        information_typed = IInformationType(self.context, None)
        if information_typed is None:
            information_typed = self.context
        if information_typed.information_type in PRIVATE_INFORMATION_TYPES:
            return 'sprite private'
        else:
            return 'sprite public'

    @property
    def privacy_portlet_css(self):
        information_typed = IInformationType(self.context, None)
        if information_typed is None:
            information_typed = self.context
        if information_typed.information_type in PRIVATE_INFORMATION_TYPES:
            return 'portlet private'
        else:
            return 'portlet public'
