# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os.path

from testtools.content import text_content
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.soyuz.interfaces.packagediffjob import (
    IPackageDiffJob,
    IPackageDiffJobSource,
    )
from lp.soyuz.model.packagediffjob import PackageDiffJob
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.testing import (
    run_script,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.services.job.tests import block_on_job
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import (
    CeleryJobLayer,
    LaunchpadZopelessLayer,
    )


def create_proper_job(factory):
    archive = factory.makeArchive()
    foo_dash1 = factory.makeSourcePackageRelease(archive=archive)
    foo_dash15 = factory.makeSourcePackageRelease(archive=archive)
    suite_dir = 'lib/lp/archiveuploader/tests/data/suite'
    files = {
        '%s/foo_1.0-1/foo_1.0-1.diff.gz' % suite_dir: None,
        '%s/foo_1.0-1/foo_1.0-1.dsc' % suite_dir: None,
        '%s/foo_1.0-1/foo_1.0.orig.tar.gz' % suite_dir: None,
        '%s/foo_1.0-1.5/foo_1.0-1.5.diff.gz' % suite_dir: None,
        '%s/foo_1.0-1.5/foo_1.0-1.5.dsc' % suite_dir: None}
    for name in files:
        filename = os.path.split(name)[-1]
        with open(name, 'r') as content:
            files[name] = factory.makeLibraryFileAlias(
                filename=filename, content=content.read())
    transaction.commit()
    dash1_files = (
        '%s/foo_1.0-1/foo_1.0-1.diff.gz' % suite_dir,
        '%s/foo_1.0-1/foo_1.0-1.dsc' % suite_dir,
        '%s/foo_1.0-1/foo_1.0.orig.tar.gz' % suite_dir)
    dash15_files = (
        '%s/foo_1.0-1/foo_1.0.orig.tar.gz' % suite_dir,
        '%s/foo_1.0-1.5/foo_1.0-1.5.diff.gz' % suite_dir,
        '%s/foo_1.0-1.5/foo_1.0-1.5.dsc' % suite_dir)
    for name in dash1_files:
        foo_dash1.addFile(files[name])
    for name in dash15_files:
        foo_dash15.addFile(files[name])
    return foo_dash1.requestDiffTo(factory.makePerson(), foo_dash15)


class TestPackageDiffJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def makeJob(self):
        ppa = self.factory.makeArchive()
        from_spr = self.factory.makeSourcePackageRelease(archive=ppa)
        to_spr = self.factory.makeSourcePackageRelease(archive=ppa)
        diff = from_spr.requestDiffTo(ppa.owner, to_spr)
        return diff, getUtility(IPackageDiffJobSource).get(diff)

    def test_job_implements_IPackageDiffJob(self):
        _, job = self.makeJob()
        self.assertTrue(verifyObject(IPackageDiffJob, job))

    def test_job_source_implements_IPackageDiffJobSource(self):
        job_source = getUtility(IPackageDiffJobSource)
        self.assertTrue(verifyObject(IPackageDiffJobSource, job_source))

    def test_iterReady(self):
        _, job1 = self.makeJob()
        removeSecurityProxy(job1).job._status = JobStatus.COMPLETED
        _, job2 = self.makeJob()
        jobs = list(PackageDiffJob.iterReady())
        self.assertEqual(1, len(jobs))

    def test_run(self):
        diff, job = self.makeJob()
        method = FakeMethod()
        removeSecurityProxy(diff).performDiff = method
        job.run()
        self.assertEqual(1, method.call_count)

    def test_smoke(self):
        diff = create_proper_job(self.factory)
        transaction.commit()
        out, err, exit_code = run_script(
            "LP_DEBUG_SQL=1 cronscripts/process-job-source.py -vv %s" % (
                IPackageDiffJobSource.getName()))

        self.addDetail("stdout", text_content(out))
        self.addDetail("stderr", text_content(err))
        self.assertEqual(0, exit_code)
        self.assertIsNot(None, diff.diff_content)


class TestViaCelery(TestCaseWithFactory):
    """PackageDiffJob runs under Celery."""

    layer = CeleryJobLayer

    def test_run(self):
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'PackageDiffJob',
        }))

        diff = create_proper_job(self.factory)
        with block_on_job(self):
            transaction.commit()
        self.assertIsNot(None, diff.diff_content)
