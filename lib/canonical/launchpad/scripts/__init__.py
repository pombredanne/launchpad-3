# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Library functions for use in all scripts.

"""
__metaclass__ = type

import os
import threading
import atexit

import zope.app.appsetup
import zope.app.mail.delivery
from zope.configuration.config import ConfigurationMachine
from zope.configuration.config import GroupingContextDecorator
from zope.security.management import setSecurityPolicy
from zope.security.simplepolicies import PermissiveSecurityPolicy

from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy

# XXX: This is a total mess.  I need to work out what this all means.
# -- SteveAlexander, 2005-04-11

class NullItem:
    def __init__(self, context, handler, info, *argdata):
        newcontext = GroupingContextDecorator(context)
        newcontext.info = info
        self.context = newcontext
        self.handler = handler
        self.argdata = argdata

    def contained(self, name, data, info):
        return NullItem(self.context, None, None)

    def finish(self):
        pass

def NullFactory(context, data, info):
    return NullItem(context, data, info)

class CustomMachine(ConfigurationMachine):

    def factory(self, context, name):
        # Hackery to remove 'browser:xxx' directives from being processed.
        # This is needed to avoid page directives, which screw up when you
        # parse the zcml from a cwd that isn't the launchpad root.
        ns, simplename = name
        if ns == u'http://namespaces.zope.org/browser':
            return NullFactory
        else:
            f = ConfigurationMachine.factory(self, context, name)
            return f

def execute_zcml_for_scripts(use_web_security=False):
    """Execute the zcml rooted at launchpad/script.zcml
    
    If use_web_security is True, the same security policy as the web
    application uses will be used. Otherwise everything protected by a
    permission is allowed, and everything else denied.
    """
    scriptzcmlfilename = os.path.normpath(
        os.path.join(os.path.dirname(__file__),
                     os.pardir, os.pardir, os.pardir, os.pardir,
                     'script.zcml'))

    scriptzcmlfilename = os.path.abspath(scriptzcmlfilename)
    from zope.configuration import xmlconfig

    # Hook up custom component architecture calls
    zope.app.component.hooks.setHooks()

    # Load server-independent site config
    context = CustomMachine()
    xmlconfig.registerCommonDirectives(context)
    context = xmlconfig.file(scriptzcmlfilename, execute=True, context=context)

    if use_web_security:
        setSecurityPolicy(LaunchpadSecurityPolicy)
    else:
        setSecurityPolicy(PermissiveSecurityPolicy)


    # Register atexit handler to kill off mail delivery daemon threads, and
    # thus avoid spew at exit.  See:
    # http://mail.python.org/pipermail/python-list/2003-October/192044.html
    # http://mail.python.org/pipermail/python-dev/2003-September/038151.html
    # http://mail.python.org/pipermail/python-dev/2003-September/038153.html

    def kill_queue_processor_threads():
        for thread in threading.enumerate():
            if isinstance(thread, zope.app.mail.delivery.QueueProcessorThread):
                thread.stop()
    atexit.register(kill_queue_processor_threads)

    # This is a convenient hack to set up a zope interaction, before we get
    # the proper API for having a principal / user running in scripts.
    # The script will have full permissions because of the
    # PermissiveSecurityPolicy set up in script.zcml.
    from canonical.launchpad.ftests import login
    login('launchpad.anonymous')


