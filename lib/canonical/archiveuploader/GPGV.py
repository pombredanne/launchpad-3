# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: f230218f-d4b6-42f6-ac6a-0f15373476da

import re, os, select

from canonical.archiveuploader.utils import prefix_multi_line_string

re_taint_free = re.compile(r"^[-+~\.\w]+$");

# Our very own version of commands.getouputstatus(), hacked to support
# gathering gpgv's output from its status fd.
def gpgv_get_status_output(cmd, status_read, status_write):
    cmd = ['/bin/sh', '-c', cmd]
    # Parent-to-child pipe
    p2cread, p2cwrite = os.pipe()
    # Child-to-parent pipe
    c2pread, c2pwrite = os.pipe()
    # Stderr pipe
    errout, errin = os.pipe()
    pid = os.fork()
    if pid == 0:
        # Child
        os.close(0)
        os.close(1)
        os.dup(p2cread)
        os.dup(c2pwrite)
        os.close(2)
        os.dup(errin)
        for i in range(3, 256):
            if i != status_write:
                try:
                    os.close(i)
                except:
                    pass
        try:
            os.execvp(cmd[0], cmd)
        finally:
            os._exit(1)

    # Parent
    os.close(p2cread)
    os.close(c2pwrite)
    os.close(errin)

    output = status = ""
    while 1:
        i, o, e = select.select([c2pread, errout, status_read], [], [])
        more_data = []
        for fd in i:
            r = os.read(fd, 8196)
            if len(r) > 0:
                more_data.append(fd)
                if fd == c2pread or fd == errout:
                    output += r
                elif fd == status_read:
                    status += r
                else:
                    raise GPGInternalError("Unexpected file descriptor [%s] returned from select\n" % (fd))
        if not more_data:
            pid, exit_status = os.waitpid(pid, 0)
            try:
                os.close(status_write)
                os.close(status_read)
                os.close(c2pread)
                os.close(c2pwrite)
                os.close(p2cwrite)
                os.close(errin)
                os.close(errout)
            except:
                pass

            break

    return output, status, exit_status

# List the keywords we'll accept in GPGV output
known_keywords = {
    "VALIDSIG": "",
    "SIG_ID": "",
    "GOODSIG": "",
    "BADSIG": "",
    "ERRSIG": "",
    "SIGEXPIRED": "",
    "KEYREVOKED": "",
    "NO_PUBKEY": "",
    "BADARMOR": "",
    "NODATA": ""
    }

class VerificationError(Exception):
    """This indicates an issue with the signed file"""
    pass

class TaintedFileNameError(VerificationError):
    """This indicates the input filename(s) were tainted"""
    pass

class SignatureExpiredError(VerificationError):
    """This indicates that the signature expired"""
    pass

class KeyRevokedError(VerificationError):
    """This indicates the signature is from a revoked key"""
    pass

class BadSignatureError(VerificationError):
    """This indicates the signature was bad"""
    pass

class SignatureCheckError(VerificationError):
    """There was a failure while checking the signature"""
    pass

class NoPublicKeyError(VerificationError):
    """The public key referred to was not found"""
    def __init__(self, msg, key):
        VerificationError.__init__(self,msg)
        self.key = key

class BadArmorError(VerificationError):
    """The ascii armoring was damaged"""
    pass

class NoSignatureFoundError(VerificationError):
    """No signature was found"""
    pass

class NoGoodSignatureError(VerificationError):
    """No good signature result was returned"""
    pass

class NoSignatureIDError(VerificationError):
    """No signature ID was returned"""
    pass

class NoValidSignatureError(VerificationError):
    """No valid signature token was returned"""
    pass

class UnknownTokenError(VerificationError):
    """An unknown token was returned from GPGV"""
    pass

class GPGInternalError(Exception):
    """This indicates an issue with the installation"""
    pass

def verify_signed_file(filename, keyrings, detached_sigfile = None):
    """Verify that the signature on the file in 'filename' is valid.
    Return the fingerprint of the key if it succeeds or raise an exception
    if it fails. Two kinds of exception come out of here, GPGInternalError
    or VerificationError. The first indicates a problem with the installation;
    the second a problem with the signed file."""

    rejr = []
    def reject(m):
        """Quick and dirty function to append 'reject' messages to a queue.
        Allows us to collect up the rejection message neatly"""
        rejr.append(m)

    # Ensure the filename contains no shell meta-characters or other badness
    if not re_taint_free.match(os.path.basename(filename)):
        raise TaintedFileNameError("%s: potentially dangerous metacharacters in filename" % (filename))

    if detached_sigfile is not None and \
           not re_taint_free.match(os.path.basename(detached_sigfile)):
        raise TaintedFileNameError("%s: potentially dangerous metacharacters in filename" % (detached_sigfile))

    if type(keyrings) != list:
        raise GPGInternalError("<keyrings>: list expected, got %s", type(keyrings))


    keyrings = [ "'" + k + "'" for k in keyrings ]
    keyrings.insert(0, "")

    # Invoke gpgv on the file
    status_read, status_write = os.pipe()
    if detached_sigfile is None:
        cmd = "gpgv --status-fd %s %s '%s'" \
              % (status_write, " --keyring ".join(keyrings), filename)
    else:
        cmd = "gpgv --status-fd %s %s %s '%s'" \
              % (status_write, " --keyring ".join(keyrings), \
                 filename, detached_sigfile)

    (output, status, exit_status) = \
             gpgv_get_status_output(cmd, status_read, status_write)

    # Process the status-fd output
    keywords = {}
    bad = internal_error = ""
    for line in status.split('\n'):
        line = line.strip()
        if line == "":
            continue
        split = line.split()
        if len(split) < 2:
            internal_error += "gpgv status line is malformed (< 2 atoms) ['%s'].\n" % (line)
            continue
        (gnupg, keyword) = split[:2]
        if gnupg != "[GNUPG:]":
            internal_error += "gpgv status line is malformed (incorrect prefix '%s').\n" % (gnupg)
            continue
        args = split[2:]
        if keywords.has_key(keyword) and (keyword != "NODATA" and keyword != "SIGEXPIRED"):
            internal_error += "found duplicate status token ('%s').\n" % (keyword)
            continue
        else:
            keywords[keyword] = args

    # If we failed to parse the status-fd output, let's just whine and bail now
    if internal_error:
        raise GPGInternalError(internal_error)

    # Now check for obviously bad things in the processed output
    if keywords.has_key("SIGEXPIRED"):
        raise SignatureExpiredError("%s: signature has expired." % (filename))
    if keywords.has_key("KEYREVOKED") or keywords.has_key("REVKEYSIG"):
        raise KeyRevokedError("%s: key has been revoked." % (filename))
    if keywords.has_key("BADSIG"):
        raise BadSignatureError("%s: bad signature" % (filename))
    if keywords.has_key("NO_PUBKEY"):
        args = keywords["NO_PUBKEY"]
        key = "UNKNOWN"
        if len(args) >= 1:
            key = args[0]
        raise NoPublicKeyError("%s: key (0x%s) wasn't found in the keyring(s)" % (filename, key), key)
    if keywords.has_key("ERRSIG") and not keywords.has_key("NO_PUBKEY"):
        raise SignatureCheckError("%s: failed to check signature" % (filename))
    if keywords.has_key("BADARMOR"):
        raise BadArmorError("%s: ASCII armour of signature was corrupt" % (filename))
    if keywords.has_key("NODATA"):
        raise NoSignatureFoundError("%s: no signature found" % (filename))

    if bad:
        raise VerificationError( "\n".join(rejr) )

    # Next check gpgv exited with a zero return code
    if exit_status:
        reject("gpgv failed while checking %s." % (filename));
        if status.strip():
            reject(prefix_multi_line_string(status, " [GPG status-fd output:] "));
        else:
            reject(prefix_multi_line_string(output, " [GPG output:] "));

        raise VerificationError( "\n".join(rejr) )

    # Sanity check the good stuff we expect
    if not keywords.has_key("VALIDSIG"):
        raise NoValidSignatureError("%s signature does not appear to be valid [No VALIDSIG]" % (filename))
    else:
        args = keywords["VALIDSIG"]
        if len(args) < 1:
            raise VerificationError("%s: internal error while checking signature" % (filename))
        else:
            fingerprint = args[0]

    if not keywords.has_key("GOODSIG"):
        raise NoGoodSignatureError("%s: signature does not appear to be valid [No GOODSIG]" % (filename))
    if not keywords.has_key("SIG_ID"):
        raise NoSignatureIDError("%s: signature does not appear to be valid [No SIG_ID]" % (filename))

    for keyword in keywords.keys():
        if not known_keywords.has_key(keyword):
            raise UnknownTokenError("%s: found unknown status token '%s' from gpgv with args '%r'" % (filename, keyword, keywords[keyword]))

    if bad:
        raise VerificationError( "\n".join(rejr) )

    return fingerprint
