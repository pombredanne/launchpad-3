#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.
#

# XXX: Carlos Perello Marin 22/12/2004 This script sucks too much. It's an
# ugly hack to get imported faster some products into Rosetta and it should
# not used as a code example of anything. Please DON'T reuse it without fixing
# lots of things. After the initial import of many products into Rosetta I
# will 'Fix' this script so it lets us to import a whole Hoary with error
# handling and quality code.

import os, popen2
import apt_pkg
import bz2
from tempfile import TemporaryFile
from canonical.launchpad.scripts.nicole import sourceforge


downloadDir = '/tmp/rosetta/'
launchpadURL = 'http://localhost:8085'

errorMessage= '''<!-- macro commented out for now, until we get our own skin and macros
     declarations in place -->
<html xmetal:use-macro="context/@@standard_macros/dialog">
<body>

<div xmetal:fill-slot="body">

<h3>
  The page that you are trying to access is not available
</h3>
<br /> 
<b>Please note the following:</b>
<br />
<ol>
   <li> You might have miss-spelled the url </li>
   <li>
     You might be trying to access a non-existing page
   </li>
</ol>
</div>
</body>
</html>
'''

mapping = {
    'atk1.0' : 'atk',
    'doc++' : 'docpp',
    'epiphany-extensions': 'ephy-extensions',
    'gstreamer0.8': 'gstreamer',
    'gst-plugins0.8': 'gstreamer',
    'lvm2': 'logicalvolumemanager',
}

def download(local, uri, resume, md5sum=None):
    if resume:
        res = '-C -'
    else:
        res = ''
    curl = popen2.Popen3('/usr/bin/curl %s --create-dirs -o %s -s %s' %
            (uri, local, res), True)

    # Now we wait until the command ends
    status = curl.wait()

    if os.WIFEXITED(status):
        # XXX: Seems like with really small files curl fails, thus, we
        # ignore this error, it's safe to ignore it because we are checking
        # the md5 later so if there was a real problem, we will catch it
        # there.
        if os.WEXITSTATUS(status) != 0 and os.WEXITSTATUS(status) != 33:
            # The command failed.
            raise RuntimeError("Curl failed with %d code downloading %s" %
                (os.WEXITSTATUS(status), uri))
        elif md5sum is not None:
            # We verify the download
            import md5

            m = md5.new()
            m.update(open(local).read())
            if md5sum != m.hexdigest():
                RuntimeError("The md5sum is not valid for %s" % local)
    else:
        raise RuntimeError("There was an unknown error executing curl.")

def extractDeb(filename):
    dpkg = popen2.Popen3('/usr/bin/dpkg-source -x %s' % filename, True)

    # Now we wait until the command ends
    status = dpkg.wait()

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) != 0:
            # The command failed.
            raise RuntimeError("dpkg-source failed with %d code processing %s" %
                (os.WEXITSTATUS(status), filename))
    else:
        raise RuntimeError("There was an unknown error executing dpkg-source.")

def updateCDBS(path):
    oldPath = os.getcwd()
    os.chdir(path)

    rules = popen2.Popen3('./debian/rules apply-patches > /dev/null', True)

    # Now we wait until the command ends
    status = rules.wait()

    # Restore old path
    os.chdir(oldPath)

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) != 0:
            # The command failed.
            raise RuntimeError("debian/rules failed with %d code" %
                os.WEXITSTATUS(status))
    else:
        raise RuntimeError("There was an unknown error executing debian/rules.")

def getPODirs(path):
    poDirs = []
    for root, dirs, files in os.walk(path, topdown=True):
        for file in files:
            if file == 'POTFILES.in':
                poDirs.append(root)
    return poDirs

def checkURL(url):
    curl = popen2.Popen3('curl -k %s' % url, True)

    output = curl.fromchild.read()

    status = curl.wait()

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) == 0:
            # The command finished correctly
            if output == errorMessage:
                # The URL is wrong
                return False
            else:
                return True
        else:
            raise RuntimeError('We had an unknown error with curl.')
    else:
        raise RuntimeError('We had an unknown error with curl.')

def uploadPOT(product, template, podir, potfile):
    url = '%s/rosetta/products/%s/%s' % (launchpadURL, product, template)
    if checkURL(url):
        upload_url = '%s/+edit' % url
        submit = 'Update=Update POTemplate'
    else:
        upload_url = '%s/rosetta/products/%s/+newpotemplate' % (
            launchpadURL, product)
        submit = 'Register=Register POTemplate'

    upload_command = 'curl --user %s:%s -F "name=%s" -F "title=%s" -F "file=@%s" -F "%s" %s' % (
        'carlos@canonical.com',
        'test',
        template,
        '%s from Hoary' % template,
        podir + '/' + potfile,
        submit,
        upload_url)

    curl = popen2.Popen3(upload_command, True)

    curl.fromchild.read()

    status = curl.wait()

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) == 0:
            # The command finished correctly
                return True
        else:
            raise RuntimeError('We had an unknown error with curl.')
    else:
        raise RuntimeError('We had an unknown error with curl.')

def uploadPO(product, template, lang, podir, pofile):
    upload_command = 'curl --user %s:%s -F "file=@%s" -F "UPLOAD=Upload" %s/rosetta/products/%s/%s/%s/+edit' % (
        'carlos@canonical.com',
        'test',
        podir + '/' + pofile,
        launchpadURL,
        product,
        template,
        lang)

    curl = popen2.Popen3(upload_command, True)

    curl.fromchild.read()

    status = curl.wait()

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) == 0:
            # The command finished correctly
                return True
        else:
            raise RuntimeError('We had an unknown error with curl.')
    else:
        raise RuntimeError('We had an unknown error with curl.')

def data_sanitizer(data):
    if not data:
        return data
    try:
        # check that this is unicode data
        data.decode("utf-8").encode("utf-8")
        return data
    except UnicodeError:
        # check that this is latin-1 data
        s = data.decode("latin-1").encode("utf-8")
        s.decode("utf-8")
        return s


def createProduct(product):
    try:
        product_info = sourceforge.getProductSpec(product, 'fm')
    except sourceforge.Error:
        try:
            product_info = sourceforge.getProductSpec(product, 'sv')
        except sourceforge.Error:
            try:
                product_info = sourceforge.getProductSpec(product, 'sf')
            except sourceforge.Error:
                # We didn't got the product in any of the repositories we
                # know, we cannot create it.
                return False

    if 'shortdesc' in product_info.keys():
        shortdesc = data_sanitizer(product_info['shortdesc'])
    else:
        shortdesc = data_sanitizer(product_info['description']).split(".")[0]
    if 'productname' in product_info.keys():
        displayname = data_sanitizer(product_info['productname'])
    else:
        displayname = product

    create_command = '''curl --user %s:%s -F 'field.name=%s' -F 'field.displayname=%s' -F 'field.title=%s' -F 'field.shortdesc=%s' -F 'field.description=%s' -F 'UPDATE_SUBMIT=Add' %s/doap/products/+new''' % (
        'carlos@canonical.com',
        'test',
        product, displayname.replace("'", "'\"'\"'"),
        product.replace("'", "'\"'\"'"), shortdesc.replace("'", "'\"'\"'"),
        data_sanitizer(product_info['description']).replace("'", "'\"'\"'"),
        launchpadURL)
    print create_command

    curl = popen2.Popen3(create_command, True)

    curl.fromchild.read()

    status = curl.wait()

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) == 0:
            # The command finished correctly
                return True
        else:
            raise RuntimeError('We had an unknown error with curl.')
    else:
        raise RuntimeError('We had an unknown error with curl.')


if __name__ == '__main__':

    os.chdir(downloadDir)
    # First, we download the Sources.bz2 file
    # XXX: We should implement a way to use a cache
    uri = 'http://192.168.0.10:9999/ubuntu/dists/hoary/main/source/Sources.bz2'
    file = 'Sources.bz2'
    print "Getting %s" % uri
    download(file, uri, False)
    tmpFile = TemporaryFile()
    tmpFile.write(bz2.decompress(open(file).read()))
    tmpFile.seek(0)

    # Here we can forget about the file format, apt_pkg will handle it for us.
    parser = apt_pkg.ParseTagFile(tmpFile)

    while parser.Step() == 1:

        # Every iteration is a new package from Sources.bz2
        print "Processing: %s" % parser.Section.get("Package")

        # We will work only with packages that work with cdbs
        if parser.Section.get("Build-Depends") is not None and \
           'cdbs' in parser.Section.get("Build-Depends").split():

            for srcFile in parser.Section.get("Files").strip().split('\n'):

                (md5, size, filename) = srcFile.strip().split()
                if filename.endswith('.dsc'):
                    dscFile = filename
                elif filename.endswith('.tar.gz'):
                    tarFile = filename
                    # We get the directory name for this package from the .tar.gz
                    if len(filename.split('.orig.tar.gz')) == 2:
                        dirName = filename.split('.orig.tar.gz')[0]
                    else:
                        # For native packages
                        dirName = filename.split('.tar.gz')[0]
                    # XXX: This is uuugly, but necessary, I'm open to other
                    # options. The main idea behind this is that the directory
                    # names have the '-' char instead of the '_' one from the
                    # tar.gz
                    dirName = dirName.replace('_', '-', 1)

                uri = ("http://192.168.0.10:9999/ubuntu/%s/%s" %
                    (parser.Section.get("Directory").strip(), filename))
                print "Downloading %s" % filename
                download(filename, uri, True, md5)

            # At this point we have all needed files downloaded.
            print "Processing %s" % dscFile
            extractDeb(dscFile)
            try:
                updateCDBS(dirName)
            except RuntimeError, e:
                print "***********************************"
                print e
                print "***********************************"
                pass

            product = parser.Section.get("Package")

            if product in mapping.keys():
                product = mapping[product]

            url = '%s/rosetta/products/%s' % (launchpadURL, product)
            try:
                valid = checkURL(url)
            except:
                # We had an error checking the URL, we jump to the next product.
                print 'Error checking the URL: %s' % url
                continue

            if not valid:
                # We need to create the product
                try:
                    if product in mapping.keys():
                        product = mapping[product]
                    if not createProduct(product):
                        print 'Unable to found the %s product' % product
                        continue
                except:
                    print 'Error creating the new product'
                    continue

            for poDir in getPODirs(dirName):
                print poDir
                files = os.listdir(poDir)
                for file in files:
                    if file.endswith('.pot'):
                        potname = file[:len(file)-4]
                        uploadPOT(
                            product,
                            potname,
                            poDir,
                            file)
                for file in files:
                    if file.endswith('.po'):
                        uploadPO(
                            product,
                            potname,
                            file[:len(file)-3],
                            poDir,
                            file)
