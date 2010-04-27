#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a XXX comment reports in many formats."""


__metaclass__ = type


import cgi
from optparse import OptionParser
import os
import re
import sys
from textwrap import dedent
import time

from bzrlib import bzrdir
from bzrlib.errors import (NotBranchError)


excluded_dir_re = re.compile(r'.*(not-used|lib/mailman)')
excluded_file_re = re.compile(r'.*(pyc$)')


class Report:
    """The base class for an XXX report."""
    # Match XXX comments.
    xxx_re = re.compile('^\s*(<!--|//|#) XXX[:,]?')

    def __init__(self, root_dir, output_name=None):
        """Create and write the HTML report to a file.

        :param root_dir: The root directory that contains files with comments.
        :param output_name: The name of the html file to write to.
        """
        assert os.path.isdir(root_dir), (
            "Root directory does not exist: %s." % root_dir)
        self.root_dir = root_dir
        self.output_name = output_name
        self.revno = self._getBranchRevno()
        self.comments = self._findComments()

    def _close(self, output_file):
        """Close the output_file if it was opened."""
        if self.output_name is not None:
            output_file.close()

    def _getBranchRevno(self):
        """Return the bazaar revision number of the branch or None."""
        # pylint: disable-msg=W0612
        a_bzrdir = bzrdir.BzrDir.open_containing(self.root_dir)[0]
        try:
            branch = a_bzrdir.open_branch()
            branch.lock_read()
            try:
                revno, head = branch.last_revision_info()
            finally:
                branch.unlock()
        except NotBranchError:
            revno = None
        return revno

    def _findComments(self):
        """Set the list of XXX comments in files below a directory."""
        comments = []
        for file_path in self._findFiles():
            comments.extend(self._extractComments(file_path))
        return comments


    def _findFiles(self):
        """Generate a list of matching files below a directory."""
        for path, subdirs, files in os.walk(self.root_dir):
            subdirs[:] = [dir_name for dir_name in subdirs
                          if self._isTraversable(path, dir_name)]
            for file in files:
                file_path = os.path.join(path, file)
                if os.path.islink(file_path):
                    continue
                if excluded_file_re.match(file) is None:
                    yield os.path.join(path, file)

    def _isTraversable(self, path, dir_name):
        """Return True if path/dir_name does not match dir_re pattern."""
        return excluded_dir_re.match(os.path.join(path, dir_name)) is None

    def _extractComments(self, file_path):
        """Return a list of XXX comments in a file.

        :param file_path: The path of the file that contains XXX comments.
        """
        comments = []
        file = open(file_path, 'r')
        try:
            comment = None
            for line_num, line in enumerate(file):
                xxx_mark = self.xxx_re.match(line)
                if xxx_mark is None and comment is None:
                    # The loop is not in a comment or starting a comment.
                    continue
                if xxx_mark is not None and comment is not None:
                    # Two XXX comments run together.
                    self._finaliseComment(comments, comment)
                    comment = None
                if xxx_mark is not None and comment is None:
                    # Start a new comment.
                    comment = self.extractMetadata(line)
                    comment['file_path'] = file_path
                    comment['line_no'] = line_num + 1
                    comment['context_list'] = []
                elif '#' in line and '##' not in line:
                    # Continue collecting the comment text.
                    leading_, text = line.split('#', 1)
                    comment['text_list'].append(text.lstrip())
                elif xxx_mark is None and len(comment['context_list']) < 2:
                    # Collect the code context of the comment.
                    comment['context_list'].append(line)
                elif xxx_mark is None and len(comment['context_list']) == 2:
                    # Finalise the comment.
                    comment['context_list'].append(line)
                    self._finaliseComment(comments, comment)
                    comment = None
                else:
                    raise ValueError, (
                        "comment or xxx_mark are in an unknown state.")
            if comment is not None:
                self._finaliseComment(comments, comment)
        finally:
            file.close()
        return comments

    def _finaliseComment(self, comments, comment):
        """Replace the lists with strs and append the comment to comments."""
        context = ''.join(comment['context_list'])
        if context.strip() == '':
            # Whitespace is not context; do not store it.
            context = ''
        comment['context'] = context
        comment['text'] = ''.join(comment['text_list']).strip()
        del comment['context_list']
        del comment['text_list']
        comments.append(comment)

    # The standard XXX comment form of:
    # 'XXX: First Last Name 2007-07-01 bug=nnnn spec=cccc:'
    # Colons, commas, and spaces may follow each token.
    xxx_person_date_re = re.compile(r"""
        .*XXX[:,]?[ ]                               # The XXX indicator.
        (?P<person>[a-zA-Z][^:]*[\w])[,: ]*         # The persons's nick.
        (?P<date>\d\d\d\d[/-]?\d\d[/-]?\d\d)[,: ]*  # The date in YYYY-MM-DD.
        (?:[(]?bug[s]?[= ](?P<bug>[\w-]*)[),: ]*)?  # The bug id.
        (?:[(]?spec[= ](?P<spec>[\w-]*)[),: ]*)?    # The spec name.
        (?P<text>.*)                                # The comment text.
        """, re.VERBOSE)

    # An uncommon XXX comment form of:
    # 'XXX: 2007-01-01 First Last Name bug=nnnn spec=cccc:'
    # Colons, commas, and spaces may follow each token.
    xxx_date_person_re = re.compile(r"""
        .*XXX[:,]?[ ]                               # The XXX indicator.
        (?P<date>\d\d\d\d[/-]?\d\d[/-]?\d\d)[,: ]*  # The date in YYYY-MM-DD.
        (?P<person>[a-zA-Z][\w]+)[,: ]*             # The person's nick.
        (?:[(]?bug[s]?[= ](?P<bug>[\w-]*)[),: ]*)?  # The bug id.
        (?:[(]?spec[= ](?P<spec>[\w-]*)[),: ]*)?    # The spec name.
        (?P<text>.*)                                # The comment text.
        """, re.VERBOSE)

    def extractMetadata(self, comment_line):
        """Return a dict of metadata extracted from the comment line.

        :param comment_line: The first line of an XXX comment contains the
            metadata.
        :return: dict(person, date, bug, spec, and [text]). The text is the
        same as remainder of the comment_line after the metadata is extracted.
        """
        comment = dict(person=None, date=None, bug=None, spec=None, text=[])
        match = (self.xxx_person_date_re.match(comment_line)
                 or self.xxx_date_person_re.match(comment_line))
        if match is not None:
            # This comment follows a known style.
            comment['person'] = match.group('person')
            comment['date'] = match.group('date')
            comment['bug'] = match.group('bug') or None
            comment['spec'] = match.group('spec') or None
            text = match.group('text').lstrip(':, ')
        else:
            # Unknown comment format.
            text = comment_line

        text = text.strip()
        comment['text_list'] = [text + '\n']
        return comment

    def write(self):
        """Write the total count of comments."""
        output_file = self._open()
        try:
            output_file.write('%s\n' % len(self.comments))
            output_file.flush()
        finally:
            self._close(output_file)

    def _open(self):
        """Open the output_name or use STDOUT."""
        if self.output_name is not None:
            return open(self.output_name, 'w')
        return sys.stdout


class HTMLReport(Report):
    """A HTML XXX report."""
    # Match URLs.
    http_re = re.compile('(https?://[^ \n&]*)')

    # Match bugs.
    bug_link_re = re.compile(r'\b(bugs?:?) #?(\d+)', re.IGNORECASE)

    report_top = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
  <head>
    <title>XXX Comment report for Launchpad</title>
    <style type="text/css" media="screen, print">
      @import url(https://launchpad.net/+icing/rev6895/+style-slimmer.css);
      .context {
        border: #666 1px dashed;
        width: 50em;
      }
    </style>
  </head>

  <body style="margin: 1em;">
    <h1>XXX Comment report for Launchpad</h1>

    <p>
      A report of the XXX comments in the rocketfuel branch. All files
      except *.pyc files were examined.
      <br />This report may also be available as a tab-delimted file:
      <a href="xxx-report.csv">xxx-report.csv</a>
    </p>

    <h3>Summary</h3>

    <p>
      There are <strong>%(commentcount)s XXX comments</strong>
      in <strong>revno: %(revno)s</strong>.
      <br />Generated on %(reporttime)s.
    </p>

    <hr/>

    <h3>Listing</h3>

    <ol>"""

    report_comment = """
      <li>
        <div>
          <strong>File: %(file_path)s:%(line_no)s</strong>
        </div>
        <div style="margin: .5em 0em 0em 0em;">
        <strong class="xxx">XXX</strong>:
        <strong class="person">%(person)s</strong>
        <strong class="date">%(date)s</strong>
        bug %(bugurl)s
        spec %(specurl)s
        </div>
        <pre style="margin-top: 0px;">%(text)s</pre>
        <pre class="context">%(context)s</pre>
      </li>"""

    report_bottom = """
    </ol>
  </body>
</html>
"""

    def write(self):
        """Write the report in HTML format."""
        report_time = time.strftime(
            "%a, %d %b %Y %H:%M:%S UTC", time.gmtime())
        output_file = self._open()
        try:
            output_file.write(
                self.report_top % {"commentcount": len(self.comments),
                              "reporttime": report_time,
                              "revno": self.revno})

            for comment in self.comments:
                comment['text'] = self.markupText(comment['text'])
                comment['context'] = self.markupText(comment['context'])
                if comment['bug'] is not None:
                    comment['bugurl'] = (
                        '<a href="https://bugs.launchpad.net/bugs/%s">%s</a>'
                        % (comment['bug'], comment['bug']))
                else:
                    comment['bugurl'] = comment['bug']
                if comment['spec'] is not None:
                    comment['specurl'] = (
                        '<a href="https://blueprints.launchpad.net'
                        '/launchpad-project/+specs?searchtext=%s">%s</a>'
                        % (comment['spec'], comment['spec']))
                else:
                    comment['specurl'] = comment['spec']
                output_file.write(self.report_comment % comment)

            output_file.write(self.report_bottom)
            output_file.flush()
        finally:
            self._close(output_file)

    def markupText(self, text):
        """Return the line as HTML markup.

        :param text: The text to escape and link.
        """
        text = cgi.escape(text)
        text = self.http_re.sub(r'<a href="\1">\1</a>', text)
        bug_sub = r'<a href="https://bugs.launchpad.net/bugs/\2">\1 \2</a>'
        text = self.bug_link_re.sub(bug_sub, text)
        return text


class CSVReport(Report):
    """A CSV XXX report."""
    report_header = (
        'File_Path, Line_No, Person, Date, Bug, Spec, Text\n')
    report_comment = (
        '%(file_path)s, %(line_no)s, '
        '%(person)s, %(date)s, %(bug)s, %(spec)s, %(text)s\n')

    def markupText(self, text):
        """Return the line as TSV markup.

        :param text: The text to escape.
        """
        if text is not None:
            return text.replace('\n', ' ').replace(',', ';')

    def write(self):
        """Write the report in CSV format."""
        output_file = self._open()
        try:
            output_file.write(self.report_header)
            for comment in self.comments:
                comment['person'] = self.markupText(comment['person'])
                comment['text'] = self.markupText(comment['text'])
                output_file.write(self.report_comment % comment)
            output_file.flush()
        finally:
            self._close(output_file)


class TSVReport(CSVReport):
    """A TSV XXX report."""
    report_header = (
        'File_Path\tLine_No\tPerson\tDate\tBug\tSpec\tText\n')
    report_comment = (
        '%(file_path)s\t%(line_no)s\t'
        '%(person)s\t%(date)s\t%(bug)s\t%(spec)s\t%(text)s\n')

    def markupText(self, text):
        """Return the line as TSV markup.

        :param text: The text to escape.
        """
        if text is not None:
            return text.replace('\n', ' ').replace('\t', ' ')


def get_option_parser():
    """Return the option parser for this program."""
    usage = dedent("""    %prog [options] <root-dir>

    Create a report of all the XXX comments in the files below a directory.
    Set the -f option to 'count' to print the total number of XXX comments,
    which is the default when -f is not set.""")
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-f", "--format", dest="format", default="count",
        help="the format of the report: count, html, csv, tsv")
    parser.add_option(
        "-o", "--output", dest="output_name",
        help="the name of the output file, otherwise STDOUT is used")
    return parser


def main(argv=None):
    """Run the command line operations."""
    if argv is None:
        argv = sys.argv
    parser = get_option_parser()
    (options, arguments) = parser.parse_args(args=argv[1:])
    if len(arguments) != 1:
        parser.error('No root directory was provided.')
    root_dir = arguments[0]

    if options.format.lower() == 'html':
        report = HTMLReport(root_dir, options.output_name)
    elif options.format.lower() == 'tsv':
        report = TSVReport(root_dir, options.output_name)
    elif options.format.lower() == 'csv':
        report = CSVReport(root_dir, options.output_name)
    else:
        report = Report(root_dir, options.output_name)
    report.write()
    sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())

