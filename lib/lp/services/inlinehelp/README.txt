Inline Help System
==================

The inline help system offers a base implementation for help folder called
HelpFolder. They make it easy for components to register directories
containing inline help documentation.

These are lazr.folder.ExportedFolder that automatically export
their subdirectories.

    >>> from canonical.lazr.folder import ExportedFolder
    >>> from lp.services.inlinehelp.browser import HelpFolder

    >>> issubclass(HelpFolder, ExportedFolder)
    True
    >>> HelpFolder.export_subdirectories
    True

ZCML Registration
-----------------

HelpFolder can be easily registered using a ZCML directive. The directive
takes the directory served by the HelpFolder and the request type for which
it should be registered.

    >>> import tempfile
    >>> help_folder = tempfile.mkdtemp(prefix='help')

    >>> from zope.configuration import xmlconfig
    >>> zcmlcontext = xmlconfig.string("""
    ... <configure xmlns:lp="http://namespaces.canonical.com/lp">
    ...   <include package="lp.services.inlinehelp" file="meta.zcml" />
    ...   <lp:help-folder folder="%s"/>
    ... </configure>
    ... """ % help_folder)

The help folder is registered on the ILaunchpadRoot interface.

    >>> from zope.interface import directlyProvides
    >>> from zope.publisher.interfaces.browser import IBrowserRequest
    >>> class FakeRequest:
    ...     pass
    >>> request = FakeRequest()
    >>> directlyProvides(request, IBrowserRequest)

    >>> from zope.component import queryMultiAdapter
    >>> from canonical.launchpad.webapp.publisher import rootObject
    >>> help = queryMultiAdapter((rootObject, request), name="+help")

    >>> help.folder == help_folder
    True

    >>> isinstance(help, HelpFolder)
    True

The help folder can also be registered for a specific request type using the
"type" attribute.

    >>> from zope.publisher.interfaces.http import IHTTPRequest
    >>> directlyProvides(request, IHTTPRequest)

    >>> print queryMultiAdapter((rootObject, request), name="+help")
    None
    >>> zcmlcontext = xmlconfig.string("""
    ... <configure
    ...     xmlns:lp="http://namespaces.canonical.com/lp">
    ...   <include package="lp.services.inlinehelp" file="meta.zcml" />
    ...   <lp:help-folder folder="%s"
    ...                   type="zope.publisher.interfaces.http.IHTTPRequest"/>
    ... </configure>
    ... """ % help_folder)

    >>> queryMultiAdapter((rootObject, request), name="+help")
    <lp.services...>


Cleanup
-------

    >>> from zope.testing.cleanup import cleanUp
    >>> cleanUp()

    >>> import shutil
    >>> shutil.rmtree(help_folder)
