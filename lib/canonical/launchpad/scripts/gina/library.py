from canonical.librarian.client import FileUploadClient
import os, sha

librarian = None

def _libType(fname):
    if fname.endswith(".dsc"):
        return "text/x-debian-source-package"
    if fname.endswith(".deb"):
        return "application/x-debian-package"
    if fname.endswith(".udeb"):
        return "application/x-micro-debian-package"
    if fname.endswith(".diff.gz"):
        return "application/gzipped-patch"
    if fname.endswith(".tar.gz"):
        return "application/gzipped-tar"
    return "application/octet-stream"


def attachLibrarian(uploadhost, uploadport):
    global librarian
    librarian = FileUploadClient()
    librarian.connect(uploadhost,uploadport)

def getLibraryAlias(root, filename):
    global librarian
    if librarian is None:
        return None
    fname = "%s/%s"%(root,filename)
    fobj = open( fname, "rb" )
    size = os.stat(fname).st_size
    digest = sha.sha(open(fname,'rb').read()).hexdigest()
    id,alias = librarian.addFile(filename, size, fobj,
                                 contentType=_libType(filename),
                                 digest=digest)
    fobj.close()
    return alias

