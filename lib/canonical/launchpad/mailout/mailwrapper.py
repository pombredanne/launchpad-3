# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The MailWrapper class."""

__metaclass__ = type
__all__ = [
    'MailWrapper',
    ]


import textwrap


class MailWrapper:
    """Wraps text that should be included in an email.

        :width: how long should the lines be
        :indent: specifies how much indentation the lines should have
        :indent_first_line: indicates whether the first line should be
                            indented or not.

    Note that MailWrapper doesn't guarantee that all lines will be less
    than :width:, sometimes it's better not to break long lines in
    emails. See textformatting.txt for more information.
    """

    def __init__(self, width=72, indent='', indent_first_line=True):
        self.indent = indent
        self.indent_first_line = indent_first_line
        self._text_wrapper = textwrap.TextWrapper(
            width=width, subsequent_indent=indent,
            replace_whitespace=False, break_long_words=False)

    def format(self, text, force_wrap=False):
        """Format the text to be included in an email.

        If force_wrap is False, only paragraphs containing a single line
        will be wrapped.
        """
        wrapped_lines = []

        if self.indent_first_line:
            indentation = self.indent
        else:
            indentation = ''

        # We don't care about trailing whitespace.
        text = text.rstrip()

        # Normalize dos-style line endings to unix-style.
        text = text.replace('\r\n', '\n')

        for paragraph in text.split('\n\n'):
            lines = paragraph.split('\n')

            if len(lines) == 1:
                # We use TextWrapper only if the paragraph consists of a
                # single line, like in the case where a person enters a
                # comment via the web ui, without breaking the lines
                # manually.
                self._text_wrapper.initial_indent = indentation
                wrapped_lines += self._text_wrapper.wrap(paragraph)
            elif force_wrap:
                self._text_wrapper.initial_indent = indentation
                for line in lines:
                    wrapped_lines += self._text_wrapper.wrap(line)
            else:
                # If the user has gone through the trouble of wrapping
                # the lines, we shouldn't re-wrap them for him.
                wrapped_lines += (
                    [indentation + lines[0]] +
                    [self.indent + line for line in lines[1:]])

            if not self.indent_first_line:
                # 'indentation' was temporarily set to '' in order to
                # prevent the first line from being indented. Set it
                # back to self.indent so that the rest of the lines get
                # indented.
                indentation = self.indent

            # Add an empty line so that the paragraphs get separated by
            # a blank line when they are joined together again.
            wrapped_lines.append('')

        # We added one line too much, remove it.
        wrapped_lines = wrapped_lines[:-1]
        return '\n'.join(wrapped_lines)
