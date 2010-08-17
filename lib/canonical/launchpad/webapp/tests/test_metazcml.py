# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.configuration import xmlconfig


from lp.testing import TestCase


class TestCallDirective(TestCase):

    def test_call(self):
        self.assertEqual(0, called)
        directive = """ 
            <call callable="%(this)s.callable" />
            """ % dict(this=this)
        xmlconfig.string(zcml_configure % directive)
        self.assertEqual(1, called)


def callable():
    global called
    called += 1


called = 0
this = "canonical.launchpad.webapp.tests.test_metazcml"
zcml_configure = """
    <configure xmlns="http://namespaces.zope.org/zope">
      <include package="canonical.launchpad.webapp" file="meta.zcml" />
      %s
    </configure>
    """
