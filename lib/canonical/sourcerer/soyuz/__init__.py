#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Soyuz.

This isn't Soyuz, it's a quick and dirty version of Soyuz implemented in
GDBM.
"""

import os
import gdbm


ROOT = __path__[0]

class Database(object):
    TABLES = {
        "Product":                      [ "name" ],
        "UpstreamRelease":              [ "product", "name", "manifest" ],
        "ProductBranchRelationship":    [ "product", "branch", "label" ], # UNUSED
        "Branch":                       [ "repository" ],
        "BranchRelationship":           [ "src", "dst", "label" ],
        "Changeset":                    [ "branch", "patchlvl" ],
        "ManifestEntry":                [ "manifest", "seq", "branch",
                                          "changeset", "kind", "path",
                                          "dirname" ],
        "Manifest":                     [ ],
        "SourcePackage":                [ "name", "manifest" ],
        "SourcePackageRelease":         [ "sourcepackage", "version",
                                          "manifest" ],
        }

    def __init__(self):
        for table, fields in self.TABLES.items():
            setattr(self, table, Table(table, fields))

class Table(object):
    def __init__(self, name, fields):
        self.name = name
        self.fields = list(fields)

        filename = os.path.join(ROOT, name)
        if not os.path.isfile(filename):
            open(filename, "w").close()

        self.db = gdbm.open(filename, "w")

    def contains(self, id):
        return self.db.has_key(str(id))

    def get(self, id):
        if not self.contains(id):
            raise KeyError, "No such record"

        r = Record()
        r._db = self.db
        r._table = self
        r.id = id
        for field in self.fields:
            setattr(r, field, self.db["%s.%s" % (id, field)])

        return r

    def new(self):
        if self.db.has_key("_id"):
            id = int(self.db["_id"]) + 1
        else:
            id = 1
        self.db["_id"] = str(id)

        r = Record()
        r._db = self.db
        r._table = self
        r.id = id
        for field in self.fields:
            setattr(r, field, "")

        return r

    def close(self):
        self.db.close()
        self.db = None

    def find(self, key, value):
        if key not in self.fields:
            raise KeyError, "No such field"

        match = []
        for field in self.db.keys():
            if field.endswith("." + key) and self.db[field] == str(value):
                match.append(self.get(field[:-len("." + key)]))

        return match

class Record(object):
    def save(self):
        self._db[str(self.id)] = str(self.id)
        for field in self._table.fields:
            self._db["%s.%s" % (self.id, field)] = str(getattr(self, field))

    def delete(self):
        del self._db[str(self.id)]
        for field in self._table.fields:
            del self._db["%s.%s" % (self.id, field)]

class RecordObject(object):
    def __init__(self, _):
        self._ = _

    def updateRecord(self):
        self._.save()

    def deleteRecord(self):
        self._.delete()

class Product(RecordObject):
    def __init__(self, _):
        self.name = _.name
        self._ = _

    def updateRecord(self):
        self._.name = self.name
        self._.save()

class ManifestRecordObject(RecordObject):
    def getManifest(self):
        res = db.Manifest.get(self._.manifest)
        return Manifest(res)

class UpstreamRelease(ManifestRecordObject):
    def __init__(self, _):
        if _.product:
            self.product = Product(db.Product.get(_.product))
        else:
            self.product = None
        self.name = _.name
        self._ = _

    def updateRecord(self):
        if self.product:
            self._.product = self.product._.id
        else:
            self._.product = ""
        self._.name = self.name
        self._.save()

class SourcePackage(ManifestRecordObject):
    def __init__(self, _):
        self.name = _.name
        self._ = _

    def updateRecord(self):
        self._.name = self.name
        self._.save()

    def getRelease(self, release):
        res = db.SourcePackageRelease.find("sourcepackage", self._.id)
        for entry in res:
            if entry.version == str(release):
                return SourcePackageRelease(entry)

class SourcePackageRelease(ManifestRecordObject):
    def __init__(self, _):
        if _.sourcepackage:
            self.sourcepackage = SourcePackage(db.SourcePackage.get(_.sourcepackage))
        else:
            self.sourcepackage = None
        self.version = _.version
        self._ = _

    def updateRecord(self):
        if self.sourcepackage:
            self._.sourcepackage = self.sourcepackage._.id
        else:
            self._.sourcepackage = ""
        self._.version = self.version
        self._.save()

class Manifest(list):
    def __init__(self, _):
        self._ = _

        res = [ (e.seq, e)
                for e in db.ManifestEntry.find("manifest", self._.id) ]
        res.sort()
        for seq, entry in res:
            self.append(ManifestEntry(entry))

    def createEntry(self):
        res = db.ManifestEntry.new()
        res.manifest = self._.id
        return ManifestEntry(res)

class ManifestEntry(RecordObject):
    def __init__(self, _):
        if _.branch:
            self.branch = Branch(db.Branch.get(_.branch))
        else:
            self.branch = None
        if _.changeset:
            self.changeset = Changeset(db.Changeset.get(_.changeset))
        else:
            self.changeset = None
        self.seq = _.seq
        self.kind = _.kind
        self.path = _.path
        self.dirname = _.dirname
        self._ = _

    def updateRecord(self):
        if self.branch:
            self._.branch = self.branch._.id
        else:
            self._.branch = ""
        if self.changeset:
            self._.changeset = self.changeset._.id
        else:
            self._.changeset = ""
        self._.seq = self.seq
        self._.kind = self.kind
        self._.path = self.path
        self._.dirname = self.dirname
        self._.save()

class Branch(RecordObject):
    def __init__(self, _):
        self.repository = _.repository
        self._ = _

    def updateRecord(self):
        self._.repository = self.repository
        self._.save()

    def createRelationship(self, dst, label):
        res = db.BranchRelationship.new()
        res.src = self._.id
        res.dst = dst._.id
        res.label = str(label)
        res.save()
        return BranchRelationship(res)

    def getRelations(self, label):
        relations = []

        res = db.BranchRelationship.find("src", self._.id)
        for entry in res:
            if entry.label == str(label):
                relations.append(Branch(db.Branch.get(entry.dst)))

        return relations

class BranchRelationship(RecordObject):
    def __init__(self, _):
        if _.src:
            self.src = Branch(db.Branch.get(_.src))
        else:
            self.src = None
        if _.dst:
            self.dst = Branch(db.Branch.get(_.dst))
        else:
            self.dst = None
        self.label = _.label
        self._ = _

    def updateRecord(self):
        if self.src:
            self._.src = self.src._.id
        else:
            self._.src = ""
        if self.dst:
            self._.dst = self.dst._.id
        else:
            self._.dst = ""
        self._.label = self.label
        self._.save()

class Changeset(RecordObject):
    def __init__(self, _):
        if _.branch:
            self.branch = Branch(db.Branch.get(_.branch))
        else:
            self.branch = None
        self.patchlvl = _.patchlvl
        self._ = _

    def updateRecord(self):
        if self.branch:
            self._.branch = self.branch._.id
        else:
            self._.branch = ""
        self._.patchlvl = self.patchlvl
        self._.save()

def getUpstreamRelease(name):
    res = db.UpstreamRelease.find("name", name)
    if len(res) < 1:
        return None

    return UpstreamRelease(res[0])

def getSourcePackage(name):
    res = db.SourcePackage.find("name", name)
    if len(res) < 1:
        return None

    return SourcePackage(res[0])

def createSourcePackage(name):
    man = db.Manifest.new()
    man.save()

    res = db.SourcePackage.new()
    res.name = str(name)
    res.manifest = man.id
    res.save()

    return SourcePackage(res)

def createBranch(repository):
    res = db.Branch.new()
    res.repository = str(repository)
    res.save()

    return Branch(res)


# naughty, but effective
db = Database()
