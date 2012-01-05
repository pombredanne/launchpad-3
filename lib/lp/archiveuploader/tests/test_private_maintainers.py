# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from lp.archiveuploader.dscfile import SignableTagFile
from lp.archiveuploader.nascentuploadfile import UploadError
from lp.registry.interfaces.person import PersonVisibility
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestPrivateMaintainers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_private_team_non_member(self):
        # Maintainers can not be private teams. If the uploader isn't set,
        # or isn't a member, the rejection message is delibrately vague.
        with celebrity_logged_in('admin'):
            team = self.factory.makeTeam(
                email="foo@bar.com", visibility=PersonVisibility.PRIVATE)
        sigfile = SignableTagFile()
        sigfile.changes = SignableTagFile()
        sigfile.changes.changed_by = {}
        self.assertRaisesWithContent(
            UploadError, 'Invalid Maintainer.', sigfile.parseAddress,
            "foo@bar.com")

    def test_private_team_member(self):
        # Maintainers can not be private teams. If the uploader is a member
        # of the team, the rejection message can be clear.
        uploader = self.factory.makePerson()
        with celebrity_logged_in('admin'):
            team = self.factory.makeTeam(
                email="foo@bar.com", visibility=PersonVisibility.PRIVATE,
                members=[uploader])
        sigfile = SignableTagFile()
        sigfile.changes = SignableTagFile()
        sigfile.changes.changed_by = {'person': uploader}
        self.assertRaisesWithContent(
            UploadError, 'Maintainer can not be set to a private team.',
            sigfile.parseAddress, "foo@bar.com")
