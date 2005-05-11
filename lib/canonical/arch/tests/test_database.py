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

from canonical.arch.tests.framework import DatabaseTestCase

from canonical.launchpad.interfaces import RevisionAlreadyRegistered
from canonical.launchpad.interfaces import VersionAlreadyRegistered
from canonical.launchpad.interfaces import BranchAlreadyRegistered
from canonical.launchpad.interfaces import CategoryAlreadyRegistered
from canonical.launchpad.interfaces import ArchiveLocationDoublyRegistered



class Database(DatabaseTestCase):

    tests = []

    def test_imports(self):
        """canonical.launchpad.database is importable."""
        import canonical.launchpad.database
    tests.append('test_imports')

    def test_archive_doesnt_exist(self):
        """a query for a non extant archive returns false"""
        import canonical.launchpad.database
        archive_name = "test@example.com--archive"
        self.failIf(canonical.launchpad.database.archive_present(archive_name))
    tests.append('test_archive_doesnt_exist')


class ArchiveMapper(DatabaseTestCase):

    def test_ArchiveMapperFindMissing(self):
        """test ArchiveMapper.findByName("foo") returns a MissingArchive"""
        from canonical.launchpad.database import ArchiveMapper
        from canonical.arch.broker import MissingArchive
        name="foo@bar"
        mapper=ArchiveMapper()
        self.failUnless(isinstance(mapper.findByName(name), MissingArchive))

    def insertArchive(self, name):
        from canonical.launchpad.database.archarchive import ArchArchive
        return ArchArchive(name = name,
                           title = 'a title', description = 'a description',
                           visible = True, owner = None)

    def test_ArchiveMapperFindPresent(self):
        """test ArchiveMapper.findByName("foo") returns an Archive"""
        from canonical.launchpad.database import ArchiveMapper
        from canonical.arch.broker import MissingArchive
        name="foo@bar"
        self.insertArchive(name)
        mapper=ArchiveMapper()
        archive=mapper.findByName(name)
        self.failIf(isinstance(archive, MissingArchive))
        self.assertEqual(archive.name, name)
        self.failUnless(archive.exists())

    def test_ArchiveMapperFindMultiple(self):
        """test ArchiveMapper.findByName("foo@%") returns a list of archives"""
        from canonical.launchpad.database import ArchiveMapper
        from canonical.arch.broker import MissingArchive
        name1="foo@bar"
        name2="foo@gam"
        self.insertArchive(name1)
        self.insertArchive(name2)
        mapper=ArchiveMapper()
        archives=mapper.findByMatchingName('foo@%')
        self.failIf(isinstance(archives, MissingArchive))
        self.assertEqual(archives[0].name, name1)
        self.assertEqual(archives[1].name, name2)
        self.failUnless(archives[0].exists())
        self.failUnless(archives[1].exists())

    def test_ArchiveMapperInsertPresent(self):
        """test canonical.arch.ArchiveMapper.insert fails when an archive already exists."""
        from canonical.launchpad.database import ArchiveMapper
        from canonical.arch.broker import Archive
        name="foo@bar"
        self.insertArchive(name)
        mapper=ArchiveMapper()
        self.assertRaises(KeyError, mapper.insert, Archive(name))

    def test_ArchiveMapperInsertNew(self):
        """test ArchiveMapper.insert works when an archive is new."""
        from canonical.launchpad.database import ArchiveMapper
        from canonical.arch.broker import MissingArchive
        name="foo@bar"
        mapper=ArchiveMapper()
        mapper.insert(MissingArchive(name))
        archive=mapper.findByName(name)
        self.failUnless(archive.exists())

    def test_ArchiveMapperGetId(self):
        """test we can get the archive id correctly"""
        from canonical.launchpad.database import ArchiveMapper
        from canonical.arch.broker import Archive
        name="foo@bar"
        archive = self.insertArchive(name)
        new_id = archive.id
        mapper=ArchiveMapper()
        self.assertEqual(new_id, mapper._getId(Archive(name)))


class ArchiveLocationMapper(DatabaseTestCase):

    tests = []

    def test_ArchiveLocationMapperGetAllNone(self):
        """test that we can get an empty list when there are no registered Locations"""
        from canonical.arch.broker import Archive
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        self.assertEqual(archiveLocationMapper.getAll(archive), [])
    tests.append('test_ArchiveLocationMapperGetAllNone')
    
    def test_ArchiveLocationMapperGetAllLots(self):
        """test that we can get back the correct urls from the db"""
        locations = [u"http://googo.com/foo",
                     u"http://fooboo.com/bar",
                     u"http://barbar.com/bleh"]
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        from canonical.launchpad.database import ArchiveLocation
        from canonical.lp.dbschema import ArchArchiveType
        archive = self.getTestArchive()
        archiveMapper = ArchiveMapper()
        archiveLocationMapper = ArchiveLocationMapper()
        for location in locations:
            ArchiveLocation(archive = archiveMapper._getId(archive),
                            archivetype = ArchArchiveType.READWRITE,
                            url = location,
                            gpgsigned = True)
        output = archiveLocationMapper.getAll(archive)
        self.assertEqual(len(output), len(locations))
        for archive_location in output:
            self.assertEqual(output[0].archive, archive)
            self.assertEqual(output[0]._type, ArchArchiveType.READWRITE)
        output_urls = [archive_location.url for archive_location in output]
        output_urls.sort()
        locations.sort()
        self.assertEqual(output_urls, locations)

    tests.append('test_ArchiveLocationMapperGetAllLots')

    def makeLocation(self, archive, url):
        from canonical.lp.dbschema import ArchArchiveType
        from canonical.arch.broker import ArchiveLocation
        return ArchiveLocation(archive, url, ArchArchiveType.READWRITE)

    def test_ArchiveLocationMapperInsertLocation(self):
        """test that we can insert a location"""
        url = "http://googo.com/foo"
        from canonical.arch.broker import Archive
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        from canonical.launchpad.database import ArchiveLocation
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        location = self.makeLocation(archive, url)
        archiveLocationMapper.insertLocation(location)
        result = ArchiveLocation.selectBy(url=location.url)
        self.assertEqual(result.count(), 1)
        self.failUnless(archiveLocationMapper.locationExists(location))
    tests.append('test_ArchiveLocationMapperInsertLocation')

    def test_ArchiveLocationMapperExistsNone(self):
        """Test we can tell if a location is not in the db"""
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        from canonical.arch.broker import Archive, ArchiveLocation
        location = "http://foo.com/"
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        location = self.makeLocation(archive, location)
        self.failIf(archiveLocationMapper.locationExists(location))
    tests.append('test_ArchiveLocationMapperExistsNone')

    def test_ArchiveLocationMapperExistsOne(self):
        """Test we can tell if a location is in the db"""
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        from canonical.arch.broker import Archive
        location = "http://foo.com/"
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()
        location = self.makeLocation(archive, location)
        archiveLocationMapper.insertLocation(location)
        self.failUnless(archiveLocationMapper.locationExists(location))
    tests.append('test_ArchiveLocationMapperExistsOne')

    def test_ArchiveLocationMapperExistsTwo(self):
        """Test that duplicated urls are an error"""
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        from canonical.arch.broker import Archive
        location = "http://foo.com/"
        archive = self.getTestArchive()
        archiveLocationMapper = ArchiveLocationMapper()

        location1 = self.makeLocation(archive, location)
        archiveLocationMapper.insertLocation(location1)

        location2 = self.makeLocation(archive, location)
        archiveLocationMapper.insertLocation(location2)

        self.assertRaises(ArchiveLocationDoublyRegistered, archiveLocationMapper.locationExists, location1)
        self.assertRaises(ArchiveLocationDoublyRegistered, archiveLocationMapper.locationExists, location2)
    tests.append('test_ArchiveLocationMapperExistsTwo')

    def test_ArchiveLocationMapperGetSomeNone(self):
        """Test that we can get no locations with a criteria"""
        from canonical.lp.dbschema import ArchArchiveType
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        from canonical.arch.broker import Archive, ArchiveLocation
        location = "http://foo.com/"
        archive = self.getTestArchive()
        mapper = ArchiveLocationMapper()
        self.assertEqual(mapper.getSome(archive, ArchArchiveType.READWRITE), [])
    tests.append('test_ArchiveLocationMapperGetSomeNone')

    def test_ArchiveLocationMapperGetSomeMore(self):
        """Test that we can get some locations with criteria"""
        from canonical.lp.dbschema import ArchArchiveType
        from canonical.launchpad.database import ArchiveMapper, ArchiveLocationMapper
        from canonical.arch.broker import Archive, ArchiveLocation
        locations = ["http://googo.com/foo", "http://fooboo.com/bar", "http://barbar.com/bleh"]
        archive = self.getTestArchive()
        mapper = ArchiveLocationMapper()
        archive_locations = []
        archive_types = [getattr(ArchArchiveType, X)
                         for X in ('READWRITE', 'READONLY', 'MIRRORTARGET')]
        for archive_type, location in zip(archive_types, locations):
            archive_location = ArchiveLocation(archive, location, archive_type)
            archive_locations.append(archive_location)
            mapper.insertLocation(archive_location)
        for archive_type, location in zip(archive_types, locations):
            locs = mapper.getSome(archive, archive_type)
            self.assertEqual(len(locs), 1)
            self.assertEqual(locs[0].url, location)

    tests.append('test_ArchiveLocationMapperGetSomeMore')

class CategoryMapper(DatabaseTestCase):

    def test_CategoryMapperInstantiation(self):
        """Test that we can create a CategoryMapper object"""
        from canonical.launchpad.database import CategoryMapper
        foo = CategoryMapper()

    def test_CategoryMapperInsertNew(self):
        """Test that CategoryMapper.insert works for non-existent categories"""
        from canonical.launchpad.database import ArchiveMapper, CategoryMapper
        from canonical.arch.broker import Archive, Category
        archive = self.getTestArchive()
        name = "fnord"
        mapper = CategoryMapper()
        category = Category(name, archive)
        mapper.insert(category)
        # FIXME: read the category back in and check that the data matches
        self.failUnless(category.exists())

    def test_CategoryMapperInsertExisting(self):
        """Test that inserting an existing Category raises an exception"""
        from canonical.launchpad.database import ArchiveMapper, CategoryMapper
        from canonical.arch.broker import Archive, Category
        archive = self.getTestArchive()
        name = "fnord"
        mapper = CategoryMapper()
        category = Category(name, archive)
        mapper.insert(category)
        self.assertRaises(CategoryAlreadyRegistered, mapper.insert, category)
        self.failUnless(mapper.exists(category))

    def test_category_exist_missing(self):
        """Test that we can tell that a category doesn't exist."""
        from canonical.launchpad.database import CategoryMapper
        from canonical.arch.broker import Category
        name = "blah"
        archive = self.getTestArchive()
        mapper = CategoryMapper()
        category = Category(name, archive)
        self.failIf(mapper.exists(category))

    def test_category_exist_present(self):
        """Test that we can tell that a category does exist."""
        from canonical.arch.broker import Category, Archive
        from canonical.launchpad.database import CategoryMapper
        name = "category"
        archive = self.getTestArchive()
        category = Category(name, archive)
        mapper = CategoryMapper()
        mapper.insert(category)
        self.failUnless(mapper.exists(category))


class BranchMapper(DatabaseTestCase):

    tests = []

    def test_BranchMapperInstantiation(self):
        """Test that we can create a BranchMapper object"""
        from canonical.launchpad.database import BranchMapper
        foo = BranchMapper()
    tests.append('test_BranchMapperInstantiation')

    def test_BranchMapperInsertNew(self):
        """Test that BranchMapper.insert works for non-existent categories"""
        from canonical.launchpad.database import ArchiveMapper, CategoryMapper, BranchMapper
        from canonical.arch.broker import Archive, Category, Branch
        archive = self.getTestArchive()
        name = "fnord"
        mapper = CategoryMapper()
        category = Category(name, archive)
        mapper.insert(category)
        name = "barnch" # deliberate, smart-arse
        mapper = BranchMapper()
        branch = Branch(name, category)
        mapper.insert(branch)
        # FIXME: read the branch back in and check that the data matches
        self.failUnless(branch.exists())
    tests.append('test_BranchMapperInsertNew')

    def test_BranchMapperInsertExisting(self):
        """Test that inserting an existing Branch raises an exception"""
        from canonical.launchpad.database import ArchiveMapper, CategoryMapper, BranchMapper
        from canonical.arch.broker import Archive, Category, Branch
        name = "barnch"
        mapper = BranchMapper()
        branch = Branch(name, self.getTestCategory())
        mapper.insert(branch)
        self.assertRaises(BranchAlreadyRegistered, mapper.insert, branch)
        self.failUnless(mapper.exists(branch))
    tests.append('test_BranchMapperInsertExisting')

    def test_branch_exist_missing(self):
        """Test that we can tell that a Branch doesn't exist."""
        from canonical.launchpad.database import BranchMapper
        from canonical.arch.broker import Branch
        name = "blah"
        branch = Branch(name, self.getTestCategory())
        mapper = BranchMapper()
        self.failIf(mapper.exists(branch))
    tests.append('test_branch_exist_missing')
        
    def test_branch_exist_present(self):
        """Test that we can tell that a Branch does exist."""
        from canonical.arch.broker import Branch
        from canonical.launchpad.database import BranchMapper
        name = "branch"
        branch = Branch(name, self.getTestCategory())
        mapper = BranchMapper()
        mapper.insert(branch)
        self.failUnless(mapper.exists(branch))
    tests.append('test_branch_exist_present')

class VersionMapper(DatabaseTestCase):

    tests = []
    
    def test_VersionMapperInstantiation(self):
        """Test that we can create a VersionMapper object"""
        from canonical.launchpad.database import VersionMapper
        foo = VersionMapper()
    tests.append('test_VersionMapperInstantiation')

    def test_VersionMapperInsertNew(self):
        """Test that VersionMapper.insert works for non-existent versions"""
        from canonical.launchpad.database import ArchiveMapper, CategoryMapper, BranchMapper, VersionMapper
        from canonical.arch.broker import Archive, Category, Branch, Version
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
        # FIXME: read the branch back in and check that the data matches
        self.failUnless(mapper.exists(version))
    tests.append('test_VersionMapperInsertNew')

    def test_VersionMapperInsertExisting(self):
        """Test that inserting an existing Version raises an exception"""
        from canonical.launchpad.database import ArchiveMapper, CategoryMapper, BranchMapper, VersionMapper
        from canonical.arch.broker import Archive, Category, Branch, Version
        name = "0"
        mapper = VersionMapper()
        version = Version(name, self.getTestBranch())
        mapper.insert(version)
        self.assertRaises(VersionAlreadyRegistered, mapper.insert, version)
        self.failUnless(mapper.exists(version))
    tests.append('test_VersionMapperInsertExisting')

    def test_version_exist_missing(self):
        """Test that we can tell that a Version doesn't exist."""
        from canonical.launchpad.database import VersionMapper
        from canonical.arch.broker import Version
        name = "0"
        version = Version(name, self.getTestVersion())
        mapper = VersionMapper()
        self.failIf(mapper.exists(version))
    tests.append('test_version_exist_missing')
        
    def test_version_exist_present(self):
        """Test that we can tell that a Version does exist."""
        from canonical.arch.broker import Version
        from canonical.launchpad.database import VersionMapper
        name = "0"
        version = Version(name, self.getTestBranch())
        mapper = VersionMapper()
        mapper.insert(version)
        self.failUnless(mapper.exists(version))
    tests.append('test_version_exist_present')

    def test_VersionMapperGetId(self):
        """test we can get the Version id correctly"""
        from canonical.launchpad.database import ArchiveMapper, VersionMapper
        from canonical.arch.broker import Archive
        from canonical.launchpad.database import ArchNamespace
        version = self.getTestVersion()
        query = ArchNamespace.selectBy(
            category = version.branch.category.name,
            branch = version.branch.name,
            version = version.name)
        self.assertEqual(query.count(), 1)
        expected_id = list(query)[0].id
        mapper = VersionMapper()
        self.assertEqual(expected_id, mapper._getId(version))
    tests.append('test_VersionMapperGetId')

    def test_VersionMapperGetDBBranchId(self):
        """test we can get the Version id for the 'Branch' correctly"""
        from canonical.launchpad.database import ArchiveMapper, VersionMapper
        from canonical.arch.broker import Archive
        from canonical.launchpad.database.archbranch import Branch
        version = self.getTestVersion()
        version_id=VersionMapper()._getId(version)
        query = Branch.selectBy(archnamespaceID = version_id)
        self.assertEqual(query.count(), 1)
        expected_id = list(query)[0].id
        mapper = VersionMapper()
        self.assertEqual(expected_id, mapper._getDBBranchId(version))
    tests.append('test_VersionMapperGetDBBranchId')


class RevisionMapper(DatabaseTestCase):

    tests = []
    
    def test_RevisionMapperInstantiation(self):
        """Test that we can create a RevisionMapper object"""
        from canonical.launchpad.database import RevisionMapper
        foo = RevisionMapper()
    tests.append('test_RevisionMapperInstantiation')

    def test_RevisionMapperInsertNew(self):
        """Test that RevisionMapper.insert works for non-existent revisions"""
        from canonical.launchpad.database import RevisionMapper
        mapper = RevisionMapper()
        revision = self.getTestRevision()
        # FIXME: read the branch back in and check that the data matches
        self.failUnless(mapper.exists(revision))
    tests.append('test_RevisionMapperInsertNew')

    def test_RevisionMapperExists(self):
        """test revision mapper exists works for existing ones"""
        from canonical.launchpad.database import VersionMapper, RevisionMapper
        from canonical.launchpad.database.archchangeset import Changeset
        mapper = RevisionMapper()
        revision = self.getTestRevision()
        branchid = VersionMapper()._getDBBranchId(revision.version)
        query = Changeset.selectBy(branchID = branchid)
        self.assertEqual(query.count(), 1)
        self.failUnless(mapper.exists(revision))
    tests.append('test_RevisionMapperExists')

    def test_RevisionMapperDoesntExist(self):
        """test revision mapper exists works for non-existant ones"""
        from canonical.launchpad.database import VersionMapper, RevisionMapper, BranchMapper
        from canonical.arch.broker import Revision
        from canonical.launchpad.database.archchangeset import Changeset
        mapper = RevisionMapper()
        version = self.getTestVersion()
        branchid = VersionMapper()._getId(version)
        revision = Revision("base-0", version)
        query = Changeset.selectBy(branchID = branchid)
        self.assertEqual(query.count(), 0)
        self.failIf(mapper.exists(revision))
    tests.append('test_RevisionMapperDoesntExist')

    def test_RevisionMapperInsertExisting(self):
        """RevisionMapper.insert(REV) fails if REV already exists."""
        from canonical.launchpad.database import RevisionMapper
        from canonical.arch.broker import Revision
        mapper = RevisionMapper()
        revision = Revision("base-0", self.getTestVersion())
        mapper.insert(revision)
        self.assertRaises(RevisionAlreadyRegistered, mapper.insert, revision)
        self.failUnless(mapper.exists(revision))
    tests.append('test_RevisionMapperInsertExisting')

    def test_revision_exist_missing(self):
        """RevisionMapper.exists() tells non-existence in existing Version."""
        from canonical.launchpad.database import RevisionMapper
        from canonical.arch.broker import Revision
        revision = Revision("base-0", self.getTestVersion())
        mapper = RevisionMapper()
        self.failIf(mapper.exists(revision))
    tests.append('test_revision_exist_missing')

    def test_revision_exist_present(self):
        """RevisionMapper.exists() tells existence."""
        from canonical.arch.broker import Revision
        from canonical.launchpad.database import RevisionMapper
        revision = Revision("base-0", self.getTestVersion())
        mapper = RevisionMapper()
        mapper.insert(revision)
        self.failUnless(mapper.exists(revision))
    tests.append('test_revision_exist_present')

    def test_revision_exist_imposter(self):
        """RevisionMapper.exists() is not confused by another Version."""
        from canonical.arch.broker import Revision
        from canonical.launchpad.database import RevisionMapper
        name = "base-0"
        revision = Revision(name, self.getTestVersion())
        mapper = RevisionMapper()
        mapper.insert(revision)
        otherrevision = Revision(name, self.getTestVersion("1"))
        self.failIf(mapper.exists(otherrevision))
    tests.append('test_revision_exist_imposter')

    def test_RevisionMapperGetId(self):
        """test we can get the Revision id correctly"""
        from canonical.launchpad.database import VersionMapper
        from canonical.launchpad.database import RevisionMapper, Changeset
        revision = self.getTestRevision()
        version = self.getTestVersion()
        versionmapper = VersionMapper()
        query = Changeset.selectBy(
            branchID = versionmapper._getDBBranchId(version),
            name = revision.name)
        self.assertEqual(query.count(), 1)
        expected_id = list(query)[0].id
        mapper = RevisionMapper()
        self.assertEqual(expected_id, mapper._getId(revision))
    tests.append('test_RevisionMapperGetId')

    def test_insert_file(self):
        """test we can insert a file into the database"""
        from canonical.launchpad.database import ChangesetFile
        from canonical.launchpad.database import ChangesetFileName
        from canonical.launchpad.database import ChangesetFileHash
        version = self.getTestVersion()
        revision = version.create_revision("base-0")
        revision.add_file("foo", "baaaz", {"md5": "1234"})
        self.assertEqual(ChangesetFile.select().count(), 1)
        self.assertEqual(ChangesetFileName.select().count(), 1)
        self.assertEqual(ChangesetFileHash.select().count(), 1)

    tests.append('test_insert_file')


import framework
framework.register(__name__)
