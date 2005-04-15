#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.

import sys

import canonical.lp
from canonical.launchpad.database import Project

def showproducts(projectname):
    projects = list(Project.selectBy(name = projectname))

    if len(projects) != 1:
        raise KeyError, projectname

    project = projects[0]

    for product in project.products():
        print product.name

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise RuntimeError("usage: %s project" % sys.argv[0])

    project = sys.argv[1]

    ztm = canonical.lp.initZopeless()

    showproducts(project)

