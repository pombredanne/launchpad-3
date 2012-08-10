# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.services.auditor.client import AuditorClient
from lp.testing import TestCaseWithFactory
from lp.testing.layers import AuditorLayer


class TestAuditorClient(TestCaseWithFactory):

    layer = AuditorLayer

    def test_send_and_receive(self):
        # We can use .send() and .receive() on AuditorClient to log.
        actor = self.factory.makePerson()
        pu = self.factory.makePackageUpload()
        client = AuditorClient()
        result = client.send(pu, 'packageupload-accepted', actor)
        self.assertEqual('Operation recorded.', result)
        result = client.receive(obj=pu)
        del result[0]['date'] # Ignore the date.
        expected = [{
            u'comment': u'', u'details': u'', u'actor': actor,
            u'operation': u'packageupload-accepted', u'object': pu}]
        self.assertContentEqual(expected, result)
