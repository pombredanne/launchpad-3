#!/usr/bin/python
# arch-tag: 7dec9a9d-a8c2-465e-8843-7b2204c1f85c
#
# Copyright (C) 2004 Canonical Software
# 	Authors: Rob Weir <rob.weir@canonical.com>
#		 Robert Collins <robert.collins@canonical.com>

"""Common code for the test suite for the database and broker layers."""

import unittest
import sys
import os
import shutil
from zope.interface.verify import verifyClass, verifyObject
from canonical.arch.database import dbname, nuke
import psycopg
import tempfile
import arch

class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        self.__db_handle = psycopg.connect(dbname())
        self.flushArchiveData(self.cursor())
        self._archive = None
        self._category = None
        self._branch = None
        self._version = None
        self._revision = None

    def tearDown(self):
        self.commit()

    def commit(self):
        self.__db_handle.commit()

    def cursor(self):
        return self.__db_handle.cursor()

    def flushArchiveData(self, cursor):
        """Remove all ArchArchive and ArchArchiveLocation entries"""
        nuke()
#         cursor.execute("DELETE FROM Changeset")
#         cursor.execute("DELETE FROM ArchArchiveLocation")
#         cursor.execute("DELETE FROM Branch")
#         cursor.execute("DELETE FROM ArchArchive")
        self.commit()

    def _getTestArchive(self):
        """Insert a test archive into the db and return it"""
        from canonical.arch.broker import Archive
        from canonical.arch.database import ArchiveMapper
        archive = Archive("foo@bar")
        archiveMapper = ArchiveMapper()
        archiveMapper.insert(archive)
        return archive

    def getTestArchive(self):
        """Return the stored archive"""
        if self._archive is None:
            self._archive = self._getTestArchive()
        return self._archive

    def _getTestCategory(self):
        """Insert a test category into the db and return it"""
        from canonical.arch.database import CategoryMapper
        from canonical.arch.broker import Category
        category = Category("bah", self.getTestArchive())
        categoryMapper = CategoryMapper()
        categoryMapper.insert(category)
        return category

    def getTestCategory(self):
        """return the stored category"""
        if self._category is None:
            self._category = self._getTestCategory()
        return self._category

    def _getTestBranch(self, name="meh"):
        """Insert a test branch into the db and return it"""
        from canonical.arch.database import BranchMapper
        from canonical.arch.broker import Branch
        branch = Branch(name, self.getTestCategory())
        branchMapper = BranchMapper()
        branchMapper.insert(branch)
        return branch
    
    def getTestBranch(self, name="meh"):
        """return the stored branch"""
        if self._branch is None:
            self._branch = self._getTestBranch(name)
        return self._branch

    def _getTestVersion(self):
        """Insert a test version into the db and return it"""
        from canonical.arch.database import VersionMapper
        from canonical.arch.broker import Version
        version = Version("0", self.getTestBranch())
        versionMapper = VersionMapper()
        versionMapper.insert(version)
        return version
    
    def getTestVersion(self):
        """return the stored version"""
        if self._version is None:
            self._version = self._getTestVersion()
        return self._version

    def _getTestRevision(self):
        """Insert a test revision into the db and return it"""
        from canonical.arch.database import RevisionMapper
        from canonical.arch.broker import Revision
        revision = Revision("base-0", self.getTestVersion())
        revisionMapper = RevisionMapper()
        revisionMapper.insert(revision)
        return revision
    
    def getTestRevision(self):
        """return the stored revision"""
        if self._revision is None:
            self._revision = self._getTestRevision()
        return self._revision


class DatabaseAndArchiveTestCase(DatabaseTestCase):

    # FIXME: A lot of stuff here should be factored out with PyArch
    # test framework when the PyArch test suite will be reorganized.
    
    def setUp(self):
        DatabaseTestCase.setUp(self)
        self._saved_env_home = os.environ.get('HOME')
        if os.environ.has_key('EDITOR'):
            self._saved_env_editor = os.environ['EDITOR']
            del(os.environ['EDITOR'])
        else:
            self._saved_env_editor = None
        self._saved_working_directory = os.getcwd()
        tmp_dir = arch.DirName(tempfile.mkdtemp(prefix='pyarch-')).realpath()
        self._arch_tmp_home = tmp_dir
        os.environ['HOME'] = self._arch_tmp_home
        self._arch_dir = tmp_dir / arch.DirName(r'pyarch\(sp)tests')
        os.mkdir(self._arch_dir)

    def tearDown(self):
        os.environ['HOME'] = self._saved_env_home
        shutil.rmtree(self._arch_tmp_home, ignore_errors=True)
        if self._saved_env_editor is not None:
            os.environ['EDITOR'] = self._saved_env_editor
        os.chdir(self._saved_working_directory)
        DatabaseTestCase.tearDown(self)

    def arch_set_user_id(self):
        arch.set_my_id("John Doe <jdoe@example.com>")

    def arch_make_archive(self, name):
        return arch.make_archive(name, self._arch_dir/name)

    def arch_make_tree(self, name, version):
        path = self._arch_dir/name
        os.mkdir(path)
        return arch.init_tree(path, version)


class TestFramework(unittest.TestCase):

    tests = []

    def test_flushArchiveData(self):
        """test that flushArchiveData works"""

        DBHandle = psycopg.connect(dbname())
        cursor = DBHandle.cursor()
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % "bah@bleh")
        DBHandle.commit()
        
        DBHandle = None
        cursor = None

        framework = DatabaseTestCase("commit")
        framework.setUp() 

        DBHandle = psycopg.connect(dbname())
        cursor = DBHandle.cursor()
        
        cursor.execute("SELECT * FROM ArchArchive")
        self.assertEqual(len(cursor.fetchall()), 0)

        cursor.execute("SELECT * FROM ArchNamespace")
        self.assertEqual(len(cursor.fetchall()), 0)
        
        cursor.execute("SELECT * FROM ArchArchiveLocation")
        self.assertEqual(len(cursor.fetchall()), 0)

        cursor.execute("SELECT * FROM Branch")
        self.assertEqual(len(cursor.fetchall()), 0)

        cursor.execute("SELECT * FROM Changeset")
        self.assertEqual(len(cursor.fetchall()), 0)
    tests.append('test_flushArchiveData')

def test_suite():
    return unittest.TestSuite()

def main(argv):
    """Run the full test suite."""
    suite = unittest.TestSuite()
    def addTests(klass): suite.addTests(map(klass, klass.tests))
    # there should be a more elegant way - addClasses or something
    map(addTests, (TestFramework,))
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful(): return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

