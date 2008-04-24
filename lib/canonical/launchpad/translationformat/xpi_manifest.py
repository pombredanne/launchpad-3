# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['XpiManifest']


import logging
import re


def normalize_path(path):
    """Normalize filesystem path within XPI file."""
    # Normalize "jar:" prefix.  Make sure it's there when needed, not there
    # when not needed.
    if path.startswith('jar:'):
        # No leading slashes please.
        path = re.sub('^jar:/+', 'jar:', path)

        if '.jar!' not in path:
            logging.debug("Removing 'jar:' from manifest path: '%s'" % path)
            path = path[4:]
    else:
        # No leading slashes please.
        path = re.sub('^/+', '', path)

        if '.jar!' in path:
            # Path delves into a jar file, but lacks "jar:" prefix.  This is
            # really a malformed path.
            logging.info("Adding 'jar:' to manifest path: '%s'" % path)
            path = 'jar:' + path

    # A path inside a jar file must begin with a slash.
    path.replace('.jar!', '.jar!/')

    # Finally, eliminate redundant slashes.  The previous steps may have
    # introduced some.
    return re.sub('/+', '/', path)


def is_valid_path(path):
    """Check that path is a valid, normalized path inside an XPI file."""
    if '//' in path:
        return False
    if re.search('\\.jar![^/]', path):
        return False
    if path.startswith('jar:'):
        if path.startswith('jar:jar:'):
            return False
        if '.jar!' not in path:
            return False
    else:
        if '.jar!' in path:
            return False
    return True


def is_valid_dir_path(path):
    """Check that path is a normalized directory path in an XPI file."""
    if not is_valid_path(path):
        return False
    if not path.endswith('/'):
        return False
    return True


class ManifestEntry:
    """A "locale" line in a manifest file."""

    chrome = None
    locale = None
    path = None

    def __init__(self, chrome, locale, path):
        self.chrome = chrome
        self.locale = locale

        # Normalize path so we can do simple, reliable text matching on it.
        # The directory paths in an XPI file should end in a single slash.
        # Append the slash here; the normalization will take care of redundant
        # slashes.
        self.path = normalize_path(path + "/")

        assert is_valid_dir_path(self.path), (
            "Normalized path not valid: '%s' -> '%s'" % (path, self.path))


def manifest_entry_sort_key(entry):
    """We keep manifest entries sorted by path length."""
    return len(entry.path)


class XpiManifest:
    """Representation of an XPI manifest file.

    Does two things: parsers an XPI file; and looks up chrome paths and
    locales for given filesystem paths inside the XPI file.
    """

    # List of locale entries, sorted by increasing path length.  The sort
    # order matters for lookup.
    _locales = None

    def __init__(self, content):
        """Initialize: parse `content` as a manifest file."""
        locales = []
        for line in content.splitlines():
            words = line.split()
            num_words = len(words)
            if num_words == 0 or words[0] != 'locale':
                pass
            if num_words < 4:
                logging.info("Ignoring short manifest line: '%s'" % line)
            elif num_words > 4:
                logging.info("Ignoring long manifest line: '%s'" % line)
            else:
                locales.append(ManifestEntry(words[1], words[2], words[3]))

        self._locales = sorted(locales, key=manifest_entry_sort_key)

        if not locales:
            return

        # Verify manifest.
        paths = set()
        last_entry = None
        for entry in self._locales:
            assert entry.path.endswith('/'), "Manifest path lost its slash"

            if last_entry is not None:
                assert len(entry.path) >= len(last_entry.path), (
                    "Manifest entries not sorted by path length")

            if entry in paths:
                logging.info("Duplicate paths in manifest: '%s'" % entry.path)

            paths.add(entry.path)

            last_entry = entry

    def _get_matching_entry(self, file_path):
        """Return longest matching entry matching file_path."""
        assert is_valid_path(file_path), (
            "Generated path not valid: %s" % file_path)

        # Locale entries are sorted by path length.  If we scan backwards, the
        # first entry whose path is a prefix of file_path is the longest
        # match.  The fact that the entries' paths have trailing slashes
        # guarantees that we won't match in the middle of a file or directory
        # name.
        for entry in reversed(self._locales):
            if file_path.startswith(entry.path):
                return entry

        # No match found.
        return None

    def get_chrome_path_and_locale(self, file_path):
        """Return chrome path and locale applying to a filesystem path.
        """
        assert file_path is not None, "Looking up chrome path for None"
        file_path = normalize_path(file_path)
        entry = self._get_matching_entry(file_path)

        if entry is None:
            return None, None

        assert file_path.startswith(entry.path), "Found non-matching entry"
        replace = len(entry.path)
        chrome_path = "%s/%s" % (entry.chrome, file_path[replace:])
        return chrome_path, entry.locale

    @classmethod
    def make_jarpath(cls, path, jarname):
        """Construct base path for files inside a jar file.

        To name some translation file that's inside a jar file inside an XPI
        file, concatenate the result of this method (for the jar file) and the
        translation file's path within the jar file.

        For example, let's say the XPI file contains foo/bar.jar.  Inside
        foo/bar.jar is a translation file locale/gui.dtd.  Then
        make_jarfile('foo', 'bar.jar') will return "jar:foo/bar.jar!/", to
        which you can append "locale/gui.dtd" to get the full path
        "jar:foo/bar.jar!/locale/gui.dtd" which identifies the translation
        file within the XPI file.
        """
        # This method is where we drill down into a jar file, so prefix with
        # "jar:" (unless it's already there).  We carry the "jar:" prefix only
        # for paths that drill into jar files.
        if not path.startswith('jar:'):
            path = 'jar:' + path

        return normalize_path("%s/%s!" % (path, jarname))

