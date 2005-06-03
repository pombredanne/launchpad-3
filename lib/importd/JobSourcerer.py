# Copyright 2004 Canonical Ltd.
# Authors:
#     Robert Collins  <robertc@robertcollins.net>
#     David Allouche <david@allouche.net>

import os
import shutil

from canonical.lp import initZopeless
from canonical.launchpad import database
from canonical.doap import fileimporter
from linkscrape import getweb
from canonical.librarian.client import FileDownloadClient
from sourcerer import deb
from sourcerer import bubblewrap


class BubblewrapMethod(self):

    def __init__(self, job, wdir, logger):
        self.wdir = wdir
        self.job = job
        self.logger = logger

    def run(self):
        '''run Sourcerer over a recently imported task'''
        self.initTxnManager() # sets job.txnManager
        ### TEMP
        self.job.txnManager = self.txnManager
        ###
        importer = self.makeFileImporter()
        self.importReleasesIntoLibrarian(importer)
        self.txnManager.commit()
        self.ungodlyZopelessHack()
        librarian = self.makeDownloadClient()
        print 'importer.getReleases =>', list(importer.getReleases())
        todo = self.makeTodo(importer)
        print 'todo =', todo
        self.job.bubblewrapImport(importer, librarian, todo)
        self.job.txnManager.commit()

    def initTxnManager(self):
        # FIXME: redundant initZopeless, the txnManager should be set at object
        # creation. -- David Allouche 2005-02-08
        if self.txnManager is None:
            self.txnManager = initZopeless()

    def makeFileImporter(self):
        product = database.Product.get(self.job.product_id)
        return fileimporter.ProductReleaseImporter(product)

    def importReleasesIntoLibrarian(self, importer):
        webdir = getweb.getwebdir(self.job.releaseRoot)
        urls = webdir.glob(self.job.releaseFileGlob)
        for url in urls:
            try:
                print "found url:", url
                importer.addURL (url)
            except ValueError:
                self.logger.critical('Failed to retrieve url %s', url)

    def ungodlyZopelessHack(self):
        # XXX: Awful hack -- the librarian's updated the database, so we need
        # to reset our connection so that we can see it.
        # -- Andrew Bennetts, 2005-01-27
        from canonical.database.sqlbase import SQLBase
        SQLBase._connection.rollback()
        SQLBase._connection.begin()
        self.txnManager.begin()

    def makeDownloadClient(self):
        host = os.environ.get('LIBRARIAN_HOST', 'macaroni.ubuntu.com')
        librarian = FileDownloadClient(host, 8000)
        librarian.logger = self.logger
        return librarian

    def makeTodo(self, importer):
        # XXX: Need a more descriptive name -- DavidAllouche 2005-02-11
        todo = []
        for release in importer.getReleases():
            for file in release.files:
                todo_item = (file.libraryfile.filename, file, release)
                todo.append(todo_item)
        todo.sort(lambda l,r: deb.version.deb_cmp(l[0],r[0]))
        return todo

    def bubblewrapImport(self, importer, librarian, todo):
        # XXX: Need a more descriptive name -- DavidAllouche 2005-02-11
        for filename, file, release in todo:
            #clean out sourcerer
            sourcererDir = os.path.join(self.getWorkingDir(), 'sourcerer')
            shutil.rmtree(sourcererDir, ignore_errors = True)
            os.makedirs(sourcererDir)
            #extract the file to self.getWorkingDir(dir) + 'sourcerer'
            inputFile = librarian.getFileByAlias (file.libraryfile.id)
            tarballPath = os.path.join (sourcererDir, filename)
            outFile = open(tarballPath, 'w')
            for chunk in iter(lambda: inputFile.read(4096), ''):
                outFile.write(chunk)
            outFile.close()
            manifest_args = (
                [tarballPath],
                self.getArchiveName(),
                None,
                self.logger,
                sourcererDir,)
            manifest_kwargs = {
                'success_func': self.mirrorVersion,
                'error_func': self.RollbackToMirror,}
            print 'manifest call ', manifest_args, manifest_kwargs
            # bubblewrap returns a manifest, but we have nothing to do with it
            # if anything goes wrong, it will raise an exception
            bubblewrap.run(*manifest_args, **manifest_kwargs)

    def getWorkingDir(self):
        return self.job.getWorkingDir(self.wdir)

    def getArchiveName(self):
        return self.job.archivename

    def RollbackToMirror(self, version):
        self.job.RollbackToMirror(version)

    def mirrorVersion(self, version):
        self.job.mirrorVersion(self.wdir, self.logger, version)
