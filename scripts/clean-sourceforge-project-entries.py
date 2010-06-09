#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import re
import sys

import _pythonpath

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.database.product import Product
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.interfaces.product import (
    valid_sourceforge_project_name)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


re_find_project_names = [
    re.compile(r'(?:sou?rcefor..|sf)[.]net/projects?/([^/]+)'),
    re.compile(r'([a-zA-Z0-9-]+)[.](?:sou?rceforge|sf)[.]net'),
    ]


def extract_project_name(project_name):
    # Remove whitespace and slashes.
    project_name = project_name.strip().strip('/')
    if valid_sourceforge_project_name(project_name):
        return project_name

    # Try to pattern match.
    for regex in re_find_project_names:
        match = regex.search(project_name)
        if match is not None:
            if valid_sourceforge_project_name(match.group(1)):
                return match.group(1)

    # No luck.
    return None


def main(argv):
    execute_zcml_for_scripts()
    ztm = initZopeless()
    store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    # Get all products with a sourceforgeproject.
    products = store.find(Product,
                          Product.sourceforgeproject != None,
                          Product.sourceforgeproject != '')

    for product in products:
        if not valid_sourceforge_project_name(product.sourceforgeproject):
            extracted_project_name = (
                extract_project_name(product.sourceforgeproject))
            print '%r ==> %r' % (
                product.sourceforgeproject, extracted_project_name)
            product.sourceforgeproject = extracted_project_name

    ztm.commit()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
