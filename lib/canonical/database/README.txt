This is the central repository for our PostgreSQL -> Python glue.
You should not use these classes and interfaces directly. Instead, you
should shadow the ones you need using a launchpad unique prefix.
Use an adapter to adapt the object provided by this package to
the object used by your application.

This allows somewhere to put product specific extensions. It also solves
the problem of attaching views and traversal of classes shared between
applications (eg. All of Soyuz, Malone and Rosetta will want to traverse
an IProject, but there can be only one traversal hook). This limitation
may change, but the convention may still remain.

