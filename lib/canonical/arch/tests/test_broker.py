#!/usr/bin/env python
#
# arch-tag: a1262849-780c-4124-9a58-19256ca74c1b
#
# Copyright (C) 2004 Canonical Software
# 	Authors: Rob Weir <rob.weir@canonical.com>
#		 Robert Collins <robert.collins@canonical.com>

"""Test suite for Canonical broker broker module."""

import operator
import sys
import unittest
from zope.interface.verify import verifyClass, verifyObject
from canonical.arch.tests.test_framework import DatabaseTestCase
from canonical.arch.tests.test_framework import DatabaseAndArchiveTestCase


class NamespaceObject(unittest.TestCase):
    tests = []

    def test_None_is_not_equal(self):
        """Test that any object is != None"""
        from canonical.arch.broker import Revision
        r = Revision("")
        self.failIf(r == None)
    tests.append('test_None_is_not_equal')

    def test_identical_is_equal(self):
        """Test that an object is identical to itself"""
        from canonical.arch.broker import Revision
        r = Revision("")
        self.failUnless(r == r)

    def test_blah(self):
        """blah"""
        from canonical.arch.broker import Revision
        r1 = Revision("")
        from canonical.arch.broker import Revision
        r2 = Revision("")
        self.assertEqual(r1, r2)
    tests.append('test_blah')

    def test_everything_in_the_world(self):
        """Test equality combinations"""
        results = [[True] * 10] * 10
        #           R      V      C      A
        results = [[True,  False, False, False], # R
                   [False, True,  False, True], # V
                   [False, False, True,  False], # C
                   [True,  False, False, True]] # A
        i = 0
        j = 0
        from canonical.arch.broker import Revision, Version, Category, Archive
        l = [Revision(""), Version(""), Category(""), Archive("")]
        from canonical.arch.broker import Revision, Version, Category, Archive
        r = [Revision(""), Version(""), Category(""), Archive("")]
        for x in l:
            # ROCK.
            for y in r:
                print "%r" % ([i, j])
                print "(u = %r, v = %r): should be = %r, is = %r" % (x, y, results[i][j], (x == y))
                self.assertEqual(results[i][j], (x == y))
                j = j + 1
            j = 0
            i = i + 1
        # FIXME
        # tests.append('test_everything_in_the_world')


class Archives(DatabaseTestCase):
    tests=[]
    def test_implements(self):
        """canonical.arch.broker.Archives implement IArchiveCollection"""
        from canonical.arch.broker import Archives
        from canonical.arch.interfaces import IArchiveCollection
        self.failUnless(verifyClass(IArchiveCollection, Archives))
    tests.append('test_implements')

    def _help_test_keys(self, names):
        from canonical.arch.broker import Archives
        from canonical.arch.database import connect
        connect()
        for name in names: Archives().create(name)
        self.assertEqual(Archives().keys(), list(names))

    def test_keys_zero(self):
        """Archives.keys() work with zero archive"""
        self._help_test_keys([])
    tests.append('test_keys_zero')

    def test_keys_one(self):
        """Archives.keys() works with one archive"""
        self._help_test_keys(["foo@bar"])
    tests.append('test_keys_one')

    def test_keys_two(self):
        """Archives.keys() works with two archives"""
        self._help_test_keys(["foo@bar", "gam@bar"])
    tests.append('test_keys_two')
    
    def test_create(self):
        """Archives.create("foo@bar") works"""
        from canonical.arch.broker import Archives, Archive
        from canonical.arch.database import _archive_purge, ArchiveMapper
        from canonical.arch.database import connect
        connect()
        name="foo@bar"
        mapper=ArchiveMapper()
        self.failIf(mapper.findByName(name).exists())
        archive=Archives().create(name)
        self.commit()
        self.failUnless(isinstance(archive, Archive))
        self.failUnless(mapper.findByName(name).exists())
    tests.append('test_create')

    def test_create_invalid(self):
        """Archives.create raises NamespaceError on invalid archive name"""
        from canonical.arch.broker import Archives
        from canonical.arch.interfaces import NamespaceError
        name="foo%ouch@bar"
        def thunk(): Archives().create(name)
        self.assertRaises(NamespaceError, thunk)
    tests.append('test_create_invalid')

    def test_create_one_location(self):
        """Archives.create also creates a single location."""
        from canonical.arch.broker import Archives, Archive
        from canonical.arch.database import ArchiveMapper
        name, location ="foo@bar", "http://example.com/archives/foo@bar"
        mapper=ArchiveMapper()
        self.failIf(mapper.findByName(name).exists())
        archive=Archives().create(name, location)
        self.commit()
        self.failUnless(isinstance(archive, Archive))
        self.failUnless(mapper.findByName(name).exists())
    # FIXME
    # tests.append('test_create_one_location')

    def test_setitem_raises(self):
        """Archives.__setitem__ raises a TypeError."""
        from canonical.arch.broker import Archives, Archive
        name = 'foo@bar'
        collection, archive = Archives(), Archive(name)
        def thunk(): collection[name] = archive
        self.assertRaises(TypeError, thunk)
    tests.append('test_setitem_raises')

    def test_delitem_raises(self):
        """Archives.__delitem__ raises a TypeError."""
        from canonical.arch.broker import Archives, Archive
        name = 'foo@bar'
        collection, archive = Archives(), Archive(name)
        def thunk(): del collection[name]
        self.assertRaises(TypeError, thunk)
    tests.append('test_delitem_raises')

    def test_getitem_invalid_raises(self):
        """Archives.__getitem__ raises NamespaceError on invalid name"""
        from canonical.arch.broker import Archives
        from canonical.arch.interfaces import NamespaceError
        name="foo%ouch@bar"
        def thunk(): Archives()[name]
        self.assertRaises(NamespaceError, thunk)
    tests.append('test_getitem_invalid_raises')

    def test_getitem(self):
        """Archives.__getitem__ works"""
        from canonical.arch.broker import Archives, MissingArchive, Archive
        from canonical.arch.database import connect
        connect()
        name = 'foo@bar'
        archives = Archives()
        missing_archive = archives[name]
        self.assert_(isinstance(missing_archive, MissingArchive))
        archives.create(name)
        self.commit()
        created_archive = archives[name]
        self.assert_(isinstance(created_archive, Archive))
        self.assertEqual(name, created_archive.name)
    tests.append('test_getitem')


class ArchiveLocation(DatabaseTestCase):
    tests=[]

    def test_implements(self):
        """canonical.arch.broker.ArchiveLocation implement IArchiveLocation"""
        from canonical.arch.broker import ArchiveLocation
        from canonical.arch.interfaces import IArchiveLocation
        self.failUnless(verifyClass(IArchiveLocation, ArchiveLocation))
    tests.append('test_implements')

    def test_instantiate(self):
        """canonical.arch.broker.ArchiveLocation can be instantiated"""
        from canonical.arch.broker import Archive, ArchiveLocation
        archive = Archive("foo@bar")
        url = "http://blah/"
        location = ArchiveLocation(archive, url, 0)
    tests.append('test_instantiate')

    def test_equality(self):
        from canonical.arch.broker import Archive, ArchiveLocation
        archive1 = Archive("foo@bar")
        archive2 = Archive("baz@boo")
        url1 = "http://blah/"
        url2 = "http://foo/"
        location1 = ArchiveLocation(archive1, url1, 0)
        location2 = ArchiveLocation(archive1, url2, 0)

class ArchiveLocationRegistry(DatabaseTestCase):
    tests=[]

    def test_instantiate(self):
        """canonical.arch.broker.ArchiveLocationRegistry can be instantiated"""
        from canonical.arch.broker import Archive, ArchiveLocationRegistry
        from canonical.arch.database import connect
        connect()
        archive = Archive("foo@bar")
        registry = ArchiveLocationRegistry(archive)
    tests.append('test_instantiate')

    def test_insert_location(self):
        """test that we can insert a location and check it exists"""
        from canonical.arch.broker import Archives, ArchiveLocationRegistry
        url = "http://blah/"
        archives = Archives()
        from canonical.arch.database import connect
        connect()
        archive = archives.create("foo@bar")
        registry = ArchiveLocationRegistry(archive)
        location = registry.createMirrorTargetLocation(url)
        self.commit()
        self.failUnless(registry.existsLocation(location))
    tests.append('test_insert_location')

    def test_extract_mirrors(self):
        """test that we can extract a list of mirrorarchives"""
        from canonical.arch.broker import Archive, Archives, ArchiveLocationRegistry
        url = "http://blah/"
        archives = Archives()
        from canonical.arch.database import connect
        connect()
        archive = archives.create("foo@bar")
        registry = ArchiveLocationRegistry(archive)
        location = registry.createMirrorTargetLocation(url)
        locations = registry.getMirrorTargetLocations()
        self.failUnless(registry.existsLocation(location))
        self.assertEqual(location.url, url)
        self.assertEqual(location.archive, archive)
    tests.append('test_extract_mirrors')

class NamespaceTestCase(DatabaseTestCase):
    def _help_test_implements(self, concrete, interface, fullname):
        import canonical.arch.broker
        import canonical.arch.interfaces
        concrete_class = getattr(canonical.arch.broker, concrete)
        interface_class = getattr(canonical.arch.interfaces, interface)
        concrete_object = concrete_class(fullname)
        self.failUnless(verifyClass(interface_class, concrete_class))
        self.failUnless(verifyObject(interface_class, concrete_object))

    def _help_test_create(self, classname, fullname):
        self._help_test_create_worker(classname, fullname)

    def _help_test_create_parent(self, classname, name, parent):
        self._help_test_create_worker(classname, name, parent)
            
    def _help_test_create_worker(self, classname, *args):
        import canonical.arch.broker
        concrete_class = getattr(canonical.arch.broker, classname)
        namespace_object = concrete_class(*args)
        self.failUnless(isinstance(namespace_object, concrete_class))
        self.failUnless(namespace_object.exists())

    def _help_test_create_new(self, klass, name, *args):
        instance = klass(name, *args)

    def _help_test_name(self, classname, fullname):
        import canonical.arch.broker
        concrete_class = getattr(canonical.arch.broker, classname)
        namespace_object = concrete_class(fullname)
        self.assertEqual(namespace_object.fullname, fullname)

    def _help_test_name_new(self, klass, expectedname, *args):
        instance=klass(expectedname, *args)
        self.assertEqual(instance.name, expectedname)

    def _help_test_null_equality(self, classname, fullname):
        import canonical.arch.broker
        concrete_class = getattr(canonical.arch.broker, classname)
        namespace_object = concrete_class(fullname)
        self.assertEqual(namespace_object, namespace_object)

    def _help_test_null_equality_new(self, klass, fullname, *args):
        instance = klass(fullname, *args)
        self.assertEqual(instance, instance)

    def _help_test_simple_equality(self, classname, fullname):
        import canonical.arch.broker
        concrete_class = getattr(canonical.arch.broker, classname)
        first_object = concrete_class(fullname)
        second_object = concrete_class(fullname)
        self.assertEqual(first_object, second_object)

    def _help_test_simple_equality_new(self, klass, fullname, *args):
        instance1 = klass(fullname, *args)
        instance2 = klass(fullname, *args)
        self.assertEqual(instance1, instance2)
        
    def _help_test_none_inequality(self, classname, fullname):
        import canonical.arch.broker
        concrete_class = getattr(canonical.arch.broker, classname)
        namespace_object = concrete_class(fullname)
        self.assertNotEqual(namespace_object, None)

    def _help_test_none_inequality_new(self, klass, fullname, *args):
        instance = klass(fullname, *args)
        self.assertNotEqual(instance, None)

    def _help_test_named_inequality(self, classname, fullname, other_fullname):
        import canonical.arch.broker
        concrete_class = getattr(canonical.arch.broker, classname)
        first_object = concrete_class(fullname)
        second_object = concrete_class(other_fullname)
        self.assertNotEqual(first_object, second_object)

    def _help_test_named_inequality_new(self, klass, fullname1, fullname2, *args):
        instance1 = klass(fullname1, *args)
        instance2 = klass(fullname2, *args)
        self.assertNotEqual(instance1, instance2)


class Archive(NamespaceTestCase):
    tests = []
               
    def test_imports(self):
        """canonical.arch.interfaces is importable."""
        from canonical.arch.broker import Archive
    tests.append('test_imports')

    def test_construct(self):
        """canonical.arch.broker.Archive is constructable"""
        from canonical.arch.broker import Archive
        foo=Archive("test@example.com--cad")
    tests.append('test_construct')

    def test_implements(self):
        """canonical.arch.broker.Archive implements Archive"""
        from canonical.arch.broker import Archive
        from canonical.arch.interfaces import IArchive
        self.failUnless(verifyClass(IArchive, Archive))
    tests.append('test_implements')

    def test_archive_exists_missing(self):
        """canonical.arch.broker.Archive.exists() on an absent archive works"""
        archive_name = "test@example.com"
        from canonical.arch.broker import Archives
        a = Archives()[archive_name]
        self.failIf(a.exists())
    tests.append('test_archive_exists_missing')

    def test_MissingArchive(self):
        """MissingArchive has exists false, and the correct name"""
        from canonical.arch.broker import MissingArchive
        name="foo@bar"
        archive=MissingArchive(name)
        self.failIf(archive.exists())
        self.assertEqual(archive.name, name)
    tests.append('test_MissingArchive')

    def test_name_return(self):
        """Test that the name is returned correctly"""
        from canonical.arch.broker import Archive
        name = "foo@bar"
        archive = Archive(name)
        self.assertEqual(name, archive.fullname)
        self.assertEqual(name, archive.name)
    tests.append('test_name_return')

    def test_getitem_invalid_raises(self):
        """Archive.__getitem__ raises NamespaceError on invalid category"""
        from canonical.arch.broker import Archive
        from canonical.arch.interfaces import NamespaceError
        name = "foo@bar"
        archive = Archive(name)
        def thunk(): archive['break/me']
        self.assertRaises(NamespaceError, thunk)
    tests.append('test_getitem_invalid_raises')

    def test_getitem(self):
        """Archive.__getitem__ works"""
        from canonical.arch.broker import Archive
        archive_name = "foo@bar"
        archive = Archive(archive_name)
        category_name = "cat3-gory"
        category = archive[category_name]
        self.assertEqual('%s/%s' % (archive_name, category_name),
                         category.fullname)
    tests.append('test_getitem')

    def test_getitem_missing_raises(self):
        """MissingArchive.__getitem__ raises TypeError."""
        from canonical.arch.broker import MissingArchive
        archive_name = "foo@bar"
        archive = MissingArchive(archive_name)
        category_name = "cat3-gory"
        def thunk(): archive[category_name]
        self.assertRaises(TypeError, thunk)
    tests.append('test_getitem_missing_raises')

    classname="Archive"
    fullname="foo@bar"
    other_fullname="foo@baz"
    def test_null_equality(self):
        """Test equality of an Archive against itself"""
        self._help_test_null_equality(self.classname, self.fullname)
    tests.append('test_null_equality')

    def test_simple_equality(self):
        """Test equality of two identical Archives"""
        self._help_test_simple_equality(self.classname, self.fullname)
    tests.append('test_simple_equality')

    def test_None_inequality(self):
        """Compare an Archive against None"""
        self._help_test_none_inequality(self.classname, self.fullname)
    tests.append('test_None_inequality')

    def test_named_inequality(self):
        """Differing fullnames make Archive unequal"""
        self._help_test_named_inequality(self.classname, self.fullname, self.other_fullname)
    tests.append('test_named_inequality')

    def test_unregistered(self):
        """Test we can tell we're unregistered"""
        from canonical.arch.broker import Archives
        archives = Archives()
        from canonical.arch.database import connect
        connect()

        archive = archives.create("foo@bar")
        self.failIf(archive.is_registered())
    tests.append('test_unregistered')

    def test_registered(self):
        """Test we call tell when we're registered"""
        from canonical.arch.broker import Archives
        archives = Archives()
        from canonical.arch.database import connect
        connect()

        archive = archives.create("foo@bar")
        self.failIf(archive.is_registered())
        archive.location.createReadOnlyTargetLocation("http://foo/")
        self.failUnless(archive.is_registered())
    tests.append('test_registered')

    def test_insert_category(self):
        """Test we can insert a category into the db"""
        from canonical.arch.database import connect
        connect()

        archive = self.getTestArchive()
        name = "cat"
        category = archive.create_category(name)
        from canonical.arch.database import CategoryMapper
        mapper = CategoryMapper()
        self.commit()
        self.failUnless(mapper.exists(category))
        read_back = archive[name]
        self.assertEqual(read_back, category)
    tests.append('test_insert_category')

class Category(NamespaceTestCase):
    tests=[]
    interfacename = "ICategory"
    classname = "Category"
    fullname = "foo@bar/baz"
    name = "baz"
    other_fullname = "foo@bar/bar"

    def klass(self):
        import canonical.arch.broker
        return canonical.arch.broker.Category
    
    def test_implements(self):
        """instances of canonical.arch.broker.Category implements ICategory"""
        from canonical.arch.database import connect
        connect()
        self._help_test_implements(self.classname, self.interfacename, self.fullname)
#    tests.append('test_implements')

    def test_create(self):
        """Category can be instantiated with a fullname"""
        from canonical.arch.database import connect
        connect()
        self._help_test_create_new(self.klass(), self.name, self.getTestArchive())
    tests.append('test_create')

    def test_name(self):
        """Test it stores it's name correctly"""
        from canonical.arch.database import connect
        connect()
        self._help_test_name_new(self.klass(), self.name, self.getTestArchive())
    tests.append('test_name')

    def test_null_equality(self):
        """Test equality of a Category against itself"""
        from canonical.arch.database import connect
        connect()
        self._help_test_null_equality_new(self.klass(), self.name, self.getTestArchive())
    tests.append('test_null_equality')

    def test_simple_equality(self):
        """Test equality of two identical Category"""
        from canonical.arch.database import connect
        connect()
        self._help_test_simple_equality_new(self.klass(), self.fullname, self.getTestArchive())
    tests.append('test_simple_equality')

    def test_None_inequality(self):
        """Compare a Category against None"""
        from canonical.arch.database import connect
        connect()
        self._help_test_none_inequality_new(self.klass(), self.fullname, self.getTestArchive())
    tests.append('test_None_inequality')

    def test_named_inequality(self):
        """Differing fullnames make Category unequal"""
        from canonical.arch.database import connect
        connect()
        self._help_test_named_inequality_new(self.klass(), self.fullname, self.other_fullname, self.getTestArchive())
    tests.append('test_named_inequality')

    def test_getitem(self):
        """Category.__getitem__ works"""
        from canonical.arch.broker import Category, Branch
        from canonical.arch.database import connect
        connect()
        archive = self.getTestArchive()
        category = Category("baz", archive)
        branch = category["bork"]
        self.assertEqual(branch.fullname, archive.name + "/baz--bork")
        self.failUnless(isinstance(branch, Branch))
    tests.append('test_getitem')

    def test_always_exists(self):
        """Categories always exist"""
        from canonical.arch.broker import Category
        from canonical.arch.database import connect
        connect()
        archive = self.getTestArchive()
        category = Category("bang", archive)
        self.assertEqual(category.exists(), True)
    tests.append('test_always_exists')

    def test_can_setup(self):
        """Test we can setup a Category"""
        from canonical.arch.broker import Category
        from canonical.arch.database import connect
        connect()
        archive = self.getTestArchive()
        category = Category("bang", archive)
        category.setup()
        self.commit()
        self.failUnless(category.exists())
    tests.append('test_can_setup')

    def test_nonarch_name(self):
        """Test Category.nonarch returns the correct string"""
        from canonical.arch.broker import Category
        from canonical.arch.database import connect
        connect()
        archive = self.getTestArchive()
        category = Category(self.name, archive)
        self.assertEqual(category.nonarch, self.name)
    tests.append('test_nonarch_name')

    def test_get_archive(self):
        """Test we can get the archive out of a Category correctly"""
        from canonical.arch.broker import Category
        from canonical.arch.database import connect
        connect()
        archive = self.getTestArchive()
        category = Category(self.name, archive)
        self.assertEqual(category.archive, archive)
    tests.append('test_get_archive')

    def test_get_fullname(self):
        """Test Category sets it's .fullname correctly"""
        from canonical.arch.broker import Category
        from canonical.arch.database import connect
        connect()
        archive = self.getTestArchive()
        name = "bah"
        category = Category(name, archive)
        self.assertEqual(category.fullname, archive.name + "/" + name)
    tests.append('test_get_fullname')

class Branch(NamespaceTestCase):
    tests=[]
    interfacename = "IBranch"
    classname = "Branch"
    fullname = "foo@bar/baz--bork"
    name = "bork"
    other_fullname = "foo@bar/baz--fork"
    other_name = "fork"
    
    def klass(self):
        import canonical.arch.broker
        return canonical.arch.broker.Branch

    def test_implements(self):
        """instances of canonical.arch.broker.Branch implements IBranch"""
#        self._help_test_implements(self.classname, self.interfacename, self.fullname)
    tests.append('test_implements')

    def test_create(self):
        """Branch can be instantiated with a fullname"""
        from canonical.arch.database import connect
        connect()
        self._help_test_create_new(self.klass(), self.name, self.getTestCategory())
    tests.append('test_create')

    def test_name(self):
        """Test it stores it's name correctly"""
        from canonical.arch.database import connect
        connect()
        self._help_test_name_new(self.klass(), self.name, self.getTestCategory())
    tests.append('test_name')

    def test_null_equality(self):
        """Test equality of a Branch against itself"""
        from canonical.arch.database import connect
        connect()
        self._help_test_null_equality_new(self.klass(), self.name, self.getTestCategory())
    tests.append('test_null_equality')

    def test_simple_equality(self):
        """Test equality of two identical Branches"""
        from canonical.arch.database import connect
        connect()
        self._help_test_simple_equality_new(self.klass(), self.name, self.getTestCategory())
    tests.append('test_simple_equality')

    def test_None_inequality(self):
        """Compare a Branch against None"""
        from canonical.arch.database import connect
        connect()
        self._help_test_none_inequality_new(self.klass(), self.name, self.getTestCategory())
    tests.append('test_None_inequality')

    def test_named_inequality(self):
        """Differing fullnames make Branches unequal"""
        from canonical.arch.database import connect
        connect()
        self._help_test_named_inequality_new(self.klass(), self.name, self.other_name, self.getTestCategory())
    tests.append('test_named_inequality')

    def test_get_category(self):
        """Test we can get our parent category"""
        from canonical.arch.broker import Branch
        from canonical.arch.database import connect
        connect()
        self.assertEqual(self.getTestBranch().category, self.getTestCategory())
    tests.append('test_get_category')

    def test_get_fullname(self):
        """Test Branch sets it's .fullname correctly"""
        from canonical.arch.broker import Branch
        from canonical.arch.database import connect
        connect()
        
        category = self.getTestCategory()
        name = "bah"
        branch = Branch(name, category)
        self.assertEqual(branch.fullname, category.fullname + "--" + name)
    tests.append('test_get_fullname')

class Version(NamespaceTestCase):
    tests=[]
    interfacename = "IVersion"
    classname = "Version"
    fullname = "foo@bar/baz--bork--0"
    name = "0"
    other_fullname = "foo@bar/baz--bork--0.1"
    other_name = "1"
    
    def klass(self):
        import canonical.arch.broker
        return canonical.arch.broker.Version

    def test_implements(self):
        """instances of canonical.arch.broker.Version implements IVersion"""
#        self._help_test_implements(
#            self.classname, self.interfacename, self.fullname)
    tests.append('test_implements')

    def test_create(self):
        """Version can be instantiated with a fullname"""
        from canonical.arch.database import connect
        connect()
        self._help_test_create_new(self.klass(), self.fullname, self.getTestBranch())
    tests.append('test_create')

    def test_name(self):
        """Test it stores it's name correctly"""
        from canonical.arch.database import connect
        connect()
        self._help_test_name_new(self.klass(), self.fullname, self.getTestBranch())
    tests.append('test_name')

    def test_null_equality(self):
        """Test equality of a Version against itself"""
        from canonical.arch.database import connect
        connect()
        self._help_test_null_equality_new(self.klass(), self.fullname, self.getTestBranch())
    tests.append('test_null_equality')

    def test_simple_equality(self):
        """Test equality of two identical Versions"""
        from canonical.arch.database import connect
        connect()
        self._help_test_simple_equality_new(self.klass(), self.fullname, self.getTestBranch())
    tests.append('test_simple_equality')

    def test_None_inequality(self):
        """Compare Version against None"""
        from canonical.arch.database import connect
        connect()
        self._help_test_none_inequality_new(self.klass(), self.fullname, self.getTestBranch())
    tests.append('test_None_inequality')

    def test_named_inequality(self):
        """Differing fullnames make Versions unequal"""
        from canonical.arch.database import connect
        connect()
        self._help_test_named_inequality_new(self.klass(), self.fullname, self.other_fullname, self.getTestBranch())
    tests.append('test_named_inequality')

    def test_get_fullname(self):
        """Test Version sets it's .fullname correctly"""
        from canonical.arch.broker import Version
        from canonical.arch.database import connect
        connect()
        
        branch = self.getTestBranch()
        name = "bah"
        version = Version(name, branch)
        self.assertEqual(version.fullname, branch.fullname + "--" + name)
    tests.append('test_get_fullname')

class Revision(NamespaceTestCase):
    tests=[]
    interfacename = "IRevision"
    classname = "Revision"
    fullname = "foo@bar/baz--bork--0--patch-2"
    name = "patch-2"
    other_fullname = "foo@bar/baz--bork--0--patch-3"
    other_name = "patch-3"
    
    def klass(self):
        import canonical.arch.broker
        return canonical.arch.broker.Revision

    def test_implements(self):
        """instances of canonical.arch.broker.Revision implements IRevision"""
        self._help_test_implements(
            self.klass(), self.interfacename, self.fullname)
#    tests.append('test_implements')

    def test_create(self):
        """Revision can be instantiated with a name"""
        from canonical.arch.database import connect
        connect()
        self._help_test_create_new(self.klass(), self.name, self.getTestVersion())
    tests.append('test_create')

    def test_name(self):
        """Tests that it stores it's name"""
        from canonical.arch.database import connect
        connect()
        self._help_test_name_new(self.klass(), self.name, self.getTestVersion())
    tests.append('test_name')

    def test_null_equality(self):
        """Test equality of a Revision against itself"""
        from canonical.arch.database import connect
        connect()
        self._help_test_null_equality_new(self.klass(), self.name, self.getTestVersion())
    tests.append('test_null_equality')

    def test_simple_equality(self):
        """Test equality of two identical Revisiones"""
        from canonical.arch.database import connect
        connect()
        self._help_test_simple_equality_new(self.klass(), self.name, self.getTestVersion())
    tests.append('test_simple_equality')

    def test_None_inequality(self):
        """Compare Revision against None"""
        from canonical.arch.database import connect
        connect()
        self._help_test_none_inequality_new(self.klass(), self.name, self.getTestVersion())
    tests.append('test_None_inequality')

    def test_named_inequality(self):
        """Differing fullnames make Revisions unequal"""
        from canonical.arch.database import connect
        connect()
        self._help_test_named_inequality_new(self.klass(), self.name, self.other_name, self.getTestVersion())
    tests.append('test_named_inequality')

    def test_parents(self):
        """Test we can access our parents correctly."""
        from canonical.arch.database import connect
        connect()
        revision = self.getTestRevision()
        self.assertEqual(revision, self.getTestRevision())
        self.assertEqual(revision.version, self.getTestVersion())
        self.assertEqual(revision.version.branch, self.getTestBranch())
        self.assertEqual(revision.version.branch.category, self.getTestCategory())
        self.assertEqual(revision.version.branch.category.archive, self.getTestArchive())
    tests.append('test_parents')

    def test_previous(self):
        """Test that the .previous method returns correct values"""
        from canonical.arch.broker import Revision
        current = Revision("foo@bar/baz--bar--0--base-0")
        self.assertEquals(current.previous, None)
        current = Revision("foo@bar/baz--bar--0--patch-1")
        self.assertEquals(current.previous, "foo@bar/baz--bar--0--base-0")
        current = Revision("foo@bar/baz--bar--0--patch-44")
        self.assertEquals(current.previous, "foo@bar/baz--bar--0--patch-43")
        current = Revision("foo@bar/baz--bar--0--versionfix-1")
        ### FIXME FIXME FIXME FIXME FIXME  FIXME FIXME FIXME FIXME FIXME ###
        self.assertEquals(current.previous,"foo@bar/baz--bar--0--versionfix-0")
        ### FIXME FIXME FIXME FIXME FIXME  FIXME FIXME FIXME FIXME FIXME ###
        current = Revision("foo@bar/baz--bar--0--versionfix-34")
        self.assertEquals(current.previous,
                          "foo@bar/baz--bar--0--versionfix-33")
    # tests.append('test_previous')

class RevisionImport(DatabaseAndArchiveTestCase):
    tests=[]

    def test_clone_files(self):
        "c.a.b.Revision.clone_files integrates with arch.Revision.iter_files"
        import arch
        db_rev = self.getTestRevision()
        self.arch_set_user_id()
        # arch_name = db_rev.archive.name
        # arch_vsn = arch.Version(db_rev.version.fullname)
        # FIXME: the former _should_ work but buttress is too borken
        arch_name = arch.Revision(db_rev.fullname).archive.name
        arch_vsn = arch.Revision(db_rev.fullname).version
        # end of hack
        archive = self.arch_make_archive(arch_name)
        tree = self.arch_make_tree('wtree', arch_vsn)
        arch_vsn.setup()
        tree.tagging_method = 'names'
        open(tree/'foo', 'w').write('Hello, World!\n')
        tree.import_()
        arch_rev = arch_vsn['base-0']
        db_rev.clone_files(arch_rev.iter_files())
        # Now, let's check that the data looks correct.
        from canonical.arch.database import ChangesetFile
        from canonical.arch.database import ChangesetFileName
        from canonical.arch.database import ChangesetFileHash
        db_cset = db_rev.changeset
        db_files = list(ChangesetFile.select("changeset = '%s'" % db_cset.id))
        db_names = [F.changesetfilename.filename for F in db_files]
        db_names.sort()
        expected = ['bah--meh--0--base-0.src.tar.gz', 'checksum', 'log']
        self.assertEqual(expected, db_names)
        for db_file in db_files:
            db_hashes = list(ChangesetFileHash.select(
                "changesetfile = '%s'" % db_file.id))
            filename = db_file.changesetfilename.filename
            if filename == 'checksum':
                self.assertEqual(list(), db_hashes) # checksums have no hash
            else:
                for db_hash in db_hashes:
                    def is_hexa(s):
                        for C in s:
                            if C not in '0123456789abcdef': return False
                        return True
                    if not db_hash.hash or not is_hexa(db_hash.hash):
                        self.fail("hash %d for %s is not hexa: %r" %
                                  (db_hash.hashalg, filename, db_hash.hash))
            
    tests.append('test_clone_files')


def test_suite():
    return unittest.TestSuite()

def main(argv):
    """Run the full test suite."""
    suite = unittest.TestSuite()
    def addTests(klass): suite.addTests(map(klass, klass.tests))
    # there should be a more elegant way - addClasses or something
    addTests(Archive)
    addTests(ArchiveLocation)
    addTests(ArchiveLocationRegistry)
    addTests(Archives)
    addTests(Category)
    addTests(Branch)
    addTests(Version)
    addTests(Revision)
    addTests(RevisionImport)
    # addTests(NamespaceObject)
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful(): return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
