# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type


from datetime import timedelta

from storm.locals import Store
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.buildmaster.enums import BuildStatus
from lp.code.mail.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildMailer,
    )
from lp.testing import TestCaseWithFactory


expected_body = u"""\
 * State: Successfully built
 * Recipe: person/recipe
 * Archive: archiveowner/ppa
 * Distroseries: distroseries
 * Duration: 5 minutes
 * Build Log: %s
 * Upload Log: 
 * Builder: http://launchpad.dev/builders/bob
"""

superseded_body = u"""\
 * State: Build for superseded Source
 * Recipe: person/recipe
 * Archive: archiveowner/ppa
 * Distroseries: distroseries
 * Duration: 
 * Build Log: 
 * Upload Log: 
 * Builder: 
"""

class TestSourcePackageRecipeBuildMailer(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def makeStatusEmail(self, build):
        mailer = SourcePackageRecipeBuildMailer.forStatus(build)
        email = removeSecurityProxy(build.requester).preferredemail.email
        return mailer.generateEmail(email, build.requester)

    def test_generateEmail(self):
        """GenerateEmail produces the right headers and body."""
        person = self.factory.makePerson(name='person')
        cake = self.factory.makeSourcePackageRecipe(
            name=u'recipe', owner=person)
        pantry_owner = self.factory.makePerson(name='archiveowner')
        pantry = self.factory.makeArchive(name='ppa', owner=pantry_owner)
        secret = self.factory.makeDistroSeries(name=u'distroseries')
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=cake, distroseries=secret, archive=pantry,
            status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=5))
        naked_build = removeSecurityProxy(build)
        naked_build.builder = self.factory.makeBuilder(name='bob')
        naked_build.log = self.factory.makeLibraryFileAlias()
        Store.of(build).flush()
        ctrl = self.makeStatusEmail(build)
        self.assertEqual(
            u'[recipe build #%d] of ~person recipe in distroseries: '
            'Successfully built' % (build.id), ctrl.subject)
        body, footer = ctrl.body.split('\n-- \n')
        self.assertEqual(
            expected_body % build.log.getURL(), body)
        build_url = canonical_url(build)
        self.assertEqual(
            '%s\nYou are the requester of the build.\n' % build_url, footer)
        self.assertEqual(
            config.canonical.noreply_from_address, ctrl.from_addr)
        self.assertEqual(
            'Requester', ctrl.headers['X-Launchpad-Message-Rationale'])
        self.assertEqual(
            'recipe-build-status',
            ctrl.headers['X-Launchpad-Notification-Type'])
        self.assertEqual(
            'FULLYBUILT', ctrl.headers['X-Launchpad-Build-State'])

    def test_generateEmail_with_null_fields(self):
        """GenerateEmail works when many fields are NULL."""
        person = self.factory.makePerson(name='person')
        cake = self.factory.makeSourcePackageRecipe(
            name=u'recipe', owner=person)
        pantry_owner = self.factory.makePerson(name='archiveowner')
        pantry = self.factory.makeArchive(name='ppa', owner=pantry_owner)
        secret = self.factory.makeDistroSeries(name=u'distroseries')
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=cake, distroseries=secret, archive=pantry,
            status=BuildStatus.SUPERSEDED)
        Store.of(build).flush()
        ctrl = self.makeStatusEmail(build)
        self.assertEqual(
            u'[recipe build #%d] of ~person recipe in distroseries: '
            'Build for superseded Source' % (build.id), ctrl.subject)
        body, footer = ctrl.body.split('\n-- \n')
        self.assertEqual(superseded_body, body)
        build_url = canonical_url(build)
        self.assertEqual(
            '%s\nYou are the requester of the build.\n' % build_url, footer)
        self.assertEqual(
            config.canonical.noreply_from_address, ctrl.from_addr)
        self.assertEqual(
            'Requester', ctrl.headers['X-Launchpad-Message-Rationale'])
        self.assertEqual(
            'recipe-build-status',
            ctrl.headers['X-Launchpad-Notification-Type'])
        self.assertEqual(
            'SUPERSEDED', ctrl.headers['X-Launchpad-Build-State'])

    def test_generateEmail_upload_failure(self):
        """GenerateEmail works when many fields are NULL."""
        build = self.factory.makeSourcePackageRecipeBuild()
        removeSecurityProxy(build).upload_log = (
            self.factory.makeLibraryFileAlias())
        upload_log_fragment = 'Upload Log: %s' % build.upload_log_url
        ctrl = self.makeStatusEmail(build)
        self.assertTrue(upload_log_fragment in ctrl.body)
