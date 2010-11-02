# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the sanitize database script."""

__metaclass__ = type

import os.path
import subprocess
import unittest

from canonical.config import (
    config,
    dbconfig,
    )
from canonical.database.sqlbase import (
    connect,
    sqlvalues,
    )
from canonical.testing.layers import DatabaseLayer
from lp.registry.interfaces.person import PersonVisibility
from lp.testing import TestCase


class SanitizeDbScriptTestCase(TestCase):
    layer = DatabaseLayer

    def setUp(self):
        super(SanitizeDbScriptTestCase, self).setUp()
        self.script_path = os.path.join(
            config.root, 'utilities', 'sanitize-db.py')
        DatabaseLayer.force_dirty_database()

    def containsPrivateInformation(self):
        # Return True if we detect known private information in the
        # database.
        con = connect('launchpad')
        try:
            cur = con.cursor()
            cur.execute(
                "SELECT TRUE FROM Person WHERE visibility <> %s LIMIT 1"
                % sqlvalues(PersonVisibility.PUBLIC))
            if cur.fetchone() is None:
                return False
            else:
                return True
        finally:
            # Don't leave the connection dangling or it could block
            # the script.
            con.close()

    def runScript(self, *args):
        cmd = [self.script_path, dbconfig.main_master + ' user=postgres']
        cmd.extend(args)
        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = process.communicate()
        self.assertEqual(
            process.returncode, 0,
            "%s failed: %d\n%s" % (' '.join(cmd), process.returncode, err))
        return (out, err)

    def test_script(self):
        # Run the sanitize-db.py script and confirm it actually
        # changes things.
        self.assertTrue(
            self.containsPrivateInformation(),
            'No private information detected.')
        self.runScript()
        self.assertFalse(
            self.containsPrivateInformation(),
            'Private information not removed.')

    def test_script_dryrun(self):
        # Run the sanitize-db.py script in --dry-run mode and
        # confirm it doesn't change things.
        self.assertTrue(
            self.containsPrivateInformation(),
            'No private information detected.')
        self.runScript('--dry-run')
        self.assertTrue(
            self.containsPrivateInformation(),
            'Private information removed.')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

