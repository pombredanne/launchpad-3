<TeXmacs|1.0.5>

<style|<tuple|generic|section-article>>

<\body>
  <doc-data|<doc-title|Launchpad's Bazaar>>

  This document explains what are the existing components of
  <hlink|TheBazaar|https://wiki.launchpad.canonical.com/TheBazaar>, the
  Bazaar integration in Launchpad, how they relate to one another, and some
  of the future plans. It was written by David Allouche at the end of January
  2006.

  There is a strong bias towards the internal details of the components I'm
  familiar with and the issues I know about, and this documentation does not
  pretend being complete by any means. Corrections and additions are welcome.

  <section|Bazaar Overview>

  <subsection|The Big Picture>

  First, let's have a bird's eye view of the various moving parts providing
  Bazaar integration in Launchpad. That's simplistic, but that gives us a
  place to start.

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

    <item>Branch Warehouse, essentially just a big hard drive that stores
    Bazaar branches. It is represented here because it is an important
    information bus. It is also known as the ``Supermirror filesystem''.
  </itemize>

  The important world-facing systems are:

  <\itemize>
    <item>Branch Puller, periodically runs <verbatim|bzr pull> to copy remote
    branches registered in Launchpad onto the Branch Warehouse. It is the
    specific service for ``pull branches''.<no-page-break>

    <item>SFTP Server, allows <verbatim|bzr> to directly push branches on
    Launchpad, effectively providing a free community hosting service for
    Bazaar branches. It is the specific component for ``push branches''.

    <item>Branch publisher, exposes a HTTP server from which all branches
    stored in the Warehouse can be checked out. It is the Supermirror
    front-end, serving Bazaar goodness to the world, whereas the the Branch
    Puller and the SFTP Server are back-ends used to place data on the
    Supermirror.

    <item>RCS importer, sucks the living CPU out of CVS and Subversion server
    out there to free source code from the centralized versioning oppression.
    It produces Bazaar branches from upstream repositories specified in
    Launchpad and stuff the Branch Warehouse with the resulting gigabytes of
    uninteresting historical details.
  </itemize>

  Finally, the Branch Syncher in an internal system that scans branches
  stored in the Warehouse and stores summary historical information into the
  Launchpad database.

  <subsection|Supermirror?>

  The Supermirror is the historic name for the the subsystem now implemented
  by the Branch Puller, the SFTP Server, the Branch Warehouse, and the Branch
  Publisher. The original Arch Supermirror was independent from Launchpad,
  while the Bazaar Supermirror is deeply integrated with Launchpad.

  In the rest of this document, as in casual conversation, the term
  ``Supermirror'' is used interchangeably to denote the whole subsystem or
  just the Branch Warehouse, its central component.

  Although the Supermirror name is familiar to some people and useful as an
  internal project name, public communication should favor terms like
  ``Launchpad branches'' rather than ``Supermirror'', in the same way that
  ``Launchpad bug tracker'' is used in preference to ``Malone''.

  <subsection|Bazaar Hosts>

  There are currently three public servers whose name is <verbatim|bazaar>.

  <\description-dash>
    <item*|bazaar.canonical.com>The Wiki of the Bazaar revision control
    system. This is the place of the Bazaar development community and is not
    related to Launchpad.

    <item*|bazaar.ubuntu.com>The host the Arch RCS Importer historically used
    to publish branches, those branches were automatically registered on the
    Arch Supermirror.

    <item*|bazaar.launchpad.net>The host providing the Branch Publisher and
    the SFTP Server for <verbatim|bzr>.
  </description-dash>

  I am confident that our team will find a use for a <verbatim|bazaar> host
  in all the other domains that Canonical will use in the future. This
  document is mainly interested in <verbatim|bazaar.launchpad.net>, but
  <verbatim|bazaar.ubuntu.com> is also mentioned for historical reasons in
  the RCS Importer section.

  <new-page*><section|Break up by Service>

  The scary diagram at the beginning is actually the superimposition of
  diagrams for several nearly independent services. Before examining
  individual components and their relations, we will have a quick tour of
  each service.

  <subsection|Pull Branch Mirroring>

  One of the services is the mirroring of remote branches. Remote branches
  registered in Launchpad are pulled into the Supermirror and published on
  <verbatim|bazaar.launchpad.net>.<no-page-break>

  <big-figure|<postscript|pull-branch.png|*5/8|*5/8||||>|Pull branch
  mirroring>

  Pull branches are periodically updated in the Warehouse by the Branch
  Puller. The Branch Publisher serves the Warehouse data to Bazaar clients
  that want to use the Supermirror rather than accessing the master branch.

  For example, the <verbatim|bzr> mainline is hosted on
  <verbatim|http://bazaar-ng.org/bzr/bzr.dev/>, this is the branch URL. It is
  registered in Launchpad as <verbatim|/people/mbp/+branch/bzr/dev>, this is
  the Launchpad Branch page. It is published as
  <verbatim|http://bazaar.launchpad.nate/~mbp/bzr/dev>, this is the Launchpad
  mirror (or Supermirror) URL.

  <subsection|Push Branch Hosting>

  Launchpad provides a hosting service for Bazaar branches. A Bazaar user
  wishing to publish a branch, but unable use a personal web space, can push
  the branch on <verbatim|bazaar.launchpad.net> using the SFTP
  transport.<no-page-break>

  <big-figure|<postscript|push-branch.png|*5/8|*5/8||||>|Push branch hosting>

  The SFTP server writes to a private filesystem. The Branch Puller is used
  to copy branches from the private SFTP area to the Branch Warehouse,
  ensuring that only usable Bazaar branch data gets published.<no-page-break>

  Once it is stored in the Warehouse, the branch is published in the same way
  as for pull branches.

  <subsection|RCS Imports>

  The famous RCS import service produces publicly accessible Bazaar branches
  from the source code history stored in remote CVS or Subversion
  servers.<no-page-break>

  <big-figure|<postscript|rcs-import.png|*5/8|*5/8||||>|RCS import>

  A bit earlier, I told you not to worry about the dotted line. Now is the
  moment of truth where its meaning will be uncovered. The RCS import
  branches must be published on the Branch Warehouse so they will be
  accessible to the Branch Syncher, and served on the same host as the other
  branches on the Supermirror. But the way the import branches will be copied
  to the Warehouse is still undecided at the moment.

  <subsection|Branch Scanning>

  The last service in the system, at the moment at least, is the Branch
  Syncher. It updates the Launchpad database record of the ancestry of all
  branches present in the Branch Warehouse.<no-page-break>

  <big-figure|<postscript|branch-scan.png|*5/8|*5/8||||>|Branch scanning>

  <no-page-break*>The ancestry record in Launchpad is currently only used to
  display the most recent revisions on each branch. But many future features
  will use this data as well. For example measuring the activity of branches,
  grouping branches, marking merged branches, etc.\ 

  <new-page*><section|Break up by Component>

  At this point, you should have a reasonable feeling of how the various
  components relate to one another. So we can start with the really technical
  stuff.

  <subsection|Branch Publisher>

  The Branch Publisher is the web server on <verbatim|bazaar.launchpad.net>.
  It only provides Bazaar branches for use by <verbatim|bzr>, and no resource
  meant for direct human consumption.

  <big-figure|<postscript|branch-publisher.png|*5/8|*5/8||||>|Branch
  Publisher>

  The Branch Publisher has no knowledge of the Bazaar branch format, it is a
  dumb HTTP server. Each published branch is associated with a Branch object
  in the Launchpad database. Branches are served as
  <verbatim|http://bazaar.launchpad.net/~owner/product/branch>.

  <\itemize>
    <item><verbatim|owner> is the string <verbatim|branch.owner.name>.<no-page-break>

    <item><verbatim|product> is the string <verbatim|branch.product.name>, or
    <verbatim|"+junk"> if the branch is not associated with a
    Product.<no-page-break>

    <item><verbatim|branch> is the string <verbatim|branch.name>.
  </itemize>

  The URL where a branch is served changes when any of those values change:
  because the branch, product or owner's name attribute changes, or a branch
  gets associated with a different owner or product.

  The Supermirror filesystem hierarchy was designed to be indifferent to
  those renamings. Branches in the Warehouse are stored by database id.
  Specifically, if a branch's id is <verbatim|0x89ABCDEF>, the branch is a
  directory whose path is of the form <verbatim|$base/89/ab/cd/ef>.

  The mapping between filesystem names and URL is done by a
  <verbatim|mod_rewrite> rule which is periodically updated from the
  Launchpad branch data.

  <paragraph|Relation:>Branch Publisher serves branches stored in the Branch
  Warehouse.

  <paragraph|Relation:>Branch Publisher reads Launchpad Branch details to
  rewrites public URLs requested by Bazaar clients into Warehouse filesystem
  names. Only branches with an associated Branch database record are
  published.

  <paragraph|Constraint:>The public name of branches can change at any time.

  <paragraph|Constraint:>The Supermirror filesystem hierarchy should be
  encapsulated. Launchpad branch ids must not be exposed to the
  user.<no-page-break>

  <paragraph|Constraint:>Branches stored in the Warehouse must be valid at
  all times. The only legal way to modify branch data in the Warehouse is
  using <verbatim|bzr push>.

  <subsection|SFTP Server>

  The SFTP Server allows Launchpad users to host their branches on Launchpad.
  It is a custom SFTP server based on Twisted.

  <big-figure|<postscript|sftp-server.png|*5/8|*5/8||||>|SFTP Server>

  A user can log in using an SSH key whose public key is registered in
  Launchpad. Only paths of the form <verbatim|~owner/product/branch> (as for
  the Branch Publisher) can be used, where <verbatim|owner> identifies the
  user whose SSH keys are used for authentication. If <verbatim|owner> is a
  team, the SSH keys of all members of the team can be used.

  <paragraph|Relation:>SFTP Server asks Launchpad for team members and SSH
  public keys or users.

  The SFTP server writes to a private filesystem that uses the same layout as
  the Supermirror. The mapping from the virtual filesystem exposed by SFTP
  and the actual filesystem layout is performed during authentication. That
  makes the SFTP server robust against branch renames occurring concurrently
  to an SFTP session.

  <paragraph|Relation:>SFTP Server asks Launchpad for name, id and product
  name of branches owned by a person and the teams it belongs to.

  Existing branches with a non-<verbatim|NULL> URLs are pull branches. Their
  associated directories are inaccessible on the SFTP server. Branches with a
  <verbatim|NULL> URL are push branches and are associated with writable
  directories. When a user tries to create a non-existent branch
  <verbatim|~owner/product/branch>, and <verbatim|owner> is the authenticated
  user or a team it belongs to, and the named product exists (or is
  <verbatim|+junk>), a branch is automatically created in the Launchpad
  database with the given owner, product and name and with no title or
  description.

  <paragraph|Relation:>SFTP creates Branch records in Launchpad.

  If a user tries to create a branch in a product that does not exist,
  <verbatim|bzr> will fail when trying to create a branch in a directory that
  does not exist.<no-page-break>

  <paragraph|Note.>The SFTP Server is an untrusted world-facing system, it
  does not access the Launchpad database directly but goes through the
  AuthServer. In the future, the AuthServer will be renamed to reflect its
  role as an all-purposes internal XMLRPC server.

  <subsection|Branch Puller>

  <big-figure|<postscript|branch-puller.png|*5/8|*5/8||||>|Branch Puller>

  <subsubsection|Branch Puller and Launchpad>

  The Branch Puller is the component that writes to the Branch Warehouse. It
  processes two kinds of branches:

  <\itemize>
    <item>Remote branches, from untrusted public servers on the internet,
    using URLs registered in the Launchpad database.

    <item>SFTP branches, on the filesystem of the SFTP server, using the id
    of Launchpad branches without a URL.
  </itemize>

  <paragraph|Relation:>Branch Puller asks Launchpad for Branch ids and URLs.

  <paragraph|Relation:>Branch Puller pulls <verbatim|bzr> branches from the
  private SFTP Server filesystem and from public web spaces on the internet.

  At the time of writing (2005-01-31), the Branch Puller gets the list of
  branches to pull from the private Launchpad page
  <verbatim|/supermirror-pull-list.txt>, formatted as a list of branch ids
  and URLs.

  <subsubsection|Branch Puller and Branch Warehouse>

  The Branch Puller writes directly to the id-based Branch Warehouse
  filesystem.<no-page-break>

  It uses <verbatim|bzr get> to create new branches in the Warehouse and
  <verbatim|bzr pull --overwrite> to update existing branches. The use of
  <verbatim|bzr> to copy the data ensures that only Bazaar branches that are
  well-formed enough to be checked out are published. Warez swappers would
  need to use <verbatim|bzr> to be published, and blatantly corrupt branch
  data would not be published.<no-page-break>

  <paragraph|Relation:>Branch Puller writes sanitized branch data in the
  Branch Warehouse.

  <subsection|Branch Syncher>

  The Branch Syncher, also known as <verbatim|bzrsyncd> (the user running the
  script) and <verbatim|update-branches.py> (the name of script) updates the
  Launchpad tables that describe the summary history of branches published by
  the Supermirror. This metadata includes the revisions ids in the history of
  a branch, commit messages, committers, dates and ancestry
  relationships.<no-page-break>

  <big-figure|<postscript|branch-syncher.png|*5/8|*5/8||||>|Branch Syncher>

  <paragraph|Relation:>Branch Syncher asks Launchpad for a list of branches
  to scan.

  <paragraph|Relation:>Branch Syncher reads the revision-history and revision
  entries from published branches.

  The Branch Syncher does not access the Branch Warehouse directly. Instead
  it uses a special rewriting rule of the Branch Publisher that gives it
  access to branches by hexadecimal id but hides the details of the real
  filesystem layout.

  <paragraph|Relation:>Branch Syncher updates the Revision, RevisionNumber,
  RevisionParent and RevisionAuthor tables in the Launchpad database.

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
    communicates directly with potentially hostile web
    servers.<no-page-break>

    <item>The Branch Puller and Branch Syncher were developed and deployed by
    different individuals. Keeping them separate prevents crossing
    responsibility boundaries.
  </itemize>

  <subsection|RCS Importer>

  The RCS Importer creates and update Bazaar branches from the historical
  information available in third party version control systems. Currently,
  imports from CVS and Subversion are supported. It is also known as
  <verbatim|importd>, and uses Buildbot and CSCVS.<no-page-break>

  <big-figure|<postscript|rcs-importer.png|*5/8|*5/8||||>|RCS Importer>

  This is the oldest component of the system, and predates Launchpad itself.
  It is still importing into <verbatim|baz> branches and the transition to
  <verbatim|bzr> is in progress. Over time, it has accumulated many design
  and implementation problems that prevent delivering a good quality of
  service and make maintenance painful.

  <paragraph|Relation:>RCS Importer asks Launchpad for RCS to import from and
  branches to import into.

  <paragraph|Relation:>RCS Importer gets and updates import status in
  Launchpad.

  <paragraph|Relation:>RCS Importer retrieves version control history from
  remote repositories.

  <paragraph|Relation:>RCS Importer publishes imported branches on the
  Supermirror.

  <paragraph|Relation:>RCS Importer retrieves published branches from the
  Supermirror for rollback. Importd rollback is explained later.

  Historically, the role of the Branch Syncher was performed in the RCS
  Importer, by a component called Taxi. When the Launchpad database schema
  was updated to model Bazaar branch instead of Arch branches, Taxi was
  removed.

  RCS import is a very expensive and time consuming task that is bound on
  network, CPU and disk I/O at different times.

  <\itemize>
    <item>It is network bound when checking out trees from remote RCS
    repositories, retrieving historical data from remote servers and
    publishing imports.<no-page-break>

    <item>It is CPU bound when synthesizing changesets from CVS log and when
    committing revisions.

    <item><no-page-break*>It is I/O bound when comitting revisions.
  </itemize>

  The initial import of a branch can take up to several days if the source
  tree is large, the history is long, or the remote server is slow. These
  issues also tend to come in groups: projects with a large source tree often
  have a long history and an overloaded server, leading to initial imports
  taking up to several weeks.

  <subsubsection|Buildbot, Importd, and CSCVS>

  The components of the RCS Importer are Buildbot, Importd, and CSCVS.

  Buildbot is used as an infrastructure for Importd. It implements a
  master/slave architecture where a single master process (run on macquarie)
  sends tasks to several slave systems. Its roles are:

  <\itemize>
    <item>Control conversion tasks, and automatically run periodic
    conversions.

    <item>Spread tasks on multiple slave systems.

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
    <item>Create initial Bazaar branches recording all the history of an
    upstream RCS.

    <item>Update import branches for new commits in the upstream RCS.

    <item>Check that imported source is consistent with source stored in the
    upstream RCS.
  </itemize>

  <subsubsection|ProductSeries and Branches>

  The upstream RCS details required for an import are stored in the
  ProductSeries table. This table also stores details about the status of an
  import.<no-page-break>

  <paragraph|Arch legacy:>The ProductSeries targetarchsomething fields are
  used to record the Arch name of the import branch.

  When an the initial import of a RCS has succeeded and the branch is
  published, a corresponding Branch record must be created and linked from
  the branch field of the ProductSeries.

  <paragraph|Opinion:>David Allouche thinks the coupling of RCS imports with
  ProductSeries is unecessary. Most of the time, users that want to get a RCS
  import do not care about ProductSeries and their baggage. Instead, RCS
  import details should be recorded in a separate table, and it should be
  possible associate a Branch and ProductSeries manually. This would require
  a specification.

  <subsubsection|Import Status>

  RCS imports have historically followed a workflow recorded by the
  <verbatim|importstatus> field and a number of timestamps in the
  ProductSeries table. The state machine of <verbatim|importstatus> is
  documented on <hlink|SourceSourceRefactoring|https://wiki.launchpad.canonical.com/SourceSourceRefactoring>.

  <big-figure|<postscript|importstatus.png|*5/8|*5/8||||>|ProductSeries.importstatus>

  Roomba and Hoover are two Importd instances, they are covered in depth in
  the following sections.

  The critical transition is the <em|manual review> between
  <verbatim|AUTOTESTED> and <verbatim|PROCESSING>. This manual review is
  needed for a few reasons:

  <\itemize>
    <item>As policy, the RCS import service is only provided for products for
    which a reasonably good product description was created. It is the
    reponsibility of the Launchpad administrator to communicate with the user
    to get a better description if needed and mark the product as reviewed.

    <item>To perform an import that can published, we need to allocate a Arch
    namespace. To help keep the namespace used for imports vaguely organised,
    and prevent conflicts, namespace allocation was done by Buttsource
    administrators.
  </itemize>

  <paragraph|Arch legacy:>The second point is no longer relevant with Bazaar,
  misnamed branches with useless data can be published, renamed, and removed
  without problem.

  <subsubsection|Roomba and Hoover>

  <em|Roomba> and <em|Hoover> are two Importd instances that use separate
  slave systems. That separation was required so large numbers of lengthy
  test imports could be run without blocking daily updates of syncing
  imports. Buildbot scheduling is not flexible enough to meet this goal with
  a single instance.

  <paragraph|Arch legacy:>This separation was useful for privilege
  separation: the Roomba slaves do not (should not?) have the SFTP key to
  publish branches or the privileges for Taxi to write revision information
  to the database. The only information coming out of test imports is status
  changes in ProductSeries effected by the Buildbot master. That helped
  guarantee that no branch would leak out before being validated by a
  Buttsource administrator.

  <big-figure|<postscript|importd-deployment.png|*5/8|*5/8||||>|Importd
  deployment>

  The elements in gray in the Importd deployment diagram represent the way
  branches were historically published: they were uploaded to
  <verbatim|bazaar.ubuntu.com>, where the Arch Supermirror automatically
  registered and published them.

  Communication with the Launchpad database is not represented on this
  diagram. Only macquarie, galapagos and neumayer access the database.
  Macquarie so the Botmasters can load jobs and update import status in
  ProductSeries. Galapagos and Neumayer so Taxi could create Branch and
  Revision records.

  The Roomba and Hoover botmaster each expose a web user interface to monitor
  import progress, examine past logs, initiate manual builds, and reload the
  job list.

  <subsubsection|Import Validation>

  Before publishing an imported branch, the source contents of the latest
  imported revision are compared to the source retrieved from the Upstream
  RCS at the start of the import. Deviations in the imported history are
  tolerated as it is impossible to retrieve past full tree revision from CVS
  in the general case.<no-page-break>

  <paragraph|Open issue:>Better sanity checking could be performed. On CVS,
  comparison of annotated source could be reliably implemented. On Subversion
  it is generally possible to retrieve past full tree revisions.

  <subsubsection|Import Workflow>

  The workflow of an import starts by a user setting up RCS details in
  Launchpad, and ends by the registration and publication of the import
  branch. The following diagram illustrates the simplest set of interactions
  in that workflow, in the case where no failure occurs.<no-page-break>

  <big-figure|<postscript|import-workflow.png|*5/8|*5/8||||>|Import workflow>

  First the User sets up RCS details in Launchpad. That sets the
  <verbatim|importstatus> of the ProductSeries to <verbatim|TESTING>. Then
  nothing happens until Roomba is ``reloaded''.

  The operator must ``reload'' Roomba by posting a form in the Buildbot web
  UI. This will update the job list from the database. Only ProductSeries
  that are <verbatim|TESTING> or <verbatim|TESTFAILED> create Roomba jobs.
  Jobs in <verbatim|TESTING> state are started automatically shortly after
  reloading. When the Roomba job succeeds, the ProductSeries is set to
  <verbatim|AUTOTESTED> and awaits human review.

  <paragraph|Arch legacy:>If a ProductSeries does not specify the
  <verbatim|targetarchsomething> fields, the Arch branch name is
  automatically generated. The automatic branch name generation sometimes
  produces invalid names, causing autotest jobs to never succeed unless
  debugged, but that will no longer a problem with Bazaar.

  The operator must also periodically review ProductSeries that have passed
  autotest. Launchpad provides a user interface at
  <verbatim|https://launchpad.net/bazaar/series> to easily view all the
  ProductSeries with a given <verbatim|importstatus> value. After a number of
  clicks, the occasional editorial work, sometimes chatting with the User to
  ask for clarifications or improvements in the product description, the
  Product is marked as ``reviewed'' in the <verbatim|$product/+review> form
  and the ProductSeries is set to <verbatim|PROCESSING> in the
  <verbatim|$series/+sourceadmin> form.

  <paragraph|Arch legacy:>This review step was the point where a Buttsource
  administrator was required to attribute Canonical branch name to the import
  branch.

  Then the operator must ~reload Hoover to create the job for the newly
  approved import. When the initial import completes, the
  <verbatim|importstatus> is set to <verbatim|SYNCING> and an entirely
  distasteful hack is used to update the job in place without having to wait
  for a manual reload, and to immediately start the initial sync job. At the
  end of the sync job, the Branch record is created in Launchpad and the
  import branch is published.

  <paragraph|Arch legacy:>The initial import starts from scratch, so a branch
  had to be fully imported twice before being published: once in Roomba and
  once on Hoover. That was necessary with Arch since the branch name
  generally changed during the review step.

  That could obviously use some streamlining, and I have not even mentioned
  the work required when one of the jobs fails.

  <paragraph|Open issue:>A Launchpag bug exists related to the support of the
  <verbatim|importstatus> workflow in the Launchpad user interface:
  <hlink|bug 378|https://launchpad.net/products/launchpad/+bug/378>. It was
  partially and incorrectly implemented: it is currently entirely impossible
  (even for a Buttsource member) to update the RCS import details for a
  ProductSeries whose status is <verbatim|SYNCING>. However it is possible to
  update those details by direct database manipulation as the
  <verbatim|importd> user.

  <subsubsection|Importd Rollback>

  When an import fails (and many of them fail, eventually), the Upstream RCS
  checkout and the partially converted branch are left in place to allow
  diagnosing the failure.

  Some conversion errors are detected only after committing an incorrect
  revision: for example a later revision attempts to patch an non-existing
  file, or the error is is only detected at validation time. After CSCVS is
  fixed to correct the error, Importd needs to ``rollback'': revert the
  branch to a previous known-good state. There are three different cases of
  rollback:

  <\description-long>
    <item*|Import>An import starts from scratch, the branch where the
    conversion will be published must not exist yet.

    <item*|Sync>A sync starts from the currently published branch. The branch
    must already be published.

    <item*|Initial sync>Since branches are published on sync, the initial
    sync cannot rollback. Instead, it will update the branch produced by the
    import step. The initial sync is not allowed to fail, if it does, the
    <verbatim|importstatus> must be manually reverted to
    <verbatim|PROCESSING> and the import must be restarted.
  </description-long>

  <paragraph|Open issue:>An import branch is only published after the initial
  sync. If the initial sync fails, the subsequent sync has no published
  branch data to rollback to, and all subsequent syncs will fail, or worse,
  the branch will eventually be published with known bad data. Branch should
  be published after Import.

  <subsubsection|Persistent CSCVS Data>

  Running a CSCVS sync on a system without local data involves a few steps:

  <\itemize>
    <item>Get a copy of the target Bazaar branch from the publication site.

    <item>Checkout the Upstream RCS branch.

    <item>Build the CSCVS cache. That is the part where CSCVS does dark magic
    to conjure changesets out of a CVS log.

    <item>Commit the missing changesets to the Bazaar branch.

    <item>Validate the import by comparing the final Bazaar branch to the
    Upstream RCS checkout.
  </itemize>

  The Upstream RCS checkout and, in particular, the CSCVS cache build are
  expensive tasks whose cost is independent of the amount of new changes, but
  dependent on the tree size and history size. They are optimized by updating
  the Upstream RCS checkout (for example with <verbatim|cvs up>) and the
  cache (with the appropriate <verbatim|cscvs> invocation) when they are
  available.

  <subsubsection|The Split Changeset Bug>

  Preserving the CSCVS cache is not just an optimisation, it is also required
  to work around a CSCVS bug.

  CSCVS identifies CVS changesets with a sequential id and creates them by
  grouping related commits from the same user, with the same message, and
  occuring within a short time period. When a sync occurs concurrently to a
  group of related CVS commits, the part of the commit group that is
  completed at the time of the sync is interpreted as a changeset, and the
  rest of group is interpreted as a separate changeset on the next sync. I
  will call this situation a ``split changeset''.

  If the cache is generated from scratch at a later date, the changeset is
  properly grouped in the cache. But since the split changeset was imported
  in two commits by the previous syncs, all subsequent changesets do not have
  matching ids in the branch and in the cache. If there was one split commit,
  the first new changeset to import has, in the cache, the id of the last
  committed changeset in the branch, so the first new changeset is not
  imported.

  In principle it should be possible to ignore recent commits that may be
  grouped with future commits, but David Allouche looked at the problem in
  the past and was unable to understand how changesets where generated.

  Regardless, it is almost certain that several import branches now contain
  such split changesets. So being able to delete the CSCVS cache would
  require a way to deal with existing split changesets, just preventing the
  creation of new ones would not be sufficient.

  Publishing split changesets is not a big problem in itself, so this fixing
  this bug needs not be a high priority.

  <subsubsection|The Renaming Bug>

  Importd spreads jobs on slaves by hashing the job name, which is of the
  form <verbatim|[<with|font-shape|italic|project>-]<with|font-shape|italic|product>-<with|font-shape|italic|series>>.
  Since projects, products and series can be renamed, and their associations
  can change, the slave assigned to a RCS import job can change.

  Because of the Split Changest Bug, we need to transport the CSCVS cache
  when migrating a job between slaves. Since we do not know what was the
  previous name of a job, we do not know which slave to download and remove
  this data from. In the current situation, supporting job migration would
  require maintaining a central repository of CSCVS caches and updating it
  with <verbatim|rsync> after each import or sync. Ensuring Arch namespace
  consistency would also have required the local master archive to be
  migrated. This functionality is not implemented, therefore job migration
  requires careful manual operation.

  Since job migration would currently require manual operation some
  ``undocumented features'' in Importd, related to Arch archive registration,
  have not been fixed since they effectively provide early failure in the
  cases where a manual job migration needs to be done.

  <no-page-break*>This the reason why renaming or reassociating ProductSeries
  associated with a RCS import are strongly discouraged. They generally break
  the RCS import.

  <subsection|RCS Importer Transition to Bazaar>

  <\with|color|dark red>
    <paragraph|Todo:>Document tools that have been implemented for the bzr
    transition so far.
  </with>

  <new-page*><section|Future Plans and Open Issues>

  <subsection|Branch Puller's Future>

  <paragraph|Open issue:>The Bazaar branch data on remote branches and on the
  SFTP server can be altered in essentially arbitrary ways. A branch can be
  replaced by a completely unrelated branch. More practically, branches can
  be altered to remove ``Nuclear Launch Codes'', ``Nuclear Waste'' and
  garbage revisions that are not part of the branch's ancestry. However,
  although <verbatim|bzr pull --overwrite> treats the revision-history as
  rewritable, it treats the store as append only. The Branch Puller would
  need explicit support to allow users to remove Nuclear Launch Codes and
  Nuclear Waste from their branch on the Supermirror.

  <subsubsection|Future Plan: Launchpad Reporting>

  The Branch Puller should be able to store reporting information in
  Launchpad. The information that would be useful to store include:

  <\itemize>
    <item>Date of latest successful pull.

    <item>Date of latest pull attempt.

    <item>Success status of the latest pull attempt.

    <item>Diagnostic data for the latest pull attempt if it was a failure. In
    the simplest case, that could be a simple Python backtrace.
  </itemize>

  Internal system failures, like failed communication with Launchpad, may be
  reported to the <verbatim|launchpad-error-reports> mailing list and not
  recorded in the database.

  Normal pull failures should also be reported to the mailing list to allow
  fast response to users. That would allow James Blackwell to notice that an
  interesting new branch is failing and to contact the branch owner directly
  to fix the problem.

  Steve Alexander suggests that pull failures and internal system failures be
  reported using the OOPS system.

  This error reporting is mentioned as the <verbatim|branchPulled> XMLRPC
  call in <hlink|SupermirrorXmlRpc|https://wiki.launchpad.canonical.com/SupermirrorXmlRpc>
  and <hlink|BranchXmlRpc|https://wiki.launchpad.canonical.com/BranchXmlRpc>,
  and as an open issue on <hlink|BazaarTaskList|https://wiki.launchpad.canonical.com/BazaarTaskList>.

  <paragraph|Relation:>Branch Pullers stores status reports in Launchpad.

  <subsubsection|Future Plan: Ignore Expected Failures>

  In normal usage, some branches are not worth trying to pull. Mainly,
  restricted branches like those stored on
  <verbatim|sftp://chinstrap.ubuntu.com/>, but also blatantly incorrect
  branches, like those pointing to a Subversion repository.

  Those branches are characterized by pull attempts that are never
  successful. The details of how the successive failures are counted, and how
  they affect pull frequency, are still a bit uncertain. Eventually, a branch
  that is never successfully pulled will no longer be attempted. Otherwise
  error reports would quickly be drowned in expected failures.

  <no-page-break*>This is mentioned as an open issue on
  <hlink|BazaarTaskList|https://wiki.launchpad.canonical.com/BazaarTaskList>.

  <subsubsection|Future Plan: Pull Now>

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

  <subsubsection|Future Plan: Concurrent Tasks>

  Pulling a branch is a network-bound task that can take a long time. It can
  also be CPU intensive in some cases.

  To allow pull-now requests to be handled quickly, it would be necessary to
  implement the Branch Puller as a service, as opposed to a <verbatim|cron>
  job, which would be able to schedule tasks in a flexible way. Long running
  tasks should not prevent new tasks from running.

  <no-page-break*>This needs to be taken in account in the design of
  <hlink|Buildd-NG|https://wiki.launchpad.canonical.com/ImportdRefactoring>.

  <subsection|Branch Syncher's Future>

  <subsubsection|Future Plan: Launchpad Reporting>

  The date of the latest successful synch should be displayed in the
  Launchpad UI to explain that the displayed branch details might be out of
  date.

  <subsubsection|Future plan: Sync Now>

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

  <subsubsection|Future Plan: Concurrent Tasks>

  The Branch Syncher needs to traverse the complete ancestry of branches so
  old revisions can be created in the database in response to ghost filling
  in a Supermirror branch. This process is database-bound and can take a
  significant amount of time (probably several tens of minutes for very large
  branches).

  To allow sync-now requests to be handled quickly, it would be necessary to
  implement the Branch Syncher as a service with flexible scheduling
  abilities. Long running tasks should not prevent new tasks from running.

  This needs to be taken in account in the design of
  <hlink|Buildd-NG|https://wiki.launchpad.canonical.com/ImportdRefactoring>.

  <subsection|RCS Importer's Future>

  <\with|color|dark red>
    <paragraph|Todo:>Flesh out this section.
  </with>

  <paragraph|Open issue:>Number of sync failures.

  <paragraph|Open issue:>Failure triage.

  <paragraph|Open issue:>Workflow of new imports, removing review step?

  <paragraph|Open issue:>Restarting imports.
</body>

<\initial>
  <\collection>
    <associate|info-flag|short>
    <associate|language|british>
    <associate|page-medium|paper>
    <associate|par-mode|left>
    <associate|sfactor|7>
  </collection>
</initial>

<\references>
  <\collection>
    <associate|auto-1|<tuple|1|1>>
    <associate|auto-10|<tuple|3|3>>
    <associate|auto-11|<tuple|2.3|4>>
    <associate|auto-12|<tuple|4|4>>
    <associate|auto-13|<tuple|2.4|4>>
    <associate|auto-14|<tuple|5|4>>
    <associate|auto-15|<tuple|3|5>>
    <associate|auto-16|<tuple|3.1|5>>
    <associate|auto-17|<tuple|6|5>>
    <associate|auto-18|<tuple|1|5>>
    <associate|auto-19|<tuple|2|6>>
    <associate|auto-2|<tuple|1.1|1>>
    <associate|auto-20|<tuple|3|6>>
    <associate|auto-21|<tuple|4|6>>
    <associate|auto-22|<tuple|5|6>>
    <associate|auto-23|<tuple|3.2|6>>
    <associate|auto-24|<tuple|7|6>>
    <associate|auto-25|<tuple|6|6>>
    <associate|auto-26|<tuple|7|6>>
    <associate|auto-27|<tuple|8|6>>
    <associate|auto-28|<tuple|9|7>>
    <associate|auto-29|<tuple|3.3|7>>
    <associate|auto-3|<tuple|1|1>>
    <associate|auto-30|<tuple|8|7>>
    <associate|auto-31|<tuple|3.3.1|7>>
    <associate|auto-32|<tuple|3.3.1.1|7>>
    <associate|auto-33|<tuple|3.3.1.2|7>>
    <associate|auto-34|<tuple|3.3.2|7>>
    <associate|auto-35|<tuple|3.3.2.1|8>>
    <associate|auto-36|<tuple|3.4|8>>
    <associate|auto-37|<tuple|9|8>>
    <associate|auto-38|<tuple|3.4.0.2|8>>
    <associate|auto-39|<tuple|3.4.0.3|8>>
    <associate|auto-4|<tuple|1.2|2>>
    <associate|auto-40|<tuple|3.4.0.4|8>>
    <associate|auto-41|<tuple|3.5|9>>
    <associate|auto-42|<tuple|10|9>>
    <associate|auto-43|<tuple|3.5.0.5|9>>
    <associate|auto-44|<tuple|3.5.0.6|9>>
    <associate|auto-45|<tuple|3.5.0.7|9>>
    <associate|auto-46|<tuple|3.5.0.8|9>>
    <associate|auto-47|<tuple|3.5.0.9|9>>
    <associate|auto-48|<tuple|3.5.1|10>>
    <associate|auto-49|<tuple|3.5.2|10>>
    <associate|auto-5|<tuple|1.3|2>>
    <associate|auto-50|<tuple|3.5.2.1|10>>
    <associate|auto-51|<tuple|3.5.2.2|11>>
    <associate|auto-52|<tuple|3.5.3|11>>
    <associate|auto-53|<tuple|11|11>>
    <associate|auto-54|<tuple|3.5.3.1|11>>
    <associate|auto-55|<tuple|3.5.4|12>>
    <associate|auto-56|<tuple|3.5.4.1|12>>
    <associate|auto-57|<tuple|12|12>>
    <associate|auto-58|<tuple|3.5.5|12>>
    <associate|auto-59|<tuple|3.5.5.1|12>>
    <associate|auto-6|<tuple|2|3>>
    <associate|auto-60|<tuple|3.5.6|13>>
    <associate|auto-61|<tuple|13|13>>
    <associate|auto-62|<tuple|3.5.6.1|13>>
    <associate|auto-63|<tuple|3.5.6.2|13>>
    <associate|auto-64|<tuple|3.5.6.3|14>>
    <associate|auto-65|<tuple|3.5.6.4|14>>
    <associate|auto-66|<tuple|3.5.7|14>>
    <associate|auto-67|<tuple|3.5.7.1|14>>
    <associate|auto-68|<tuple|3.5.8|14>>
    <associate|auto-69|<tuple|3.5.9|15>>
    <associate|auto-7|<tuple|2.1|3>>
    <associate|auto-70|<tuple|3.5.10|15>>
    <associate|auto-71|<tuple|3.6|15>>
    <associate|auto-72|<tuple|3.6.0.1|15>>
    <associate|auto-73|<tuple|4|16>>
    <associate|auto-74|<tuple|4.1|16>>
    <associate|auto-75|<tuple|4.1.0.2|16>>
    <associate|auto-76|<tuple|4.1.1|16>>
    <associate|auto-77|<tuple|4.1.1.1|16>>
    <associate|auto-78|<tuple|4.1.2|16>>
    <associate|auto-79|<tuple|4.1.3|17>>
    <associate|auto-8|<tuple|2|3>>
    <associate|auto-80|<tuple|4.1.4|17>>
    <associate|auto-81|<tuple|4.2|17>>
    <associate|auto-82|<tuple|4.2.1|17>>
    <associate|auto-83|<tuple|4.2.2|17>>
    <associate|auto-84|<tuple|4.2.3|18>>
    <associate|auto-85|<tuple|4.3|18>>
    <associate|auto-86|<tuple|4.3.0.1|18>>
    <associate|auto-87|<tuple|4.3.0.2|18>>
    <associate|auto-88|<tuple|4.3.0.3|18>>
    <associate|auto-89|<tuple|4.3.0.4|18>>
    <associate|auto-9|<tuple|2.2|3>>
    <associate|auto-90|<tuple|4.3.0.5|18>>
  </collection>
</references>

<\auxiliary>
  <\collection>
    <\associate|figure>
      <tuple|normal|Don't panic|<pageref|auto-3>>

      <tuple|normal|Pull branch mirroring|<pageref|auto-8>>

      <tuple|normal|Push branch hosting|<pageref|auto-10>>

      <tuple|normal|RCS import|<pageref|auto-12>>

      <tuple|normal|Branch scanning|<pageref|auto-14>>

      <tuple|normal|Branch Publisher|<pageref|auto-17>>

      <tuple|normal|SFTP Server|<pageref|auto-24>>

      <tuple|normal|Branch Puller|<pageref|auto-30>>

      <tuple|normal|Branch Syncher|<pageref|auto-37>>

      <tuple|normal|RCS Importer|<pageref|auto-42>>

      <tuple|normal|ProductSeries.importstatus|<pageref|auto-53>>

      <tuple|normal|Importd deployment|<pageref|auto-57>>

      <tuple|normal|Import workflow|<pageref|auto-61>>
    </associate>
    <\associate|toc>
      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|1<space|2spc>Bazaar
      Overview> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-1><vspace|0.5fn>

      <with|par-left|<quote|1.5fn>|1.1<space|2spc>The Big Picture
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-2>>

      <with|par-left|<quote|1.5fn>|1.2<space|2spc>Supermirror?
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-4>>

      <with|par-left|<quote|1.5fn>|1.3<space|2spc>Bazaar Hosts
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-5>>

      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|2<space|2spc>Break
      up by Service> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-6><vspace|0.5fn>

      <with|par-left|<quote|1.5fn>|2.1<space|2spc>Pull Branch Mirroring
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-7>>

      <with|par-left|<quote|1.5fn>|2.2<space|2spc>Push Branch Hosting
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-9>>

      <with|par-left|<quote|1.5fn>|2.3<space|2spc>RCS Imports
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-11>>

      <with|par-left|<quote|1.5fn>|2.4<space|2spc>Branch Scanning
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-13>>

      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|3<space|2spc>Break
      up by Component> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-15><vspace|0.5fn>

      <with|par-left|<quote|1.5fn>|3.1<space|2spc>Branch Publisher
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-16>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-18><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-19><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Constraint:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-20><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Constraint:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-21><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Constraint:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-22><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|3.2<space|2spc>SFTP Server
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-23>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-25><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-26><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-27><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Note. <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-28><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|3.3<space|2spc>Branch Puller
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-29>>

      <with|par-left|<quote|3fn>|3.3.1<space|2spc>Branch Puller and Launchpad
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-31>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-32><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-33><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.3.2<space|2spc>Branch Puller and Branch
      Warehouse <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-34>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-35><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|3.4<space|2spc>Branch Syncher
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-36>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-38><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-39><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-40><vspace|0.15fn>>

      <with|par-left|<quote|1.5fn>|3.5<space|2spc>RCS Importer
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-41>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-43><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-44><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-45><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-46><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-47><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.5.1<space|2spc>Buildbot, Importd, and
      CSCVS <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-48>>

      <with|par-left|<quote|3fn>|3.5.2<space|2spc>ProductSeries and Branches
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-49>>

      <with|par-left|<quote|6fn>|Arch legacy:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-50><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Opinion:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-51><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.5.3<space|2spc>Import Status
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-52>>

      <with|par-left|<quote|6fn>|Arch legacy:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-54><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.5.4<space|2spc>Roomba and Hoover
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-55>>

      <with|par-left|<quote|6fn>|Arch legacy:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-56><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.5.5<space|2spc>Import Validation
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-58>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-59><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.5.6<space|2spc>Import Workflow
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-60>>

      <with|par-left|<quote|6fn>|Arch legacy:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-62><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Arch legacy:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-63><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Arch legacy:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-64><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-65><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.5.7<space|2spc>Importd Rollback
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-66>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-67><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|3.5.8<space|2spc>Persistent CSCVS Data
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-68>>

      <with|par-left|<quote|3fn>|3.5.9<space|2spc>The Split Changeset Bug
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-69>>

      <with|par-left|<quote|3fn>|3.5.10<space|2spc>The Renaming Bug
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-70>>

      <with|par-left|<quote|1.5fn>|3.6<space|2spc>RCS Importer Transition to
      Bazaar <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-71>>

      <with|par-left|<quote|6fn>|Todo: <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-72><vspace|0.15fn>>

      <vspace*|1fn><with|font-series|<quote|bold>|math-font-series|<quote|bold>|4<space|2spc>Future
      Plans and Open Issues> <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-73><vspace|0.5fn>

      <with|par-left|<quote|1.5fn>|4.1<space|2spc>Branch Puller's Future
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-74>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-75><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|4.1.1<space|2spc>Future Plan: Launchpad
      Reporting <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-76>>

      <with|par-left|<quote|6fn>|Relation:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-77><vspace|0.15fn>>

      <with|par-left|<quote|3fn>|4.1.2<space|2spc>Future Plan: Ignore
      Expected Failures <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-78>>

      <with|par-left|<quote|3fn>|4.1.3<space|2spc>Future Plan: Pull Now
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-79>>

      <with|par-left|<quote|3fn>|4.1.4<space|2spc>Future Plan: Concurrent
      Tasks <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-80>>

      <with|par-left|<quote|1.5fn>|4.2<space|2spc>Branch Syncher's Future
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-81>>

      <with|par-left|<quote|3fn>|4.2.1<space|2spc>Future Plan: Launchpad
      Reporting <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-82>>

      <with|par-left|<quote|3fn>|4.2.2<space|2spc>Future plan: Sync Now
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-83>>

      <with|par-left|<quote|3fn>|4.2.3<space|2spc>Future Plan: Concurrent
      Tasks <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-84>>

      <with|par-left|<quote|1.5fn>|4.3<space|2spc>RCS Importer's Future
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-85>>

      <with|par-left|<quote|6fn>|Todo: <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-86><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-87><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-88><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-89><vspace|0.15fn>>

      <with|par-left|<quote|6fn>|Open issue:
      <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-90><vspace|0.15fn>>
    </associate>
  </collection>
</auxiliary>