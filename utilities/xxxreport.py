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
    """Return a list of XXX comments in files below a directory."""
    comments = []
    for file_path in find_files(root_dir, dir_re, file_re):
        comments.extend(extract_comments(file_path))
    return comments


def find_files(root_dir, skip_dir_pattern, skip_file_pattern):
    """Generate a list of matching files below a directory."""
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
    """Return a list of XXX comments in a file."""
    comments = []
    file = open(file_path, 'r')
    comment = None
    for line_num, line in enumerate(file):
        xxx_mark = xxx_re.match(line)
        if xxx_mark is None and comment is None:
            continue
        elif xxx_mark is not None and comment is None:
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
            text = ''.join(line.split('#')[1:]).lstrip()
            comment['text'].append(text)
        elif xxx_mark is None and len(comment['context']) < 2:
            comment['context'].append(line)
        elif xxx_mark is None and len(comment['context']) == 2:
            comment['context'].append(line)
            comment['context'] = ''.join(comment['context'])
            comment['text'] = ''.join(comment['text'])
            comments.append(comment)
            comment = None
        else:
            raise ValueError, "comment or xxx_mark are in an unknown state."
    file.close()
    return comments


# The standard annotation form of 'XXX: First Last Name 2007-07-01:'
# Colans, commas, and spaces may follow each token.
person_date_re = re.compile(r"""
    .*XXX[:,]?[ ]                         # The XXX indicator.
    ([a-zA-Z][^:]*)[:,]?[ ]               # The persons's nick.
    (\d\d\d\d[/-]?\d\d[/-]?\d\d)[:,]?[ ]? # The date in YYYY-MM-DD.
    (.*)
    """, re.VERBOSE)
# An uncommon annotation form of 'XXX: 2007-01-01 First Last Name:'
# Colons, commas, and spaces may follow each token.
date_person_re = re.compile(r"""
    .*XXX[:,]?[ ]                         # The XXX indicator.
    (\d\d\d\d[/-]?\d\d[/-]?\d\d)[:,]?[ ]? # The date in YYYY-MM-DD.
    ([a-zA-Z][\w]+)                       # The person's nick.
    (.*)
    """, re.VERBOSE)
# A reference to a spec in the commment: spec grand-unification-fix
spec_re = re.compile(r"spec[= ]([\w-]*)[,:]?[ ]?(.*)")
# A reference to a bug in the commment: bug=12345 or bugs 1234, 1245
bug_re = re.compile(r"[(]?bug[s]?[= ]?([\w-]*)(, [\w-]*)*[)]?[:,]?[ ]?(.*)")


def extract_metadata(comment_line):
    """Return a dict of metadata extracted from the lines of a comment.

    Return person, date, bug, spec, and text as keys. The text is the
    same as remainder of the comment_line after the metadata is extracted.
    """
    comment = dict(person=None, date=None, bug=None, spec=None, text=None)
    match = person_date_re.match(comment_line)
    if match is not None:
        # This comment follows the standard annotation form.
        comment['person'] = match.group(1).strip(':, ')
        comment['date'] = match.group(2).strip(':, ')
        remainder = match.group(3).strip(':, ')
    else:
        # The comment uses the uncommon annotation form.
        match = date_person_re.match(comment_line)
        if match is not None:
            comment['date'] = match.group(1).strip(':, ')
            comment['person'] = match.group(2).strip(':, ')
            remainder = match.group(3).strip(':, ')
        else:
            # Unknown annotation format
            remainder = comment_line

    match = spec_re.match(remainder)
    if match is not None:
        comment['spec'] = match.group(1).strip(':, ')
        remainder = match.group(2)
    match = bug_re.match(remainder)
    if match is not None:
        comment['bug'] = match.group(1).strip(':, ')
        remainder = match.group(2)
    if remainder is not None:
        comment['text'] = [remainder.strip(':, ') + ' \n']
    else:
        comment['text'] = []
    return comment


# Match URLs.
http_re = re.compile('(https?://[^ \n&]*)')
# Match bugs.
bug_link_re = re.compile(r'\bbugs?:? #?(\w+)', re.IGNORECASE)

# HTML report parts
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
</html>"""


def markup_text(text, comment):
    """Return the line as HTML markup."""
    text = cgi.escape(text)
    text = http_re.sub(r'<a href="\1">\1</a>', text)
    bug_sub = r'<a href="https://bugs.launchpad.net/bugs/\1">\1</a>'
    text = bug_link_re.sub(bug_sub, text)
    return text


def create_html_report(outputname, comments, revno=None):
    """Create and write the HTML report to a file."""
    report_time = time.strftime("%a, %d %b %Y %H:%M:%S UTC", time.gmtime())
    outputfile = open(outputname, "w")
    outputfile.write(
        report_top % {"commentcount": len(comments),
                      "reporttime": report_time,
                      "revno": revno})

    for comment in comments:
        comment['text'] = markup_text(comment['text'], comment)
        comment['context'] = markup_text(comment['context'], comment)
        if comment['bug'] is not None:
            comment['bugurl'] = (
                r'<a href="https://bugs.launchpad.net/bugs/%s">%s</a>' %
                (comment['bug'], comment['bug']))
        else:
            comment['bugurl'] = comment['bug']
        outputfile.write(report_comment % comment)

    outputfile.write(report_bottom)
    outputfile.flush()
    outputfile.close()


def create_csv_report(outputname, comments, revno=None):
    """Create and write the comma-separated-value-report to a file."""
    report_comment = ('%(file_path)s, %(line_no)s, '
                      '%(person)s, %(date)s, %(bug)s, %(spec)s, "%(text)s"\n')
    outputfile = open(outputname, "w")
    outputfile.write('File_Path, Line_No, Person, Date, Bug, Spec, Text\n')
    for comment in comments:
        comment['text'] = comment['text'].replace(
            '\n', ' ').replace('"', "'").strip()
        outputfile.write(report_comment % comment)
    outputfile.flush()
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
    outputname = argv[2]

    revno = get_branch_revno(root_dir)
    comments = find_comments(root_dir)
    if outputname.endswith('html'):
        create_html_report(outputname, comments, revno)
    else:
        create_csv_report(outputname, comments, revno)


if __name__ == '__main__':
    sys.exit(main())

