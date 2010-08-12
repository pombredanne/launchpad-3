# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Feature control view"""


from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Choice, Set

from canonical.launchpad import _
from lp.registry.interfaces.pillar import IPillarNameSet
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView,
    )
from canonical.widgets import LabeledMultiCheckBoxWidget


class IFeatureControlForm(Interface):

    def __init__(self, context):
        self.context = context


class FeatureControlView(LaunchpadFormView):

    schema = IFeatureControlForm
    page_title = label = 'Feature control'
