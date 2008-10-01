import _pythonpath

from storm.locals import Not
from zope.component import getUtility

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)


def get_stacked_branches():
    store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
    return store.find(Branch, Not(Branch.stacked_on == None))


def main():
    execute_zcml_for_scripts()
    for db_branch in get_stacked_branches():
        print '%s %s %s %s' % (
            db_branch.id, db_branch.branch_type.name, db_branch.unique_name,
            db_branch.stacked_on.unique_name)


if __name__ == '__main__':
    main()
