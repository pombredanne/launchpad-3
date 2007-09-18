#!/usr/bin/python
# arch-tag: 831a7fe6-9e88-499f-9819-289844d1de6c

import sys

tests = [
    ('IProduct', 'Product'),
    ('IEditPOTemplate', 'POTemplate'),
    ('IEditPOFile', 'POFile'),
    ('IPOMsgSet', 'POMsgSet'),
    ('IPOTMsgSet', 'POTMsgSet'),
    ('IPOMsgID', 'POMsgID'),
    ('IPOTranslationSighting', 'POTranslationSighting'),
    ('IPOTranslation', 'POTranslation'),
    ('IBranch', 'Branch'),
    ('IPerson', 'Person'),
    ('ILanguage', 'Language'),
    ('ILanguageSet', 'LanguageSet'),
    ('ISchemaSet', 'SchemaSet'),
    ('ISchema', 'Schema'),
    ('ILabel', 'Label'),
# XXX daniels 2004-12-14: Commented until we restart their use
#    ('ICategory', 'RosettaCategory'),
#    ('ITranslationEffort', 'RosettaTranslationEffort'),
#    ('ITranslationEffortPOTemplate', 'RosettaTranslationEffortPOTemplate'),
    ('IEmailAddress', 'EmailAddress'),
    ]

if '-c' in sys.argv:
    mode = 'class'
elif '-o' in sys.argv:
    mode = 'object'
else:
    raise "no mode specified -- use '-c' (class) or '-o' (object)"

# Preamble.
print """#!/usr/bin/python

# YO! Generated code -- modify at your peril!

import sys
import unittest

from zope.interface.verify import verifyClass, verifyObject
from zope.testing.doctestunit import DocTestSuite

def verifySQLObject(interface, implementation):
    if hasattr(implementation, 'select'):
        return verifyObject(interface, implementation.select()[0])
    else:
        return True

"""

if mode == 'object':
    print "import canonical.lp"
    print
    print "canonical.lp.initZopeless()"
    print

for t in tests:
    (interface, implementation) = t

    print "def test_verify_sql_%s():" % interface[1:].lower()
    print "    '''"
    print "    >>> from canonical.launchpad.interfaces import %s" % interface
    print "    >>> from canonical.launchpad.database import %s" % implementation

    if mode == 'object':
        print "    >>> verifySQLObject(%s, %s)" % (interface, implementation)
    else:
        print "    >>> verifyClass(%s, %s)" % (interface, implementation)

    print "    True"
    print "    '''"
    print

# Postamble.
print """
def test_suite():
    suite = DocTestSuite()
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner()
    r.run(DocTestSuite())
"""

