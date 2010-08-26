Profiling Integration
=====================

The profiler module supports three basic kinds of integration.

1.  It can be configured to optionally profile requests.  To turn this on, in
    ``launchpad-lazr.conf`` (e.g.,
    ``configs/development/launchpad-lazr.conf``) , in the ``[profiling]``
    section, set ``profiling_allowed: True``.  As of this writing, this
    is the default value for development.  It might be OK to occasionally
    turn it on in staging, though note the `Profiler Warnings`_ below.

    Once it is turned on, you can insert /++profile++/ in the URL to get
    basic instructions on how to use the feature.

2.  It can be configured to profile all requests, indiscriminately.  To turn
    this on, use the ``profiling_allowed`` setting described in option 1
    above and also set ``profile_all_requests: True`` in the
    ``[profiling]`` section of ``launchpad-lazr.conf``.

    Once it is turned on, every request will create a profiling log usable
    with KCacheGrind.  The browser will include information on the file
    created for that request.

3.  It can be configured to record the virtual and resident memory before and
    after a request.  To turn this on, use the ``profiling_allowed``
    setting described in option 1 above and also set the
    ``memory_profile_log`` in the ``[profiling]`` section of
    ``launchpad-lazr.conf`` to a path to a log file.

Profiler Warnings
-----------------

The profiler in options 1 and 2 above will only allow profiled requests to
run in serial.

The data collected in option 3 will be polluted by parallel requests: if
memory increases in one request while another is also running in a different
thread, both requests will show the increase.  It also will probably be
polluted by simultaneous use of options 1 and 2.

Note that none of these options are currently blessed for production use.
For options 1 and 2, this is because of the typical cost of employing a
profiling hook.  The fact that requests are forced to run in serial is also
a concern, since some of our requests can take much longer than others.
For option 3, the implementation relies on lib/canonical/mem.py, which
as of this writing warns in its docstring that "[n]one of this should be
in day-to-day use."
