#!/usr/bin/python2.4

# Utility functions from the dak suite
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006  James Troup <james@nocrew.org>

################################################################################

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

################################################################################

import os
import pwd
import re
import sys
import tempfile

################################################################################

re_single_line_field = re.compile(r"^(\S*)\s*:\s*(.*)")
re_multi_line_field = re.compile(r"^\s(.*)")
re_no_epoch = re.compile(r"^\d+\:")
re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

changes_parse_error_exc = "Can't parse line in .changes file"
invalid_dsc_format_exc = "Invalid .dsc file"
nk_format_exc = "Unknown Format: in .changes file";
no_files_exc = "No Files: field in .dsc or .changes file.";

################################################################################

def parse_changes(filename, signing_rules=0):
    """Parses a changes file and returns a dictionary where each field is a
key.  The mandatory first argument is the filename of the .changes
file.

signing_rules is an optional argument:

 o If signing_rules == -1, no signature is required.
 o If signing_rules == 0 (the default), a signature is required.
 o If signing_rules == 1, it turns on the same strict format checking
   as dpkg-source.

The rules for (signing_rules == 1)-mode are:

  o The PGP header consists of "-----BEGIN PGP SIGNED MESSAGE-----"
    followed by any PGP header data and must end with a blank line.

  o The data section must end with a blank line and must be followed by
    "-----BEGIN PGP SIGNATURE-----".
"""

    error = ""
    changes = {}

    changes_in = open(filename)
    lines = changes_in.readlines()

    if not lines:
	raise changes_parse_error_exc, "[Empty changes file]"

    # Reindex by line number so we can easily verify the format of
    # .dsc files...
    index = 0
    indexed_lines = {}
    for line in lines:
        index += 1
        indexed_lines[index] = line[:-1]

    inside_signature = 0

    num_of_lines = len(indexed_lines.keys())
    index = 0
    first = -1
    while index < num_of_lines:
        index += 1
        line = indexed_lines[index]
        if line == "":
            if signing_rules == 1:
                index += 1
                if index > num_of_lines:
                    raise invalid_dsc_format_exc, index
                line = indexed_lines[index]
                if not line.startswith("-----BEGIN PGP SIGNATURE"):
                    raise invalid_dsc_format_exc, index
                inside_signature = 0
                break
            else:
                continue
        if line.startswith("-----BEGIN PGP SIGNATURE"):
            break
        if line.startswith("-----BEGIN PGP SIGNED MESSAGE"):
            inside_signature = 1
            if signing_rules == 1:
                while index < num_of_lines and line != "":
                    index += 1
                    line = indexed_lines[index]
            continue
        # If we're not inside the signed data, don't process anything
        if signing_rules >= 0 and not inside_signature:
            continue
        slf = re_single_line_field.match(line)
        if slf:
            field = slf.groups()[0].lower()
            changes[field] = slf.groups()[1]
	    first = 1
            continue
        if line == " .":
            changes[field] += '\n'
            continue
        mlf = re_multi_line_field.match(line)
        if mlf:
            if first == -1:
                raise changes_parse_error_exc, "'%s'\n [Multi-line field continuing on from nothing?]" % (line)
            if first == 1 and changes[field] != "":
                changes[field] += '\n'
            first = 0
	    changes[field] += mlf.groups()[0] + '\n'
            continue
	error += line

    if signing_rules == 1 and inside_signature:
        raise invalid_dsc_format_exc, index

    changes_in.close()
    changes["filecontents"] = "".join(lines)

    if error:
	raise changes_parse_error_exc, error

    return changes

################################################################################

def build_file_list(changes, is_a_dsc=0):
    files = {};

    # Make sure we have a Files: field to parse...
    if not changes.has_key("files"):
	raise no_files_exc;

    # Make sure we recognise the format of the Files: field
    format = changes.get("format", "");
    if format != "":
	format = float(format);
    if not is_a_dsc and (format < 1.5 or format > 2.0):
	raise nk_format_exc, format;

    # Parse each entry/line:
    for i in changes["files"].split('\n'):
        if not i:
            break;
        s = i.split();
        section = priority = "";
        try:
            if is_a_dsc:
                (md5, size, name) = s;
            else:
                (md5, size, section, priority, name) = s;
        except ValueError:
            raise changes_parse_error_exc, i;

        if section == "":
            section = "-";
        if priority == "":
            priority = "-";

        (section, component) = extract_component_from_section(section);

        files[name] = Dict(md5sum=md5, size=size, section=section,
                           priority=priority, component=component);

    return files

################################################################################

def fubar(msg, exit_code=1):
    sys.stderr.write("E: %s\n" % (msg))
    sys.exit(exit_code)

def warn(msg):
    sys.stderr.write("W: %s\n" % (msg))

################################################################################

def prefix_multi_line_string(str, prefix, include_blank_lines=0):
    out = ""
    for line in str.split('\n'):
        line = line.strip()
        if line or include_blank_lines:
            out += "%s%s\n" % (prefix, line)
    # Strip trailing new line
    if out:
        out = out[:-1]
    return out

################################################################################

# Split command line arguments which can be separated by either commas
# or whitespace.  If dwim is set, it will complain about string ending
# in comma since this usually means someone did 'madison -a i386, m68k
# foo' or something and the inevitable confusion resulting from 'm68k'
# being treated as an argument is undesirable.

def split_args (s, dwim=1):
    if not s:
        return []

    if s.find(",") == -1:
        return s.split();
    else:
        if s[-1:] == "," and dwim:
            fubar("split_args: found trailing comma, spurious space maybe?");
        return s.split(",");

################################################################################

def extract_component_from_section(section):
    component = "";

    if section.find('/') != -1:
        component = section.split('/')[0];

    # XXX James Troup 2006-01-30:
    # We don't have Cnf, don't want to use DB particularly, so...
    valid_components = [ "main", "restricted", "universe", "multiverse", "contrib", "non-free" ]

    # Expand default component
    if component == "":
        if section in valid_components:
            component = section;
        else:
            component = "main";

    return (section, component);

################################################################################

def Dict(**dict): return dict

################################################################################

def our_raw_input(prompt=""):
    if prompt:
        sys.stdout.write(prompt);
    sys.stdout.flush();
    try:
        ret = raw_input();
        return ret;
    except EOFError:
        sys.stderr.write("\nUser interrupt (^D).\n");
        raise SystemExit;

################################################################################

def temp_filename(directory=None, dotprefix=None, perms=0700):
    """Return a secure and unique filename by pre-creating it.
If 'directory' is non-null, it will be the directory the file is pre-created in.
If 'dotprefix' is non-null, the filename will be prefixed with a '.'."""

    if directory:
        old_tempdir = tempfile.tempdir;
        tempfile.tempdir = directory;

    filename = tempfile.mktemp();

    if dotprefix:
        filename = "%s/.%s" % (os.path.dirname(filename), os.path.basename(filename));
    fd = os.open(filename, os.O_RDWR|os.O_CREAT|os.O_EXCL, perms);
    os.close(fd);

    if directory:
        tempfile.tempdir = old_tempdir;

    return filename;

################################################################################

def pp_deps (deps):
    pp_deps = [];
    for atom in deps:
        (pkg, version, constraint) = atom;
        if constraint:
            pp_dep = "%s (%s %s)" % (pkg, constraint, version);
        else:
            pp_dep = pkg;
        pp_deps.append(pp_dep);
    return " |".join(pp_deps);

################################################################################

# Returns the user name with a laughable attempt at rfc822 conformancy
# (read: removing stray periods).
def whoami ():
    return pwd.getpwuid(os.getuid())[4].split(',')[0].replace('.', '');

################################################################################

def join_with_commas_and(list):
	if len(list) == 0: return "nothing";
	if len(list) == 1: return list[0];
	return ", ".join(list[:-1]) + " and " + list[-1];

################################################################################

# Function for use in sorting lists of architectures.
# Sorts normally except that 'source' dominates all others.

def arch_compare_sw (a, b):
    if a == "source" and b == "source":
        return 0;
    elif a == "source":
        return -1;
    elif b == "source":
        return 1;

    return cmp (a, b);

################################################################################
