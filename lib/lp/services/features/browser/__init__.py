# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Feature control view"""


from zope.interface import Interface

from canonical.launchpad.webapp import (
    LaunchpadFormView,
    )

from lp.services.features.model import (
    getAllRules,
    )


class IFeatureControlForm(Interface):

    def __init__(self, context):
        self.context = context


class FeatureControlView(LaunchpadFormView):

    schema = IFeatureControlForm
    page_title = label = 'Feature control'

    def rules_text(self):
        """Return all rules in an editable text form"""
        return '\n'.join(
            "\t".join((r.scope, str(r.priority), r.flag, r.value))
            for r in getAllRules())
