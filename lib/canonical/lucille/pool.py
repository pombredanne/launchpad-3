# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: d20d2ded-7987-4383-b5b8-4d8cd0c857ba

POOL_DEBIAN = object()

class Poolifier(object):
    """The Poolifier takes a (source name, component) tuple and tells you
    where in the pool it should live.

    E.g.

    Source: mozilla-thunderbird
    Component: main
    Location: main/m/mozilla-thunderbird

    Source: libglib2.0
    Component: main
    Location: main/libg/libglib2.0
    """

    def __init__(self, style = POOL_DEBIAN, component = None):
        self._style = style
        if style is not POOL_DEBIAN:
            raise ValueError, "Unknown style"
        self._component = component

    def poolify(self, source, component = None):
        """Poolify a given source and component name. If the component is
        not supplied, the default set with the component() call is used.
        if that has not been supplied then an error is raised"""
        
        if component is None:
            component = self._component
        if component is None:
            raise ValueError, "poolify needs a component"
        
        if self._style is POOL_DEBIAN:
            if source.startswith("lib"):
                return "%s/%s/%s" % (component,source[:4],source)
            else:
                return "%s/%s/%s" % (component,source[:1],source)

    def component(self, component):
        """Set the default component for the poolify call"""
        self._component = component
