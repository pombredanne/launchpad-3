# This file is under the terms of the Python license.
#
# The original author of this work is Brett Cannon. The recipe from
# which this code was used is at:
#
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/358228

"""Wrap textwrap.TextWrapper to properly handle multiple paragraphs"""

import textwrap
import re

class DocWrapper(textwrap.TextWrapper):
    """Wrap text in a document, processing each paragraph individually"""

    def wrap(self, text):
        """Override textwrap.TextWrapper to process 'text' properly when
        multiple paragraphs present"""
        para_edge = re.compile(r"(\n\s*\n)", re.MULTILINE)
        paragraphs = para_edge.split(text)
        wrapped_lines = []
        for para in paragraphs:
            if para.isspace():
                if not self.replace_whitespace:
                    # Do not take the leading and trailing newlines since
                    # joining the list with newlines (as self.fill will do)
                    # will put them back in.
                    if self.expand_tabs:
                        para = para.expandtabs()
                    wrapped_lines.append(para[1:-1])
                else:
                    # self.fill will end up putting in the needed newline to
                    # space out the paragraphs
                    wrapped_lines.append('')
            else:
                wrapped_lines.extend(textwrap.TextWrapper.wrap(self, para))
        return wrapped_lines
