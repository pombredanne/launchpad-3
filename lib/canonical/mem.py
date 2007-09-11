"""
This code is from:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/286222
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65333
This is under the Python Licence.

It also contains spiv's code from:
    http://twistedmatrix.com/users/spiv/countrefs.py
This is under 'MIT Licence if I'm pressed'

None of this should be in day-to-day use. Feel free to document usage
and improve APIs as needed.

"""

import os
import gc


_proc_status = '/proc/%d/status' % os.getpid()

_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0}

def _VmB(VmKey):
    '''Private.
    '''
    global _proc_status, _scale
     # get pseudo file  /proc/<pid>/status
    try:
        t = open(_proc_status)
        v = t.read()
        t.close()
    except OSError:
        return 0.0  # non-Linux?
     # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    i = v.index(VmKey)
    v = v[i:].split(None, 3)  # whitespace
    if len(v) < 3:
        return 0.0  # invalid format?
     # convert Vm value to bytes
    return float(v[1]) * _scale[v[2]]


def memory(since=0.0):
    '''Return memory usage in bytes.
    '''
    return _VmB('VmSize:') - since


def resident(since=0.0):
    '''Return resident memory usage in bytes.
    '''
    return _VmB('VmRSS:') - since


def stacksize(since=0.0):
    '''Return stack size in bytes.
    '''
    return _VmB('VmStk:') - since


def dump_garbage():
    """
    show us what's the garbage about

    import gc
    gc.enable()
    gc.set_debug(gc.DEBUG_LEAK)

    """

    # force collection
    print "\nGARBAGE:"
    gc.collect()

    print "\nGARBAGE OBJECTS:"
    for x in gc.garbage:
        s = str(x)
        if len(s) > 80: s = s[:80]
        print type(x),"\n  ", s

# This is spiv's reference count code, under 'MIT Licence if I'm pressed'.
#
import gc, sys, types
import threading, time

def mostRefs(n=30):
    d = {}
    for obj in gc.get_objects():
        if type(obj) in (types.ClassType, types.TypeType):
            d[obj] = sys.getrefcount(obj)
    counts = [(x[1],x[0]) for x in d.items()]
    counts.sort()
    counts = counts[-n:]
    counts.reverse()
    return counts


def printCounts(counts, file=None):
    for c, obj in counts:
        if file is None:
            print c, obj
        else:
            file.write("%s %s\n" % (c, obj))


def logInThread(n=30):
    reflog = file('/tmp/refs.log','w')
    t = threading.Thread(target=_logRefsEverySecond, args=(reflog, n))
    t.setDaemon(True) # allow process to exit without explicitly stopping thread
    t.start()


def _logRefsEverySecond(log, n):
    while True:
        printCounts(mostRefs(n=n), file=log)
        log.write('\n')
        log.flush()
        time.sleep(1)

if __name__=="__main__":
    counts = mostRefs()
    printCounts(counts)

    gc.enable()
    gc.set_debug(gc.DEBUG_LEAK)

    # make a leak
    l = []
    l.append(l)
    del l

    # show the dirt ;-)
    dump_garbage()


