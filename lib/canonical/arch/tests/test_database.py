#!/usr/bin/env python
#
# arch-tag: 794e491c-ce40-4a66-a325-72984e7dbbbd
#
# Copyright (C) 2004 Canonical Software
# 	Authors: Rob Weir <rob.weir@canonical.com>
#		 Robert Collins <robert.collins@canonical.com>

"""Test suite for Canonical broker broker module."""

import unittest
import sys
from zope.interface.verify import verifyClass, verifyObject
from canonical.arch.tests.test_framework import DatabaseTestCase
from canonical.arch.database import DBHandle

class Database(DatabaseTestCase):

    tests = []

    def test_imports(self):
        """canonical.arch.database is importable."""
        import canonical.arch.database
    tests.append('test_imports')

    def test_archive_doesnt_exist(self):
        """a query for a non extant archive returns false"""
        import canonical.arch.database
        cursor = self.cursor()
        archive_name = "test@example.com--archive"
        cursor.execute("DELETE FROM ArchArchive WHERE name = '%s'" % archive_name)
        self.commit()
        self.failIf(canonical.arch.database.archive_present(archive_name))
    tests.append('test_archive_doesnt_exist')

    def test__archive_purge_missing(self):
        """test unconditional purging of an archive not present."""
        # this test is incomplete. we should add categories etc
        # and check they are nuked too.
        import canonical.arch.database
        cursor = self.cursor()
        archive_name = "test@example.com--archive"
        cursor.execute("DELETE FROM ArchArchive WHERE name = '%s'" % archive_name)
        self.commit()
        canonical.arch.database._archive_purge(archive_name)
        self.failIf(canonical.arch.database.archive_present(archive_name))
        self.commit()
    tests.append('test__archive_purge_missing')
        
    def test__archive_purge_present(self):
        """test unconditional purging of an archive that is present."""
        # this test is incomplete. we should add categories etc
        # and check they are nuked too.
        import canonical.arch.database
        cursor = self.cursor()
        archive_name = "test@example.com--archive"
        cursor.execute("DELETE FROM ArchArchive WHERE name = '%s'" % archive_name)
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % archive_name)
        self.commit()
        canonical.arch.database._archive_purge(archive_name)
        self.failIf(canonical.arch.database.archive_present(archive_name))
    tests.append('test__archive_purge_present')


class ArchiveMapper(DatabaseTestCase):
    
    tests = []

    def test_ArchiveMapperFindMissing(self):
        """test ArchiveMappter.findByName("foo") returns a MissingArchive"""
        from canonical.arch.database import _archive_purge, ArchiveMapper
        from canonical.arch.broker import MissingArchive
        name="foo@bar"
        cursor = self.cursor()
        _archive_purge(name)
        mapper=ArchiveMapper()
        self.failUnless(isinstance(mapper.findByName(name), MissingArchive))
    tests.append('test_ArchiveMapperFindMissing')

    def test_ArchiveMapperFindPresent(self):
        """test ArchiveMapper.findByName("foo") returns an Archive"""
        from canonical.arch.database import _archive_purge, ArchiveMapper, connect
        from canonical.arch.broker import MissingArchive
        name="foo@bar"
        cursor = self.cursor()
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % name)
        self.commit()
        connect()
        mapper=ArchiveMapper()
        archive=mapper.findByName(name)
        self.failIf(isinstance(archive, MissingArchive))
        self.assertEqual(archive.name, name)
        self.failUnless(archive.exists())
    tests.append('test_ArchiveMapperFindPresent')

    def test_ArchiveMapperFindMultiple(self):
        """test ArchiveMapper.findByName("foo@%") returns an list of archives"""
        from canonical.arch.database import _archive_purge, ArchiveMapper, commit, connect
        from canonical.arch.broker import MissingArchive
        name1="foo@bar"
        name2="foo@gam"
        cursor = self.cursor()
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % name1)
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % name2)
        self.commit()
        connect()
        mapper=ArchiveMapper()
        archives=mapper.findByMatchingName('foo@%')
        self.failIf(isinstance(archives, MissingArchive))
        self.assertEqual(archives[0].name, name1)
        self.assertEqual(archives[1].name, name2)
        self.failUnless(archives[0].exists())
        self.failUnless(archives[1].exists())
    tests.append('test_ArchiveMapperFindMultiple')

    def test_ArchiveMapperInsertPresent(self):
        """test canonical.arch.ArchiveMapper.insert fails when an archive already exists."""
        from canonical.arch.database import _archive_purge, ArchiveMapper, commit
        from canonical.arch.broker import Archive
        name="foo@bar"
        cursor = self.cursor()
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % name)
        self.commit()
        mapper=ArchiveMapper()
        self.assertRaises(KeyError, mapper.insert, Archive(name))
    tests.append('test_ArchiveMapperInsertPresent')
    
    def test_ArchiveMapperInsertNew(self):
        """test ArchiveMapper.insert works when an archive is new."""
        from canonical.arch.database import _archive_purge, ArchiveMapper
        from canonical.arch.broker import MissingArchive
        name="foo@bar"
        _archive_purge(name)
        cursor = self.cursor()
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % name)
        self.commit()
        mapper=ArchiveMapper()
        mapper.insert(Archive(name))
        archive=mapper.findByName(name)
        self.failUnless(archive.exists())
    tests.append('test_ArchiveMapperFindPresent')

    def test_ArchiveMapperGetId(self):
        """test we can get the archive id correctly"""
        from canonical.arch.database import _archive_purge, ArchiveMapper, connect
        from canonical.arch.broker import Archive
        name="foo@bar"
        cursor = self.cursor()
        cursor.execute("INSERT INTO ArchArchive (name, title, description, visible) VALUES ('%s', 'a title', 'a description', true)" % name)
        cursor.execute("SELECT currval('archarchive_id_seq')");
        new_id = cursor.fetchone()[0]
        self.commit()
        connect()
        mapper=ArchiveMapper()
        self.assertEqual(new_id, mapper._getId(Archive(name), cursor))
    tests.append('test_ArchiveMapperGetId')

class ArchiveLocationMapper(DatabaseTestCase):

    tests = []

    def test_ArchiveLocationMapperGetAllNone(self):
        """test that we can get an empty list when there are no registered Locations"""
        from canonical.arch.broker import Archive
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper
        cursor = self.cursor()
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        self.assertEqual(archiveLocationMapper.getAll(archive), [])
    tests.append('test_ArchiveLocationMapperGetAllNone')
    
    def test_ArchiveLocationMapperGetAllLots(self):
        """test that we can get back the correct urls from the db"""
        locations = ["http://googo.com/foo", "http://fooboo.com/bar", "http://barbar.com/bleh"]
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper
        cursor = self.cursor()
        archive = self.getTestArchive()
        archiveMapper = ArchiveMapper()
        archiveLocationMapper = ArchiveLocationMapper()
        for location in locations:
            cursor.execute("INSERT INTO ArchArchiveLocation (archive, archivetype, url, gpgsigned) " \
                           "VALUES (%s, %s, '%s', '%s')" %
                           (archiveMapper._getId(archive, cursor), '0', location, 'true'))
        self.commit()
        output = archiveLocationMapper.getAll(archive)
        for (l,r) in zip(locations, output):
            print
            print l
            print r.url
            self.assertEqual(l, r.url)
    #tests.append('test_ArchiveLocationMapperGetAllLots')

    def test_ArchiveLocationMapperInsertLocation(self):
        """test that we can insert a location"""
        url = "http://googo.com/foo"
        from canonical.arch.broker import Archive, ArchiveLocation
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper, connect, commit
        connect()
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        location = ArchiveLocation(archive, url, 0)
        archiveLocationMapper.insertLocation(location)
        commit()
        cursor = self.cursor()
        cursor.execute("SELECT count(*) FROM ArchArchiveLocation WHERE url = '%s'" % location.url)
        self.assertEqual(cursor.fetchone()[0], 1)
        self.failUnless(archiveLocationMapper.locationExists(location))
    tests.append('test_ArchiveLocationMapperInsertLocation')
    
    def test_ArchiveLocationMapperExistsNone(self):
        """Test we can tell if a location is not in the db"""
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper, connect, commit
        from canonical.arch.broker import Archive, ArchiveLocation
        location = "http://foo.com/"
        connect()
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        location = ArchiveLocation(archive, location, 0)
        commit()
        self.failIf(archiveLocationMapper.locationExists(location))
    tests.append('test_ArchiveLocationMapperExistsNone')

    def test_ArchiveLocationMapperExistsOne(self):
        """Test we can tell if a location is in the db"""
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper, connect, commit
        from canonical.arch.broker import Archive, ArchiveLocation
        location = "http://foo.com/"
        connect()
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        location = ArchiveLocation(archive, location, 0)
        archiveLocationMapper.insertLocation(location)
        commit()
        self.failUnless(archiveLocationMapper.locationExists(location))
    tests.append('test_ArchiveLocationMapperExistsOne')

    def test_ArchiveLocationMapperExistsTwo(self):
        """Test that duplicated urls are an error"""
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper, connect, commit
        from canonical.arch.broker import Archive, ArchiveLocation
        location = "http://foo.com/"
        connect()
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()

        location1 = ArchiveLocation(archive, location, 0)
        archiveLocationMapper.insertLocation(location1)

        location2 = ArchiveLocation(archive, location, 0)
        archiveLocationMapper.insertLocation(location2)

        from canonical.arch.interfaces import ArchiveLocationDoublyRegistered
        commit()
        self.assertRaises(ArchiveLocationDoublyRegistered, archiveLocationMapper.locationExists, location1)
        self.assertRaises(ArchiveLocationDoublyRegistered, archiveLocationMapper.locationExists, location2)
    tests.append('test_ArchiveLocationMapperExistsTwo')

    def test_ArchiveLocationMapperGetSomeNone(self):
        """Test that we can get no locations with a criteria"""
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper, connect, commit
        from canonical.arch.broker import Archive, ArchiveLocation
        location = "http://foo.com/"
        connect()
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        commit()
        self.assertEqual(archiveLocationMapper.getSome(archive, 0), [])
    tests.append('test_ArchiveLocationMapperGetSomeNone')

    def test_ArchiveLocationMapperGetSomeMore(self):
        """Test that we can get some locations with criteria"""
        from canonical.arch.database import ArchiveMapper, ArchiveLocationMapper, connect, commit
        from canonical.arch.broker import Archive, ArchiveLocation
        locations = ["http://googo.com/foo", "http://fooboo.com/bar", "http://barbar.com/bleh"]

        connect()
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()

        locs = []
        
        for i in range(0,2):
            for location in locations:
                locs.append(ArchiveLocation(archive, location, i))
                archiveLocationMapper.insertLocation(locs[-1])
                self.commit()

    tests.append('test_ArchiveLocationMapperGetSomeMore')

class CategoryMapper(DatabaseTestCase):

    tests = []

    def test_CategoryMapperInstantiation(self):
        """Test that we can create a CategoryMapper object"""
        from canonical.arch.database import CategoryMapper
        foo = CategoryMapper()
    tests.append('test_CategoryMapperInstantiation')

    def test_CategoryMapperInsertNew(self):
        """Test that CategoryMapper.insert works for non-existent categories"""
        from canonical.arch.database import ArchiveMapper, CategoryMapper, connect, commit
        from canonical.arch.broker import Archive, Category
        connect()
        archive = self.getTestArchive()
        name = "fnord"
        mapper = CategoryMapper()
        category = Category(name, archive)
        mapper.insert(category)
        commit()
        connect()
        # FIXME: read the category back in and check that the data matches
        self.failUnless(category.exists())
    tests.append('test_CategoryMapperInsertNew')

    def test_CategoryMapperInsertExisting(self):
        """Test that inserting an existing Category raises an exception"""
        from canonical.arch.database import ArchiveMapper, CategoryMapper, connect, commit
        from canonical.arch.broker import Archive, Category
        from canonical.arch.interfaces import CategoryAlreadyRegistered
        connect()
        archive = self.getTestArchive()
        name = "fnord"
        mapper = CategoryMapper()
        category = Category(name, archive)
        mapper.insert(category)
        commit()
        connect()
        self.assertRaises(CategoryAlreadyRegistered, mapper.insert, category)
        self.failUnless(mapper.exists(category))
    tests.append('test_CategoryMapperInsertExisting')

    def test_category_exist_missing(self):
        """Test that we can tell that a category doesn't exist."""
        from canonical.arch.database import CategoryMapper, connect, commit
        from canonical.arch.broker import Category
        name = "blah"
        connect()
        archive = self.getTestArchive()
        mapper = CategoryMapper()
        category = Category(name, archive)
        commit()
        connect()
        self.failIf(mapper.exists(category))
    tests.append('test_category_exist_missing')
        
    def test_category_exist_present(self):
        """Test that we can tell that a category does exist."""
        from canonical.arch.broker import Category, Archive
        from canonical.arch.database import CategoryMapper, connect, commit
        connect()
        name = "category"
        archive = self.getTestArchive()
        category = Category(name, archive)
        mapper = CategoryMapper()
        mapper.insert(category)
        commit()
        connect()
        self.failUnless(mapper.exists(category))
    tests.append('test_category_exist_present')
    

class BranchMapper(DatabaseTestCase):

    tests = []

    def test_BranchMapperInstantiation(self):
        """Test that we can create a BranchMapper object"""
        from canonical.arch.database import BranchMapper
        foo = BranchMapper()
    tests.append('test_BranchMapperInstantiation')

    def test_BranchMapperInsertNew(self):
        """Test that BranchMapper.insert works for non-existent categories"""
        from canonical.arch.database import ArchiveMapper, CategoryMapper, BranchMapper, connect, commit
        from canonical.arch.broker import Archive, Category, Branch
        connect()
        archive = self.getTestArchive()
        name = "fnord"
        mapper = CategoryMapper()
        category = Category(name, archive)
        mapper.insert(category)
        name = "barnch" # deliberate, smart-arse
        mapper = BranchMapper()
        branch = Branch(name, category)
        mapper.insert(branch)
        commit()
        connect()
        # FIXME: read the branch back in and check that the data matches
        self.failUnless(branch.exists())
    tests.append('test_BranchMapperInsertNew')

    def test_BranchMapperInsertExisting(self):
        """Test that inserting an existing Branch raises an exception"""
        from canonical.arch.database import ArchiveMapper, CategoryMapper, BranchMapper, connect, commit
        from canonical.arch.broker import Archive, Category, Branch
        from canonical.arch.interfaces import BranchAlreadyRegistered
        name = "barnch"
        connect()
        mapper = BranchMapper()
        branch = Branch(name, self.getTestCategory())
        mapper.insert(branch)
        commit()
        connect()
        self.assertRaises(BranchAlreadyRegistered, mapper.insert, branch)
        self.failUnless(mapper.exists(branch))
    tests.append('test_BranchMapperInsertExisting')

    def test_branch_exist_missing(self):
        """Test that we can tell that a Branch doesn't exist."""
        from canonical.arch.database import BranchMapper, connect, commit
        from canonical.arch.broker import Branch
        name = "blah"
        connect()
        branch = Branch(name, self.getTestCategory())
        mapper = BranchMapper()
        commit()
        connect()
        self.failIf(mapper.exists(branch))
    tests.append('test_branch_exist_missing')
        
    def test_branch_exist_present(self):
        """Test that we can tell that a Branch does exist."""
        from canonical.arch.broker import Branch
        from canonical.arch.database import BranchMapper, connect, commit
        name = "branch"
        connect()
        branch = Branch(name, self.getTestCategory())
        mapper = BranchMapper()
        mapper.insert(branch)
        commit()
        connect()
        self.failUnless(mapper.exists(branch))
    tests.append('test_branch_exist_present')

class VersionMapper(DatabaseTestCase):

    tests = []
    
    def test_VersionMapperInstantiation(self):
        """Test that we can create a VersionMapper object"""
        from canonical.arch.database import VersionMapper
        foo = VersionMapper()
    tests.append('test_VersionMapperInstantiation')

    def test_VersionMapperInsertNew(self):
        """Test that VersionMapper.insert works for non-existent versions"""
        from canonical.arch.database import ArchiveMapper, CategoryMapper, BranchMapper, VersionMapper, connect, commit
        from canonical.arch.broker import Archive, Category, Branch, Version
        connect()
        archive = self.getTestArchive()
        name = "fnord"
        mapper = CategoryMapper()
        category = Category(name, archive)
        mapper.insert(category)
        name = "barnch" # deliberate, smart-arse
        mapper = BranchMapper()
        branch = Branch(name, category)
        mapper.insert(branch)
        name = "0"
        mapper = VersionMapper()
        version = Version(name, branch)
        mapper.insert(version)
        commit()
        connect()
        # FIXME: read the branch back in and check that the data matches
        self.failUnless(mapper.exists(version))
    tests.append('test_VersionMapperInsertNew')

    def test_VersionMapperInsertExisting(self):
        """Test that inserting an existing Version raises an exception"""
        from canonical.arch.database import ArchiveMapper, CategoryMapper, BranchMapper, VersionMapper, connect, commit
        from canonical.arch.broker import Archive, Category, Branch, Version
        from canonical.arch.interfaces import VersionAlreadyRegistered
        name = "0"
        connect()
        mapper = VersionMapper()
        version = Version(name, self.getTestBranch())
        mapper.insert(version)
        commit()
        connect()
        self.assertRaises(VersionAlreadyRegistered, mapper.insert, version)
        self.failUnless(mapper.exists(version))
    tests.append('test_VersionMapperInsertExisting')

    def test_version_exist_missing(self):
        """Test that we can tell that a Version doesn't exist."""
        from canonical.arch.database import VersionMapper, connect, commit
        from canonical.arch.broker import Version
        name = "0"
        connect()
        version = Version(name, self.getTestVersion())
        commit()
        connect()
        mapper = VersionMapper()
        self.failIf(mapper.exists(version))
    tests.append('test_version_exist_missing')
        
    def test_version_exist_present(self):
        """Test that we can tell that a Version does exist."""
        from canonical.arch.broker import Version
        from canonical.arch.database import VersionMapper, connect, commit
        name = "0"
        connect()
        version = Version(name, self.getTestBranch())
        mapper = VersionMapper()
        mapper.insert(version)
        commit()
        connect()
        self.failUnless(mapper.exists(version))
    tests.append('test_version_exist_present')

    def test_VersionMapperGetId(self):
        """test we can get the Version id correctly"""
        from canonical.arch.database import ArchiveMapper, VersionMapper, commit, connect
        from canonical.arch.broker import Archive
        connect()
        version = self.getTestVersion()
        commit()
        cursor = self.cursor()
        cursor.execute("SELECT id FROM archnamespace WHERE category = '%s' AND branch = '%s' AND version = '%s'" %
                       (version.branch.category.name, version.branch.name, version.name))
        expected_id = cursor.fetchall()[0][0]
        connect()
        mapper = VersionMapper()
        self.assertEqual(expected_id, mapper._getId(version, cursor))
    tests.append('test_VersionMapperGetId')
    def test_VersionMapperGetDBBranchId(self):
        """test we can get the Version id for the 'Branch' correctly"""
        from canonical.arch.database import ArchiveMapper, VersionMapper, commit, connect
        from canonical.arch.broker import Archive
        connect()
        version = self.getTestVersion()
        commit()
        version_id=VersionMapper()._getId(version)
        cursor = self.cursor()
        cursor.execute("SELECT id FROM branch WHERE archnamespace = %d" % version_id)
        expected_id = cursor.fetchall()[0][0]
        connect()
        mapper = VersionMapper()
        self.assertEqual(expected_id, mapper._getDBBranchId(version))
    tests.append('test_VersionMapperGetDBBranchId')


class RevisionMapper(DatabaseTestCase):

    tests = []
    
    def test_RevisionMapperInstantiation(self):
        """Test that we can create a RevisionMapper object"""
        from canonical.arch.database import RevisionMapper
        foo = RevisionMapper()
    tests.append('test_RevisionMapperInstantiation')

    def test_RevisionMapperInsertNew(self):
        """Test that RevisionMapper.insert works for non-existent revisions"""
        from canonical.arch.database import RevisionMapper, connect, commit
        connect()
        mapper = RevisionMapper()
        revision = self.getTestRevision()
        commit()
        # FIXME: read the branch back in and check that the data matches
        connect()
        self.failUnless(mapper.exists(revision))
    tests.append('test_RevisionMapperInsertNew')

    def test_RevisionMapperExists(self):
        """test revision mapper exists works for existing ones"""
        from canonical.arch.database import VersionMapper, RevisionMapper, connect, commit
        connect()
        mapper = RevisionMapper()
        revision = self.getTestRevision()
        commit()
        connect()
        c = self.cursor()
        branchid = VersionMapper()._getDBBranchId(revision.version)
        print "branchid = %r" % branchid
        c.execute("SELECT count(*) FROM Changeset where branch = %d" % branchid)
        self.assertEqual(c.fetchone()[0], 1)
        self.failUnless(mapper.exists(revision), "It's in the DB, why isn't the mapper noticing?")
    tests.append('test_RevisionMapperExists')

    def test_RevisionMapperDoesntExist(self):
        """test revision mapper exists works for non-exustant ones"""
        from canonical.arch.database import VersionMapper, RevisionMapper, BranchMapper, connect, commit
        from canonical.arch.broker import Revision
        connect()
        mapper = RevisionMapper()
        version = self.getTestVersion()
        commit()
        connect()
        c = self.cursor()
        branchid = VersionMapper()._getId(version)
        revision = Revision("base-0", version)
        c.execute("SELECT count(*) FROM Changeset WHERE branch = %d" % branchid)
        self.assertEqual(c.fetchone()[0], 0)
        self.failIf(mapper.exists(revision), "It's not in the DB, why does the mapper think it is?")
    tests.append('test_RevisionMapperDoesntExist')

    def test_VersionMapperInsertExisting(self):
        """Test that inserting an existing Version raises an exception"""
        from canonical.arch.database import ArchiveMapper, CategoryMapper, BranchMapper, VersionMapper, connect, commit
        from canonical.arch.broker import Archive, Category, Branch, Version
        from canonical.arch.interfaces import VersionAlreadyRegistered
        name = "0"
        mapper = VersionMapper()
        connect()
        version = Version(name, self.getTestBranch())
        mapper.insert(version)
        commit()
        connect()
        self.assertRaises(VersionAlreadyRegistered, mapper.insert, version)
        self.failUnless(mapper.exists(version))
#    tests.append('test_VersionMapperInsertExisting')

    def test_version_exist_missing(self):
        """Test that we can tell that a Version doesn't exist."""
        from canonical.arch.database import VersionMapper
        from canonical.arch.broker import Version
        name = "0"
        version = Version(name, self.getTestVersion())
        mapper = VersionMapper()
        self.failIf(mapper.exists(version))
#    tests.append('test_version_exist_missing')
        
    def test_version_exist_present(self):
        """Test that we can tell that a Version does exist."""
        from canonical.arch.broker import Version
        from canonical.arch.database import VersionMapper
        cursor = self.cursor()
        name = "0"
        version = Version(name, self.getTestBranch())
        mapper = VersionMapper()
        mapper.insert(version)
        self.commit()
        self.failUnless(mapper.exists(version))
#    tests.append('test_version_exist_present')

    def test_version_exist_imposter(self):
        """Test that we can tell that a Version doesn't exist, regardless of
        other branches."""
        from canonical.arch.broker import Version
        from canonical.arch.database import VersionMapper
        cursor = self.cursor()
        name = "0"
        version = Version(name, self.getTestBranch())
        mapper = VersionMapper()
        mapper.insert(version)
        self.commit()
        otherversion = Version(name, self.getTestBranch('other'))
        self.failIf(mapper.exists(otherversion))
    tests.append('test_version_exist_imposter')

    def test_VersionMapperGetId(self):
        """test we can get the Version id correctly"""
        from canonical.arch.database import ArchiveMapper, VersionMapper
        from canonical.arch.broker import Archive
        cursor = self.cursor()
        version = self.getTestVersion()
        self.commit()
        mapper = ArchiveMapper()
        archive_id = mapper._getId(version.branch.category.archive, cursor)
        cursor.execute("SELECT currval('branch_id_seq')");
        new_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO Branch (archive, category, branch, version, title, description, visible) VALUES"
                       "(%d, '%s', '%s', '%s', 'a title', 'a description', true)" %
                       (archive_id, version.branch.category.name, version.branch.name, version.name))
        mapper = VersionMapper()
        self.assertEqual(new_id, mapper._getId(version, cursor))
        #    tests.append('test_VersionMapperGetId')

    def test_insert_file(self):
        """test we can insert a file into the database"""
        from canonical.arch.database import commit, connect
        connect()
        version = self.getTestVersion()
        revision = version.create_revision("base-0")
        print revision
        revision.add_file("foo", "baaaz", [("md5", "1234")])
        commit()
        c = self.cursor()
        c.execute("SELECT count(*) FROM changesetfile")
        self.assertEqual(c.fetchone()[0], 1)
        c.execute("SELECT count(*) FROM changesetfilename")
        self.assertEqual(c.fetchone()[0], 1)
        c.execute("SELECT count(*) FROM changesetfilehash")
        self.assertEqual(c.fetchone()[0], 1)
        import sys
#        sys.exit(0)

    tests.append('test_insert_file')
    
def test_suite():
    return unittest.TestSuite()

def main(argv):
    """Run the full test suite."""
    suite = unittest.TestSuite()
    def addTests(klass): suite.addTests(map(klass, klass.tests))
    # there should be a more elegant way - addClasses or something
    map(addTests, (Database, ArchiveMapper, ArchiveLocationMapper, CategoryMapper, BranchMapper, VersionMapper, RevisionMapper))
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful(): return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
