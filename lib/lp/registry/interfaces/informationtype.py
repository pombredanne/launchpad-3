# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'IInformationType',
    ]

from zope.schema import Choice

from lp import _
from lp.app.interfaces.launchpad import IPrivacy
from lp.registry.enums import InformationType

class IInformationType(IPrivacy):

    information_type = Choice(
        title=_('Information Type'),
        vocabulary=InformationType,
        )
