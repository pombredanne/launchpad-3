# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `DistroSeriesDifferenceJob` and utility."""

__metaclass__ = type

import os
import subprocess
import sys
import transaction
from psycopg2 import ProgrammingError
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.registry.model.distroseriesdifference import DistroSeriesDifference
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.distributionjob import (
    IDistroSeriesDifferenceJobSource,
    )
from lp.soyuz.model.distroseriesdifferencejob import (
    create_job,
    FEATURE_FLAG_ENABLE_MODULE,
    find_waiting_jobs,
    make_metadata,
    may_require_job,
    )
from lp.testing import TestCaseWithFactory


class TestDistroSeriesDifferenceJobSource(TestCaseWithFactory):
    """Tests for `IDistroSeriesDifferenceJobSource`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestDistroSeriesDifferenceJobSource, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))

    def getJobSource(self):
        return getUtility(IDistroSeriesDifferenceJobSource)

    def makeDerivedDistroSeries(self):
        return self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())

    def test_baseline(self):
        verifyObject(IDistroSeriesDifferenceJobSource, self.getJobSource())

    def test_make_metadata_is_consistent(self):
        package = self.factory.makeSourcePackageName()
        self.assertEqual(make_metadata(package), make_metadata(package))

    def test_make_metadata_distinguishes_packages(self):
        one_package = self.factory.makeSourcePackageName()
        another_package = self.factory.makeSourcePackageName()
        self.assertNotEqual(
            make_metadata(one_package), make_metadata(another_package))

    def test_may_require_job_accepts_none_distroseries(self):
        package = self.factory.makeSourcePackageName()
        self.assertFalse(may_require_job(None, package))

    def test_may_require_job_allows_new_jobs(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.assertTrue(may_require_job(distroseries, package))

    def test_may_require_job_forbids_redundant_jobs(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        create_job(distroseries, package)
        self.assertFalse(may_require_job(distroseries, package))

    def test_may_require_job_forbids_jobs_on_nonderived_series(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertFalse(may_require_job(
            sourcepackage.distroseries, sourcepackage.sourcepackagename))

    def test_may_require_job_forbids_jobs_for_intra_distro_derivation(self):
        package = self.factory.makeSourcePackageName()
        parent = self.factory.makeDistroSeries()
        child = self.factory.makeDistroSeries(
            distribution=parent.distribution, parent_series=parent)
        self.assertFalse(may_require_job(child, package))

    def test_may_require_job_only_considers_waiting_jobs_for_redundancy(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        existing_job = create_job(distroseries, package)
        existing_job.job.start()
        self.assertTrue(may_require_job(distroseries, package))

    def test_create_job_creates_waiting_job(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        dsdjob = create_job(distroseries, package)
        self.assertEqual(JobStatus.WAITING, dsdjob.job.status)

    def find_waiting_jobs_finds_waiting_jobs(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        job = create_job(distroseries, sourcepackagename)
        self.assertContentEqual(
            [job], find_waiting_jobs(distroseries, sourcepackagename))

    def find_waiting_jobs_ignores_other_series(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        create_job(distroseries, sourcepackagename)
        other_series = self.factory.makeDistroSeries()
        self.assertContentEqual(
            [], find_waiting_jobs(other_series, sourcepackagename))

    def find_waiting_jobs_ignores_other_packages(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        create_job(distroseries, sourcepackagename)
        other_spn = self.factory.makeSourcePackageName()
        self.assertContentEqual(
            [], find_waiting_jobs(distroseries, other_spn))

    def find_waiting_jobs_considers_only_waiting_jobs(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        job = create_job(distroseries, sourcepackagename)
        job.start()
        self.assertContentEqual(
            [], find_waiting_jobs(distroseries, sourcepackagename))
        job.complete()
        self.assertContentEqual(
            [], find_waiting_jobs(distroseries, sourcepackagename))

    def test_createForPackagedPublication_creates_jobs_for_its_child(self):
        derived_series = self.factory.makeDistroSeries(
            parent_series=self.makeDerivedDistroSeries())
        package = self.factory.makeSourcePackageName()
        # Create a job for the derived_series parent, which should create
        # two jobs. One for derived_series, and the other for its child.
        self.getJobSource().createForPackagePublication(
            derived_series.parent_series, package)
        jobs = (list(
            find_waiting_jobs(derived_series.parent_series, package)) +
            list(find_waiting_jobs(derived_series, package)))
        self.assertEqual(2, len(jobs))
        self.assertEqual(package.id, jobs[0].metadata['sourcepackagename'])
        self.assertEqual(package.id, jobs[1].metadata['sourcepackagename'])
        # Lastly, a job was not created for the grandparent.
        jobs = list(
            find_waiting_jobs(derived_series.parent_series.parent_series,
                package))
        self.assertEqual(0, len(jobs))

    def test_createForPackagePublication_creates_job_for_derived_series(self):
        derived_series = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            derived_series, package)
        jobs = list(find_waiting_jobs(derived_series, package))
        self.assertEqual(1, len(jobs))
        self.assertEqual(package.id, jobs[0].metadata['sourcepackagename'])

    def test_createForPackagePublication_obeys_feature_flag(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: ''}))
        self.getJobSource().createForPackagePublication(distroseries, package)
        self.assertContentEqual([], find_waiting_jobs(distroseries, package))

    def test_cronscript(self):
        derived_series = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            derived_series, package)
        transaction.commit() # The cronscript is a different process.
        script = os.path.join(
            config.root, 'cronscripts', 'distroseriesdifference_job.py')
        args = [sys.executable, script, '-v']
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        # The cronscript ran how we expected it to.
        self.assertEqual(process.returncode, 0)
        self.assertIn(
            'INFO    Ran 1 DistroSeriesDifferenceJob jobs.', stderr)
        # And it did what we expected.
        jobs = list(find_waiting_jobs(derived_series, package))
        self.assertEqual(0, len(jobs))
        store = IMasterStore(DistroSeriesDifference)
        ds_diff = store.find(
            DistroSeriesDifference, 
            DistroSeriesDifference.derived_series == derived_series,
            DistroSeriesDifference.source_package_name == package)
        self.assertEqual(1, ds_diff.count())

    def test_job_runner_does_not_create_multiple_dsds(self):
        derived_series = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        job = self.getJobSource().createForPackagePublication(
            derived_series, package)
        job[0].start()
        job[0].run()
        job[0].job.complete() # So we can create another job.
        # The first job would have created a DSD for us.
        store = IMasterStore(DistroSeriesDifference)
        ds_diff = store.find(
            DistroSeriesDifference, 
            DistroSeriesDifference.derived_series == derived_series,
            DistroSeriesDifference.source_package_name == package)
        self.assertEqual(1, ds_diff.count())
        # If we run the job again, it will not create another DSD.
        job = self.getJobSource().createForPackagePublication(
            derived_series, package)
        job[0].start()
        job[0].run()
        ds_diff = store.find(
            DistroSeriesDifference, 
            DistroSeriesDifference.derived_series == derived_series,
            DistroSeriesDifference.source_package_name == package)
        self.assertEqual(1, ds_diff.count())


class TestDistroSeriesDifferenceJobPermissions(TestCaseWithFactory):
    """Database permissions test for `DistroSeriesDifferenceJob`."""

    layer = LaunchpadZopelessLayer

    def test_permissions(self):
        script_users = [
            'archivepublisher',
            'queued',
            'uploader',
            ]
        derived_series = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())
        packages = dict(
            (user, self.factory.makeSourcePackageName())
            for user in script_users)
        transaction.commit()
        for user in script_users:
            self.layer.switchDbUser(user)
            try:
                create_job(derived_series, packages[user])
            except ProgrammingError, e:
                self.assertTrue(
                    False,
                    "Database role %s was unable to create a job.  "
                    "Error was: %s" % (user, e))

        # The test is that we get here without exceptions.
        pass
