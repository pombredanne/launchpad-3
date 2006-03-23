import os

import bzrlib.bzrdir


def createbranch(branchdir):
    os.makedirs(branchdir)
    tree = bzrlib.bzrdir.BzrDir.create_standalone_workingtree(branchdir)
    f = open(branchdir + 'hello', 'w')
    f.write('foo')
    f.close()
    tree.commit('message')
    return tree

