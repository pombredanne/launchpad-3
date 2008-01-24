# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for testing feeds."""

__metaclass__ = type
__all__ = [
    'IThing',
    'Thing',
    'ThingFeedView',
    'validate_feed',
    ]


from cStringIO import StringIO
import socket
from textwrap import wrap

from zope.interface import implements, Interface, Attribute

from canonical.launchpad.webapp.publisher import LaunchpadView

# Importing the feedvalidator changes the default socket timeout,
# so we have to reset it to prevent this error.
# canonical.testing.layers.LayerIsolationError:
#   Test didn't reset the socket default timeout.
default = socket.getdefaulttimeout()
import feedvalidator
from feedvalidator.mediaTypes import FEED_TYPES
socket.setdefaulttimeout(default)


class IThing(Interface):
    value = Attribute('the value of the thing')


class Thing(object):
    implements(IThing)

    def __init__(self, value):
        self.value = value

        def __repr__(self):
            return "<Thing '%s'>" % self.value


class ThingFeedView(LaunchpadView):
    usedfor = IThing
    feedname = "thing-feed"
    def __call__(self):
        return "a feed view on an IThing"


def validate_feed(content, content_type, base_uri):
    """Validate the content of an Atom, RSS, or KML feed.

    :param content: string containing xml feed
    :param content_type: Content-Type HTTP header
    :param base_uri: Feed URI for comparison with <link rel="self">

    Prints formatted list of warnings and errors for use in doctests.
    No return value.
    """
    lines = content.split('\n')
    result = feedvalidator.validateStream(
        StringIO(content),
        contentType=content_type,
        base=base_uri)

    errors = []
    for error_level in (feedvalidator.logging.Error,
                        feedvalidator.logging.Warning,
                        feedvalidator.logging.Info):
        for item in result['loggedEvents']:
            if isinstance(item, error_level):
                errors.append("-------- %s: %s --------"
                    % (error_level.__name__, item.__class__.__name__))
                for key, value in sorted(item.params.items()):
                    errors.append('%s: %s' % (key.title(), value))
                if 'line' not in item.params:
                    continue
                if isinstance(item,
                              feedvalidator.logging.SelfDoesntMatchLocation):
                    errors.append('Location: %s' % base_uri)
                error_line_number = item.params['line']
                column_number = item.params['column']
                errors.append('=')
                # Wrap the line with the error to make it clearer
                # which column contains the error.
                max_line_length = 66
                wrapped_column_number = column_number % max_line_length
                for line_number in range(max(error_line_number-2, 1),
                                         min(error_line_number+3, len(lines))):
                    unicode_line = unicode(
                        lines[line_number-1], 'ascii', 'replace')
                    ascii_line = unicode_line.encode('ascii', 'replace')
                    wrapped_lines = wrap(ascii_line, max_line_length)
                    if line_number == error_line_number:
                        # Point to the column where the error occurs, e.g.
                        # Error: <feed><entriez>
                        # Point: ~~~~~~~~~~~~~^~~~~~~~~~~~~~~
                        point_list = ['~'] * max_line_length
                        point_list[wrapped_column_number] = '^'
                        point_string = ''.join(point_list)
                        index = column_number/max_line_length + 1
                        wrapped_lines.insert(index, point_string)
                    errors.append(
                        "% 3d: %s" % (line_number,
                                      '\n   : '.join(wrapped_lines)))
                errors.append('=')
    if len(errors) == 0:
        print "No Errors"
    else:
        print '\n'.join(errors)
