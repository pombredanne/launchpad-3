#!/usr/bin/env python

# Copyright (C) 2005 Aaron Bentley
# <aaron.bentley@utoronto.ca>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import itertools
import os
import tempfile
import doctest
import shutil
import md5
import stat
import sys
try:
    import psyco
    psyco.full()
except:
    pass

def make_work_dir():
    work_dir = {"root": tempfile.mkdtemp()}
    for filename in ("texta", "texta_copy", "texta_perms", "texta_symlink",
        "texta_symlink2", "textb", "textb_link", "textc"):
        work_dir[filename] = os.path.join(work_dir["root"], filename)
    file(work_dir["texta"], "wb").write("texta")
    file(work_dir["texta_copy"], "wb").write("texta")
    file(work_dir["texta_perms"], "wb").write("texta")
    os.symlink(work_dir["texta"], work_dir["texta_symlink"])
    os.chmod(work_dir["texta_perms"], 0666)
    file(work_dir["textb"], "wb").write("textb")
    os.link(work_dir["textb"], work_dir["textb_link"])
    file(work_dir["textc"], "wb").write("tc")
    return work_dir
    
        
def file_same_w(perm_file, relinkable_file):
    return file_same((perm_file, os.lstat(perm_file)), 
                     (relinkable_file, os.lstat(relinkable_file)))

def file_same(perm_file, relinkable_file):
    """
    >>> work_dir = make_work_dir()
    >>> file_same_w (work_dir["texta"], work_dir["texta"])
    True
    >>> file_same_w (work_dir["texta"], work_dir["texta_copy"])
    True
    >>> file_same_w (work_dir["texta"], work_dir["texta_perms"])
    False
    >>> file_same_w (work_dir["texta"], work_dir["texta_symlink"])
    Traceback (most recent call last):
    AssertionError
    >>> file_same_w (work_dir["texta"], work_dir["textb"])
    False
    >>> file_same_w (work_dir["texta"], work_dir["textc"])
    False
    >>> shutil.rmtree(work_dir["root"])
    """
    assert (stat.S_ISREG(perm_file[1].st_mode))
    assert (stat.S_ISREG(relinkable_file[1].st_mode))
    if not same_lstat(perm_file[1], relinkable_file[1]):
        return False
    else:
        return file_same_contents(perm_file[0], relinkable_file[0])

def file_same_lstat(perm_file, relinkable_file):
    """
    >>> work_dir = make_work_dir()
    >>> file_same_lstat (work_dir["texta"], work_dir["texta"])
    True
    >>> file_same_lstat (work_dir["texta"], work_dir["texta_copy"])
    True
    >>> file_same_lstat (work_dir["texta"], work_dir["texta_perms"])
    False
    >>> file_same_lstat (work_dir["texta"], work_dir["textb"])
    True
    >>> file_same_lstat (work_dir["texta"], work_dir["textc"])
    False
    >>> shutil.rmtree(work_dir["root"])
    """
    stat_p = os.lstat(perm_file)
    stat_r = os.lstat(relinkable_file)
    return same_lstat(stat_p, stat_r)

def same_lstat(stat_p, stat_r):
    if stat_p.st_size != stat_r.st_size:
        return False
    elif stat_p.st_mode & 0777 != stat_r.st_mode & 0777:
        return False
    else:
        return True

def file_same_contents(filename_a, filename_b):
    """
    >>> work_dir = make_work_dir()
    >>> file_same_contents (work_dir["texta"], work_dir["texta"])
    True
    >>> file_same_contents (work_dir["texta"], work_dir["texta_copy"])
    True
    >>> file_same_contents (work_dir["texta"], work_dir["texta_perms"])
    True
    >>> file_same_contents (work_dir["texta"], work_dir["textb"])
    False
    >>> file_same_contents (work_dir["texta"], work_dir["textc"])
    False
    >>> shutil.rmtree(work_dir["root"])
    """
    a = open(filename_a)
    b = open(filename_b)
    for (a_line, b_line) in itertools.izip(a, b):
        if a_line != b_line:
            return False
    return True


def get_id(new_stat):
    """Determines an ID for a file's contents that uses stat info, but will not
    be affected by hard-linking"""
    return (new_stat.st_dev, new_stat.st_ino, new_stat.st_mode, 
            new_stat.st_mtime, new_stat.st_size)


class FileSet(object):
    """
    >>> fs = FileSet()
    >>> work_dir = make_work_dir()
    >>> fs.find_same(work_dir["texta"]) is None
    True
    >>> fs.find_same(work_dir["texta"]) is None
    True
    >>> fs.find_same(work_dir["texta_symlink"]) is None
    True
    >>> fs.find_same(work_dir["texta_copy"]) == work_dir["texta"]
    True
    >>> fs.find_same(work_dir["texta_perms"]) is None
    True
    >>> fs.find_same(work_dir["textb"]) is None
    True
    >>> fs.find_same(work_dir["textb_link"]) is None
    True
    >>> fs.find_same(work_dir["textc"]) is None
    True
    >>> shutil.rmtree(work_dir["root"])
    """
    def __init__(self):
        object.__init__(self)
        self.known_files = {}
        self.known_ids = {}
        self.prev_results = {}
        self.prev_result_hits = 0
        self.space_savings = 0
        self.new_result_hits = 0
        self.size_scanned = 0

    def statistics(self):
        print "%i relink candidates in total" % (self.new_result_hits + self.prev_result_hits)
        print "%i were not hard links of other candidates" % self.new_result_hits
        print "%i were hard links of other candidates" % self.prev_result_hits
        print "%s total space savings possible " % \
            size_string(self.space_savings) 
        print "%i ids known" % len(self.known_ids.keys())
        print "%i md5sums known" % len(self.known_files.keys())
        print "%s scanned" % size_string(self.size_scanned)


    def recognize(self, filename, stat, md5):
        if not self.known_files.has_key(md5):
            self.known_files[md5] = []
        self.known_files[md5].append((filename, stat))
        self.known_ids[get_id(stat)] = filename
        

    def find_same(self, new_file, new_stat = None):
        """Find first known file with same contents and mode as the new file.
        Files which are not the same as any known file are added to the list
        of known files.

        If the file or a hardlink of it is already in the list of known files,
        None will be returned.

        Note that we do not assume that two files with the same md5sum are the
        same, so it is safe to use md5 here.
        :param new_file: The file to check and possibly add
        """
        if new_stat is None:
            new_stat = os.lstat(new_file)
        if not stat.S_ISREG(new_stat.st_mode):
            return None
        id = get_id(new_stat)
        if self.known_ids.has_key(id):
            return None
        prev_result = self.prev_results.get(id)
        if prev_result is not None:
            self.prev_result_hits += 1
            return prev_result

        md5 = md5_read(file(new_file, "rb"))
        self.size_scanned += new_stat.st_size
        if not self.known_files.has_key(md5):
            self.recognize(new_file, new_stat, md5)
            return None
        for listing in self.known_files[md5]:
            if file_same(listing, (new_file, new_stat)):
                self.new_result_hits += 1
                self.prev_results[id] = listing[0]
                self.space_savings += new_stat.st_size
                return self.prev_results[id] 
        self.recognize(new_file, new_stat, md5)
        return None

    def walk_candidates(self, tree):
        for filepath in tree.walk():
            known = self.find_same(filepath, tree.get_stat(filepath))
            if known is not None:
                yield (filepath, known)

def md5comp(file_a, file_b):
    return md5_read(file(file_a, "rb")) ==  md5_read(file(file_b, "rb"))


def size_string(bytes):
    """
    >>> size_string(-1)
    Traceback (most recent call last):
    AssertionError
    >>> size_string(0)
    '0 B'
    >>> size_string(1)
    '1 B'
    >>> size_string(1023)
    '1023 B'
    >>> size_string(1024)
    '1.0 KiB'
    >>> size_string(1024*1024)
    '1.0 MiB'
    >>> size_string(1024*1024*1024)
    '1.0 GiB'
    >>> size_string(1024*1024*1024*1024)
    '1024.0 GiB'
    """
    assert(bytes >= 0)
    format = "%d B"
    size = float(bytes)
    if size >= 1024:
        size /= 1024
        format = "%0.1f KiB"
    if size >= 1024:
        size /= 1024
        format = "%0.1f MiB"
    if size >= 1024:
        size /= 1024
        format = "%0.1f GiB"
    return format % size


def md5_read(iterable):
    """Read all the items in an iterable and compute the md5 checksum.

    :param iterable: The iterable to get strings from
    :return: the hex md5sum

    >>> work_dir = make_work_dir()
    >>> md5comp(work_dir["texta"], work_dir["texta"])
    True
    >>> md5comp(work_dir["texta"], work_dir["texta_copy"])
    True
    >>> md5comp(work_dir["texta"], work_dir["texta_perms"])
    True
    >>> md5comp(work_dir["texta"], work_dir["textb"])
    False
    >>> md5comp(work_dir["texta"], work_dir["textc"])
    False
    >>> shutil.rmtree(work_dir["root"])
    """
    m = md5.new()
    for line in iterable:
        m.update(line)
    return m.hexdigest()

def walk_file_paths(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            yield filepath


def print_candidates(directory, fs):
    for filepath in walk_file_paths(directory):
        known = fs.find_same(filepath)
        if known is not None and False:
            print "%s => %s" % (filepath, known)

class ValidationFailure(Exception):
    def __init__(self, file, revision):
        self.file = file
        self.revision = revision
        message = "Library validation failure\nFile: %s\nRevision %s" %\
            (file, revision)
        Exception.__init__(self, message)


class LibTree(object):
    def __init__(self, archive, revision, path):
        object.__init__(self)
        self.archive = archive
        self.revision = revision
        self.path = path
        self.alpha_filenames = []
        self.file_id = {}
        self._cached_stats = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.dev_in_old_sig = False
        self._init_filedata()
        self.validate_sigs()

    def _init_filedata(self):
        for filename, id in self.iter_filepair():
            self.alpha_filenames.append(filename)
            self.file_id[filename] = id

    def _full_name(self):
        return "%s/%s" % (self.archive, self.revision)

    def statistics(self):
        print "%i cache hits" % self.cache_hits
        print "%i cache misses" % self.cache_misses

    full_revision = property(_full_name)
    """The fully-qualified revision name"""

    def iter_filepair(self):
        """Generate an iterator of all filename,id pairs for this tree
        """
        path = os.path.join(self.path, ",,index-by-name")
        for line in file(path, "rb"):
            filename, id =  line.rstrip('\n').split('\t')
            id = id.replace('\\"', '"')
            yield filename, id

    def full_path(self, filename):
        """Return the full path of a filename"""
        return os.path.join(self.path, filename)

    def walk(self):
        """Generate an iterator of all source file paths
        """
        for filename in self.alpha_filenames:
            yield self.full_path(filename)

    def sig_path(self):
        """Return the file path of the inode sig file"""
        return os.path.join(self.path, "{arch}", ",,inode-sigs",
                            "%s%%%s" % (self.archive, self.revision))

    def re_signable(self):
        """Determine whether a tree can be re-signed"""
        return os.access(os.path.dirname(self.sig_path()), os.W_OK)

    def iter_sigs(self):
        """Generate an iterator of id, sig line pairs for this tree"""
        for line in file(self.sig_path(), "rb"):
            yield (line.split('\t')[0], line)

    def validate_sigs(self):
        """Determine whether the current sig file matches the stat results
        """
        sig_map = {}
        for id, sig in self.iter_sigs():
            sig_map[id] = sig
        for filename in self.alpha_filenames:
            self.validate_file_sig(filename, sig_map)
        assert(self.new_inode_sig(use_dev=self.dev_in_old_sig) == 
               file(self.sig_path(), "rb").read())

    def get_stat(self, full_path):
        """Return lstat data for the given full path"""
        new_stat = self._cached_stats.get(full_path)
        if new_stat is None:
            self.cache_misses+=1
            new_stat = os.lstat(full_path)
            self._cached_stats[full_path] = new_stat
        else:
            self.cache_hits+=1
        return new_stat

    def relink(self, existing, relinkable):
        del self._cached_stats[relinkable]
        (dirname, filename) = os.path.split(relinkable)
        tmp_name= os.path.join(dirname, ",,relink-"+filename)
        os.link(existing, tmp_name)
        os.rename(tmp_name, relinkable)

    def new_file_sig(self, id, new_stat, use_dev=False):
        """Return a new signature line for a given id and stat data"""
        if use_dev:
            return "%s\tdev=%d:ino=%d:mtime=%d:size=%d\n" % (id,
                                                             new_stat.st_dev,
                                                             new_stat.st_ino,
                                                             new_stat.st_mtime, 
                                                             new_stat.st_size)

        return "%s\tino=%d:mtime=%d:size=%d\n" % (id, new_stat.st_ino,
                                                new_stat.st_mtime, 
                                                new_stat.st_size)

    def validate_file_sig(self, file, sig_map):
        """Compare a sig line to the line that would be generated from the
        current stat data"""
        try:
            new_stat = self.get_stat(self.full_path(file))
            file_id = self.file_id[file]
            if not stat.S_ISREG(new_stat.st_mode):
                assert(not sig_map.has_key(file_id))
                return
            cur_sig = sig_map[file_id]
            new_sig = self.new_file_sig(file_id, new_stat)
            if new_sig != cur_sig:
                new_sig = self.new_file_sig(file_id, new_stat, use_dev=True)
                assert(new_sig == cur_sig)
                self.dev_in_old_sig=True

        except AssertionError:
            raise ValidationFailure(file, self.full_revision)
        except OSError:
            raise ValidationFailure(file, self.full_revision)

    def new_inode_sig(self, use_dev=False):
        sigs = []
        for filename, file_id in self.file_id.iteritems():
            new_stat = self.get_stat(self.full_path(filename))
            if not stat.S_ISREG(new_stat.st_mode):
                continue
            sigs.append(self.new_file_sig(file_id, new_stat, use_dev=use_dev))
        sigs.sort()
        return "".join(sigs)

    def write_inode_sigs(self):
        os.unlink(self.sig_path())
        file(self.sig_path(), "wb").write(self.new_inode_sig())
        os.chmod(self.sig_path(), 0666)


def library_revisions(revlib_root):
    for archive in os.listdir(revlib_root):
        archive_dir = os.path.join(revlib_root, archive)
        if ignorable(archive, archive_dir):
            continue
        for category in os.listdir(archive_dir):
            category_dir = os.path.join(archive_dir, category)
            if ignorable(category, category_dir):
                continue
            for package in os.listdir(category_dir):
                package_dir = os.path.join(category_dir, package)
                if ignorable(package, package_dir):
                    continue
                for version in os.listdir(package_dir):
                    version_dir = os.path.join(package_dir, version)
                    if ignorable(version, version_dir):
                        continue
                    for revision in os.listdir(version_dir):
                        revision_dir = os.path.join(version_dir, revision)
                        if ignorable(revision, revision_dir):
                            continue
                        try:
                            yield LibTree(archive, revision, revision_dir)
                        except ValidationFailure, e:
                            print "Skipping %s because %s didn't validate" %\
                                (e.revision, e.file)
                            


def ignorable(filename, file_path):
    return ignored_file(filename) or not os.path.isdir(file_path)

def ignored_file(filename):
    return filename.startswith(',') or filename.startswith('+')

def gen_stats(directory):
    fs = FileSet()
    num_revisions = 0
    print "Re-linking revisions:"
    try:
        for tree in library_revisions(directory):
            print tree.full_revision
            if not tree.re_signable():
                print "Cannot be re-signed.  Skipping."
                continue
            changed = False
            try:
                for relinkable, existing in fs.walk_candidates(tree):
                    try:
                        changed = True
                        tree.relink(existing, relinkable)
                    except OSError:
                        pass
            finally:
                if changed:
                    tree.write_inode_sigs()
            num_revisions += 1
    finally:
        print 
        print "FINAL RESULTS"
        print "Scanned %i complete revisions" % num_revisions
        fs.statistics()

if len(sys.argv) == 2:
    try:
        gen_stats(sys.argv[1])
    except KeyboardInterrupt:
        pass
    
else:
    doctest.testmod()
