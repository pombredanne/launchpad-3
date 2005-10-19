import logging
import MySQLdb

import _pythonpath

from zope.component import getUtility
from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.helpers import setupInteraction
from canonical.launchpad.interfaces import IPersonSet

from canonical.launchpad.scripts import bugzilla

logging.basicConfig(level=logging.INFO)

ztm = initZopeless()
execute_zcml_for_scripts()

person = getUtility(IPersonSet).getByName('name12')
setupInteraction(person)

db = MySQLdb.connect(db='bugs_warty')
bz = bugzilla.Bugzilla(db)

bz.handle_bug(6002)

ztm.commit()
