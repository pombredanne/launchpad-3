__metaclass__ = type

__all__ = [
    'IHTTPResource',
]

from zope.interface import Interface

class IHTTPResource(Interface):
    """An object published through HTTP."""

    def __call__(self):
        """Publish this resource to the web."""
