#!/usr/bin/python
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.app.errors import NotFoundError
from lp.archiveuploader.uploadpolicy import (
    AbstractUploadPolicy,
    ArchiveUploadType,
    )
from lp.testing import TestCase, TestCaseWithFactory


class TestUploadPolicy_validateUploadType(TestCase):
    """Test what kind (sourceful/binaryful/mixed) of uploads are accepted."""

    def test_sourceful_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.SOURCE_ONLY)
        upload = make_fake_upload(sourceful=True)

        policy.validateUploadType(upload)

        self.assertEquals([], upload.rejections)

    def test_binaryful_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.BINARY_ONLY)
        upload = make_fake_upload(binaryful=True)

        policy.validateUploadType(upload)

        self.assertEquals([], upload.rejections)

    def test_mixed_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.MIXED_ONLY)
        upload = make_fake_upload(sourceful=True, binaryful=True)

        policy.validateUploadType(upload)

        self.assertEquals([], upload.rejections)

    def test_sourceful_not_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.BINARY_ONLY)
        upload = make_fake_upload(sourceful=True)

        policy.validateUploadType(upload)

        self.assertIn(
            'Sourceful uploads are not accepted by this policy.',
            upload.rejections)

    def test_binaryful_not_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.SOURCE_ONLY)
        upload = make_fake_upload(binaryful=True)

        policy.validateUploadType(upload)

        self.assertTrue(len(upload.rejections) > 0)
        self.assertIn(
            'Upload rejected because it contains binary packages.',
            upload.rejections[0])

    def test_mixed_not_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.SOURCE_ONLY)
        upload = make_fake_upload(sourceful=True, binaryful=True)

        policy.validateUploadType(upload)

        self.assertIn(
            'Source/binary (i.e. mixed) uploads are not allowed.',
            upload.rejections)

    def test_sourceful_when_only_mixed_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.MIXED_ONLY)
        upload = make_fake_upload(sourceful=True, binaryful=False)

        policy.validateUploadType(upload)

        self.assertIn(
            'Sourceful uploads are not accepted by this policy.',
            upload.rejections)

    def test_binaryful_when_only_mixed_accepted(self):
        policy = make_policy(accepted_type=ArchiveUploadType.MIXED_ONLY)
        upload = make_fake_upload(sourceful=False, binaryful=True)

        policy.validateUploadType(upload)

        self.assertTrue(len(upload.rejections) > 0)
        self.assertIn(
            'Upload rejected because it contains binary packages.',
            upload.rejections[0])


class TestUploadPolicy(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_setDistroSeriesAndPocket_distro_not_found(self):
        policy = AbstractUploadPolicy()
        policy.distro = self.factory.makeDistribution()
        self.assertRaises(
            NotFoundError, policy.setDistroSeriesAndPocket,
            'nonexistent_security')


class FakeNascentUpload:

    def __init__(self, sourceful, binaryful):
        self.sourceful = sourceful
        self.binaryful = binaryful
        self.is_ppa = False
        self.rejections = []

    def reject(self, msg):
        self.rejections.append(msg)


def make_fake_upload(sourceful=False, binaryful=False):
    return FakeNascentUpload(sourceful, binaryful)


def make_policy(accepted_type):
    policy = AbstractUploadPolicy()
    policy.accepted_type = accepted_type
    return policy
