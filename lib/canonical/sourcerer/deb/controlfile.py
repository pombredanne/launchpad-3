#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 8d3c2452-09f4-4a8f-afe6-fe233bc2c006
"""Parse Debian control files.

This module contains a generic class to parse Debian control, dsc,
changes and changelog files.  It may be subclassed to provide
functionality specific to each format.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


class ControlFileError(Exception): pass
class ControlFileSyntaxError(ControlFileError): pass

class ControlFile(object):
    """Debian control file.

    This can be used directly by calling the parse() function or
    overridden to add functionality.

    Class Properties:
      FieldNames  Alternate canonical capitalisation of field names

    Properties:
      paras       List of paragraphs as dictionaries
      para        Final (or single) paragraph
      signed      True if the paragraph was PGP signed
    """

    FieldNames = []

    def __init__(self, filename=None, fileobj=None, *args, **kwds):
        self.paras = []
        self.para = None
        self.signed = False

        if fileobj is not None:
            self.parse(fileobj, *args, **kwds)
        elif filename is not None:
            self.open(filename, *args, **kwds)

    def capitaliseField(self, field):
        """Capitalise a field name correctly.

        Fields are stored in the dictionary canonically capitalised,
        words split by dashes and the first letter of each in upper
        case.

        This can be overriden by adding the canonical capitalisation
        of a field name to the FieldNames list.
        """
        for canon in self.FieldNames:
            if canon.lower() == field.lower():
                return canon

        return "-".join([ w.title() for w in field.split("-") ])

    def open(self, file, *args, **kwds):
        """Open and parse a control-file format file."""
        f = open(file)
        try:
            self.parse(f, *args, **kwds)
        finally:
            f.close()

    def parse(self, file, multi_para=False, signed=False):
        """Parse a control-file format file.

        File is any object that acts as an iterator and returns lines,
        file-like objects being most common.

        Some control files may contain multiple paragraphs separated
        by blank lines, if this is the case set multi_para to True.

        Some single-paragraph control files may be PGP signed, if this
        is the case set signed to True.  If the file was actually
        signed, the signed member of the object will be set to True.
        """
        self.para = {}
        is_signed = False
        last_field = None
        para_border = True

        for line in file:
            line = line.rstrip()
            if line.startswith("#"):
                continue

            # Multiple blank lines are permitted at paragraph borders
            if not len(line) and para_border:
                continue
            para_border = False

            if line[:1].isspace():
                if last_field is None:
                    raise ControlFileSyntaxError, \
                          "Continuation line not after field"

                self.para[last_field] += "\n" + line.lstrip()

            elif ":" in line:
                (field, value) = line.split(":", 1)
                if len(field.rstrip().split(None)) > 1:
                    raise ControlFileSyntaxError, \
                          "Key names may not contain whitespace"

                last_field = self.capitaliseField(field)
                self.para[last_field] = value.lstrip()

            elif line.startswith("-----BEGIN PGP") and signed:
                if is_signed:
                    raise ControlFileSyntaxError, \
                          "No blank line before PGP signature"
                for line in file:
                    if not len(line) or line.startswith("\n"): break
                is_signed = True

            elif not len(line):
                para_border = True
                if multi_para:
                    self.paras.append(self.para)
                    self.para = {}
                    last_field = None

                elif is_signed:
                    try:
                        pgpsig = file.next()
                        if not len(pgpsig):
                            raise ControlFileSyntaxError, \
                                  "EOF where PGP signature expected"
                    except StopIteration:
                        raise ControlFileSyntaxError, \
                              "EOF where PGP signature expected"

                    if not pgpsig.startswith("-----BEGIN PGP"):
                        raise ControlFileSyntaxError, \
                              "Unexpected data where PGP signature expected"

                    self.signed = True
                    break

                else:
                    raise ControlFileSyntaxError, \
                          "Paragraph break when only one paragraph permitted"

            else:
                raise ControlFileSyntaxError, "Unknown line format"

        if is_signed and not self.signed:
            raise ControlFileSyntaxError, "PGP body without PGP signature"

        if last_field:
            self.paras.append(self.para)
        elif not len(self.paras):
            raise ControlFileSyntaxError, "Empty file"
        else:
            self.para = self.paras[-1]
