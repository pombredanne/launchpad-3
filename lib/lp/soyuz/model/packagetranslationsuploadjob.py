# Copyright 2013-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    '_filter_ubuntu_translation_file',
    'PackageTranslationsUploadJob',
    ]

import json

from lazr.delegates import delegate_to
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )

from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.job.interfaces.job import JobType
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.mail.sendmail import format_address_for_person
from lp.soyuz.interfaces.packagetranslationsuploadjob import (
    IPackageTranslationsUploadJob,
    IPackageTranslationsUploadJobSource,
    )
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )


def _filter_ubuntu_translation_file(filename):
    """Filter for translation filenames in tarball.

    Grooms filenames of translation files in tarball, returning None or
    empty string for files that should be ignored.

    Passed to `ITranslationImportQueue.addOrUpdateEntriesFromTarball`.
    """
    source_prefix = 'source/'
    if not filename.startswith(source_prefix):
        return None

    filename = filename[len(source_prefix):]

    blocked_prefixes = [
        # Translations for use by debconf--not used in Ubuntu.
        'debian/po/',
        # Debian Installer translations--treated separately.
        'd-i/',
        # Documentation--not translatable in Launchpad.
        'help/',
        'man/po/',
        'man/po4a/',
        ]

    for prefix in blocked_prefixes:
        if filename.startswith(prefix):
            return None

    return filename


@delegate_to(IPackageTranslationsUploadJob)
@provider(IPackageTranslationsUploadJobSource)
class PackageTranslationsUploadJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    config = config.IPackageTranslationsUploadJobSource

    def __init__(self, job):
        assert job.base_job_type == JobType.UPLOAD_PACKAGE_TRANSLATIONS
        self.job = job
        self.context = self

    def __repr__(self):
        return "<%(job_class)s for %(source)s in %(series)s>" % {
            "job_class": self.__class__.__name__,
            "source": self.sourcepackagename.name,
            "series": self.distroseries,
            }

    @classmethod
    def create(cls, distroseries, libraryfilealias, sourcepackagename,
               requester):
        job = Job(
            base_job_type=JobType.UPLOAD_PACKAGE_TRANSLATIONS,
            requester=requester,
            base_json_data=json.dumps(
                {'distroseries': distroseries.id,
                 'libraryfilealias': libraryfilealias.id,
                 'sourcepackagename': sourcepackagename.id,
                 }))
        derived = cls(job)
        derived.celeryRunOnCommit()
        return derived

    @classmethod
    def iterReady(cls):
        jobs = IStore(Job).find(
            Job, Job.id.is_in(Job.ready_jobs),
            Job.base_job_type == JobType.UPLOAD_PACKAGE_TRANSLATIONS)
        return (cls(job) for job in jobs)

    def getErrorRecipients(self):
        if self.requester is not None:
            return [format_address_for_person(self.requester)]
        return []

    @property
    def distroseries_id(self):
        return json.loads(self.base_json_data)['distroseries']

    @property
    def libraryfilealias_id(self):
        return json.loads(self.base_json_data)['libraryfilealias']

    @property
    def sourcepackagename_id(self):
        return json.loads(self.base_json_data)['sourcepackagename']

    @property
    def distroseries(self):
        return getUtility(IDistroSeriesSet).get(self.distroseries_id)

    @property
    def libraryfilealias(self):
        return getUtility(ILibraryFileAliasSet)[self.libraryfilealias_id]

    @property
    def sourcepackagename(self):
        return getUtility(ISourcePackageNameSet).get(self.sourcepackagename_id)


@implementer(IPackageTranslationsUploadJob)
@provider(IPackageTranslationsUploadJobSource)
class PackageTranslationsUploadJob(PackageTranslationsUploadJobDerived):

    def attachTranslationFiles(self, by_maintainer):
        distroseries = self.distroseries
        sourcepackagename = self.sourcepackagename
        only_templates = distroseries.getSourcePackage(
            sourcepackagename).has_sharing_translation_templates
        importer = self.requester
        tarball = self.libraryfilealias.read()

        queue = getUtility(ITranslationImportQueue)

        queue.addOrUpdateEntriesFromTarball(
            tarball, by_maintainer, importer,
            sourcepackagename=sourcepackagename,
            distroseries=distroseries,
            filename_filter=_filter_ubuntu_translation_file,
            only_templates=only_templates)

    def run(self):
        self.attachTranslationFiles(True)
