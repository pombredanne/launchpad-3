#!/usr/bin/env


# read from database
# write to database
# seq# automatically generated
# deleteRecord


import soyuz


def getSourcePackage(package):
    return None

def createSourcePackage(package):
    sp = SourcePackage()
    sp.name = package
    return sp

def createBranch(repo):
    b = [ b for b in Branch.all if b.repository == repo ]
    if len(b):
        branch = b[0]
    else:
        branch = Branch()
        branch.repository = repo

    return branch


class SourcePackage(object):
    def __init__(self):
        self.dirty = True
        self.name = ""
        self.releases = {}

    def getRelease(self, release):
        return self.releases[release]

    def createRelease(self, release):
        r = SourcePackageRelease()
        r.version = release
        r.manifest = Manifest()

        self.releases[release] = r
        return r


class SourcePackageRelease(object):
    def __init__(self):
        self.dirty = True
        self.version = ""
        self.manifest = None

    def getManifest(self):
        return self.manifest


class Manifest(list):
    def __init__(self):
        self.dirty = True

    def createEntry(self):
        e = ManifestEntry()
        self.append(e)
        return e

    def write(self, file):
        for m in self:
            m.write(file)

    def read(self, file):
        try:
            while True:
                e = ManifestEntry()
                e.read(file)
                self.append(e)
        except IOError:
            pass


class ManifestEntry(object):
    def __init__(self):
        self.dirty = True
        self.branch = None
        self.changeset = None
        self.kind = ""
        self.path = None
        self.dirname = None

    def write(self, file):
        if self.branch is not None:
            print >>file, "Branch:", self.branch.repository
            for r in self.branch.getRelatives():
                print >>file, "Relative:", r.label, r.dst.repository
        print >>file, "Kind:", self.kind
        if self.path is not None:
            print >>file, "Path:", self.path
        if self.dirname is not None:
            print >>file, "Dirname:", self.dirname
        print >>file

    def read(self, file):
        for line in file:
            line = line.rstrip()
            if not len(line): return

            (key, value) = line.split(":", 1)
            value = value.lstrip()
            if key == "Branch":
                self.branch = createBranch(value)
            elif key == "Relative":
                (label, dest_repo) = value.split(" ", 1)
                dest = createBranch(dest_repo)
                self.branch.createRelationship(dest, label)
            elif key == "Kind":
                self.kind = value
            elif key == "Path":
                self.path = value
            elif key == "Dirname":
                self.dirname = value
        else:
            raise IOError, "End of file"

    def deleteRecord(self):
        print "FIXME!"

class Branch(object):
    all = []

    def __init__(self):
        self.dirty = True
        self.repository = ""
        self.all.append(self)

    def createRelationship(self, dest, label):
        r = BranchRelationship()
        r.src = self
        r.dst = dest
        r.label = label
        return r

    def getRelatives(self):
        ret = []
        for r in BranchRelationship.all:
            if r.src == self:
                ret.append(r)
        return ret

    def getRelations(self, label):
        ret = []
        for r in BranchRelationship.all:
            if r.src == self and r.label == label:
                ret.append(r.dst)
        return ret


class BranchRelationship(object):
    all = []

    def __init__(self):
        self.dirty = True
        self.src = None
        self.dst = None
        self.label = ""
        self.all.append(self)
