# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.translations.browser.pofile import POExportView
from lp.translations.browser.potemplate import POTemplateExportView
from lp.translations.model.poexportrequest import POExportRequest


def get_poexportrequests():
    """Get (template, pofile) tuples of  all pending export requests."""
    requests = IStore(POExportRequest).find(POExportRequest)
    return [(request.potemplate, request.pofile) for request in requests]


class TestPOTEmplateExportView(TestCaseWithFactory):
    """Test POTEmplateExportView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPOTEmplateExportView, self).setUp()
        self.potemplate = self.factory.makePOTemplate()
        # All exports can be requested by an unprivileged user.
        self.translator = self.factory.makePerson()

    def _createView(self, form):
        login_person(self.translator)
        request = LaunchpadTestRequest(method='POST', form=form)
        view = POTemplateExportView(self.potemplate, request)
        view.initialize()
        return view

    def test_request_all_only_template(self):
        # Selecting 'all' will place the template into the request queue.
        self._createView({'what': 'all', 'format': 'PO'}) 

        self.assertContentEqual(
            [(self.potemplate, None)], get_poexportrequests())

    def test_request_some_potemplate(self):
        # Using 'some' allows to select only the template.
        pofile = self.factory.makePOFile(potemplate=self.potemplate)
        self._createView({'what': 'some', 'potemplate': True, 'format': 'PO'}) 

        self.assertContentEqual(
            [(self.potemplate, None)], get_poexportrequests())

    def test_request_some_pofile(self):
        # Using 'some' allows to select only a pofile.
        pofile = self.factory.makePOFile(potemplate=self.potemplate)
        self._createView({
            'what': 'some',
            pofile.language.code: True,
            'format': 'PO'}) 

        self.assertContentEqual(
            [(self.potemplate, pofile)], get_poexportrequests())
