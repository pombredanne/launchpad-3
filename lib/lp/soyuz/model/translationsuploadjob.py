# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'TranslationsUploadJob',
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
from lp.soyuz.interfaces.translationsuploadjob import (
    ITranslationsUploadJob,
    ITranslationsUploadJobSource,
    )
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class TranslationsUploadJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    delegates(ITranslationsUploadJob)
    classProvides(ITranslationsUploadJobSource)
    config = config.ITranslationsUploadJobSource

    def __init__(self, job):
        assert job.base_job_type == JobType.UPLOAD_TRANSLATIONS_FILES
        self.job = job
        self.context = self

    @classmethod
    def create(cls, sourcepackagerelease, libraryfilealias):
        job = Job(
            base_job_type=JobType.UPLOAD_TRANSLATIONS_FILES,
            requester=sourcepackagerelease.creator,
            base_json_data=simplejson.dumps(
                {'sourcepackagerelease': sourcepackagerelease.id,
                 'libraryfilealias': libraryfilealias.id}))
        derived = cls(job)
        derived.celeryRunOnCommit()
        return derived

    @classmethod
    def get(cls, sourcepackagerelease, libraryfilealias):
        metadata = simplejson.dumps(
            {'sourcepackagerelease': sourcepackagerelease.id,
             'libraryfilealias': libraryfilealias.id})
        return cls(IStore(Job).find(Job, Job.base_json_data == metadata).one())

    @classmethod
    def iterReady(cls):
        jobs = IStore(Job).find(
            Job, Job.id.is_in(Job.ready_jobs),
            Job.base_job_type == JobType.UPLOAD_TRANSLATIONS_FILES)
        return [cls(job) for job in jobs]


class TranslationsUploadJob(TranslationsUploadJobDerived):

    implements(ITranslationsUploadJob)
    classProvides(ITranslationsUploadJobSource)

    @property
    def sourcepackagerelease_id(self):
        return simplejson.loads(self.base_json_data)['sourcepackagerelease']

    @property
    def libraryfilealias_id(self):
        return simplejson.loads(self.base_json_data)['libraryfilealias']

    @property
    def sourcepackagerelease(self):
        return SourcePackageRelease.get(self.sourcepackagerelease_id)

    @property
    def libraryfilealias(self):
        return getUtility(ILibraryFileAliasSet)[self.libraryfilealias_id]

    def run(self):
        sourcepackagerelease = self.sourcepackagerelease
        if sourcepackagerelease is not None:
            libraryfilealias = self.libraryfilealias
            importer = sourcepackagerelease.creator
            sourcepackagerelease.attachTranslationFiles(
                libraryfilealias, True, importer=importer)
