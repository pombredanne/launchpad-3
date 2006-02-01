<TeXmacs|1.0.5>

<style|generic>

<\body>
  <doc-data|<doc-title|<with|color|dark red|DRAFT> Launchpad's Bazaar
  <with|color|dark red|DRAFT>>>

  This document explains what are the existing components of
  <hlink|TheBazaar|https://wiki.launchpad.canonical.com/TheBazaar>, the
  Bazaar integration in Launchpad, how they relate to one another, and some
  of the future plans. It was written by David Allouche at the end of January
  2006.

  There is a strong bias towards the internal details of the components I'm
  familiar with and the issues I know about, and this documentation does not
  pretend being complete by any mean. Corrections and additions are welcome.

  <with|color|dark red|<with|font-shape|small-caps|Work in progress!> This
  document is still incomplete. In particular, the RCS Importer is not
  covered in any detail yet. It is published so developers can provide early
  feedback.>

  <section|Bazaar Overview>

  First, let's have a bird eye's view of the various moving parts providing
  Bazaar integration in Launchpad. That's simplistic, but that gives us a
  place to start.<no-page-break>

  <big-figure|<postscript|launchpad-bzr.png|*5/8|*5/8||||>|Don't panic>

  There is a dotted arrow in this diagram, it means ``handwaving here''. The
  details of what it means will be covered a bit later.

  The dashed line is the Launchpad system boundary. Anything that is inside
  the dashed box we control and we run. Anything that is outside the dashed
  box is out there on the wild internet.

  The two important storage areas are:

  <\itemize>
    <item>Launchpad, the all-encompassing database. You know it, you can use
    its schema to cover the walls of a very large conference room. Every
    component in the system is driven by Lauchpad data.

    <item>Supermirror, essentially just a big hard drive that stores Bazaar
    branches. It is represented here because it is an important information
    bus.
  </itemize>

  The important world-facing systems are:

  <\itemize>
    <item>Branch Puller, periodically runs <verbatim|bzr pull> to copy remote
    branches registered in Launchpad onto the Supermirror. It is the specific
    service for ``pull branches''.

    <item>SFTP Server, allows <verbatim|bzr> to directly push branches on
    Launchpad, effectively providing a free community hosting service for
    Bazaar branches. It is the specific service for ``push branches''.

    <item>Branch publisher, exposes a HTTP server from which all branches
    stored on the Supermirror can be checked out. It is the Supermirror
    front-end, serving Bazaar goodness to the world, whereas the the Branch
    Puller and the SFTP Server are back-ends used to place data on the
    Supermirror.

    <item>RCS importer, sucks the living CPU out of CVS and Subversion server
    out there to free source code from the centralized versioning oppression.
    It produces Bazaar branches from upstream repositories specified in
    Launchpad and stuff the Supermirror with the resulting gigabytes of
    uninteresting historical details.
  </itemize>

  Finally, the Branch Syncher in an internal system that scans branches
  stored on the Supermirror and stores summary historical information into
  the Launchpad database.

  <section|Break up by service>

  The scary diagram at the beginning is actually the superimposition of
  diagrams for several nearly independent services. Before examining
  individual components and their relations, we will have a quick tour of
  each service.

  <subsection|Pull branch mirroring>

  One of the services is the mirroring of remote branches. Remote branches
  registered in Launchpad are pulled onto the Supermirror and published on
  <verbatim|bazaar.launchpad.net>.<no-page-break>

  <big-figure|<postscript|pull-branch.png|*5/8|*5/8||||>|Pull branch
  mirroring>

  Pull branches on the Supermirror are periodically updated on the
  Supermirror by the Branch Puller. The Branch Publisher serves the
  Supermirror data to Bazaar clients that want to use the Supermirror rather
  than accessing the master branch.

  <subsection|Push branch hosting>

  Launchpad provides a hosting service for Bazaar branch. A Bazaar user
  wishing to publish a branch, but unable use a personal web space, can push
  the branch on <verbatim|bazaar.launchpad.net> using the SFTP
  transport.<no-page-break>

  <big-figure|<postscript|push-branch.png|*5/8|*5/8||||>|Push branch hosting>

  The SFTP server writes to a private filesystem. The Branch Puller is used
  to copy branches from the private SFTP area to the Supermirror, ensuring
  that only usable Bazaar branch data gets copied to the Supermirror.

  Once it is stored on the Supermirror, the branch is published in the same
  way as for pull branches.

  <subsection|RCS imports>

  The famous RCS import service produces a publicly accessible Bazaar
  branches from the source code history stored in a remote centralized
  VCS.<no-page-break>

  <big-figure|<postscript|rcs-import.png|*5/8|*5/8||||>|RCS import>

  A bit earlier, I told you not to worry about the dotted line. Now is the
  minute of truth where its meaning will be uncovered. The RCS import
  branches must be published on the Supermirror so they will be accessible to
  the Branch Syncher, and served on the same host as the other branches on
  the Supermirror. But the way the import branches will be copied on the
  Supermirror is still undecided at the moment.

  A full explanation of the issue would be quite lengthy and technical. We
  will do it later when we are looking really closely at the RCS Importer.

  <subsection|Branch scanning>

  The last service in the system, at the moment at least, is the Branch
  Syncher. It update the Launchpad database record of the ancestry of all
  branches present on the Supermirror.<no-page-break>

  <big-figure|<postscript|branch-scan.png|*5/8|*5/8||||>|Branch scanning>

  The ancestry record in Launchpad is currently only used to display the most
  recent revisions on each branch. But many future features will use this
  data as well. For example measuring the activity of branches, grouping
  branches, marking merged branches, etc.\ 

  <section|Break up by component>

  At this point, you should have a reasonable feeling of how the various
  components relate to one another. So we can start with the really technical
  stuff.

  <subsection|Branch Publisher>

  <big-figure|<postscript|branch-publisher.png|*5/8|*5/8||||>|Branch
  Publisher>

  The Branch Publisher is the web server on <verbatim|bazaar.launchpad.net>.
  It only provides web resources for use by <verbatim|bzr>, and no resource
  meant for direct human consumption.

  The only resources are Bazaar branches. The Branch Publisher has no
  knowledge of the Bazaar branch format, it is a dump HTTP server. Each
  published branch is associated to a Branch object in the Launchpad
  database. Branches are served as <verbatim|http://bazaar.launchpad.net/~owner/product/branch>.

  <\itemize>
    <item><verbatim|owner> is the string <verbatim|branch.owner.name>.<no-page-break>

    <item><verbatim|product> is the string <verbatim|branch.product.name>, or
    <verbatim|"+junk"> if the branch is not associated to a
    Product.<no-page-break>

    <item><verbatim|branch> is the string <verbatim|branch.name>.
  </itemize>

  The URL where a branch is served changes when any of those values change:
  because the branch, product or owner's name attribute change, or a branch
  gets associated to a different owner or product.

  The Supermirror filesystem hierarchy was designed to be indifferent to
  those renamings. Branches on the Supermirror are stored by database id.
  Specifically, if a branch's id is <verbatim|0x89ABCDEF>, the branch is a
  directory whose path is of the form <verbatim|$base/89/ab/cd/ef>.

  The mapping between filesystem names and URL is done by a
  <verbatim|mod_rewrite> rule which is periodically updated from the
  Launchpad branch data.

  <paragraph|Relation:>Branch Publisher serves branches stored on the
  Supermirror.

  <paragraph|Relation:>Branch Publisher reads Launchpad Branch details to
  rewrites public URLs requested by Bazaar clients into Supermirror
  filesystem names. Only branches with an associated Branch database record
  are published.

  <paragraph|Constraint:>The public name of branches can change at any time.

  <paragraph|Constraint:>The Supermirror filesystem hierarchy should be
  encapsulated. Launchpad branch ids must not be exposed to the
  user.<no-page-break>

  <paragraph|Constraint:>Branches stored on the Supermirror must be valid at
  all times. The only legal way to modify branch data on the Supermirror
  filesystem is using <verbatim|bzr push>.

  <subsection|SFTP Server>

  <big-figure|<postscript|sftp-server.png|*5/8|*5/8||||>|SFTP Server>

  The SFTP server allows Launchpad users to host their branches on Launchpad.
  It is a custom SFTP server based on Twisted. A user can log in using a SSH
  key whose public key is registered in Launchpad. Only paths of the form
  <verbatim|~owner/product/branch> (as for the Branch Publisher) can be used,
  where <verbatim|owner> identifies the user whose SSH keys are used for
  authentication. If <verbatim|owner> is a team, the SSH keys of all members
  of the team can be used.

  <paragraph|Relation:>SFTP Server asks Launchpad for team members and SSH
  public keys or users.

  The SFTP servers writes to a private filesystem that uses the same layout
  as the Supermirror. The mapping from the virtual filesystem exposed by SFTP
  and the actual filesystem layout is performed during authentication. That
  makes the SFTP server robust against branch renames occurring concurrently
  to a SFTP session.

  <paragraph|Relation:>SFTP Server asks Launchpad for name, id and product
  name of branches owned by a person and the teams it belongs to.

  Existing branches with a non-<verbatim|NULL> URLs are pull branches. Their
  associated directories are inaccessible on the SFTP server. Branches with a
  <verbatim|NULL> URL are push branches and are associated to writable
  directories. When a user tries to create a non-existent branch
  <verbatim|~owner/product/branch>, and <verbatim|owner> is the authenticated
  user or a team it belongs to, and the named product exists (or is
  <verbatim|+junk>), a branch is automatically created in the Launchpad
  database with the given owner, product and name and with no title or
  description.

  <paragraph|Relation:>SFTP creates Branch records in Launchpad.\ 

  <subsection|Branch Puller>

  <big-figure|<postscript|branch-puller.png|*5/8|*5/8||||>|Branch Puller>

  <subsubsection|Branch Puller and Launchpad>

  The Branch Puller is the component that writes to the Supermirror. It
  processes two kinds of branches:

  <\itemize>
    <item>Remote branches, from untrusted public servers on the internet,
    using URLs registered in the Launchpad database.

    <item>SFTP branches, on the filesystem of the SFTP server, using the id
    of Launchpad branches without an URL.
  </itemize>

  <paragraph|Relation:>Branch Puller asks Launchpad for Branch ids and URLs.

  <paragraph|Relation:>Branch Puller pulls <verbatim|bzr> branches from the
  private SFTP Server filesystem and from public web spaces on the internet.

  At the time of writing (2005-01-31), the Branch Puller gets its branch data
  from Launchpad by reading the <verbatim|/supermirror-pull-list.txt> page.

  <subsubsection|Branch Puller and Supermirror>

  The Branch Puller writes directly to the id-based Supermirror filesystem.

  It uses <verbatim|bzr get> to create new branches on the Supermirror and
  <verbatim|bzr pull --overwrite> to update existing branches. The use of
  <verbatim|bzr> to copy the data ensures that only vaguely sane Bazaar
  branch data is stored on the Supermirror. Warez swappers would need to use
  bzr to be published, and blatantly corrupt branch data would not be
  published.

  <paragraph|Relation:>Branch Puller writes sanitized branch data on the
  Supermirror.

  <subsection|Branch Syncher>

  <big-figure|<postscript|branch-syncher.png|*5/8|*5/8||||>|Branch Syncher>

  <paragraph|Relation:>Branch Syncher asks Launchpad for a list of branches
  to scan.

  <paragraph|Relation:>Branch Syncher reads the revision-history and revision
  entries from published branches.

  The Branch Syncher does not access the Supermirror filesystem directly.
  Instead it uses a special rewriting rule of the Branch Publisher that gives
  it access to branches by hexadecimal id but hides the details of the real
  filesystem layout.

  <paragraph|Relation:>Branch Syncher updates the Revision, RevisionNumber
  and RevisionParent tables in the Launchpad database.

  In particular, the Branch Syncher needs to be able to delete RevisionNumber
  records because the revision-history of a branch is not append-only.
  However, Revision and RevisionParent records are never deleted or modified.

  Since the published branches were sanitized by the Branch Puller, the
  Branch Syncher should not normally fail.

  This process is separate from the Branch Puller for two reasons:

  <\itemize>
    <item>It needs database permissions, in particular <verbatim|DELETE>
    permissions, which are not required by the Branch Puller, and the Branch
    Puller is considered compromised because it handles untrusted data and
    communicates directly with potentially hostile web servers.

    <item>The Branch Puller and Branch Syncher were developed and deployed by
    different individuals. Keeping them separate prevents crossing
    responsibility boundaries.
  </itemize>

  <subsection|RCS Importer>

  <big-figure|<postscript|rcs-importer.png|*5/8|*5/8||||>|RCS Importer>

  The RCS Importer creates and update Bazaar branches from the historical
  information available in third party version control systems. Currently,
  imports from CVS and Subversion are supported. It is also known as
  <verbatim|importd>, and uses Buildbot and CSCVS.

  This is the oldest component of the system, and predates Launchpad itself.
  It is still importing into <verbatim|baz> branches and the transition to
  <verbatim|bzr> is in progress. Over time, it has accumulated many design
  and implementation problems that prevent delivering a good quality of
  service and make maintenance painful.

  <paragraph|Relation:>RCS Importer asks Launchpad for RCS to import from and
  branches to import into.

  <paragraph|Relation:>RCS Importer gets and update import status in
  Launchpad.

  <paragraph|Relation:>RCS Importer retrieves version control history from
  remote repositories.

  <paragraph|Relation:>RCS Importer publish imported branches on the
  Supermirror.

  Historically, the role of the Branch Syncher was performed in the RCS
  Importer, by a component called Taxi. When the Launchpad database schema
  was updated to model Bazaar branch instead of Arch branches, Taxi was
  removed.

  RCS Import is a very expensive and time consuming task that is bound on
  network, CPU and disk I/O at different times.

  <\itemize>
    <item>It is network bound when checking out trees from remote RCS
    repositories, retrieving historical data from remote servers and
    publishing imports.

    <item>It is CPU bound when synthetizing changesets from CVS log and when
    committing revisions.

    <item>It is I/O bound when comitting revisions and doing consistency
    checks.
  </itemize>

  The initial import of a branch can take up to several days if the source
  tree is large, the history is long, or the remote server is slow. Also,
  these issues tend to come in groups: projects with a large source tree
  often have a long history and an overloaded server, leading to initial
  imports taking up to several weeks.

  <subsubsection|Buildbot and CSCVS>

  The components of the RCS Importer Buildbot, Importd and CSCVS.

  Buildbot's is used as an abstract build control system. Its roles are:

  <\itemize>
    <item>Control conversion tasks, and automatically run periodic
    conversions.

    <item>Spread tasks on multiple systems.

    <item>Provide a web-accessible control panel, to manually start
    conversions and report historical conversion status and logs.
  </itemize>

  Importd specializes Buildbot to:

  <\itemize>
    <item>Load jobs from Launchpad.

    <item>Prepare data and run CSCVS.

    <item>Update the importstatus in Launchpad.

    <item>Register and publish branches.

    <item>Display jobs in Buildbot's web control panel.
  </itemize>

  CSCVS is an independent system that performs the actual RCS conversion. Its
  roles are:

  <\itemize>
    <item>
  </itemize>

  <subsubsection|Import Status>

  \;

  <subsubsection|Sanity Checking and Rollback>

  When an import is attempted again after a failure, the base for the second
  attempt is the published branch. Data produced during the previous failed
  import is discarded.

  Before publishing an imported branch, the source contents of the latest
  imported revision are compared to the source retrieved from the Upstream
  RCS at the start of the import. Deviations in the imported history are
  tolerated as it is impossible to retrieve past full tree revision from CVS
  in the general case.

  <paragraph|Open Issue:>Better sanity checking could be performed. On CVS,
  comparison of annotated source could be reliably implemented. On Subversion
  it is generally possible to retrieve past full tree revisions.

  <subsubsection|RCS Imports in Arch>

  The RCS Importer was designed, implemented and maintained for a long time
  with the assumption that the output format was Arch branches. In particular
  a lot of work was done to avoid Arch namespace collisions. The histor

  Historically, RCS import branches were published on
  <verbatim|bazaar.ubuntu.com>. Then they were treated as remote branches and
  pulled by the Supermirror. This worked well because branches had an easy
  unique and persistent identifier: their Arch namespace. With
  <verbatim|bzr>, there is no such thing anymore. The only thing that
  persistently identify a branch in Launchpad is its id in the database. But
  if we publish the branch on <verbatim|bazaar.ubuntu.com>, and treat it as a
  pull branch, we must choose a name that is meaningful to humans because it
  will appear in the Launchpad web UI and the <verbatim|bazaar.ubuntu.com>
  private space.

  <with|color|red|TODO>

  <section|Future Plans and Open Issues>

  <subsection|Branch Puller's Future>

  <paragraph|Open issue:>The Bazaar branch data on remote branches and on the
  SFTP server can be altered in essentially arbitrary ways. A branch can be
  replaced by a completely unrelated branch. More practically, branches can
  be altered to remove ``Nuclear Launch Codes'', ``Nuclear Waste'' and
  garbage revisions that are not part of the branch's ancestry. However,
  although <verbatim|bzr pull --overwrite> treats the revision-history as
  rewritable, it treats the store as append only. The Branch Puller would
  need explicit support to allow users to remove with Nuclear Launch Codes
  and Nuclear Waste from their branch on the Supermirror.

  <subsubsection|Future plan: Launchpad reporting>

  The Branch Puller should be able to store reporting information in
  Launchpad. The information that would be useful to store include:

  <\itemize>
    <item>Date of latest successful pull.

    <item>Date of latest pull attempt.

    <item>Success status of the latest pull attempt.

    <item>Diagnostic data for the latest pull attempt if it was a failure. In
    the simplest case, that could be a simple Pyhon backtrace.
  </itemize>

  Internal system failures, like failed communication with Launchpad, must be
  reported to the <verbatim|launchpad-error-reports> mailing list and not
  recorded in the database.

  Normal pull failures should also be reported to the mailing list to allow
  fast response to users. That would allow James Blackwell to notice that an
  interesting new branch is failing and to contact the branch owner directly
  to fix the problem.

  This error reporting is mentioned as the <verbatim|branchPulled> XMLRPC
  call in <hlink|SupermirrorXmlRpc|https://wiki.launchpad.canonical.com/SupermirrorXmlRpc>
  and <hlink|BranchXmlRpc|https://wiki.launchpad.canonical.com/BranchXmlRpc>,
  and as an open issue on <hlink|BazaarTaskList|https://wiki.launchpad.canonical.com/BazaarTaskList>.

  <paragraph|Relation:>Branch Pullers stores status reports in Launchpad.

  <subsubsection|Future plan: Ignore expected failures>

  In normal usage, some branches are not worth trying to pull. Mainly,
  restricted branches like those stored on
  <verbatim|sftp://chinstrap.ubuntu.com/>, but also blatantly incorrect
  branches, like those pointing to a Subversion repository.

  Those branches are characterized by pull attempts that are never
  successful. The details of how the successive failures are counted, and how
  they affect pull frequency, are still a bit uncertain. Eventually, a branch
  that is never successfully pulled will no longer be attempted. Otherwise
  error reports would quickly be drowned in expected failures.

  This is mentioned as an open issue on <hlink|BazaarTaskList|https://wiki.launchpad.canonical.com/BazaarTaskList>.

  <subsubsection|Future plan: Pull now>

  Daniel registered a <verbatim|bzr> branch of <verbatim|gedit> to support
  MoinMoin syntax highlighting, then he comes back a couple of weeks later to
  find that his branch was never successfully pulled: all attempts failed
  with a 403 HTTP error because there was a bug in the <verbatim|.htaccess>
  file on his webspace. In the meantime, all the pull attempts on that branch
  have failed and it was classified as an expected failure. Daniel fixes the
  <verbatim|.htaccess> setting, requests a new pull attempt, and monitors the
  outcome of the pull.

  Henry has a branch of <verbatim|gnome-panel> that preserves layout when
  changing the screen resolution. He publishes it using the Launchpad SFTP
  Server. Immediately after publishing he goes on the <verbatim|#gnome-devel>
  IRC chat room to ask people to look at the fix and gives the URL of his
  branch page: <verbatim|https://launcphad.net/people/henry/+branches/gnome-panel/layout-bugfix>.
  A GNOME developer commit want to review the changes, looks at the page and
  sees that a pull is pending, then waits until the pull is complete to merge
  that branch into a fresh import of mainline and review the changes.

  Both those use cases require some new functionality:

  <\itemize>
    <item>Requesting an immediate branch pull through the Launchpad UI or
    through the SFTP Server.

    <item>Feedback in the Launchpad UI when a pull is in progress.
  </itemize>

  Part of this functionality is addressed in
  <hlink|SupermirrorXmlRpc|https://wiki.launchpad.canonical.com/SupermirrorXmlRpc>
  and <hlink|BranchXmlRpc|https://wiki.launchpad.canonical.com/BranchXmlRpc>.

  <subsubsection|Future plan: Concurrent tasks>

  Pulling a branch is a network-bound task that can take a long time. It can
  also be CPU intensive in some cases.

  To allow pull-now requests to be handled quickly, it would be necessary to
  implement the Branch Puller as a service, as opposed to a <verbatim|cron>
  job, which would be able to schedule tasks in a flexible way. Long running
  tasks should not prevent new tasks from running.

  <no-page-break*>This needs to be taken into account in the design of
  <hlink|Buildd-NG|https://wiki.launchpad.canonical.com/ImportdRefactoring>.

  <subsection|Branch Syncher's Future>

  <subsubsection|Future plan: Launchpad reporting>

  The date of the latest successful synch should be displayed in the
  Launchpad UI to explain that the displayed branch details might be out of
  date.

  <subsubsection|Future plan: Sync now>

  The Branch Puller should be able to report when a branch on the Supermirror
  has changed and needs to be scanned again. Currently, all branches are
  scanned periodically by a <verbatim|cron> job. This takes a significant
  time (one hour as of 2005-01-31), so synching is done every two hour.

  Marking branches that needs to be synched allows reducing the run time of a
  synching batch, increasing the frequency of the periodic job, therefore
  reducing the latency in the common case.

  The ``branch changed'' information would be set by the
  <verbatim|branchPulled> XMLRPC call described in
  <hlink|SupermirrorXmlRpc|https://wiki.launchpad.canonical.com/SupermirrorXmlRpc>
  and <hlink|BranchXmlRpc|https://wiki.launchpad.canonical.com/BranchXmlRpc>.

  <subsubsection|Future plan: Concurrent tasks>

  The Branch Syncher needs to traverse the complete ancestry of branches so
  old revisions can be created in the database in response to ghost filling
  in a Supermirror branch. This process is database-bound and can take a
  significant amount of time (probably several tens of minutes for very large
  branches).

  To allow sync-now requests to be handled quickly, it would be necessary to
  implement the Branch Syncher as a service with flexible scheduling
  abilities. Long running tasks should not prevent new tasks from running.

  This needs to be taken into account in the design of
  <hlink|Buildd-NG|https://wiki.launchpad.canonical.com/ImportdRefactoring>.

  <subsection|RCS Importer's Future>

  <with|color|red|TODO>
</body>

<\initial>
  <\collection>
    <associate|language|british>
    <associate|page-medium|papyrus>
    <associate|par-mode|left>
    <associate|sfactor|5>
  </collection>
</initial>

<\references>
  <\collection>
    <associate|auto-1|<tuple|1|1>>
    <associate|auto-10|<tuple|2.4|3>>
    <associate|auto-11|<tuple|5|3>>
    <associate|auto-12|<tuple|3|4>>
    <associate|auto-13|<tuple|3.1|4>>
    <associate|auto-14|<tuple|6|4>>
    <associate|auto-15|<tuple|1|4>>
    <associate|auto-16|<tuple|2|4>>
    <associate|auto-17|<tuple|3|4>>
    <associate|auto-18|<tuple|4|4>>
    <associate|auto-19|<tuple|5|4>>
    <associate|auto-2|<tuple|1|1>>
    <associate|auto-20|<tuple|3.2|5>>
    <associate|auto-21|<tuple|7|5>>
    <associate|auto-22|<tuple|6|5>>
    <associate|auto-23|<tuple|7|5>>
    <associate|auto-24|<tuple|8|5>>
    <associate|auto-25|<tuple|3.3|5>>
    <associate|auto-26|<tuple|8|5>>
    <associate|auto-27|<tuple|3.3.1|6>>
    <associate|auto-28|<tuple|3.3.1.1|6>>
    <associate|auto-29|<tuple|3.3.1.2|6>>
    <associate|auto-3|<tuple|2|2>>
    <associate|auto-30|<tuple|3.3.2|6>>
    <associate|auto-31|<tuple|3.3.2.1|6>>
    <associate|auto-32|<tuple|3.4|6>>
    <associate|auto-33|<tuple|9|6>>
    <associate|auto-34|<tuple|3.4.0.2|6>>
    <associate|auto-35|<tuple|3.4.0.3|6>>
    <associate|auto-36|<tuple|3.4.0.4|6>>
    <associate|auto-37|<tuple|3.5|7>>
    <associate|auto-38|<tuple|10|7>>
    <associate|auto-39|<tuple|3.5.0.5|7>>
    <associate|auto-4|<tuple|2.1|2>>
    <associate|auto-40|<tuple|3.5.0.6|7>>
    <associate|auto-41|<tuple|3.5.0.7|7>>
    <associate|auto-42|<tuple|3.5.0.8|8>>
    <associate|auto-43|<tuple|3.5.1|8>>
    <associate|auto-44|<tuple|3.5.2|8>>
    <associate|auto-45|<tuple|3.5.3|8>>
    <associate|auto-46|<tuple|3.5.3.1|9>>
    <associate|auto-47|<tuple|3.5.4|9>>
    <associate|auto-48|<tuple|4|9>>
    <associate|auto-49|<tuple|4.1|9>>
    <associate|auto-5|<tuple|2|2>>
    <associate|auto-50|<tuple|4.1.0.1|9>>
    <associate|auto-51|<tuple|4.1.1|?>>
    <associate|auto-52|<tuple|4.1.1.1|?>>
    <associate|auto-53|<tuple|4.1.2|?>>
    <associate|auto-54|<tuple|4.1.3|?>>
    <associate|auto-55|<tuple|4.1.4|?>>
    <associate|auto-56|<tuple|4.2|?>>
    <associate|auto-57|<tuple|4.2.1|?>>
    <associate|auto-58|<tuple|4.2.2|?>>
    <associate|auto-59|<tuple|4.2.3|?>>
    <associate|auto-6|<tuple|2.2|2>>
    <associate|auto-60|<tuple|4.3|?>>
    <associate|auto-7|<tuple|3|2>>
    <associate|auto-8|<tuple|2.3|3>>
    <associate|auto-9|<tuple|4|3>>
  </collection>
</references>

<\auxiliary>
  <\collection>
    <\associate|figure>
      <tuple|normal|Don't panic|<pageref|auto-2>>

      <tuple|normal|Pull branch mirroring|<pageref|auto-5>>

      <tuple|normal|Push branch hosting|<pageref|auto-7>>

      <tuple|normal|RCS import|<pageref|auto-9>>

      <tuple|normal|Branch scanning|<pageref|auto-11>>

      <tuple|normal|Branch Publisher|<pageref|auto-14>>

      <tuple|normal|SFTP Server|<pageref|auto-21>>

      <tuple|normal|Branch Puller|<pageref|auto-26>>

      <tuple|normal|Branch Syncher|<pageref|auto-33>>
    </associate>
    <\associate|toc>
      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|Bazaar
      Overview> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-1><vspace|0.5fn>

      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|Break
      up by service> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-3><vspace|0.5fn>

      <with|par-left|<quote|1.5fn>|Pull branch mirroring
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-4>>

      <with|par-left|<quote|1.5fn>|Push branch hosting
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-6>>

      <with|par-left|<quote|1.5fn>|RCS imports
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-8>>

      <with|par-left|<quote|1.5fn>|Branch scanning
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-10>>

      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|Break
      up by component> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-12><vspace|0.5fn>

      <with|par-left|<quote|1.5fn>|Branch Publisher
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-13>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-15><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-16><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Constraint:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-17><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Constraint:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-18><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Constraint:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-19><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|SFTP Server
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-20>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-22><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-23><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-24><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|Branch Puller
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-25>>

      <with|par-left|<quote|3fn>|Branch Puller and Launchpad
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-27>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-28><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-29><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|Branch Puller and Supermirror
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-30>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-31><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|Branch Syncher
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-32>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-34><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-35><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-36><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|RCS Importer
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-37>>

      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|Future
      Plans and Open Issues> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-38><vspace|0.5fn>

      <with|par-left|<quote|1.5fn>|Branch Puller's Future
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-39>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-40><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|Future plan: Launchpad reporting
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-41>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-42><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|Future plan: Ignore expected failures
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-43>>

      <with|par-left|<quote|3fn>|Future plan: Pull now
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-44>>

      <with|par-left|<quote|3fn>|Future plan: Concurrent tasks
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-45>>

      <with|par-left|<quote|1.5fn>|Branch Syncher's Future
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-46>>

      <with|par-left|<quote|3fn>|Future plan: Launchpad reporting
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-47>>

      <with|par-left|<quote|3fn>|Future plan: Sync now
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-48>>

      <with|par-left|<quote|3fn>|Future plan: Concurrent tasks
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-49>>

      <with|par-left|<quote|1.5fn>|RCS Importer's Future
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-50>>
    </associate>
  </collection>
</auxiliary>