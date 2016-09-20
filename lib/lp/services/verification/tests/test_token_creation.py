# Copyright 2009, 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import testtools

from lp.services.tokens import create_token


class Test_create_token(testtools.TestCase):

    def test_length(self):
        token = create_token(99)
        self.assertEquals(len(token), 99)
