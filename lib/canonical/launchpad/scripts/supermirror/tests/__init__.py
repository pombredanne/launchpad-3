import os

def createbranch(directory):
    whine("Creating branch at %s" % (directory))
    current = os.getcwd()
    os.makedirs(directory)
    os.chdir(directory)
    whine(os.popen("bzr init").readlines())
    whine(os.popen("echo hello > hello").readlines())
    whine(os.popen("bzr add hello").readlines())
    whine(os.popen("bzr commit -m'Test branch' 2> /dev/null").readlines())
    os.chdir(current)

def whine(data):
    if os.environ.get("DEBUG") is not None:
        print "\n", data

