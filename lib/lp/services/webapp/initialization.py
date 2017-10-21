# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initializes the application after ZCML has been processed."""

from zope.component import (
    adapter,
    getSiteManager,
    )
from zope.interface import (
    alsoProvides,
    implementer,
    Interface,
    )
from zope.processlifetime import IDatabaseOpened
import zope.publisher.browser
from zope.publisher.interfaces import IRequest
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.http import IHTTPRequest
from zope.traversing.interfaces import ITraversable

from lp.services.webapp.interfaces import IUnloggedException


@implementer(Interface)
def adapter_mask(*args):
    return None


@adapter(IDatabaseOpened)
def handle_process_start(ev):
    """Post-process ZCML configuration.

    Normal configuration should happen in ZCML (or whatever our Zope
    configuration standard might become in the future).  The only kind
    of configuration that should happen here is automated fix-up
    configuration. Code below should call functions, each of which explains
    why it cannot be performed in ZCML.

    Also see the lp_sitecustomize module for initialization that is done when
    Python first starts.
    """
    fix_up_namespace_traversers()
    customize_get_converter()


def fix_up_namespace_traversers():
    """Block namespace traversers from being found as normal views.

    See bug 589010.

    This is done in a function rather than in ZCML because automation is
    appropriate: there has already been an explicit registration of the
    namespace, and having to also say "please don't assume it is a view"
    is a DRY violation that we can avoid.
    """
    sm = getSiteManager()
    info = 'see %s.fix_up_namespace_traversers' % (__name__,)
    namespace_factories = sm.adapters.lookupAll(
        (Interface, IBrowserRequest), ITraversable)
    for request_iface in (Interface, IRequest, IHTTPRequest, IBrowserRequest):
        for name, factory in namespace_factories:
            current = sm.adapters.lookup(
                (Interface, request_iface), Interface, name)
            if current is factory:
                sm.registerAdapter(
                    adapter_mask,
                    required=(Interface, request_iface), name=name, info=info)


def customize_get_converter(zope_publisher_browser=zope.publisher.browser):
    """URL parameter conversion errors shouldn't generate an OOPS report.

    This injects (monkey patches) our wrapper around get_converter so improper
    use of parameter type converters (like http://...?foo=bar:int) won't
    generate OOPS reports.

    This is done in a function rather than in ZCML because zope.publisher
    doesn't provide fine enough control of this any other way.
    """
    original_get_converter = zope_publisher_browser.get_converter

    def get_converter(*args, **kws):
        """Get a type converter but turn off OOPS reporting if it fails."""
        converter = original_get_converter(*args, **kws)

        def wrapped_converter(v):
            try:
                return converter(v)
            except ValueError as e:
                # Mark the exception as not being OOPS-worthy.
                alsoProvides(e, IUnloggedException)
                raise

        # The converter can be None, in which case wrapping it makes no sense,
        # otherwise it is a function which we wrap.
        if converter is None:
            return None
        else:
            return wrapped_converter

    zope_publisher_browser.get_converter = get_converter
