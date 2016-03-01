#!/usr/bin/python -S
#
# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
import _pythonpath

import sys
import json

from zope.component import getUtility

from lp.registry.interfaces.gpg import IGPGKeySet
from lp.registry.model.gpgkey import GPGKey
from lp.services.database.interfaces import IStore
from lp.services.scripts.base import LaunchpadScript


class GPGKeyExportScript(LaunchpadScript):

    description = "Export GPG keys as json."

    def add_my_options(self):
        self.parser.add_option(
            '-o', '--output', metavar='FILE', action='store',
            help='Export keys to this file', type='string', dest='output')

    def main(self):
        output = sys.stdout
        if self.options.output is not None:
            output = open(self.options.output, 'wb')

        output.write('[')
        output.write(','.join(get_keys_as_json()))
        output.write(']')
        output.write('\n')

def get_keys_as_json():
    keyset = getUtility(IGPGKeySet)
    for gpg_key in IStore(GPGKey).find(GPGKey):
        key_data = {
            'owner': keyset.getOwnerIdForPerson(gpg_key.owner),
            'id': gpg_key.id,
            'fingerprint': gpg_key.fingerprint,
            'size': gpg_key.keysize,
            'algorithm': gpg_key.algorithm.name,
            'enabled': gpg_key.active,
            'can_encrypt': gpg_key.can_encrypt,
        }
        yield json.dumps(key_data)

if __name__ == '__main__':
    GPGKeyExportScript("gpgkey-export").run()
