# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    '_filter_ubuntu_translation_file',
    'PackageTranslationsUploadJob',
    ]

from lazr.delegates import delegates
import simplejson
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

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
from lp.soyuz.model.queue import PackageUpload
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease

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


class PackageTranslationsUploadJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    delegates(IPackageTranslationsUploadJob)
    classProvides(IPackageTranslationsUploadJobSource)
    config = config.IPackageTranslationsUploadJobSource

    def __init__(self, job):
        assert job.base_job_type == JobType.UPLOAD_PACKAGE_TRANSLATIONS
        self.job = job
        self.context = self

    @classmethod
    def create(cls, packageupload, sourcepackagerelease, libraryfilealias,
               requester):
        job = Job(
            base_job_type=JobType.UPLOAD_PACKAGE_TRANSLATIONS,
            requester=requester,
            base_json_data=simplejson.dumps(
                {'packageupload': packageupload.id,
                 'sourcepackagerelease': sourcepackagerelease.id,
                 'libraryfilealias': libraryfilealias.id}))
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


class PackageTranslationsUploadJob(PackageTranslationsUploadJobDerived):

    implements(IPackageTranslationsUploadJob)
    classProvides(IPackageTranslationsUploadJobSource)

    @property
    def packageupload_id(self):
        return simplejson.loads(self.base_json_data)['packageupload']

    @property
    def sourcepackagerelease_id(self):
        return simplejson.loads(self.base_json_data)['sourcepackagerelease']

    @property
    def libraryfilealias_id(self):
        return simplejson.loads(self.base_json_data)['libraryfilealias']

    @property
    def packageupload(self):
        return PackageUpload.get(self.packageupload_id)

    @property
    def sourcepackagerelease(self):
        return SourcePackageRelease.get(self.sourcepackagerelease_id)

    @property
    def libraryfilealias(self):
        return getUtility(ILibraryFileAliasSet)[self.libraryfilealias_id]

    def attachTranslationFiles(self, by_maintainer):
        pu = self.packageupload
        spr = self.sourcepackagerelease
        only_templates = spr.sourcepackage.has_sharing_translation_templates
        importer = self.requester
        tarball = self.libraryfilealias.read()

        queue = getUtility(ITranslationImportQueue)

        queue.addOrUpdateEntriesFromTarball(
            tarball, by_maintainer, importer,
            sourcepackagename=spr.sourcepackagename,
            distroseries=pu.distroseries,
            filename_filter=_filter_ubuntu_translation_file,
            only_templates=only_templates)

    def run(self):
        self.attachTranslationFiles(True)
