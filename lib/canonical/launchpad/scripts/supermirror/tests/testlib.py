import unittest
import os
from supermirror.genericbranch import GenericBranch

class TestConfig(unittest.TestCase):

    def testNegativeDetection(self):
        from supermirror.genericbranch import GenericBranch
        bn = "testdir/genericbranch-negative"
        branchdir = os.getcwd() + os.sep + bn
        createbranch(bn)
        mybranch = GenericBranch(branchdir, None)
        if mybranch.supportsFormat() is not False:
            raise RuntimeError

    def testPositiveDetection(self):
        from supermirror.genericbranch import GenericBranch
        bn = "testdir/genericbranch-positive"
        branchdir = os.path.join(os.getcwd(),bn)
        createbranch(bn)
        handle = open (os.path.join (branchdir, ".bzr/branch-format"), "w")
        handle.write("A non existant detection file\n")
        handle.close()

        mybranch = GenericBranch(branchdir, None)
        if mybranch.supportsFormat() is not True:
            raise RuntimeError


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

def createbranch(directory):
    whine("Creating branch at %s" % (directory))
    current = os.getcwd()
    os.makedirs(directory)
    os.chdir(directory)
    whine(os.popen("bzr init").readlines())
    whine(os.popen("echo hello > hello").readlines())
    whine(os.popen(" bzr add hello").readlines())
    whine(os.popen("bzr commit -m'Test branch' 2> /dev/null").readlines())
    os.chdir(current)

def random_commit(directory):
    current = os.getcwd()
    os.chdir(directory)
    filename = _randomname()
    handle = open (filename, "w")
    handle.write("%s\n%s\n%s\n" % (filename, filename, filename))
    handle.close()
    whine(os.popen(" bzr add %s" % (filename)).readlines())
    whine(os.popen(" bzr commit -m \"%s\"" % (filename)).readlines())
    os.chdir(current)

def _randomname():
    import random

    name = ""
    count=10

    randomizer = random.Random()
    while count:
        name = name + randomizer.choice("abcdefghijklmnopqrstuvwxyz")
        count = count - 1
    return name

def whine(data):
    if os.environ.get("DEBUG") is not None:
        print "\n", data

