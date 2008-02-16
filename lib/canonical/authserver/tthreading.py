import threading

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata

from zope.interface.interface import Method

def get_method_names_in_interface(interface):
    for attribute_name in interface:
        if isinstance(interface[attribute_name], Method):
            yield attribute_name


def defer_methods_to_threads(obj, interface):
    for name in get_method_names_in_interface(interface):
        setattr(obj, name, defer_to_thread(getattr(obj, name)))


def defer_to_thread(function):
    """Run in a thread and return a Deferred that fires when done."""

    def decorated(*args, **kwargs):
        deferred = defer.Deferred()

        def run_in_thread():
            return threads._putResultInDeferred(
                deferred, function, args, kwargs)

        t = threading.Thread(target=run_in_thread)
        t.start()
        return deferred

    return mergeFunctionMetadata(function, decorated)
