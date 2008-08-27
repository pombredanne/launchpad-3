#!/usr/bin/python2.4
# Copyright 2007-2008 Canonical Ltd.  All rights reserved.
"""Create a XXX comment report in HTML format."""


__metaclass__ = type


import cgi
import os
import re
import sys
import time

from bzrlib import bzrdir
from bzrlib.errors import (NotBranchError)


dir_re = re.compile('(sourcecode)')
file_re = re.compile('.*(pyc$)')


class Report:
    """The base class for an XXX report."""


def get_branch_revno(root_dir):
    """Return the bazaar revision number of the branch or None."""
    # pylint: disable-msg=W0612
    a_bzrdir = bzrdir.BzrDir.open_containing(root_dir)[0]
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


def find_comments(root_dir):
    """Return a list of XXX comments in files below a directory.

    :param root_dir: The root directory that contains files with comments.
    """
    comments = []
    for file_path in find_files(root_dir, dir_re, file_re):
        comments.extend(extract_comments(file_path))
    return comments


def find_files(root_dir, skip_dir_pattern, skip_file_pattern):
    """Generate a list of matching files below a directory.

    :param root_dir: The root directory that will be walked for files.
    :param skip_dir_pattern: An re pattern of the directory names to skip.
    :param skip_file_pattern: An re pattern of the file names to skip.
    """
    for path, subdirs, files in os.walk(root_dir):
        subdirs[:] = [dir for dir in subdirs
                      if skip_dir_pattern.match(dir) is None]
        for file in files:
            file_path = os.path.join(path, file)
            if os.path.islink(file_path):
                continue
            if skip_file_pattern.match(file) is None:
                yield os.path.join(path, file)


# Match XXX comments.
xxx_re = re.compile('^\s*(<!--|//|#) XXX[:,]?')


def extract_comments(file_path):
    """Return a list of XXX comments in a file.

    :param file_path: The path of the file that contains XXX comments.
    """
    comments = []
    file = open(file_path, 'r')
    try:
        comment = None
        for line_num, line in enumerate(file):
            xxx_mark = xxx_re.match(line)
            if xxx_mark is None and comment is None:
                # The loop is not in a comment or starting a comment.
                continue
            elif xxx_mark is not None and comment is None:
                # Start a new comment.
                comment = extract_metadata(line)
                comment['file_path'] = file_path
                comment['line_no'] = line_num + 1
                comment['context'] = []
            elif xxx_mark is not None and comment is not None:
                # Two XXX comments run together.
                comment['context'] = ''
                comment['text'] = ''.join(comment['text'])
                comments.append(comment)
                comment = extract_metadata(line)
                comment['file_path'] = file_path
                comment['line_no'] = line_num + 1
                comment['context'] = []
            elif '#' in line and '##' not in line:
                # Continue collecting the comment text.
                text = ''.join(line.split('#')[1:]).lstrip()
                comment['text'].append(text)
            elif xxx_mark is None and len(comment['context']) < 2:
                # Collect the code context of the comment.
                comment['context'].append(line)
            elif xxx_mark is None and len(comment['context']) == 2:
                # Finalise the comment.
                comment['context'].append(line)
                comment['context'] = ''.join(comment['context'])
                comment['text'] = ''.join(comment['text'])
                comments.append(comment)
                comment = None
            else:
                raise ValueError, (
                    "comment or xxx_mark are in an unknown state.")
    finally:
        file.close()
    return comments


# The standard XXX comment form of:
# 'XXX: First Last Name 2007-07-01 bug=nnnn spec=cccc:'
# Colans, commas, and spaces may follow each token.
xxx_person_date_re = re.compile(r"""
    .*XXX[:,]?[ ]                                  # The XXX indicator.
    (?P<person>[a-zA-Z][^:]*[\w])[,: ]*            # The persons's nick.
    (?P<date>\d\d\d\d[/-]?\d\d[/-]?\d\d)[,: ]*     # The date in YYYY-MM-DD.
    (?:[(]?bug[s]?[= ](?P<bug>[\w-]*)[),: ]*)?     # The bug id.
    (?:[(]?spec[= ](?P<spec>[\w-]*)[),: ]*)?       # The spec name.
    (?P<text>.*)                                   # The comment text.
    """, re.VERBOSE)

# An uncommon XXX comment form of:
# 'XXX: 2007-01-01 First Last Name bug=nnnn spec=cccc:'
# Colons, commas, and spaces may follow each token.
xxx_date_person_re = re.compile(r"""
    .*XXX[:,]?[ ]                                  # The XXX indicator.
    (?P<date>\d\d\d\d[/-]?\d\d[/-]?\d\d)[,: ]*     # The date in YYYY-MM-DD.
    (?P<person>[a-zA-Z][\w]+)[,: ]*                # The person's nick.
    (?:[(]?bug[s]?[= ](?P<bug>[\w-]*)[),: ]*)?     # The bug id.
    (?:[(]?spec[= ](?P<spec>[\w-]*)[),: ]*)?       # The spec name.
    (?P<text>.*)                                   # The comment text.
    """, re.VERBOSE)


def extract_metadata(comment_line):
    """Return a dict of metadata extracted from the comment line.

    :param comment_line: The first line of an XXX comment contains the
        metadata.
    :return: dict(person, date, bug, spec, and [text]). The text is the
    same as remainder of the comment_line after the metadata is extracted.
    """
    comment = dict(person=None, date=None, bug=None, spec=None, text=[])
    match = (xxx_person_date_re.match(comment_line)
             or xxx_date_person_re.match(comment_line))
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
    if text != '':
        comment['text'] = [text + '\n']
    return comment


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
      <a href="xxxreport.csv">xxxreport.csv</a>
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
        spec %(spec)s
        </div>
        <pre style="margin-top: 0px;">%(text)s</pre>
        <pre class="context">%(context)s</pre>
      </li>"""

    report_bottom = """
    </ol>
  </body>
</html>
"""

    def __init__(self, output_name, comments, revno=None):
        """Create and write the HTML report to a file.

        :param output_name: The name of the html file to write to.
        :param comments: A list of comment dicts to include in the report.
        :param revno: The revision number of tree the comments came from.
        """
        self.output_name = output_name
        self.comments = comments
        self.revno = revno

    def write(self):
        report_time = time.strftime(
            "%a, %d %b %Y %H:%M:%S UTC", time.gmtime())
        output_file = open(self.output_name, "w")
        try:
            output_file.write(
                self.report_top % {"commentcount": len(self.comments),
                              "reporttime": report_time,
                              "revno": self.revno})

            for comment in self.comments:
                comment['text'] = self.markup_text(comment['text'])
                comment['context'] = self.markup_text(comment['context'])
                if comment['bug'] is not None:
                    comment['bugurl'] = (
                        r'<a href="https://bugs.launchpad.net/bugs/%s">%s</a>'
                        % (comment['bug'], comment['bug']))
                else:
                    comment['bugurl'] = comment['bug']
                output_file.write(self.report_comment % comment)

            output_file.write(self.report_bottom)
            output_file.flush()
        finally:
            output_file.close()

    def markup_text(self, text):
        """Return the line as HTML markup.

        :param text: The text to escape and link.
        """
        text = cgi.escape(text)
        text = self.http_re.sub(r'<a href="\1">\1</a>', text)
        bug_sub = r'<a href="https://bugs.launchpad.net/bugs/\2">\1 \2</a>'
        text = self.bug_link_re.sub(bug_sub, text)
        return text


def create_csv_report(output_name, comments, revno=None):
    """Create and write the comma-separated-value-report to a file.

    :param output_name: The name of the html file to write to.
    :param comments: A list of comment dicts to include in the report.
    :param revno: The revision number of tree the comments came from.
    """
    report_comment = ('%(file_path)s, %(line_no)s, '
                      '%(person)s, %(date)s, %(bug)s, %(spec)s, "%(text)s"\n')
    outputfile = open(output_name, "w")
    try:
        outputfile.write(
            'File_Path, Line_No, Person, Date, Bug, Spec, Text\n')
        for comment in comments:
            comment['text'] = comment['text'].replace(
                '\n', ' ').replace('"', "'").strip()
            outputfile.write(report_comment % comment)
        outputfile.flush()
    finally:
        outputfile.close()


def main(argv=None):
    """Run the command line operations."""
    if argv is None:
        argv = sys.argv
    if len(argv) < 3 or not os.path.isdir(argv[1]):
        print ("Usage: xxxreport.py "
               "<root-dir|log-file> <output-filename>.<csv|html>")
        sys.exit()
    root_dir = argv[1]
    if not os.path.isdir(root_dir):
        print "Log file is not implemented yet."
        sys.exit()
    output_name = argv[2]

    revno = get_branch_revno(root_dir)
    comments = find_comments(root_dir)
    if output_name.endswith('html'):
        report = HTMLReport(output_name, comments, revno)
        report.write()
    else:
        create_csv_report(output_name, comments, revno)


if __name__ == '__main__':
    sys.exit(main())

