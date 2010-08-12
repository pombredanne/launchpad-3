# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test uploads of SourcePackageRecipeBuilds."""

__metaclass__ = type

import os

from storm.store import Store
from zope.component import getUtility

from lp.archiveuploader.tests.test_uploadprocessor import (
    TestUploadProcessorBase)
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildSource)
from lp.soyuz.interfaces.queue import PackageUploadStatus


class TestSourcePackageRecipeBuildUploads(TestUploadProcessorBase):

    def setUp(self):
        super(TestSourcePackageRecipeBuildUploads, self).setUp()

        self.setupBreezy()

        # We need at least one architecture for the PPA upload to be
        # accepted.
        self.breezy['i386'].supports_virtualized = True

        self.recipe = self.factory.makeSourcePackageRecipe()
        self.build = getUtility(ISourcePackageRecipeBuildSource).new(
            distroseries=self.breezy,
            recipe=self.recipe,
            archive=self.factory.makeArchive(
                distribution=self.ubuntu, owner=self.recipe.owner),
            requester=self.recipe.owner)

        Store.of(self.build).flush()
        self.options.context = 'recipe'
        self.options.buildid = self.build.id

        self.uploadprocessor = self.getUploadProcessor(
            self.layer.txn)

    def testSetsBuildAndState(self):
        # Ensure that the upload processor correctly links the SPR to
        # the SPRB, and that the status is set properly.
        # This test depends on write access being granted to anybody
        # (it does not matter who) on SPRB.{status,upload_log}.
        self.assertIs(None, self.build.source_package_release)
        self.assertEqual(False, self.build.verifySuccessfulUpload())
        self.queueUpload('bar_1.0-1', '%d/ubuntu' % self.build.archive.id)
        self.uploadprocessor.processChangesFile(
            os.path.join(self.queue_folder, "incoming", 'bar_1.0-1'),
            '%d/ubuntu/bar_1.0-1_source.changes' % self.build.archive.id)
        self.layer.txn.commit()

        queue_item = self.uploadprocessor.last_processed_upload.queue_root
        self.assertTrue(
            queue_item is not None,
            "Source upload failed\nGot: %s" % "\n".join(self.log.lines))

        self.assertEqual(PackageUploadStatus.DONE, queue_item.status)
        spr = queue_item.sources[0].sourcepackagerelease
        self.assertEqual(self.build, spr.source_package_recipe_build)
        self.assertEqual(spr, self.build.source_package_release)
        self.assertEqual(BuildStatus.FULLYBUILT, self.build.status)
        self.assertEqual(True, self.build.verifySuccessfulUpload())
