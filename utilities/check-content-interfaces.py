#! /usr/bin/python2.4
# Copyright 2007 Canonical

"""
check-content-interfaces.py - Check Content Interfaces.

= Launchpad Content Interfaces =

XXX flacoste 2007/02/21 Ideally this should be a unit test.
Unfortunately, it would currently fail. See bug 87199.

Launchpad is complex piece of software composed of multiple
applications. Many components use other components, so it is important
for each of them to clearly define the interface it supports and make
sure that it respects its contract.

This is especially important as newcomers joining the team will often look
at the interface of a component in another part of Launchpad to know
what properties/methods are available on the object.

Ideally, all components should have a test of this form as part of their
system documentation.

    > > > verifyObject(IContentInterface, object)
    True

This is a fall back test that makes sure that all content classes
really do implement the interfaces it declares to.

It's not because a class implements correctly an interface that
verifyObject on its instances would also pass. verifyClass only checks
the methods of the interface (since it is possible that some attributes
will be provided at construction time). Also additional constraints will
be checked on instance attributes that are part of a schema.

"""

import _pythonpath

from zope.interface import implementedBy
from zope.interface.exceptions import (
    BrokenImplementation, BrokenMethodImplementation)
from zope.interface.verify import verifyClass

import canonical.launchpad.database

def check_content_classes():
    classes_checked = 0
    classes_with_failures = 1
    for class_name in dir(canonical.launchpad.database):
        klass = getattr(canonical.launchpad.database, class_name)
        # Skip names that don't implement anything.
        if getattr(klass, '__implemented__', None) is None:
            continue
        for interface in implementedBy(klass):
            interface_name = interface.__name__.split('.')[-1]
            try:
                classes_checked += 1
                result = verifyClass(interface, klass)
            except BrokenImplementation, e:
                classes_with_failures += 1
                print "%s fails to implement %s: missing attribute %s" % (
                    class_name, interface_name, e.name)
            except BrokenMethodImplementation, e:
                classes_with_failures += 1
                print "%s fails to implement %s: invalid method %s: %s" % (
                    class_name, interface_name, e.method, e.mess)
    print "** Checked %d content classes. Found %d with broken implementation." % (
        classes_checked, classes_with_failures)


if __name__ == '__main__':
    check_content_classes()
