# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite


def test_suite():
    return DocTestSuite('lp.services.mail.commands')
