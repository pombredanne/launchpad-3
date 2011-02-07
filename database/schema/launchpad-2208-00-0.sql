-- Generated Tue Aug 17 10:52:11 2010 UTC

SET client_min_messages TO ERROR;


SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

CREATE TYPE pgstattuple_type AS (
	table_len bigint,
	tuple_count bigint,
	tuple_len bigint,
	tuple_percent double precision,
	dead_tuple_count bigint,
	dead_tuple_len bigint,
	dead_tuple_percent double precision,
	free_space bigint,
	free_percent double precision
);

SET default_tablespace = '';

SET default_with_oids = false;

CREATE TABLE revision (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    log_body text NOT NULL,
    revision_author integer NOT NULL,
    gpgkey integer,
    revision_id text NOT NULL,
    revision_date timestamp without time zone,
    karma_allocated boolean DEFAULT false
);
ALTER TABLE ONLY revision ALTER COLUMN revision_author SET STATISTICS 500;
ALTER TABLE ONLY revision ALTER COLUMN revision_date SET STATISTICS 500;

CREATE FUNCTION pgstattuple(text) RETURNS pgstattuple_type
    AS '$libdir/pgstattuple', 'pgstattuple'
    LANGUAGE c STRICT;

CREATE FUNCTION pgstattuple(oid) RETURNS pgstattuple_type
    AS '$libdir/pgstattuple', 'pgstattuplebyid'
    LANGUAGE c STRICT;

CREATE FUNCTION plpgsql_call_handler() RETURNS language_handler
    AS '$libdir/plpgsql', 'plpgsql_call_handler'
    LANGUAGE c;

CREATE FUNCTION plpython_call_handler() RETURNS language_handler
    AS '$libdir/plpython', 'plpython_call_handler'
    LANGUAGE c;

CREATE TABLE account (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    creation_rationale integer NOT NULL,
    status integer NOT NULL,
    date_status_set timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    displayname text NOT NULL,
    openid_identifier text DEFAULT generate_openid_identifier() NOT NULL,
    status_comment text,
    old_openid_identifier text
);

CREATE SEQUENCE account_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE account_id_seq OWNED BY account.id;

CREATE TABLE accountpassword (
    id integer NOT NULL,
    account integer NOT NULL,
    password text NOT NULL
);

CREATE SEQUENCE accountpassword_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE accountpassword_id_seq OWNED BY accountpassword.id;

CREATE VIEW alllocks AS
    SELECT a.procpid, a.usename, (now() - a.query_start) AS age, c.relname, l.mode, l.granted, a.current_query FROM ((pg_locks l JOIN pg_class c ON ((l.relation = c.oid))) LEFT JOIN pg_stat_activity a ON ((a.procpid = l.pid)));

CREATE TABLE announcement (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_announced timestamp without time zone,
    registrant integer NOT NULL,
    product integer,
    distribution integer,
    project integer,
    title text NOT NULL,
    summary text,
    url text,
    active boolean DEFAULT true NOT NULL,
    date_updated timestamp without time zone,
    CONSTRAINT has_target CHECK ((((product IS NOT NULL) OR (project IS NOT NULL)) OR (distribution IS NOT NULL))),
    CONSTRAINT valid_url CHECK (valid_absolute_url(url))
);

CREATE SEQUENCE announcement_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE announcement_id_seq OWNED BY announcement.id;

CREATE TABLE answercontact (
    id integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer,
    person integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_target CHECK ((((product IS NULL) <> (distribution IS NULL)) AND ((product IS NULL) OR (sourcepackagename IS NULL))))
);

CREATE SEQUENCE answercontact_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE answercontact_id_seq OWNED BY answercontact.id;

CREATE TABLE apportjob (
    id integer NOT NULL,
    job integer NOT NULL,
    blob integer NOT NULL,
    job_type integer NOT NULL,
    json_data text
);

CREATE SEQUENCE apportjob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE apportjob_id_seq OWNED BY apportjob.id;

CREATE TABLE archive (
    id integer NOT NULL,
    owner integer NOT NULL,
    description text,
    enabled boolean DEFAULT true NOT NULL,
    authorized_size integer,
    distribution integer NOT NULL,
    purpose integer NOT NULL,
    private boolean DEFAULT false NOT NULL,
    sources_cached integer,
    binaries_cached integer,
    package_description_cache text,
    fti ts2.tsvector,
    buildd_secret text,
    require_virtualized boolean DEFAULT true NOT NULL,
    name text DEFAULT 'default'::text NOT NULL,
    publish boolean DEFAULT true NOT NULL,
    date_updated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    total_count integer DEFAULT 0 NOT NULL,
    pending_count integer DEFAULT 0 NOT NULL,
    succeeded_count integer DEFAULT 0 NOT NULL,
    failed_count integer DEFAULT 0 NOT NULL,
    building_count integer DEFAULT 0 NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    signing_key integer,
    removed_binary_retention_days integer,
    num_old_versions_published integer,
    displayname text NOT NULL,
    relative_build_score integer DEFAULT 0 NOT NULL,
    external_dependencies text,
    status integer DEFAULT 0 NOT NULL,
    commercial boolean DEFAULT false NOT NULL,
    build_debug_symbols boolean DEFAULT false NOT NULL,
    CONSTRAINT valid_buildd_secret CHECK ((((private = true) AND (buildd_secret IS NOT NULL)) OR (private = false))),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE archive_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archive_id_seq OWNED BY archive.id;

CREATE TABLE archivearch (
    id integer NOT NULL,
    archive integer NOT NULL,
    processorfamily integer NOT NULL
);

CREATE SEQUENCE archivearch_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archivearch_id_seq OWNED BY archivearch.id;

CREATE TABLE archiveauthtoken (
    id integer NOT NULL,
    archive integer NOT NULL,
    person integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_deactivated timestamp without time zone,
    token text NOT NULL
);

CREATE SEQUENCE archiveauthtoken_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archiveauthtoken_id_seq OWNED BY archiveauthtoken.id;

CREATE TABLE archivedependency (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    archive integer NOT NULL,
    dependency integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    CONSTRAINT distinct_archives CHECK ((archive <> dependency))
);

CREATE SEQUENCE archivedependency_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archivedependency_id_seq OWNED BY archivedependency.id;

CREATE TABLE archivejob (
    id integer NOT NULL,
    job integer NOT NULL,
    archive integer NOT NULL,
    job_type integer NOT NULL,
    json_data text
);

CREATE SEQUENCE archivejob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archivejob_id_seq OWNED BY archivejob.id;

CREATE TABLE archivepermission (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    person integer NOT NULL,
    permission integer NOT NULL,
    archive integer NOT NULL,
    component integer,
    sourcepackagename integer,
    packageset integer,
    explicit boolean DEFAULT false NOT NULL,
    CONSTRAINT one_target CHECK ((null_count(ARRAY[packageset, component, sourcepackagename]) = 2))
);

CREATE SEQUENCE archivepermission_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archivepermission_id_seq OWNED BY archivepermission.id;

CREATE TABLE archivesubscriber (
    id integer NOT NULL,
    archive integer NOT NULL,
    registrant integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subscriber integer NOT NULL,
    date_expires timestamp without time zone,
    status integer NOT NULL,
    description text,
    date_cancelled timestamp without time zone,
    cancelled_by integer
);

CREATE SEQUENCE archivesubscriber_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archivesubscriber_id_seq OWNED BY archivesubscriber.id;

CREATE TABLE authtoken (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_consumed timestamp without time zone,
    token_type integer NOT NULL,
    token text NOT NULL,
    requester integer,
    requester_email text,
    email text NOT NULL,
    redirection_url text
);

CREATE SEQUENCE authtoken_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE authtoken_id_seq OWNED BY authtoken.id;

CREATE TABLE binarypackagename (
    id integer NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE TABLE sourcepackagename (
    id integer NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE VIEW binaryandsourcepackagenameview AS
    SELECT binarypackagename.name FROM binarypackagename UNION SELECT sourcepackagename.name FROM sourcepackagename;

CREATE TABLE binarypackagebuild (
    id integer NOT NULL,
    package_build integer NOT NULL,
    distro_arch_series integer NOT NULL,
    source_package_release integer NOT NULL
);

CREATE SEQUENCE binarypackagebuild_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagebuild_id_seq OWNED BY binarypackagebuild.id;

CREATE TABLE binarypackagefile (
    binarypackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval(('binarypackagefile_id_seq'::text)::regclass) NOT NULL
);

CREATE SEQUENCE binarypackagefile_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagefile_id_seq OWNED BY binarypackagefile.id;

CREATE TABLE binarypackagepublishinghistory (
    id integer NOT NULL,
    binarypackagerelease integer NOT NULL,
    distroarchseries integer NOT NULL,
    status integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer NOT NULL,
    datecreated timestamp without time zone NOT NULL,
    datepublished timestamp without time zone,
    datesuperseded timestamp without time zone,
    supersededby integer,
    datemadepending timestamp without time zone,
    scheduleddeletiondate timestamp without time zone,
    dateremoved timestamp without time zone,
    pocket integer DEFAULT 0 NOT NULL,
    archive integer NOT NULL,
    removed_by integer,
    removal_comment text
);

CREATE TABLE binarypackagerelease (
    id integer NOT NULL,
    binarypackagename integer NOT NULL,
    version text NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    build integer NOT NULL,
    binpackageformat integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer NOT NULL,
    shlibdeps text,
    depends text,
    recommends text,
    suggests text,
    conflicts text,
    replaces text,
    provides text,
    essential boolean NOT NULL,
    installedsize integer,
    architecturespecific boolean NOT NULL,
    fti ts2.tsvector,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    pre_depends text,
    enhances text,
    breaks text,
    debug_package integer,
    CONSTRAINT valid_version CHECK (valid_debian_version(version))
);

CREATE TABLE component (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE TABLE distroarchseries (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    processorfamily integer NOT NULL,
    architecturetag text NOT NULL,
    owner integer NOT NULL,
    official boolean NOT NULL,
    package_count integer DEFAULT 0 NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    supports_virtualized boolean DEFAULT false NOT NULL
);

CREATE TABLE distroseries (
    id integer NOT NULL,
    distribution integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    version text NOT NULL,
    releasestatus integer NOT NULL,
    datereleased timestamp without time zone,
    parent_series integer,
    owner integer NOT NULL,
    lucilleconfig text,
    summary text NOT NULL,
    displayname text NOT NULL,
    datelastlangpack timestamp without time zone,
    messagecount integer DEFAULT 0 NOT NULL,
    nominatedarchindep integer,
    changeslist text,
    binarycount integer DEFAULT 0 NOT NULL,
    sourcecount integer DEFAULT 0 NOT NULL,
    driver integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    hide_all_translations boolean DEFAULT true NOT NULL,
    defer_translation_imports boolean DEFAULT true NOT NULL,
    language_pack_base integer,
    language_pack_delta integer,
    language_pack_proposed integer,
    language_pack_full_export_requested boolean DEFAULT false NOT NULL,
    CONSTRAINT valid_language_pack_delta CHECK (((language_pack_base IS NOT NULL) OR (language_pack_delta IS NULL))),
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_version CHECK (sane_version(version))
);

CREATE TABLE libraryfilealias (
    id integer NOT NULL,
    content integer,
    filename text NOT NULL,
    mimetype text NOT NULL,
    expires timestamp without time zone,
    last_accessed timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    restricted boolean DEFAULT false NOT NULL,
    hits integer DEFAULT 0 NOT NULL,
    CONSTRAINT valid_filename CHECK ((filename !~~ '%/%'::text))
);

CREATE TABLE sourcepackagerelease (
    id integer NOT NULL,
    creator integer NOT NULL,
    version text NOT NULL,
    dateuploaded timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    urgency integer NOT NULL,
    dscsigningkey integer,
    component integer NOT NULL,
    changelog_entry text,
    builddepends text,
    builddependsindep text,
    architecturehintlist text NOT NULL,
    dsc text,
    section integer NOT NULL,
    maintainer integer NOT NULL,
    sourcepackagename integer NOT NULL,
    upload_distroseries integer NOT NULL,
    format integer NOT NULL,
    dsc_maintainer_rfc822 text,
    dsc_standards_version text,
    dsc_format text NOT NULL,
    dsc_binaries text,
    upload_archive integer,
    copyright text,
    build_conflicts text,
    build_conflicts_indep text,
    sourcepackage_recipe_build integer,
    changelog integer,
    CONSTRAINT valid_version CHECK (valid_debian_version(version))
);

CREATE VIEW binarypackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (securebinarypackagepublishinghistory.id)::text) AS id, distroseries.distribution, securebinarypackagepublishinghistory.id AS binarypackagepublishing, component.name AS componentname, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, binarypackagefile.libraryfile AS libraryfilealias, distroseries.name AS distroseriesname, distroarchseries.architecturetag, securebinarypackagepublishinghistory.status AS publishingstatus, securebinarypackagepublishinghistory.pocket, securebinarypackagepublishinghistory.archive FROM (((((((((binarypackagepublishinghistory securebinarypackagepublishinghistory JOIN binarypackagerelease ON ((securebinarypackagepublishinghistory.binarypackagerelease = binarypackagerelease.id))) JOIN binarypackagebuild ON ((binarypackagerelease.build = binarypackagebuild.id))) JOIN sourcepackagerelease ON ((binarypackagebuild.source_package_release = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN binarypackagefile ON ((binarypackagefile.binarypackagerelease = binarypackagerelease.id))) JOIN libraryfilealias ON ((binarypackagefile.libraryfile = libraryfilealias.id))) JOIN distroarchseries ON ((securebinarypackagepublishinghistory.distroarchseries = distroarchseries.id))) JOIN distroseries ON ((distroarchseries.distroseries = distroseries.id))) JOIN component ON ((securebinarypackagepublishinghistory.component = component.id))) WHERE (securebinarypackagepublishinghistory.dateremoved IS NULL);

CREATE SEQUENCE binarypackagename_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagename_id_seq OWNED BY binarypackagename.id;

CREATE SEQUENCE binarypackagepublishinghistory_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagepublishinghistory_id_seq OWNED BY binarypackagepublishinghistory.id;

CREATE SEQUENCE binarypackagerelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagerelease_id_seq OWNED BY binarypackagerelease.id;

CREATE TABLE binarypackagereleasedownloadcount (
    id integer NOT NULL,
    archive integer NOT NULL,
    binary_package_release integer NOT NULL,
    day date NOT NULL,
    country integer,
    count integer NOT NULL
);

CREATE SEQUENCE binarypackagereleasedownloadcount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagereleasedownloadcount_id_seq OWNED BY binarypackagereleasedownloadcount.id;

CREATE TABLE bounty (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    usdvalue numeric(10,2) NOT NULL,
    difficulty integer NOT NULL,
    reviewer integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    owner integer NOT NULL,
    deadline timestamp without time zone,
    claimant integer,
    dateclaimed timestamp without time zone,
    bountystatus integer DEFAULT 1 NOT NULL
);

CREATE SEQUENCE bounty_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bounty_id_seq OWNED BY bounty.id;

CREATE TABLE bountymessage (
    id integer NOT NULL,
    bounty integer NOT NULL,
    message integer NOT NULL
);

CREATE SEQUENCE bountymessage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bountymessage_id_seq OWNED BY bountymessage.id;

CREATE TABLE bountysubscription (
    id integer NOT NULL,
    bounty integer NOT NULL,
    person integer NOT NULL
);

CREATE SEQUENCE bountysubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bountysubscription_id_seq OWNED BY bountysubscription.id;

CREATE TABLE branch (
    id integer NOT NULL,
    title text,
    summary text,
    owner integer NOT NULL,
    product integer,
    author integer,
    name text NOT NULL,
    home_page text,
    url text,
    whiteboard text,
    lifecycle_status integer DEFAULT 1 NOT NULL,
    last_mirrored timestamp without time zone,
    last_mirror_attempt timestamp without time zone,
    mirror_failures integer DEFAULT 0 NOT NULL,
    mirror_status_message text,
    last_scanned timestamp without time zone,
    last_scanned_id text,
    last_mirrored_id text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    revision_count integer DEFAULT 0 NOT NULL,
    next_mirror_time timestamp without time zone,
    private boolean DEFAULT false NOT NULL,
    branch_type integer NOT NULL,
    reviewer integer,
    merge_robot integer,
    merge_control_status integer DEFAULT 1 NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    branch_format integer,
    repository_format integer,
    metadir_format integer,
    stacked_on integer,
    distroseries integer,
    sourcepackagename integer,
    owner_name text NOT NULL,
    target_suffix text,
    unique_name text,
    size_on_disk bigint,
    CONSTRAINT branch_merge_control CHECK (((merge_robot IS NULL) OR (merge_control_status = ANY (ARRAY[3, 4])))),
    CONSTRAINT branch_type_url_consistent CHECK (((((branch_type = 2) AND (url IS NOT NULL)) OR ((branch_type = ANY (ARRAY[1, 3])) AND (url IS NULL))) OR (branch_type = 4))),
    CONSTRAINT branch_url_no_trailing_slash CHECK ((url !~~ '%/'::text)),
    CONSTRAINT branch_url_not_supermirror CHECK ((url !~~ 'http://bazaar.launchpad.net/%'::text)),
    CONSTRAINT one_container CHECK ((((distroseries IS NULL) = (sourcepackagename IS NULL)) AND ((distroseries IS NULL) OR (product IS NULL)))),
    CONSTRAINT valid_home_page CHECK (valid_absolute_url(home_page)),
    CONSTRAINT valid_name CHECK (valid_branch_name(name)),
    CONSTRAINT valid_url CHECK (valid_absolute_url(url))
);

CREATE SEQUENCE branch_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branch_id_seq OWNED BY branch.id;

CREATE TABLE branchjob (
    id integer NOT NULL,
    job integer NOT NULL,
    branch integer,
    job_type integer NOT NULL,
    json_data text
);

CREATE SEQUENCE branchjob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchjob_id_seq OWNED BY branchjob.id;

CREATE TABLE branchmergeproposal (
    id integer NOT NULL,
    registrant integer NOT NULL,
    source_branch integer NOT NULL,
    target_branch integer NOT NULL,
    dependent_branch integer,
    whiteboard text,
    date_merged timestamp without time zone,
    merged_revno integer,
    merge_reporter integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    commit_message text,
    queue_position integer,
    queue_status integer DEFAULT 1 NOT NULL,
    date_review_requested timestamp without time zone,
    reviewer integer,
    date_reviewed timestamp without time zone,
    reviewed_revision_id text,
    queuer integer,
    date_queued timestamp without time zone,
    queued_revision_id text,
    merger integer,
    merged_revision_id text,
    date_merge_started timestamp without time zone,
    date_merge_finished timestamp without time zone,
    merge_log_file integer,
    superseded_by integer,
    root_message_id text,
    review_diff integer,
    merge_diff integer,
    description text,
    CONSTRAINT different_branches CHECK ((((source_branch <> target_branch) AND (dependent_branch <> source_branch)) AND (dependent_branch <> target_branch))),
    CONSTRAINT positive_revno CHECK (((merged_revno IS NULL) OR (merged_revno > 0)))
);

CREATE SEQUENCE branchmergeproposal_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchmergeproposal_id_seq OWNED BY branchmergeproposal.id;

CREATE TABLE branchmergeproposaljob (
    id integer NOT NULL,
    job integer NOT NULL,
    branch_merge_proposal integer NOT NULL,
    job_type integer NOT NULL,
    json_data text
);

CREATE SEQUENCE branchmergeproposaljob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchmergeproposaljob_id_seq OWNED BY branchmergeproposaljob.id;

CREATE TABLE branchmergerobot (
    id integer NOT NULL,
    registrant integer NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    whiteboard text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE branchmergerobot_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchmergerobot_id_seq OWNED BY branchmergerobot.id;

CREATE TABLE branchrevision (
    id integer NOT NULL,
    sequence integer,
    branch integer NOT NULL,
    revision integer NOT NULL
);
ALTER TABLE ONLY branchrevision ALTER COLUMN branch SET STATISTICS 500;
ALTER TABLE ONLY branchrevision ALTER COLUMN revision SET STATISTICS 500;

CREATE SEQUENCE branchrevision_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchrevision_id_seq OWNED BY branchrevision.id;

CREATE TABLE branchsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    branch integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    notification_level integer DEFAULT 1 NOT NULL,
    max_diff_lines integer,
    review_level integer DEFAULT 0 NOT NULL,
    subscribed_by integer NOT NULL
);

CREATE SEQUENCE branchsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchsubscription_id_seq OWNED BY branchsubscription.id;

CREATE TABLE branchvisibilitypolicy (
    id integer NOT NULL,
    project integer,
    product integer,
    team integer,
    policy integer DEFAULT 1 NOT NULL,
    CONSTRAINT only_one_target CHECK (((project IS NULL) <> (product IS NULL)))
);

CREATE SEQUENCE branchvisibilitypolicy_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchvisibilitypolicy_id_seq OWNED BY branchvisibilitypolicy.id;

CREATE TABLE person (
    id integer NOT NULL,
    displayname text NOT NULL,
    teamowner integer,
    teamdescription text,
    name text NOT NULL,
    language integer,
    fti ts2.tsvector,
    defaultmembershipperiod integer,
    defaultrenewalperiod integer,
    subscriptionpolicy integer DEFAULT 1 NOT NULL,
    merged integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    homepage_content text,
    icon integer,
    mugshot integer,
    hide_email_addresses boolean DEFAULT false NOT NULL,
    creation_rationale integer,
    creation_comment text,
    registrant integer,
    logo integer,
    renewal_policy integer DEFAULT 10 NOT NULL,
    personal_standing integer DEFAULT 0 NOT NULL,
    personal_standing_reason text,
    mail_resumption_date date,
    mailing_list_auto_subscribe_policy integer DEFAULT 1 NOT NULL,
    mailing_list_receive_duplicates boolean DEFAULT true NOT NULL,
    visibility integer DEFAULT 1 NOT NULL,
    verbose_bugnotifications boolean DEFAULT false NOT NULL,
    account integer,
    CONSTRAINT creation_rationale_not_null_for_people CHECK (((creation_rationale IS NULL) = (teamowner IS NOT NULL))),
    CONSTRAINT no_loops CHECK ((id <> teamowner)),
    CONSTRAINT non_empty_displayname CHECK ((btrim(displayname) <> ''::text)),
    CONSTRAINT people_have_no_emblems CHECK (((icon IS NULL) OR (teamowner IS NOT NULL))),
    CONSTRAINT sane_defaultrenewalperiod CHECK (CASE WHEN (teamowner IS NULL) THEN (defaultrenewalperiod IS NULL) WHEN (renewal_policy = ANY (ARRAY[20, 30])) THEN ((defaultrenewalperiod IS NOT NULL) AND (defaultrenewalperiod > 0)) ELSE ((defaultrenewalperiod IS NULL) OR (defaultrenewalperiod > 0)) END),
    CONSTRAINT teams_have_no_account CHECK (((account IS NULL) OR (teamowner IS NULL))),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE TABLE product (
    id integer NOT NULL,
    project integer,
    owner integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    description text,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    homepageurl text,
    screenshotsurl text,
    wikiurl text,
    listurl text,
    programminglang text,
    downloadurl text,
    lastdoap text,
    sourceforgeproject text,
    freshmeatproject text,
    reviewed boolean DEFAULT false NOT NULL,
    active boolean DEFAULT true NOT NULL,
    fti ts2.tsvector,
    autoupdate boolean DEFAULT false NOT NULL,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    official_rosetta boolean DEFAULT false NOT NULL,
    official_malone boolean DEFAULT false NOT NULL,
    bug_supervisor integer,
    security_contact integer,
    driver integer,
    bugtracker integer,
    development_focus integer,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    official_answers boolean DEFAULT false NOT NULL,
    private_bugs boolean DEFAULT false NOT NULL,
    private_specs boolean DEFAULT false NOT NULL,
    license_info text,
    official_blueprints boolean DEFAULT false NOT NULL,
    enable_bug_expiration boolean DEFAULT false NOT NULL,
    bug_reporting_guidelines text,
    reviewer_whiteboard text,
    license_approved boolean DEFAULT false NOT NULL,
    registrant integer NOT NULL,
    remote_product text,
    translation_focus integer,
    max_bug_heat integer,
    date_next_suggest_packaging timestamp without time zone,
    bug_reported_acknowledgement text,
    answers_usage integer DEFAULT 10 NOT NULL,
    blueprints_usage integer DEFAULT 10 NOT NULL,
    translations_usage integer DEFAULT 10 NOT NULL,
    CONSTRAINT only_launchpad_has_expiration CHECK (((enable_bug_expiration IS FALSE) OR (official_malone IS TRUE))),
    CONSTRAINT private_bugs_need_contact CHECK (((private_bugs IS FALSE) OR (bug_supervisor IS NOT NULL))),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE VIEW branchwithsortkeys AS
    SELECT branch.id, branch.title, branch.summary, branch.owner, branch.product, branch.author, branch.name, branch.home_page, branch.url, branch.whiteboard, branch.lifecycle_status, branch.last_mirrored, branch.last_mirror_attempt, branch.mirror_failures, branch.mirror_status_message, branch.last_scanned, branch.last_scanned_id, branch.last_mirrored_id, branch.date_created, branch.revision_count, branch.next_mirror_time, branch.private, branch.branch_type, branch.reviewer, branch.merge_robot, branch.merge_control_status, branch.date_last_modified, branch.registrant, branch.branch_format, branch.repository_format, branch.metadir_format, branch.stacked_on, product.name AS product_name, author.displayname AS author_name, owner.displayname AS owner_name FROM (((branch JOIN person owner ON ((branch.owner = owner.id))) LEFT JOIN product ON ((branch.product = product.id))) LEFT JOIN person author ON ((branch.author = author.id)));

CREATE TABLE bug (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    name text,
    title text NOT NULL,
    description text NOT NULL,
    owner integer NOT NULL,
    duplicateof integer,
    fti ts2.tsvector,
    private boolean DEFAULT false NOT NULL,
    security_related boolean DEFAULT false NOT NULL,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_made_private timestamp without time zone,
    who_made_private integer,
    date_last_message timestamp without time zone,
    number_of_duplicates integer DEFAULT 0 NOT NULL,
    message_count integer DEFAULT 0 NOT NULL,
    users_affected_count integer DEFAULT 0,
    users_unaffected_count integer DEFAULT 0,
    heat integer DEFAULT 0 NOT NULL,
    heat_last_updated timestamp without time zone,
    latest_patch_uploaded timestamp without time zone,
    CONSTRAINT notduplicateofself CHECK ((NOT (id = duplicateof))),
    CONSTRAINT sane_description CHECK (((ltrim(description) <> ''::text) AND (char_length(description) <= 50000))),
    CONSTRAINT valid_bug_name CHECK (valid_bug_name(name))
);

CREATE SEQUENCE bug_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bug_id_seq OWNED BY bug.id;

CREATE TABLE bugactivity (
    id integer NOT NULL,
    bug integer NOT NULL,
    datechanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    whatchanged text NOT NULL,
    oldvalue text,
    newvalue text,
    message text
);

CREATE SEQUENCE bugactivity_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugactivity_id_seq OWNED BY bugactivity.id;

CREATE TABLE bugaffectsperson (
    id integer NOT NULL,
    bug integer NOT NULL,
    person integer NOT NULL,
    affected boolean DEFAULT true NOT NULL
);

CREATE SEQUENCE bugaffectsperson_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugaffectsperson_id_seq OWNED BY bugaffectsperson.id;

CREATE TABLE bugattachment (
    id integer NOT NULL,
    message integer NOT NULL,
    name text,
    title text,
    libraryfile integer NOT NULL,
    bug integer NOT NULL,
    type integer NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE bugattachment_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugattachment_id_seq OWNED BY bugattachment.id;

CREATE TABLE bugbranch (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    bug integer NOT NULL,
    branch integer NOT NULL,
    revision_hint integer,
    whiteboard text,
    registrant integer NOT NULL
);

CREATE SEQUENCE bugbranch_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugbranch_id_seq OWNED BY bugbranch.id;

CREATE TABLE bugcve (
    id integer NOT NULL,
    bug integer NOT NULL,
    cve integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE bugcve_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugcve_id_seq OWNED BY bugcve.id;

CREATE TABLE bugjob (
    id integer NOT NULL,
    job integer NOT NULL,
    bug integer NOT NULL,
    job_type integer NOT NULL,
    json_data text
);

CREATE SEQUENCE bugjob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugjob_id_seq OWNED BY bugjob.id;

CREATE TABLE bugmessage (
    id integer NOT NULL,
    bug integer NOT NULL,
    message integer NOT NULL,
    bugwatch integer,
    remote_comment_id text,
    visible boolean DEFAULT true NOT NULL,
    CONSTRAINT imported_comment CHECK (((remote_comment_id IS NULL) OR (bugwatch IS NOT NULL)))
);

CREATE SEQUENCE bugmessage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugmessage_id_seq OWNED BY bugmessage.id;

CREATE TABLE bugnomination (
    id integer NOT NULL,
    bug integer NOT NULL,
    distroseries integer,
    productseries integer,
    status integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    date_decided timestamp without time zone,
    owner integer NOT NULL,
    decider integer,
    CONSTRAINT distroseries_or_productseries CHECK (((distroseries IS NULL) <> (productseries IS NULL)))
);

CREATE SEQUENCE bugnomination_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugnomination_id_seq OWNED BY bugnomination.id;

CREATE TABLE bugnotification (
    id integer NOT NULL,
    bug integer NOT NULL,
    message integer NOT NULL,
    is_comment boolean NOT NULL,
    date_emailed timestamp without time zone
);

CREATE SEQUENCE bugnotification_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugnotification_id_seq OWNED BY bugnotification.id;

CREATE TABLE bugnotificationarchive (
    id integer NOT NULL,
    bug integer,
    message integer,
    is_comment boolean,
    date_emailed timestamp without time zone
);

CREATE TABLE bugnotificationattachment (
    id integer NOT NULL,
    message integer NOT NULL,
    bug_notification integer NOT NULL
);

CREATE SEQUENCE bugnotificationattachment_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugnotificationattachment_id_seq OWNED BY bugnotificationattachment.id;

CREATE TABLE bugnotificationrecipient (
    id integer NOT NULL,
    bug_notification integer NOT NULL,
    person integer NOT NULL,
    reason_header text NOT NULL,
    reason_body text NOT NULL
);

CREATE SEQUENCE bugnotificationrecipient_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugnotificationrecipient_id_seq OWNED BY bugnotificationrecipient.id;

CREATE TABLE bugnotificationrecipientarchive (
    id integer NOT NULL,
    bug_notification integer,
    person integer,
    reason_header text,
    reason_body text
);

CREATE TABLE bugpackageinfestation (
    id integer NOT NULL,
    bug integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    explicit boolean NOT NULL,
    infestationstatus integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    creator integer NOT NULL,
    dateverified timestamp without time zone,
    verifiedby integer,
    lastmodified timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    lastmodifiedby integer NOT NULL
);

CREATE SEQUENCE bugpackageinfestation_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugpackageinfestation_id_seq OWNED BY bugpackageinfestation.id;

CREATE TABLE bugproductinfestation (
    id integer NOT NULL,
    bug integer NOT NULL,
    productrelease integer NOT NULL,
    explicit boolean NOT NULL,
    infestationstatus integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    creator integer NOT NULL,
    dateverified timestamp without time zone,
    verifiedby integer,
    lastmodified timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    lastmodifiedby integer NOT NULL
);

CREATE SEQUENCE bugproductinfestation_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugproductinfestation_id_seq OWNED BY bugproductinfestation.id;

CREATE TABLE bugsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    bug integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subscribed_by integer NOT NULL,
    bug_notification_level integer DEFAULT 40 NOT NULL
);

CREATE SEQUENCE bugsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugsubscription_id_seq OWNED BY bugsubscription.id;

CREATE TABLE bugtag (
    id integer NOT NULL,
    bug integer NOT NULL,
    tag text NOT NULL,
    CONSTRAINT valid_tag CHECK (valid_name(tag))
);

CREATE SEQUENCE bugtag_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugtag_id_seq OWNED BY bugtag.id;

CREATE TABLE bugtask (
    id integer NOT NULL,
    bug integer NOT NULL,
    product integer,
    distribution integer,
    distroseries integer,
    sourcepackagename integer,
    binarypackagename integer,
    status integer NOT NULL,
    priority integer,
    importance integer DEFAULT 5 NOT NULL,
    assignee integer,
    date_assigned timestamp without time zone,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    owner integer NOT NULL,
    milestone integer,
    bugwatch integer,
    statusexplanation text,
    fti ts2.tsvector,
    targetnamecache text,
    date_confirmed timestamp without time zone,
    date_inprogress timestamp without time zone,
    date_closed timestamp without time zone,
    productseries integer,
    date_incomplete timestamp without time zone,
    date_left_new timestamp without time zone,
    date_triaged timestamp without time zone,
    date_fix_committed timestamp without time zone,
    date_fix_released timestamp without time zone,
    date_left_closed timestamp without time zone,
    heat_rank integer DEFAULT 0 NOT NULL,
    date_milestone_set timestamp without time zone,
    CONSTRAINT bugtask_assignment_checks CHECK (CASE WHEN (product IS NOT NULL) THEN ((((productseries IS NULL) AND (distribution IS NULL)) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL)) WHEN (productseries IS NOT NULL) THEN (((distribution IS NULL) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL)) WHEN (distribution IS NOT NULL) THEN (distroseries IS NULL) WHEN (distroseries IS NOT NULL) THEN true ELSE false END)
);

CREATE SEQUENCE bugtask_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugtask_id_seq OWNED BY bugtask.id;

CREATE TABLE bugtracker (
    id integer NOT NULL,
    bugtrackertype integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text,
    baseurl text NOT NULL,
    owner integer NOT NULL,
    contactdetails text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    version text,
    block_comment_pushing boolean DEFAULT false NOT NULL,
    has_lp_plugin boolean,
    active boolean DEFAULT true NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE bugtracker_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugtracker_id_seq OWNED BY bugtracker.id;

CREATE TABLE bugtrackeralias (
    id integer NOT NULL,
    bugtracker integer NOT NULL,
    base_url text NOT NULL
);

CREATE SEQUENCE bugtrackeralias_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugtrackeralias_id_seq OWNED BY bugtrackeralias.id;

CREATE TABLE bugtrackerperson (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    bugtracker integer NOT NULL,
    person integer NOT NULL,
    name text NOT NULL
);

CREATE SEQUENCE bugtrackerperson_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugtrackerperson_id_seq OWNED BY bugtrackerperson.id;

CREATE TABLE bugwatch (
    id integer NOT NULL,
    bug integer NOT NULL,
    bugtracker integer NOT NULL,
    remotebug text NOT NULL,
    remotestatus text,
    lastchanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    lastchecked timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    owner integer NOT NULL,
    last_error_type integer,
    remote_importance text,
    remote_lp_bug_id integer,
    next_check timestamp without time zone
);

CREATE SEQUENCE bugwatch_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugwatch_id_seq OWNED BY bugwatch.id;

CREATE TABLE bugwatchactivity (
    id integer NOT NULL,
    bug_watch integer NOT NULL,
    activity_date timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    result integer NOT NULL,
    message text,
    oops_id text
);

CREATE SEQUENCE bugwatchactivity_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugwatchactivity_id_seq OWNED BY bugwatchactivity.id;

CREATE TABLE builder (
    id integer NOT NULL,
    processor integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    owner integer NOT NULL,
    speedindex integer,
    builderok boolean NOT NULL,
    failnotes text,
    virtualized boolean DEFAULT true NOT NULL,
    url text NOT NULL,
    manual boolean DEFAULT false,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    vm_host text,
    active boolean DEFAULT true NOT NULL,
    CONSTRAINT valid_absolute_url CHECK (valid_absolute_url(url))
);

CREATE SEQUENCE builder_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE builder_id_seq OWNED BY builder.id;

CREATE TABLE buildfarmjob (
    id integer NOT NULL,
    processor integer,
    virtualized boolean,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    date_first_dispatched timestamp without time zone,
    builder integer,
    status integer NOT NULL,
    log integer,
    job_type integer NOT NULL,
    CONSTRAINT started_if_finished CHECK (((date_finished IS NULL) OR (date_started IS NOT NULL)))
);

CREATE SEQUENCE buildfarmjob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE buildfarmjob_id_seq OWNED BY buildfarmjob.id;

CREATE TABLE buildpackagejob (
    id integer NOT NULL,
    job integer NOT NULL,
    build integer NOT NULL
);

CREATE SEQUENCE buildpackagejob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE buildpackagejob_id_seq OWNED BY buildpackagejob.id;

CREATE TABLE buildqueue (
    id integer NOT NULL,
    builder integer,
    logtail text,
    lastscore integer,
    manual boolean DEFAULT false NOT NULL,
    job integer NOT NULL,
    job_type integer DEFAULT 1 NOT NULL,
    estimated_duration interval DEFAULT '00:00:00'::interval NOT NULL,
    processor integer,
    virtualized boolean
);

CREATE SEQUENCE buildqueue_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE buildqueue_id_seq OWNED BY buildqueue.id;

CREATE TABLE codeimport (
    id integer NOT NULL,
    branch integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    rcs_type integer NOT NULL,
    cvs_root text,
    cvs_module text,
    review_status integer DEFAULT 1 NOT NULL,
    date_last_successful timestamp without time zone,
    owner integer NOT NULL,
    assignee integer,
    update_interval interval,
    url text,
    CONSTRAINT valid_vcs_details CHECK (CASE WHEN (rcs_type = 1) THEN (((((cvs_root IS NOT NULL) AND (cvs_root <> ''::text)) AND (cvs_module IS NOT NULL)) AND (cvs_module <> ''::text)) AND (url IS NULL)) WHEN (rcs_type = ANY (ARRAY[2, 3])) THEN ((((cvs_root IS NULL) AND (cvs_module IS NULL)) AND (url IS NOT NULL)) AND valid_absolute_url(url)) WHEN (rcs_type = ANY (ARRAY[4, 5])) THEN (((cvs_root IS NULL) AND (cvs_module IS NULL)) AND (url IS NOT NULL)) ELSE false END)
);

CREATE SEQUENCE codeimport_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codeimport_id_seq OWNED BY codeimport.id;

CREATE TABLE codeimportevent (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    entry_type integer NOT NULL,
    code_import integer,
    person integer,
    machine integer
);

CREATE SEQUENCE codeimportevent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codeimportevent_id_seq OWNED BY codeimportevent.id;

CREATE TABLE codeimporteventdata (
    id integer NOT NULL,
    event integer,
    data_type integer NOT NULL,
    data_value text
);

CREATE SEQUENCE codeimporteventdata_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codeimporteventdata_id_seq OWNED BY codeimporteventdata.id;

CREATE TABLE codeimportjob (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    code_import integer NOT NULL,
    machine integer,
    date_due timestamp without time zone NOT NULL,
    state integer NOT NULL,
    requesting_user integer,
    ordering integer,
    heartbeat timestamp without time zone,
    logtail text,
    date_started timestamp without time zone,
    CONSTRAINT valid_state CHECK (CASE WHEN (state = 10) THEN (((((machine IS NULL) AND (ordering IS NULL)) AND (heartbeat IS NULL)) AND (date_started IS NULL)) AND (logtail IS NULL)) WHEN (state = 20) THEN (((((machine IS NOT NULL) AND (ordering IS NOT NULL)) AND (heartbeat IS NULL)) AND (date_started IS NULL)) AND (logtail IS NULL)) WHEN (state = 30) THEN (((((machine IS NOT NULL) AND (ordering IS NULL)) AND (heartbeat IS NOT NULL)) AND (date_started IS NOT NULL)) AND (logtail IS NOT NULL)) ELSE false END)
);

CREATE SEQUENCE codeimportjob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codeimportjob_id_seq OWNED BY codeimportjob.id;

CREATE TABLE codeimportmachine (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    hostname text NOT NULL,
    state integer DEFAULT 10 NOT NULL,
    heartbeat timestamp without time zone
);

CREATE SEQUENCE codeimportmachine_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codeimportmachine_id_seq OWNED BY codeimportmachine.id;

CREATE TABLE codeimportresult (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    code_import integer,
    machine integer,
    requesting_user integer,
    log_excerpt text,
    log_file integer,
    status integer NOT NULL,
    date_job_started timestamp without time zone
);

CREATE SEQUENCE codeimportresult_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codeimportresult_id_seq OWNED BY codeimportresult.id;

CREATE TABLE codereviewmessage (
    id integer NOT NULL,
    branch_merge_proposal integer NOT NULL,
    message integer NOT NULL,
    vote integer,
    vote_tag text
);

CREATE SEQUENCE codereviewmessage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codereviewmessage_id_seq OWNED BY codereviewmessage.id;

CREATE TABLE codereviewvote (
    id integer NOT NULL,
    branch_merge_proposal integer NOT NULL,
    reviewer integer NOT NULL,
    review_type text,
    registrant integer NOT NULL,
    vote_message integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE codereviewvote_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codereviewvote_id_seq OWNED BY codereviewvote.id;

CREATE TABLE commercialsubscription (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_starts timestamp without time zone NOT NULL,
    date_expires timestamp without time zone NOT NULL,
    status integer DEFAULT 10 NOT NULL,
    product integer NOT NULL,
    registrant integer NOT NULL,
    purchaser integer NOT NULL,
    whiteboard text,
    sales_system_id text
);

CREATE SEQUENCE commercialsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE commercialsubscription_id_seq OWNED BY commercialsubscription.id;

CREATE SEQUENCE component_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE component_id_seq OWNED BY component.id;

CREATE TABLE componentselection (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    component integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE componentselection_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE componentselection_id_seq OWNED BY componentselection.id;

CREATE TABLE continent (
    id integer NOT NULL,
    code text NOT NULL,
    name text NOT NULL
);

CREATE SEQUENCE continent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE continent_id_seq OWNED BY continent.id;

CREATE TABLE country (
    id integer NOT NULL,
    iso3166code2 character(2) NOT NULL,
    iso3166code3 character(3) NOT NULL,
    name text NOT NULL,
    title text,
    description text,
    continent integer NOT NULL
);

CREATE SEQUENCE country_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE country_id_seq OWNED BY country.id;

CREATE TABLE customlanguagecode (
    id integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer,
    language_code text NOT NULL,
    language integer,
    CONSTRAINT distro_and_sourcepackage CHECK (((sourcepackagename IS NULL) = (distribution IS NULL))),
    CONSTRAINT product_or_distro CHECK (((product IS NULL) <> (distribution IS NULL)))
);

CREATE SEQUENCE customlanguagecode_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE customlanguagecode_id_seq OWNED BY customlanguagecode.id;

CREATE TABLE cve (
    id integer NOT NULL,
    sequence text NOT NULL,
    status integer NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datemodified timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    fti ts2.tsvector,
    CONSTRAINT valid_cve_ref CHECK (valid_cve(sequence))
);

CREATE SEQUENCE cve_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE cve_id_seq OWNED BY cve.id;

CREATE TABLE cvereference (
    id integer NOT NULL,
    cve integer NOT NULL,
    source text NOT NULL,
    content text NOT NULL,
    url text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE cvereference_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE cvereference_id_seq OWNED BY cvereference.id;

CREATE TABLE databasecpustats (
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    username text NOT NULL,
    cpu integer NOT NULL
);

CREATE TABLE databasereplicationlag (
    node integer NOT NULL,
    lag interval NOT NULL,
    updated timestamp without time zone DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE databasetablestats (
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    schemaname name NOT NULL,
    relname name NOT NULL,
    seq_scan bigint NOT NULL,
    seq_tup_read bigint NOT NULL,
    idx_scan bigint NOT NULL,
    idx_tup_fetch bigint NOT NULL,
    n_tup_ins bigint NOT NULL,
    n_tup_upd bigint NOT NULL,
    n_tup_del bigint NOT NULL,
    n_tup_hot_upd bigint NOT NULL,
    n_live_tup bigint NOT NULL,
    n_dead_tup bigint NOT NULL,
    last_vacuum timestamp with time zone,
    last_autovacuum timestamp with time zone,
    last_analyze timestamp with time zone,
    last_autoanalyze timestamp with time zone
);

CREATE TABLE diff (
    id integer NOT NULL,
    diff_text integer,
    diff_lines_count integer,
    diffstat text,
    added_lines_count integer,
    removed_lines_count integer
);

CREATE SEQUENCE diff_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE diff_id_seq OWNED BY diff.id;

CREATE TABLE distribution (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    domainname text NOT NULL,
    owner integer NOT NULL,
    lucilleconfig text,
    displayname text NOT NULL,
    summary text NOT NULL,
    members integer NOT NULL,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    bug_supervisor integer,
    official_malone boolean DEFAULT false NOT NULL,
    official_rosetta boolean DEFAULT false NOT NULL,
    security_contact integer,
    driver integer,
    translation_focus integer,
    mirror_admin integer NOT NULL,
    upload_admin integer,
    upload_sender text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    fti ts2.tsvector,
    official_answers boolean DEFAULT false NOT NULL,
    language_pack_admin integer,
    official_blueprints boolean DEFAULT false NOT NULL,
    enable_bug_expiration boolean DEFAULT false NOT NULL,
    bug_reporting_guidelines text,
    reviewer_whiteboard text,
    max_bug_heat integer,
    bug_reported_acknowledgement text,
    answers_usage integer DEFAULT 10 NOT NULL,
    blueprints_usage integer DEFAULT 10 NOT NULL,
    translations_usage integer DEFAULT 10 NOT NULL,
    CONSTRAINT only_launchpad_has_expiration CHECK (((enable_bug_expiration IS FALSE) OR (official_malone IS TRUE))),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE distribution_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distribution_id_seq OWNED BY distribution.id;

CREATE TABLE distributionbounty (
    id integer NOT NULL,
    bounty integer NOT NULL,
    distribution integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE distributionbounty_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distributionbounty_id_seq OWNED BY distributionbounty.id;

CREATE TABLE distributionmirror (
    id integer NOT NULL,
    distribution integer NOT NULL,
    name text NOT NULL,
    http_base_url text,
    ftp_base_url text,
    rsync_base_url text,
    displayname text,
    description text,
    owner integer NOT NULL,
    speed integer NOT NULL,
    country integer NOT NULL,
    content integer NOT NULL,
    official_candidate boolean DEFAULT false NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    whiteboard text,
    status integer DEFAULT 10 NOT NULL,
    date_reviewed timestamp without time zone,
    reviewer integer,
    country_dns_mirror boolean DEFAULT false NOT NULL,
    CONSTRAINT one_or_more_urls CHECK ((((http_base_url IS NOT NULL) OR (ftp_base_url IS NOT NULL)) OR (rsync_base_url IS NOT NULL))),
    CONSTRAINT valid_ftp_base_url CHECK (valid_absolute_url(ftp_base_url)),
    CONSTRAINT valid_http_base_url CHECK (valid_absolute_url(http_base_url)),
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_rsync_base_url CHECK (valid_absolute_url(rsync_base_url))
);

CREATE SEQUENCE distributionmirror_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distributionmirror_id_seq OWNED BY distributionmirror.id;

CREATE TABLE distributionsourcepackage (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bug_reporting_guidelines text,
    max_bug_heat integer,
    bug_reported_acknowledgement text,
    total_bug_heat integer,
    bug_count integer,
    po_message_count integer,
    is_upstream_link_allowed boolean DEFAULT true NOT NULL
);

CREATE SEQUENCE distributionsourcepackage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distributionsourcepackage_id_seq OWNED BY distributionsourcepackage.id;

CREATE TABLE distributionsourcepackagecache (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    name text,
    binpkgnames text,
    binpkgsummaries text,
    binpkgdescriptions text,
    fti ts2.tsvector,
    changelog text,
    archive integer NOT NULL
);

CREATE SEQUENCE distributionsourcepackagecache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distributionsourcepackagecache_id_seq OWNED BY distributionsourcepackagecache.id;

CREATE SEQUENCE distroarchseries_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distroarchseries_id_seq OWNED BY distroarchseries.id;

CREATE TABLE distrocomponentuploader (
    id integer NOT NULL,
    distribution integer NOT NULL,
    component integer NOT NULL,
    uploader integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE distrocomponentuploader_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distrocomponentuploader_id_seq OWNED BY distrocomponentuploader.id;

CREATE SEQUENCE distroseries_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distroseries_id_seq OWNED BY distroseries.id;

CREATE TABLE distroserieslanguage (
    id integer NOT NULL,
    distroseries integer,
    language integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    contributorcount integer NOT NULL,
    dateupdated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    unreviewed_count integer DEFAULT 0 NOT NULL
);

CREATE SEQUENCE distroserieslanguage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distroserieslanguage_id_seq OWNED BY distroserieslanguage.id;

CREATE TABLE distroseriespackagecache (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    binarypackagename integer NOT NULL,
    name text,
    summary text,
    description text,
    summaries text,
    descriptions text,
    fti ts2.tsvector,
    archive integer NOT NULL
);

CREATE SEQUENCE distroseriespackagecache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distroseriespackagecache_id_seq OWNED BY distroseriespackagecache.id;

CREATE TABLE emailaddress (
    id integer NOT NULL,
    email text NOT NULL,
    person integer,
    status integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    account integer,
    CONSTRAINT emailaddress__is_linked__chk CHECK (((person IS NOT NULL) OR (account IS NOT NULL)))
);

CREATE SEQUENCE emailaddress_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE emailaddress_id_seq OWNED BY emailaddress.id;

CREATE TABLE entitlement (
    id integer NOT NULL,
    person integer,
    entitlement_type integer NOT NULL,
    quota integer NOT NULL,
    amount_used integer DEFAULT 0 NOT NULL,
    date_starts timestamp without time zone,
    date_expires timestamp without time zone,
    registrant integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    approved_by integer,
    date_approved timestamp without time zone,
    state integer DEFAULT 30 NOT NULL,
    whiteboard text,
    is_dirty boolean DEFAULT true NOT NULL,
    distribution integer,
    product integer,
    project integer,
    CONSTRAINT only_one_target CHECK ((null_count(ARRAY[person, product, project, distribution]) = 3))
);

CREATE SEQUENCE entitlement_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE entitlement_id_seq OWNED BY entitlement.id;

CREATE VIEW exclusivelocks AS
    SELECT alllocks.procpid, alllocks.usename, alllocks.age, alllocks.relname, alllocks.mode, alllocks.granted, alllocks.current_query FROM alllocks WHERE (alllocks.mode !~~ '%Share%'::text);

CREATE TABLE faq (
    id integer NOT NULL,
    title text NOT NULL,
    tags text,
    content text NOT NULL,
    product integer,
    distribution integer,
    owner integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    last_updated_by integer,
    date_last_updated timestamp without time zone,
    fti ts2.tsvector,
    CONSTRAINT product_or_distro CHECK (((product IS NULL) <> (distribution IS NULL)))
);

CREATE SEQUENCE faq_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE faq_id_seq OWNED BY faq.id;

CREATE TABLE featuredproject (
    id integer NOT NULL,
    pillar_name integer NOT NULL
);

CREATE SEQUENCE featuredproject_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE featuredproject_id_seq OWNED BY featuredproject.id;

CREATE TABLE featureflag (
    scope text NOT NULL,
    priority integer NOT NULL,
    flag text NOT NULL,
    value text,
    date_modified timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE TABLE flatpackagesetinclusion (
    id integer NOT NULL,
    parent integer NOT NULL,
    child integer NOT NULL
);

CREATE SEQUENCE flatpackagesetinclusion_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE flatpackagesetinclusion_id_seq OWNED BY flatpackagesetinclusion.id;

CREATE TABLE fticache (
    id integer NOT NULL,
    tablename text NOT NULL,
    columns text NOT NULL
);

CREATE SEQUENCE fticache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE fticache_id_seq OWNED BY fticache.id;

CREATE TABLE gpgkey (
    id integer NOT NULL,
    owner integer NOT NULL,
    keyid text NOT NULL,
    fingerprint text NOT NULL,
    active boolean NOT NULL,
    algorithm integer NOT NULL,
    keysize integer NOT NULL,
    can_encrypt boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_fingerprint CHECK (valid_fingerprint(fingerprint)),
    CONSTRAINT valid_keyid CHECK (valid_keyid(keyid))
);

CREATE SEQUENCE gpgkey_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE gpgkey_id_seq OWNED BY gpgkey.id;

CREATE TABLE hwdevice (
    id integer NOT NULL,
    bus_vendor_id integer NOT NULL,
    bus_product_id text NOT NULL,
    variant text,
    name text NOT NULL,
    submissions integer NOT NULL
);

CREATE SEQUENCE hwdevice_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwdevice_id_seq OWNED BY hwdevice.id;

CREATE TABLE hwdeviceclass (
    id integer NOT NULL,
    device integer NOT NULL,
    main_class integer NOT NULL,
    sub_class integer
);

CREATE SEQUENCE hwdeviceclass_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwdeviceclass_id_seq OWNED BY hwdeviceclass.id;

CREATE TABLE hwdevicedriverlink (
    id integer NOT NULL,
    device integer NOT NULL,
    driver integer
);

CREATE SEQUENCE hwdevicedriverlink_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwdevicedriverlink_id_seq OWNED BY hwdevicedriverlink.id;

CREATE TABLE hwdevicenamevariant (
    id integer NOT NULL,
    vendor_name integer NOT NULL,
    product_name text NOT NULL,
    device integer NOT NULL,
    submissions integer NOT NULL
);

CREATE SEQUENCE hwdevicenamevariant_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwdevicenamevariant_id_seq OWNED BY hwdevicenamevariant.id;

CREATE TABLE hwdmihandle (
    id integer NOT NULL,
    handle integer NOT NULL,
    type integer NOT NULL,
    submission integer
);

CREATE SEQUENCE hwdmihandle_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwdmihandle_id_seq OWNED BY hwdmihandle.id;

CREATE TABLE hwdmivalue (
    id integer NOT NULL,
    key text,
    value text,
    handle integer NOT NULL
);

CREATE SEQUENCE hwdmivalue_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwdmivalue_id_seq OWNED BY hwdmivalue.id;

CREATE TABLE hwdriver (
    id integer NOT NULL,
    package_name text,
    name text NOT NULL,
    license integer
);

CREATE SEQUENCE hwdriver_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwdriver_id_seq OWNED BY hwdriver.id;

CREATE VIEW hwdrivernames AS
    SELECT DISTINCT ON (hwdriver.name) hwdriver.id, hwdriver.name FROM hwdriver ORDER BY hwdriver.name, hwdriver.id;

CREATE VIEW hwdriverpackagenames AS
    SELECT DISTINCT ON (hwdriver.package_name) hwdriver.id, hwdriver.package_name FROM hwdriver ORDER BY hwdriver.package_name, hwdriver.id;

CREATE TABLE hwsubmission (
    id integer NOT NULL,
    date_created timestamp without time zone NOT NULL,
    date_submitted timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    format integer NOT NULL,
    status integer DEFAULT 1 NOT NULL,
    private boolean NOT NULL,
    contactable boolean NOT NULL,
    submission_key text NOT NULL,
    owner integer,
    distroarchseries integer,
    raw_submission integer NOT NULL,
    system_fingerprint integer NOT NULL,
    raw_emailaddress text
);

CREATE SEQUENCE hwsubmission_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwsubmission_id_seq OWNED BY hwsubmission.id;

CREATE TABLE hwsubmissionbug (
    id integer NOT NULL,
    submission integer NOT NULL,
    bug integer NOT NULL
);

CREATE SEQUENCE hwsubmissionbug_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwsubmissionbug_id_seq OWNED BY hwsubmissionbug.id;

CREATE TABLE hwsubmissiondevice (
    id integer NOT NULL,
    device_driver_link integer NOT NULL,
    submission integer NOT NULL,
    parent integer,
    hal_device_id integer NOT NULL
);

CREATE SEQUENCE hwsubmissiondevice_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwsubmissiondevice_id_seq OWNED BY hwsubmissiondevice.id;

CREATE TABLE hwsystemfingerprint (
    id integer NOT NULL,
    fingerprint text NOT NULL
);

CREATE SEQUENCE hwsystemfingerprint_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwsystemfingerprint_id_seq OWNED BY hwsystemfingerprint.id;

CREATE TABLE hwtest (
    id integer NOT NULL,
    namespace text,
    name text NOT NULL,
    version text NOT NULL
);

CREATE SEQUENCE hwtest_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwtest_id_seq OWNED BY hwtest.id;

CREATE TABLE hwtestanswer (
    id integer NOT NULL,
    test integer NOT NULL,
    choice integer,
    intval integer,
    floatval double precision,
    unit text,
    comment text,
    language integer,
    submission integer NOT NULL,
    CONSTRAINT hwtestanswer_check CHECK (((((choice IS NULL) AND (unit IS NOT NULL)) AND ((intval IS NULL) <> (floatval IS NULL))) OR ((((choice IS NOT NULL) AND (unit IS NULL)) AND (intval IS NULL)) AND (floatval IS NULL))))
);

CREATE SEQUENCE hwtestanswer_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwtestanswer_id_seq OWNED BY hwtestanswer.id;

CREATE TABLE hwtestanswerchoice (
    id integer NOT NULL,
    choice text NOT NULL,
    test integer NOT NULL
);

CREATE SEQUENCE hwtestanswerchoice_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwtestanswerchoice_id_seq OWNED BY hwtestanswerchoice.id;

CREATE TABLE hwtestanswercount (
    id integer NOT NULL,
    test integer NOT NULL,
    distroarchseries integer,
    choice integer,
    average double precision,
    sum_square double precision,
    unit text,
    num_answers integer NOT NULL,
    CONSTRAINT hwtestanswercount_check CHECK ((((((choice IS NULL) AND (average IS NOT NULL)) AND (sum_square IS NOT NULL)) AND (unit IS NOT NULL)) OR ((((choice IS NOT NULL) AND (average IS NULL)) AND (sum_square IS NULL)) AND (unit IS NULL))))
);

CREATE SEQUENCE hwtestanswercount_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwtestanswercount_id_seq OWNED BY hwtestanswercount.id;

CREATE TABLE hwtestanswercountdevice (
    id integer NOT NULL,
    answer integer NOT NULL,
    device_driver integer NOT NULL
);

CREATE SEQUENCE hwtestanswercountdevice_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwtestanswercountdevice_id_seq OWNED BY hwtestanswercountdevice.id;

CREATE TABLE hwtestanswerdevice (
    id integer NOT NULL,
    answer integer NOT NULL,
    device_driver integer NOT NULL
);

CREATE SEQUENCE hwtestanswerdevice_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwtestanswerdevice_id_seq OWNED BY hwtestanswerdevice.id;

CREATE TABLE hwvendorid (
    id integer NOT NULL,
    bus integer NOT NULL,
    vendor_id_for_bus text NOT NULL,
    vendor_name integer NOT NULL
);

CREATE SEQUENCE hwvendorid_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwvendorid_id_seq OWNED BY hwvendorid.id;

CREATE TABLE hwvendorname (
    id integer NOT NULL,
    name text NOT NULL
);

CREATE SEQUENCE hwvendorname_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwvendorname_id_seq OWNED BY hwvendorname.id;

CREATE TABLE ircid (
    id integer NOT NULL,
    person integer NOT NULL,
    network text NOT NULL,
    nickname text NOT NULL
);

CREATE SEQUENCE ircid_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE ircid_id_seq OWNED BY ircid.id;

CREATE TABLE jabberid (
    id integer NOT NULL,
    person integer NOT NULL,
    jabberid text NOT NULL
);

CREATE SEQUENCE jabberid_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE jabberid_id_seq OWNED BY jabberid.id;

CREATE TABLE job (
    id integer NOT NULL,
    requester integer,
    reason text,
    status integer NOT NULL,
    progress integer,
    last_report_seen timestamp without time zone,
    next_report_due timestamp without time zone,
    attempt_count integer DEFAULT 0 NOT NULL,
    max_retries integer DEFAULT 0 NOT NULL,
    log text,
    scheduled_start timestamp without time zone,
    lease_expires timestamp without time zone,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone
);

CREATE SEQUENCE job_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE job_id_seq OWNED BY job.id;

CREATE TABLE karma (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    action integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer
);

CREATE SEQUENCE karma_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE karma_id_seq OWNED BY karma.id;

CREATE TABLE karmaaction (
    id integer NOT NULL,
    category integer,
    points integer,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL
);

CREATE SEQUENCE karmaaction_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE karmaaction_id_seq OWNED BY karmaaction.id;

CREATE TABLE karmacache (
    id integer NOT NULL,
    person integer NOT NULL,
    category integer,
    karmavalue integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer,
    project integer,
    CONSTRAINT just_distribution CHECK (((distribution IS NULL) OR ((product IS NULL) AND (project IS NULL)))),
    CONSTRAINT just_product CHECK (((product IS NULL) OR ((project IS NULL) AND (distribution IS NULL)))),
    CONSTRAINT just_project CHECK (((project IS NULL) OR ((product IS NULL) AND (distribution IS NULL)))),
    CONSTRAINT sourcepackagename_requires_distribution CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);

CREATE SEQUENCE karmacache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE karmacache_id_seq OWNED BY karmacache.id;

CREATE TABLE karmacategory (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL
);

CREATE SEQUENCE karmacategory_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE karmacategory_id_seq OWNED BY karmacategory.id;

CREATE TABLE karmatotalcache (
    id integer NOT NULL,
    person integer NOT NULL,
    karma_total integer NOT NULL
);

CREATE SEQUENCE karmatotalcache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE karmatotalcache_id_seq OWNED BY karmatotalcache.id;

CREATE TABLE language (
    id integer NOT NULL,
    code text NOT NULL,
    englishname text NOT NULL,
    nativename text,
    pluralforms integer,
    pluralexpression text,
    visible boolean NOT NULL,
    direction integer DEFAULT 0 NOT NULL,
    uuid text,
    CONSTRAINT valid_language CHECK (((pluralforms IS NULL) = (pluralexpression IS NULL)))
);

CREATE SEQUENCE language_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE language_id_seq OWNED BY language.id;

CREATE TABLE languagepack (
    id integer NOT NULL,
    file integer NOT NULL,
    date_exported timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_used timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    distroseries integer NOT NULL,
    type integer DEFAULT 1 NOT NULL,
    updates integer,
    CONSTRAINT valid_updates CHECK ((((type = 2) AND (updates IS NOT NULL)) OR ((type = 1) AND (updates IS NULL))))
);

CREATE SEQUENCE languagepack_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE languagepack_id_seq OWNED BY languagepack.id;

CREATE TABLE launchpaddatabaserevision (
    major integer NOT NULL,
    minor integer NOT NULL,
    patch integer NOT NULL
);

CREATE TABLE launchpadstatistic (
    id integer NOT NULL,
    name text NOT NULL,
    value integer NOT NULL,
    dateupdated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);

CREATE SEQUENCE launchpadstatistic_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE launchpadstatistic_id_seq OWNED BY launchpadstatistic.id;

CREATE SEQUENCE libraryfilealias_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE libraryfilealias_id_seq OWNED BY libraryfilealias.id;

CREATE TABLE libraryfilecontent (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    filesize bigint NOT NULL,
    sha1 character(40) NOT NULL,
    md5 character(32) NOT NULL,
    sha256 character(64)
);

CREATE SEQUENCE libraryfilecontent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE libraryfilecontent_id_seq OWNED BY libraryfilecontent.id;

CREATE TABLE libraryfiledownloadcount (
    id integer NOT NULL,
    libraryfilealias integer NOT NULL,
    day date NOT NULL,
    count integer NOT NULL,
    country integer
);

CREATE SEQUENCE libraryfiledownloadcount_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE libraryfiledownloadcount_id_seq OWNED BY libraryfiledownloadcount.id;

CREATE TABLE logintoken (
    id integer NOT NULL,
    requester integer,
    requesteremail text,
    email text NOT NULL,
    created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    tokentype integer NOT NULL,
    token text,
    fingerprint text,
    redirection_url text,
    date_consumed timestamp without time zone,
    CONSTRAINT valid_fingerprint CHECK (((fingerprint IS NULL) OR valid_fingerprint(fingerprint)))
);

CREATE SEQUENCE logintoken_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE logintoken_id_seq OWNED BY logintoken.id;

CREATE TABLE lp_account (
    id integer NOT NULL,
    openid_identifier text NOT NULL
);

CREATE TABLE lp_person (
    id integer NOT NULL,
    displayname text,
    teamowner integer,
    teamdescription text,
    name text,
    language integer,
    fti ts2.tsvector,
    defaultmembershipperiod integer,
    defaultrenewalperiod integer,
    subscriptionpolicy integer,
    merged integer,
    datecreated timestamp without time zone,
    addressline1 text,
    addressline2 text,
    organization text,
    city text,
    province text,
    country integer,
    postcode text,
    phone text,
    homepage_content text,
    icon integer,
    mugshot integer,
    hide_email_addresses boolean,
    creation_rationale integer,
    creation_comment text,
    registrant integer,
    logo integer,
    renewal_policy integer,
    personal_standing integer,
    personal_standing_reason text,
    mail_resumption_date date,
    mailing_list_auto_subscribe_policy integer,
    mailing_list_receive_duplicates boolean,
    visibility integer,
    verbose_bugnotifications boolean,
    account integer
);

CREATE TABLE lp_personlocation (
    id integer NOT NULL,
    date_created timestamp without time zone,
    person integer,
    latitude double precision,
    longitude double precision,
    time_zone text,
    last_modified_by integer,
    date_last_modified timestamp without time zone,
    visible boolean,
    locked boolean
);

CREATE TABLE lp_teamparticipation (
    id integer NOT NULL,
    team integer,
    person integer
);

CREATE TABLE mailinglist (
    id integer NOT NULL,
    team integer NOT NULL,
    registrant integer NOT NULL,
    date_registered timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    reviewer integer,
    date_reviewed timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    date_activated timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    status integer DEFAULT 1 NOT NULL,
    welcome_message text
);

CREATE SEQUENCE mailinglist_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mailinglist_id_seq OWNED BY mailinglist.id;

CREATE TABLE mailinglistban (
    id integer NOT NULL,
    person integer NOT NULL,
    banned_by integer NOT NULL,
    date_banned timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    reason text NOT NULL
);

CREATE SEQUENCE mailinglistban_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mailinglistban_id_seq OWNED BY mailinglistban.id;

CREATE TABLE mailinglistsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    mailing_list integer NOT NULL,
    date_joined timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    email_address integer
);

CREATE SEQUENCE mailinglistsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mailinglistsubscription_id_seq OWNED BY mailinglistsubscription.id;

CREATE TABLE mentoringoffer (
    id integer NOT NULL,
    owner integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    team integer NOT NULL,
    bug integer,
    specification integer,
    CONSTRAINT context_required CHECK (((bug IS NULL) <> (specification IS NULL)))
);

CREATE SEQUENCE mentoringoffer_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mentoringoffer_id_seq OWNED BY mentoringoffer.id;

CREATE TABLE mergedirectivejob (
    id integer NOT NULL,
    job integer NOT NULL,
    merge_directive integer NOT NULL,
    action integer NOT NULL
);

CREATE SEQUENCE mergedirectivejob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mergedirectivejob_id_seq OWNED BY mergedirectivejob.id;

CREATE TABLE message (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    subject text,
    owner integer,
    parent integer,
    distribution integer,
    rfc822msgid text NOT NULL,
    fti ts2.tsvector,
    raw integer
);

CREATE SEQUENCE message_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE message_id_seq OWNED BY message.id;

CREATE TABLE messageapproval (
    id integer NOT NULL,
    posted_by integer NOT NULL,
    mailing_list integer NOT NULL,
    posted_message integer NOT NULL,
    posted_date timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    disposed_by integer,
    disposal_date timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    reason text,
    message integer NOT NULL
);

CREATE SEQUENCE messageapproval_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE messageapproval_id_seq OWNED BY messageapproval.id;

CREATE TABLE messagechunk (
    id integer NOT NULL,
    message integer NOT NULL,
    sequence integer NOT NULL,
    content text,
    blob integer,
    fti ts2.tsvector,
    CONSTRAINT text_or_content CHECK ((((blob IS NULL) AND (content IS NULL)) OR ((blob IS NULL) <> (content IS NULL))))
);

CREATE SEQUENCE messagechunk_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE messagechunk_id_seq OWNED BY messagechunk.id;

CREATE TABLE milestone (
    id integer NOT NULL,
    product integer,
    name text NOT NULL,
    distribution integer,
    dateexpected timestamp without time zone,
    active boolean DEFAULT true NOT NULL,
    productseries integer,
    distroseries integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    summary text,
    codename text,
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_target CHECK ((NOT ((product IS NULL) AND (distribution IS NULL))))
);

CREATE SEQUENCE milestone_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE milestone_id_seq OWNED BY milestone.id;

CREATE TABLE mirror (
    id integer NOT NULL,
    owner integer NOT NULL,
    baseurl text NOT NULL,
    country integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    freshness integer DEFAULT 99 NOT NULL,
    lastcheckeddate timestamp without time zone,
    approved boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirror_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirror_id_seq OWNED BY mirror.id;

CREATE TABLE mirrorcdimagedistroseries (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distroseries integer NOT NULL,
    flavour text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrorcdimagedistroseries_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrorcdimagedistroseries_id_seq OWNED BY mirrorcdimagedistroseries.id;

CREATE TABLE mirrorcontent (
    id integer NOT NULL,
    mirror integer NOT NULL,
    distroarchseries integer NOT NULL,
    component integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrorcontent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrorcontent_id_seq OWNED BY mirrorcontent.id;

CREATE TABLE mirrordistroarchseries (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distroarchseries integer NOT NULL,
    freshness integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrordistroarchseries_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrordistroarchseries_id_seq OWNED BY mirrordistroarchseries.id;

CREATE TABLE mirrordistroseriessource (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distroseries integer NOT NULL,
    freshness integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrordistroseriessource_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrordistroseriessource_id_seq OWNED BY mirrordistroseriessource.id;

CREATE TABLE mirrorproberecord (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    log_file integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);

CREATE SEQUENCE mirrorproberecord_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrorproberecord_id_seq OWNED BY mirrorproberecord.id;

CREATE TABLE mirrorsourcecontent (
    id integer NOT NULL,
    mirror integer NOT NULL,
    distroseries integer NOT NULL,
    component integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrorsourcecontent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrorsourcecontent_id_seq OWNED BY mirrorsourcecontent.id;

CREATE TABLE nameblacklist (
    id integer NOT NULL,
    regexp text NOT NULL,
    comment text,
    CONSTRAINT valid_regexp CHECK (valid_regexp(regexp))
);

CREATE SEQUENCE nameblacklist_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE nameblacklist_id_seq OWNED BY nameblacklist.id;

CREATE TABLE oauthaccesstoken (
    id integer NOT NULL,
    consumer integer NOT NULL,
    person integer NOT NULL,
    permission integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_expires timestamp without time zone,
    key text NOT NULL,
    secret text NOT NULL,
    product integer,
    project integer,
    distribution integer,
    sourcepackagename integer,
    CONSTRAINT just_one_context CHECK ((null_count(ARRAY[product, project, distribution]) >= 2)),
    CONSTRAINT sourcepackagename_needs_distro CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);

CREATE SEQUENCE oauthaccesstoken_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE oauthaccesstoken_id_seq OWNED BY oauthaccesstoken.id;

CREATE TABLE oauthconsumer (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    disabled boolean DEFAULT false NOT NULL,
    key text NOT NULL,
    secret text
);

CREATE SEQUENCE oauthconsumer_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE oauthconsumer_id_seq OWNED BY oauthconsumer.id;

CREATE TABLE oauthnonce (
    id integer NOT NULL,
    request_timestamp timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    nonce text NOT NULL,
    access_token integer NOT NULL
);

CREATE SEQUENCE oauthnonce_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE oauthnonce_id_seq OWNED BY oauthnonce.id;

CREATE TABLE oauthrequesttoken (
    id integer NOT NULL,
    consumer integer NOT NULL,
    person integer,
    permission integer,
    date_expires timestamp without time zone,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_reviewed timestamp without time zone,
    key text NOT NULL,
    secret text NOT NULL,
    product integer,
    project integer,
    distribution integer,
    sourcepackagename integer,
    CONSTRAINT just_one_context CHECK ((null_count(ARRAY[product, project, distribution]) >= 2)),
    CONSTRAINT reviewed_request CHECK ((((date_reviewed IS NULL) = (person IS NULL)) AND ((date_reviewed IS NULL) = (permission IS NULL)))),
    CONSTRAINT sourcepackagename_needs_distro CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);

CREATE SEQUENCE oauthrequesttoken_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE oauthrequesttoken_id_seq OWNED BY oauthrequesttoken.id;

CREATE TABLE officialbugtag (
    id integer NOT NULL,
    tag text NOT NULL,
    distribution integer,
    project integer,
    product integer,
    CONSTRAINT context_required CHECK (((product IS NOT NULL) OR (distribution IS NOT NULL)))
);

CREATE SEQUENCE officialbugtag_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE officialbugtag_id_seq OWNED BY officialbugtag.id;

CREATE TABLE openidassociation (
    server_url character varying(2047) NOT NULL,
    handle character varying(255) NOT NULL,
    secret bytea,
    issued integer,
    lifetime integer,
    assoc_type character varying(64),
    CONSTRAINT secret_length_constraint CHECK ((length(secret) <= 128))
);

CREATE TABLE openidconsumerassociation (
    server_url character varying(2047) NOT NULL,
    handle character varying(255) NOT NULL,
    secret bytea,
    issued integer,
    lifetime integer,
    assoc_type character varying(64),
    CONSTRAINT secret_length_constraint CHECK ((length(secret) <= 128))
);

CREATE TABLE openidconsumernonce (
    server_url character varying(2047) NOT NULL,
    "timestamp" integer NOT NULL,
    salt character(40) NOT NULL
);

CREATE TABLE openidrpconfig (
    id integer NOT NULL,
    trust_root text NOT NULL,
    displayname text NOT NULL,
    description text NOT NULL,
    logo integer,
    allowed_sreg text,
    creation_rationale integer DEFAULT 13 NOT NULL,
    can_query_any_team boolean DEFAULT false NOT NULL,
    auto_authorize boolean DEFAULT false NOT NULL
);

CREATE SEQUENCE openidrpconfig_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE openidrpconfig_id_seq OWNED BY openidrpconfig.id;

CREATE TABLE openidrpsummary (
    id integer NOT NULL,
    account integer NOT NULL,
    openid_identifier text NOT NULL,
    trust_root text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_used timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    total_logins integer DEFAULT 1 NOT NULL
);

CREATE SEQUENCE openidrpsummary_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE openidrpsummary_id_seq OWNED BY openidrpsummary.id;

CREATE TABLE packagebugsupervisor (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bug_supervisor integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packagebugsupervisor_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagebugsupervisor_id_seq OWNED BY packagebugsupervisor.id;

CREATE TABLE packagebuild (
    id integer NOT NULL,
    build_farm_job integer NOT NULL,
    archive integer NOT NULL,
    pocket integer DEFAULT 0 NOT NULL,
    upload_log integer,
    dependencies text
);

CREATE SEQUENCE packagebuild_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagebuild_id_seq OWNED BY packagebuild.id;

CREATE TABLE packagecopyrequest (
    id integer NOT NULL,
    target_archive integer NOT NULL,
    target_distroseries integer,
    target_component integer,
    target_pocket integer,
    copy_binaries boolean DEFAULT false NOT NULL,
    source_archive integer NOT NULL,
    source_distroseries integer,
    source_component integer,
    source_pocket integer,
    requester integer NOT NULL,
    status integer NOT NULL,
    reason text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_completed timestamp without time zone
);

CREATE SEQUENCE packagecopyrequest_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagecopyrequest_id_seq OWNED BY packagecopyrequest.id;

CREATE TABLE packagediff (
    id integer NOT NULL,
    date_requested timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    requester integer NOT NULL,
    from_source integer NOT NULL,
    to_source integer NOT NULL,
    date_fulfilled timestamp without time zone,
    diff_content integer,
    status integer DEFAULT 0 NOT NULL,
    CONSTRAINT distinct_sources CHECK ((from_source <> to_source))
);

CREATE SEQUENCE packagediff_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagediff_id_seq OWNED BY packagediff.id;

CREATE TABLE packageselection (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    sourcepackagename integer,
    binarypackagename integer,
    action integer NOT NULL,
    component integer,
    section integer,
    priority integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packageselection_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packageselection_id_seq OWNED BY packageselection.id;

CREATE TABLE packageset (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    packagesetgroup integer NOT NULL,
    distroseries integer NOT NULL,
    CONSTRAINT packageset_name_check CHECK (valid_name(name))
);

CREATE SEQUENCE packageset_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packageset_id_seq OWNED BY packageset.id;

CREATE TABLE packagesetgroup (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    owner integer NOT NULL
);

CREATE SEQUENCE packagesetgroup_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagesetgroup_id_seq OWNED BY packagesetgroup.id;

CREATE TABLE packagesetinclusion (
    id integer NOT NULL,
    parent integer NOT NULL,
    child integer NOT NULL
);

CREATE SEQUENCE packagesetinclusion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagesetinclusion_id_seq OWNED BY packagesetinclusion.id;

CREATE TABLE packagesetsources (
    id integer NOT NULL,
    packageset integer NOT NULL,
    sourcepackagename integer NOT NULL
);

CREATE SEQUENCE packagesetsources_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagesetsources_id_seq OWNED BY packagesetsources.id;

CREATE TABLE packageupload (
    id integer NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    distroseries integer NOT NULL,
    pocket integer NOT NULL,
    changesfile integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    signing_key integer,
    archive integer NOT NULL
);

CREATE SEQUENCE packageupload_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packageupload_id_seq OWNED BY packageupload.id;

CREATE TABLE packageuploadbuild (
    id integer NOT NULL,
    packageupload integer NOT NULL,
    build integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packageuploadbuild_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packageuploadbuild_id_seq OWNED BY packageuploadbuild.id;

CREATE TABLE packageuploadcustom (
    id integer NOT NULL,
    packageupload integer NOT NULL,
    customformat integer NOT NULL,
    libraryfilealias integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packageuploadcustom_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packageuploadcustom_id_seq OWNED BY packageuploadcustom.id;

CREATE TABLE packageuploadsource (
    id integer NOT NULL,
    packageupload integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packageuploadsource_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packageuploadsource_id_seq OWNED BY packageuploadsource.id;

CREATE TABLE packaging (
    packaging integer NOT NULL,
    id integer DEFAULT nextval(('packaging_id_seq'::text)::regclass) NOT NULL,
    sourcepackagename integer,
    distroseries integer,
    productseries integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    owner integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packaging_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packaging_id_seq OWNED BY packaging.id;

CREATE TABLE parsedapachelog (
    id integer NOT NULL,
    first_line text NOT NULL,
    bytes_read integer NOT NULL,
    date_last_parsed timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE parsedapachelog_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE parsedapachelog_id_seq OWNED BY parsedapachelog.id;

CREATE SEQUENCE person_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE person_id_seq OWNED BY person.id;

CREATE TABLE personlanguage (
    id integer NOT NULL,
    person integer NOT NULL,
    language integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE personlanguage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE personlanguage_id_seq OWNED BY personlanguage.id;

CREATE TABLE personlocation (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    person integer NOT NULL,
    latitude double precision,
    longitude double precision,
    time_zone text,
    last_modified_by integer NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    visible boolean DEFAULT true,
    locked boolean DEFAULT false,
    CONSTRAINT latitude_and_longitude_together CHECK (((latitude IS NULL) = (longitude IS NULL)))
);

CREATE SEQUENCE personlocation_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE personlocation_id_seq OWNED BY personlocation.id;

CREATE TABLE personnotification (
    id integer NOT NULL,
    person integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_emailed timestamp without time zone,
    body text NOT NULL,
    subject text NOT NULL
);

CREATE SEQUENCE personnotification_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE personnotification_id_seq OWNED BY personnotification.id;

CREATE TABLE pillarname (
    id integer NOT NULL,
    name text NOT NULL,
    product integer,
    project integer,
    distribution integer,
    active boolean DEFAULT true NOT NULL,
    alias_for integer,
    CONSTRAINT only_one_target CHECK ((null_count(ARRAY[product, project, distribution, alias_for]) = 3)),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE pillarname_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pillarname_id_seq OWNED BY pillarname.id;

CREATE TABLE pocketchroot (
    id integer NOT NULL,
    distroarchseries integer,
    pocket integer NOT NULL,
    chroot integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE pocketchroot_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pocketchroot_id_seq OWNED BY pocketchroot.id;

CREATE TABLE pocomment (
    id integer NOT NULL,
    potemplate integer NOT NULL,
    pomsgid integer,
    language integer,
    potranslation integer,
    commenttext text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer
);

CREATE SEQUENCE pocomment_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pocomment_id_seq OWNED BY pocomment.id;

CREATE TABLE poexportrequest (
    id integer NOT NULL,
    person integer NOT NULL,
    potemplate integer NOT NULL,
    pofile integer,
    format integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE poexportrequest_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE poexportrequest_id_seq OWNED BY poexportrequest.id;

CREATE TABLE pofile (
    id integer NOT NULL,
    potemplate integer NOT NULL,
    language integer NOT NULL,
    description text,
    topcomment text,
    header text,
    fuzzyheader boolean NOT NULL,
    lasttranslator integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    lastparsed timestamp without time zone,
    owner integer NOT NULL,
    variant text,
    path text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    from_sourcepackagename integer,
    unreviewed_count integer DEFAULT 0 NOT NULL,
    date_changed timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_variant CHECK ((variant <> ''::text))
);

CREATE SEQUENCE pofile_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pofile_id_seq OWNED BY pofile.id;

CREATE TABLE pofiletranslator (
    id integer NOT NULL,
    person integer NOT NULL,
    pofile integer NOT NULL,
    latest_message integer NOT NULL,
    date_last_touched timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE pofiletranslator_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pofiletranslator_id_seq OWNED BY pofiletranslator.id;

CREATE TABLE poll (
    id integer NOT NULL,
    team integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    dateopens timestamp without time zone NOT NULL,
    datecloses timestamp without time zone NOT NULL,
    proposition text NOT NULL,
    type integer NOT NULL,
    allowspoilt boolean DEFAULT false NOT NULL,
    secrecy integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT sane_dates CHECK ((dateopens < datecloses))
);

CREATE SEQUENCE poll_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE poll_id_seq OWNED BY poll.id;

CREATE TABLE polloption (
    id integer NOT NULL,
    poll integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    active boolean DEFAULT true NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE polloption_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE polloption_id_seq OWNED BY polloption.id;

CREATE TABLE pomsgid (
    id integer NOT NULL,
    msgid text NOT NULL
);

CREATE SEQUENCE pomsgid_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pomsgid_id_seq OWNED BY pomsgid.id;

CREATE TABLE posubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    potemplate integer NOT NULL,
    language integer,
    notificationinterval interval,
    lastnotified timestamp without time zone,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE posubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE posubscription_id_seq OWNED BY posubscription.id;

CREATE TABLE potemplate (
    id integer NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    description text,
    copyright text,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    path text NOT NULL,
    iscurrent boolean NOT NULL,
    messagecount integer NOT NULL,
    owner integer NOT NULL,
    sourcepackagename integer,
    distroseries integer,
    sourcepackageversion text,
    header text NOT NULL,
    binarypackagename integer,
    languagepack boolean DEFAULT false NOT NULL,
    productseries integer,
    from_sourcepackagename integer,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    source_file integer,
    source_file_format integer DEFAULT 1 NOT NULL,
    name text NOT NULL,
    translation_domain text NOT NULL,
    CONSTRAINT potemplate_valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_from_sourcepackagename CHECK (((sourcepackagename IS NOT NULL) OR (from_sourcepackagename IS NULL))),
    CONSTRAINT valid_link CHECK ((((productseries IS NULL) <> (distroseries IS NULL)) AND ((distroseries IS NULL) = (sourcepackagename IS NULL))))
);

CREATE SEQUENCE potemplate_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE potemplate_id_seq OWNED BY potemplate.id;

CREATE TABLE potmsgset (
    id integer NOT NULL,
    msgid_singular integer NOT NULL,
    sequence integer,
    potemplate integer,
    commenttext text,
    filereferences text,
    sourcecomment text,
    flagscomment text,
    context text,
    msgid_plural integer
);

CREATE TABLE translationtemplateitem (
    id integer NOT NULL,
    potemplate integer NOT NULL,
    sequence integer NOT NULL,
    potmsgset integer NOT NULL,
    CONSTRAINT translationtemplateitem_sequence_check CHECK ((sequence >= 0))
);

CREATE VIEW potexport AS
    SELECT COALESCE((potmsgset.id)::text, 'X'::text) AS id, potemplate.productseries, potemplate.sourcepackagename, potemplate.distroseries, potemplate.id AS potemplate, potemplate.header AS template_header, potemplate.languagepack, translationtemplateitem.sequence, potmsgset.id AS potmsgset, potmsgset.commenttext AS comment, potmsgset.sourcecomment AS source_comment, potmsgset.filereferences AS file_references, potmsgset.flagscomment AS flags_comment, potmsgset.context, msgid_singular.msgid AS msgid_singular, msgid_plural.msgid AS msgid_plural FROM ((((potmsgset JOIN translationtemplateitem ON ((translationtemplateitem.potmsgset = potmsgset.id))) JOIN potemplate ON ((potemplate.id = translationtemplateitem.potemplate))) LEFT JOIN pomsgid msgid_singular ON ((potmsgset.msgid_singular = msgid_singular.id))) LEFT JOIN pomsgid msgid_plural ON ((potmsgset.msgid_plural = msgid_plural.id)));

CREATE SEQUENCE potmsgset_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE potmsgset_id_seq OWNED BY potmsgset.id;

CREATE TABLE potranslation (
    id integer NOT NULL,
    translation text NOT NULL
);

CREATE SEQUENCE potranslation_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE potranslation_id_seq OWNED BY potranslation.id;

CREATE TABLE previewdiff (
    id integer NOT NULL,
    source_revision_id text NOT NULL,
    target_revision_id text NOT NULL,
    dependent_revision_id text,
    diff integer NOT NULL,
    conflicts text
);

CREATE SEQUENCE previewdiff_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE previewdiff_id_seq OWNED BY previewdiff.id;

CREATE TABLE processor (
    id integer NOT NULL,
    family integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL
);

CREATE SEQUENCE processor_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE processor_id_seq OWNED BY processor.id;

CREATE TABLE processorfamily (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    restricted boolean DEFAULT false NOT NULL
);

CREATE SEQUENCE processorfamily_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE processorfamily_id_seq OWNED BY processorfamily.id;

CREATE SEQUENCE product_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE product_id_seq OWNED BY product.id;

CREATE TABLE productbounty (
    id integer NOT NULL,
    bounty integer NOT NULL,
    product integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE productbounty_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productbounty_id_seq OWNED BY productbounty.id;

CREATE TABLE productcvsmodule (
    id integer NOT NULL,
    product integer NOT NULL,
    anonroot text NOT NULL,
    module text NOT NULL,
    weburl text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE productcvsmodule_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productcvsmodule_id_seq OWNED BY productcvsmodule.id;

CREATE TABLE productlicense (
    id integer NOT NULL,
    product integer NOT NULL,
    license integer NOT NULL
);

CREATE SEQUENCE productlicense_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productlicense_id_seq OWNED BY productlicense.id;

CREATE TABLE productrelease (
    id integer NOT NULL,
    datereleased timestamp without time zone NOT NULL,
    release_notes text,
    changelog text,
    owner integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    milestone integer NOT NULL
);

CREATE SEQUENCE productrelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productrelease_id_seq OWNED BY productrelease.id;

CREATE TABLE productreleasefile (
    productrelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval(('productreleasefile_id_seq'::text)::regclass) NOT NULL,
    description text,
    uploader integer NOT NULL,
    date_uploaded timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    fti ts2.tsvector,
    signature integer
);

CREATE SEQUENCE productreleasefile_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productreleasefile_id_seq OWNED BY productreleasefile.id;

CREATE TABLE productseries (
    id integer NOT NULL,
    product integer NOT NULL,
    name text NOT NULL,
    summary text NOT NULL,
    releasefileglob text,
    releaseverstyle integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    driver integer,
    owner integer NOT NULL,
    status integer DEFAULT 2 NOT NULL,
    translations_autoimport_mode integer DEFAULT 1 NOT NULL,
    branch integer,
    translations_branch integer,
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_releasefileglob CHECK (valid_absolute_url(releasefileglob))
);

CREATE SEQUENCE productseries_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productseries_id_seq OWNED BY productseries.id;

CREATE TABLE productseriescodeimport (
    id integer NOT NULL,
    productseries integer NOT NULL,
    codeimport integer NOT NULL
);

CREATE SEQUENCE productseriescodeimport_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productseriescodeimport_id_seq OWNED BY productseriescodeimport.id;

CREATE TABLE productsvnmodule (
    id integer NOT NULL,
    product integer NOT NULL,
    locationurl text NOT NULL,
    weburl text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE productsvnmodule_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productsvnmodule_id_seq OWNED BY productsvnmodule.id;

CREATE TABLE project (
    id integer NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    homepageurl text,
    wikiurl text,
    lastdoap text,
    sourceforgeproject text,
    freshmeatproject text,
    reviewed boolean DEFAULT false NOT NULL,
    active boolean DEFAULT true NOT NULL,
    fti ts2.tsvector,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    driver integer,
    bugtracker integer,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    bug_reporting_guidelines text,
    reviewer_whiteboard text,
    registrant integer NOT NULL,
    max_bug_heat integer,
    bug_reported_acknowledgement text,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE project_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE project_id_seq OWNED BY project.id;

CREATE TABLE projectbounty (
    id integer NOT NULL,
    bounty integer NOT NULL,
    project integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE projectbounty_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE projectbounty_id_seq OWNED BY projectbounty.id;

CREATE TABLE projectrelationship (
    id integer NOT NULL,
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);

CREATE SEQUENCE projectrelationship_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE projectrelationship_id_seq OWNED BY projectrelationship.id;

CREATE TABLE pushmirroraccess (
    id integer NOT NULL,
    name text NOT NULL,
    person integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE pushmirroraccess_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pushmirroraccess_id_seq OWNED BY pushmirroraccess.id;

CREATE TABLE question (
    id integer NOT NULL,
    owner integer NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    assignee integer,
    answerer integer,
    product integer,
    distribution integer,
    sourcepackagename integer,
    status integer NOT NULL,
    priority integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datelastquery timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    dateaccepted timestamp without time zone,
    datedue timestamp without time zone,
    datelastresponse timestamp without time zone,
    date_solved timestamp without time zone,
    dateclosed timestamp without time zone,
    whiteboard text,
    fti ts2.tsvector,
    answer integer,
    language integer NOT NULL,
    faq integer,
    CONSTRAINT product_or_distro CHECK (((product IS NULL) <> (distribution IS NULL))),
    CONSTRAINT sourcepackagename_needs_distro CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);

CREATE SEQUENCE question_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE question_id_seq OWNED BY question.id;

CREATE TABLE questionbug (
    id integer NOT NULL,
    question integer NOT NULL,
    bug integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE questionbug_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE questionbug_id_seq OWNED BY questionbug.id;

CREATE TABLE questionmessage (
    id integer NOT NULL,
    question integer NOT NULL,
    message integer NOT NULL,
    action integer NOT NULL,
    new_status integer NOT NULL
);

CREATE SEQUENCE questionmessage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE questionmessage_id_seq OWNED BY questionmessage.id;

CREATE TABLE questionreopening (
    id integer NOT NULL,
    question integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    reopener integer NOT NULL,
    answerer integer,
    date_solved timestamp without time zone,
    priorstate integer NOT NULL
);

CREATE SEQUENCE questionreopening_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE questionreopening_id_seq OWNED BY questionreopening.id;

CREATE TABLE questionsubscription (
    id integer NOT NULL,
    question integer NOT NULL,
    person integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE questionsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE questionsubscription_id_seq OWNED BY questionsubscription.id;

CREATE TABLE requestedcds (
    id integer NOT NULL,
    request integer NOT NULL,
    quantity integer NOT NULL,
    flavour integer NOT NULL,
    distroseries integer NOT NULL,
    architecture integer NOT NULL,
    quantityapproved integer NOT NULL,
    CONSTRAINT quantity_is_positive CHECK ((quantity >= 0)),
    CONSTRAINT quantityapproved_is_positive CHECK ((quantityapproved >= 0))
);

CREATE SEQUENCE requestedcds_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE requestedcds_id_seq OWNED BY requestedcds.id;

CREATE SEQUENCE revision_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE revision_id_seq OWNED BY revision.id;

CREATE TABLE revisionauthor (
    id integer NOT NULL,
    name text NOT NULL,
    email text,
    person integer
);

CREATE SEQUENCE revisionauthor_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE revisionauthor_id_seq OWNED BY revisionauthor.id;

CREATE TABLE revisioncache (
    id integer NOT NULL,
    revision integer NOT NULL,
    revision_author integer NOT NULL,
    revision_date timestamp without time zone NOT NULL,
    product integer,
    distroseries integer,
    sourcepackagename integer,
    private boolean NOT NULL,
    CONSTRAINT valid_target CHECK ((((distroseries IS NULL) = (sourcepackagename IS NULL)) AND (((distroseries IS NULL) AND (product IS NULL)) OR ((distroseries IS NULL) <> (product IS NULL)))))
);

CREATE SEQUENCE revisioncache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE revisioncache_id_seq OWNED BY revisioncache.id;

CREATE VIEW revisionnumber AS
    SELECT branchrevision.id, branchrevision.sequence, branchrevision.branch, branchrevision.revision FROM branchrevision;

CREATE TABLE revisionparent (
    id integer NOT NULL,
    sequence integer NOT NULL,
    revision integer NOT NULL,
    parent_id text NOT NULL
);

CREATE SEQUENCE revisionparent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE revisionparent_id_seq OWNED BY revisionparent.id;

CREATE TABLE revisionproperty (
    id integer NOT NULL,
    revision integer NOT NULL,
    name text NOT NULL,
    value text NOT NULL
);

CREATE SEQUENCE revisionproperty_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE revisionproperty_id_seq OWNED BY revisionproperty.id;

CREATE TABLE scriptactivity (
    id integer NOT NULL,
    name text NOT NULL,
    hostname text NOT NULL,
    date_started timestamp without time zone NOT NULL,
    date_completed timestamp without time zone NOT NULL
);

CREATE SEQUENCE scriptactivity_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE scriptactivity_id_seq OWNED BY scriptactivity.id;

CREATE TABLE section (
    id integer NOT NULL,
    name text NOT NULL
);

CREATE SEQUENCE section_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE section_id_seq OWNED BY section.id;

CREATE TABLE sectionselection (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    section integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE sectionselection_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sectionselection_id_seq OWNED BY sectionselection.id;

CREATE TABLE seriessourcepackagebranch (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    pocket integer NOT NULL,
    sourcepackagename integer NOT NULL,
    branch integer NOT NULL,
    registrant integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE seriessourcepackagebranch_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE seriessourcepackagebranch_id_seq OWNED BY seriessourcepackagebranch.id;

CREATE TABLE shipitreport (
    id integer NOT NULL,
    datecreated timestamp without time zone NOT NULL,
    csvfile integer NOT NULL
);

CREATE SEQUENCE shipitreport_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shipitreport_id_seq OWNED BY shipitreport.id;

CREATE TABLE shipitsurvey (
    id integer NOT NULL,
    account integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    exported boolean DEFAULT false NOT NULL
);

CREATE SEQUENCE shipitsurvey_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shipitsurvey_id_seq OWNED BY shipitsurvey.id;

CREATE TABLE shipitsurveyanswer (
    id integer NOT NULL,
    answer text NOT NULL
);

CREATE SEQUENCE shipitsurveyanswer_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shipitsurveyanswer_id_seq OWNED BY shipitsurveyanswer.id;

CREATE TABLE shipitsurveyquestion (
    id integer NOT NULL,
    question text NOT NULL
);

CREATE SEQUENCE shipitsurveyquestion_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shipitsurveyquestion_id_seq OWNED BY shipitsurveyquestion.id;

CREATE TABLE shipitsurveyresult (
    id integer NOT NULL,
    survey integer NOT NULL,
    question integer NOT NULL,
    answer integer
);

CREATE SEQUENCE shipitsurveyresult_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shipitsurveyresult_id_seq OWNED BY shipitsurveyresult.id;

CREATE TABLE shipment (
    id integer NOT NULL,
    logintoken text NOT NULL,
    shippingrun integer NOT NULL,
    dateshipped timestamp without time zone,
    shippingservice integer NOT NULL,
    trackingcode text
);

CREATE SEQUENCE shipment_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shipment_id_seq OWNED BY shipment.id;

CREATE TABLE shippingrequest (
    id integer NOT NULL,
    recipient integer NOT NULL,
    whoapproved integer,
    whocancelled integer,
    daterequested timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    reason text,
    highpriority boolean DEFAULT false NOT NULL,
    recipientdisplayname text NOT NULL,
    addressline1 text NOT NULL,
    addressline2 text,
    organization text,
    city text NOT NULL,
    province text,
    country integer NOT NULL,
    postcode text,
    phone text,
    fti ts2.tsvector,
    shipment integer,
    status integer NOT NULL,
    normalized_address text NOT NULL,
    type integer,
    is_admin_request boolean DEFAULT false NOT NULL,
    CONSTRAINT enforce_shipped_status CHECK (((status <> 4) OR (shipment IS NOT NULL))),
    CONSTRAINT printable_addresses CHECK (is_printable_ascii((((((((COALESCE(recipientdisplayname, ''::text) || COALESCE(addressline1, ''::text)) || COALESCE(addressline2, ''::text)) || COALESCE(organization, ''::text)) || COALESCE(city, ''::text)) || COALESCE(province, ''::text)) || COALESCE(postcode, ''::text)) || COALESCE(phone, ''::text))))
);

CREATE SEQUENCE shippingrequest_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shippingrequest_id_seq OWNED BY shippingrequest.id;

CREATE TABLE shippingrun (
    id integer NOT NULL,
    datecreated timestamp without time zone NOT NULL,
    sentforshipping boolean DEFAULT false NOT NULL,
    csvfile integer,
    requests_count integer NOT NULL
);

CREATE SEQUENCE shippingrun_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shippingrun_id_seq OWNED BY shippingrun.id;

CREATE TABLE signedcodeofconduct (
    id integer NOT NULL,
    owner integer NOT NULL,
    signingkey integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    signedcode text,
    recipient integer,
    active boolean DEFAULT false NOT NULL,
    admincomment text
);

CREATE SEQUENCE signedcodeofconduct_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE signedcodeofconduct_id_seq OWNED BY signedcodeofconduct.id;

CREATE TABLE sourcepackagepublishinghistory (
    id integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    distroseries integer NOT NULL,
    status integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    datecreated timestamp without time zone NOT NULL,
    datepublished timestamp without time zone,
    datesuperseded timestamp without time zone,
    supersededby integer,
    datemadepending timestamp without time zone,
    scheduleddeletiondate timestamp without time zone,
    dateremoved timestamp without time zone,
    pocket integer DEFAULT 0 NOT NULL,
    archive integer NOT NULL,
    removed_by integer,
    removal_comment text
);

CREATE TABLE sourcepackagereleasefile (
    sourcepackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval(('sourcepackagereleasefile_id_seq'::text)::regclass) NOT NULL
);

CREATE VIEW sourcepackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (securesourcepackagepublishinghistory.id)::text) AS id, distroseries.distribution, securesourcepackagepublishinghistory.id AS sourcepackagepublishing, sourcepackagereleasefile.libraryfile AS libraryfilealias, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, distroseries.name AS distroseriesname, securesourcepackagepublishinghistory.status AS publishingstatus, securesourcepackagepublishinghistory.pocket, securesourcepackagepublishinghistory.archive FROM ((((((sourcepackagepublishinghistory securesourcepackagepublishinghistory JOIN sourcepackagerelease ON ((securesourcepackagepublishinghistory.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN sourcepackagereleasefile ON ((sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id))) JOIN libraryfilealias ON ((libraryfilealias.id = sourcepackagereleasefile.libraryfile))) JOIN distroseries ON ((securesourcepackagepublishinghistory.distroseries = distroseries.id))) JOIN component ON ((securesourcepackagepublishinghistory.component = component.id))) WHERE (securesourcepackagepublishinghistory.dateremoved IS NULL);

CREATE TABLE sourcepackageformatselection (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    format integer NOT NULL
);

CREATE SEQUENCE sourcepackageformatselection_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackageformatselection_id_seq OWNED BY sourcepackageformatselection.id;

CREATE SEQUENCE sourcepackagename_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagename_id_seq OWNED BY sourcepackagename.id;

CREATE SEQUENCE sourcepackagepublishinghistory_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagepublishinghistory_id_seq OWNED BY sourcepackagepublishinghistory.id;

CREATE TABLE sourcepackagerecipe (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    build_daily boolean DEFAULT false NOT NULL,
    daily_build_archive integer,
    is_stale boolean DEFAULT true NOT NULL
);

CREATE SEQUENCE sourcepackagerecipe_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagerecipe_id_seq OWNED BY sourcepackagerecipe.id;

CREATE TABLE sourcepackagerecipebuild (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    requester integer NOT NULL,
    recipe integer NOT NULL,
    manifest integer,
    package_build integer NOT NULL
);

CREATE SEQUENCE sourcepackagerecipebuild_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagerecipebuild_id_seq OWNED BY sourcepackagerecipebuild.id;

CREATE TABLE sourcepackagerecipebuildjob (
    id integer NOT NULL,
    job integer NOT NULL,
    sourcepackage_recipe_build integer
);

CREATE SEQUENCE sourcepackagerecipebuildjob_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagerecipebuildjob_id_seq OWNED BY sourcepackagerecipebuildjob.id;

CREATE TABLE sourcepackagerecipedata (
    id integer NOT NULL,
    base_branch integer NOT NULL,
    recipe_format text NOT NULL,
    deb_version_template text NOT NULL,
    revspec text,
    sourcepackage_recipe integer,
    sourcepackage_recipe_build integer,
    CONSTRAINT sourcepackagerecipedata__recipe_or_build_is_not_null CHECK (((sourcepackage_recipe IS NULL) <> (sourcepackage_recipe_build IS NULL)))
);

CREATE SEQUENCE sourcepackagerecipedata_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagerecipedata_id_seq OWNED BY sourcepackagerecipedata.id;

CREATE TABLE sourcepackagerecipedatainstruction (
    id integer NOT NULL,
    name text NOT NULL,
    type integer NOT NULL,
    comment text,
    line_number integer NOT NULL,
    branch integer NOT NULL,
    revspec text,
    directory text,
    recipe_data integer NOT NULL,
    parent_instruction integer,
    CONSTRAINT sourcepackagerecipedatainstruction__directory_not_null CHECK ((((type = 1) AND (directory IS NULL)) OR ((type = 2) AND (directory IS NOT NULL))))
);

CREATE SEQUENCE sourcepackagerecipedatainstruction_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagerecipedatainstruction_id_seq OWNED BY sourcepackagerecipedatainstruction.id;

CREATE TABLE sourcepackagerecipedistroseries (
    id integer NOT NULL,
    sourcepackagerecipe integer NOT NULL,
    distroseries integer NOT NULL
);

CREATE SEQUENCE sourcepackagerecipedistroseries_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagerecipedistroseries_id_seq OWNED BY sourcepackagerecipedistroseries.id;

CREATE SEQUENCE sourcepackagerelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagerelease_id_seq OWNED BY sourcepackagerelease.id;

CREATE SEQUENCE sourcepackagereleasefile_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagereleasefile_id_seq OWNED BY sourcepackagereleasefile.id;

CREATE TABLE specification (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text,
    owner integer NOT NULL,
    assignee integer,
    drafter integer,
    approver integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    product integer,
    productseries integer,
    distribution integer,
    distroseries integer,
    milestone integer,
    definition_status integer NOT NULL,
    priority integer DEFAULT 5 NOT NULL,
    specurl text,
    whiteboard text,
    superseded_by integer,
    direction_approved boolean DEFAULT false NOT NULL,
    man_days integer,
    implementation_status integer DEFAULT 0 NOT NULL,
    goalstatus integer DEFAULT 30 NOT NULL,
    fti ts2.tsvector,
    goal_proposer integer,
    date_goal_proposed timestamp without time zone,
    goal_decider integer,
    date_goal_decided timestamp without time zone,
    completer integer,
    date_completed timestamp without time zone,
    starter integer,
    date_started timestamp without time zone,
    private boolean DEFAULT false NOT NULL,
    CONSTRAINT distribution_and_distroseries CHECK (((distroseries IS NULL) OR (distribution IS NOT NULL))),
    CONSTRAINT product_and_productseries CHECK (((productseries IS NULL) OR (product IS NOT NULL))),
    CONSTRAINT product_xor_distribution CHECK (((product IS NULL) <> (distribution IS NULL))),
    CONSTRAINT specification_completion_fully_recorded_chk CHECK (((date_completed IS NULL) = (completer IS NULL))),
    CONSTRAINT specification_completion_recorded_chk CHECK (((date_completed IS NULL) <> (((implementation_status = 90) OR (definition_status = ANY (ARRAY[60, 70]))) OR ((implementation_status = 95) AND (definition_status = 10))))),
    CONSTRAINT specification_decision_recorded CHECK (((goalstatus = 30) OR ((goal_decider IS NOT NULL) AND (date_goal_decided IS NOT NULL)))),
    CONSTRAINT specification_goal_nomination_chk CHECK ((((productseries IS NULL) AND (distroseries IS NULL)) OR ((goal_proposer IS NOT NULL) AND (date_goal_proposed IS NOT NULL)))),
    CONSTRAINT specification_not_self_superseding CHECK ((superseded_by <> id)),
    CONSTRAINT specification_start_fully_recorded_chk CHECK (((date_started IS NULL) = (starter IS NULL))),
    CONSTRAINT specification_start_recorded_chk CHECK (((date_started IS NULL) <> ((implementation_status <> ALL (ARRAY[0, 5, 10, 95])) OR ((implementation_status = 95) AND (definition_status = 10))))),
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_url CHECK (valid_absolute_url(specurl))
);

CREATE SEQUENCE specification_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specification_id_seq OWNED BY specification.id;

CREATE TABLE specificationbranch (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    specification integer NOT NULL,
    branch integer NOT NULL,
    summary text,
    registrant integer NOT NULL
);

CREATE SEQUENCE specificationbranch_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specificationbranch_id_seq OWNED BY specificationbranch.id;

CREATE TABLE specificationbug (
    id integer NOT NULL,
    specification integer NOT NULL,
    bug integer NOT NULL
);

CREATE SEQUENCE specificationbug_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specificationbug_id_seq OWNED BY specificationbug.id;

CREATE TABLE specificationdependency (
    id integer NOT NULL,
    specification integer NOT NULL,
    dependency integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT specificationdependency_not_self CHECK ((specification <> dependency))
);

CREATE SEQUENCE specificationdependency_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specificationdependency_id_seq OWNED BY specificationdependency.id;

CREATE TABLE specificationfeedback (
    id integer NOT NULL,
    specification integer NOT NULL,
    reviewer integer NOT NULL,
    requester integer NOT NULL,
    queuemsg text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE specificationfeedback_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specificationfeedback_id_seq OWNED BY specificationfeedback.id;

CREATE TABLE specificationmessage (
    id integer NOT NULL,
    specification integer,
    message integer,
    visible boolean DEFAULT true NOT NULL
);

CREATE SEQUENCE specificationmessage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specificationmessage_id_seq OWNED BY specificationmessage.id;

CREATE TABLE specificationsubscription (
    id integer NOT NULL,
    specification integer NOT NULL,
    person integer NOT NULL,
    essential boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE specificationsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specificationsubscription_id_seq OWNED BY specificationsubscription.id;

CREATE TABLE spokenin (
    language integer NOT NULL,
    country integer NOT NULL,
    id integer DEFAULT nextval(('spokenin_id_seq'::text)::regclass) NOT NULL
);

CREATE SEQUENCE spokenin_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE spokenin_id_seq OWNED BY spokenin.id;

CREATE TABLE sprint (
    id integer NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    home_page text,
    address text,
    time_zone text NOT NULL,
    time_starts timestamp without time zone NOT NULL,
    time_ends timestamp without time zone NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    driver integer,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    CONSTRAINT sprint_starts_before_ends CHECK ((time_starts < time_ends))
);

CREATE SEQUENCE sprint_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sprint_id_seq OWNED BY sprint.id;

CREATE TABLE sprintattendance (
    id integer NOT NULL,
    attendee integer NOT NULL,
    sprint integer NOT NULL,
    time_starts timestamp without time zone NOT NULL,
    time_ends timestamp without time zone NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    is_physical boolean DEFAULT false NOT NULL,
    CONSTRAINT sprintattendance_starts_before_ends CHECK ((time_starts < time_ends))
);

CREATE SEQUENCE sprintattendance_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sprintattendance_id_seq OWNED BY sprintattendance.id;

CREATE TABLE sprintspecification (
    id integer NOT NULL,
    sprint integer NOT NULL,
    specification integer NOT NULL,
    status integer DEFAULT 30 NOT NULL,
    whiteboard text,
    registrant integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    decider integer,
    date_decided timestamp without time zone,
    CONSTRAINT sprintspecification_decision_recorded CHECK (((status = 30) OR ((decider IS NOT NULL) AND (date_decided IS NOT NULL))))
);

CREATE SEQUENCE sprintspecification_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sprintspecification_id_seq OWNED BY sprintspecification.id;

CREATE TABLE sshkey (
    id integer NOT NULL,
    person integer,
    keytype integer NOT NULL,
    keytext text NOT NULL,
    comment text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE sshkey_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sshkey_id_seq OWNED BY sshkey.id;

CREATE TABLE standardshipitrequest (
    id integer NOT NULL,
    quantityx86 integer NOT NULL,
    quantityppc integer NOT NULL,
    quantityamd64 integer NOT NULL,
    isdefault boolean DEFAULT false NOT NULL,
    flavour integer NOT NULL,
    description text,
    CONSTRAINT quantityamd64_is_positive CHECK ((quantityamd64 >= 0)),
    CONSTRAINT quantityppc_is_positive CHECK ((quantityppc >= 0)),
    CONSTRAINT quantityx86_is_positive CHECK ((quantityx86 >= 0))
);

CREATE SEQUENCE standardshipitrequest_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE standardshipitrequest_id_seq OWNED BY standardshipitrequest.id;

CREATE TABLE staticdiff (
    id integer NOT NULL,
    from_revision_id text NOT NULL,
    to_revision_id text NOT NULL,
    diff integer NOT NULL
);

CREATE SEQUENCE staticdiff_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE staticdiff_id_seq OWNED BY staticdiff.id;

CREATE TABLE structuralsubscription (
    id integer NOT NULL,
    product integer,
    productseries integer,
    project integer,
    milestone integer,
    distribution integer,
    distroseries integer,
    sourcepackagename integer,
    subscriber integer NOT NULL,
    subscribed_by integer NOT NULL,
    bug_notification_level integer NOT NULL,
    blueprint_notification_level integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT one_target CHECK ((null_count(ARRAY[product, productseries, project, distroseries, distribution, milestone]) = 5)),
    CONSTRAINT sourcepackagename_requires_distribution CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);

CREATE SEQUENCE structuralsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE structuralsubscription_id_seq OWNED BY structuralsubscription.id;

CREATE TABLE suggestivepotemplate (
    potemplate integer NOT NULL
);

CREATE TABLE teammembership (
    id integer NOT NULL,
    person integer NOT NULL,
    team integer NOT NULL,
    status integer NOT NULL,
    date_joined timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    date_expires timestamp without time zone,
    last_changed_by integer,
    last_change_comment text,
    proposed_by integer,
    acknowledged_by integer,
    reviewed_by integer,
    date_proposed timestamp without time zone,
    date_last_changed timestamp without time zone,
    date_acknowledged timestamp without time zone,
    date_reviewed timestamp without time zone,
    proponent_comment text,
    acknowledger_comment text,
    reviewer_comment text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE teammembership_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE teammembership_id_seq OWNED BY teammembership.id;

CREATE TABLE teamparticipation (
    id integer NOT NULL,
    team integer NOT NULL,
    person integer NOT NULL
);

CREATE SEQUENCE teamparticipation_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE teamparticipation_id_seq OWNED BY teamparticipation.id;

CREATE TABLE temporaryblobstorage (
    id integer NOT NULL,
    uuid text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    file_alias integer NOT NULL
);

CREATE SEQUENCE temporaryblobstorage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE temporaryblobstorage_id_seq OWNED BY temporaryblobstorage.id;

CREATE TABLE translationgroup (
    id integer NOT NULL,
    name text NOT NULL,
    title text,
    summary text,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    owner integer NOT NULL,
    translation_guide_url text
);

CREATE SEQUENCE translationgroup_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translationgroup_id_seq OWNED BY translationgroup.id;

CREATE TABLE translationimportqueueentry (
    id integer NOT NULL,
    path text NOT NULL,
    content integer NOT NULL,
    importer integer NOT NULL,
    dateimported timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    distroseries integer,
    sourcepackagename integer,
    productseries integer,
    is_published boolean NOT NULL,
    pofile integer,
    potemplate integer,
    status integer DEFAULT 5 NOT NULL,
    date_status_changed timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    format integer DEFAULT 1 NOT NULL,
    error_output text,
    CONSTRAINT valid_link CHECK ((((productseries IS NULL) <> (distroseries IS NULL)) AND ((distroseries IS NULL) = (sourcepackagename IS NULL))))
);

CREATE SEQUENCE translationimportqueueentry_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translationimportqueueentry_id_seq OWNED BY translationimportqueueentry.id;

CREATE TABLE translationmessage (
    id integer NOT NULL,
    pofile integer,
    potmsgset integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    submitter integer NOT NULL,
    date_reviewed timestamp without time zone,
    reviewer integer,
    msgstr0 integer,
    msgstr1 integer,
    msgstr2 integer,
    msgstr3 integer,
    comment text,
    origin integer NOT NULL,
    validation_status integer DEFAULT 0 NOT NULL,
    is_current boolean DEFAULT false NOT NULL,
    is_fuzzy boolean DEFAULT false NOT NULL,
    is_imported boolean DEFAULT false NOT NULL,
    was_obsolete_in_last_import boolean DEFAULT false NOT NULL,
    was_fuzzy_in_last_import boolean DEFAULT false NOT NULL,
    msgstr4 integer,
    msgstr5 integer,
    potemplate integer,
    language integer,
    variant text,
    CONSTRAINT translationmessage__reviewer__date_reviewed__valid CHECK (((reviewer IS NULL) = (date_reviewed IS NULL)))
);

CREATE SEQUENCE translationmessage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translationmessage_id_seq OWNED BY translationmessage.id;

CREATE TABLE translationrelicensingagreement (
    id integer NOT NULL,
    person integer NOT NULL,
    allow_relicensing boolean DEFAULT true NOT NULL,
    date_decided timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE translationrelicensingagreement_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translationrelicensingagreement_id_seq OWNED BY translationrelicensingagreement.id;

CREATE SEQUENCE translationtemplateitem_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translationtemplateitem_id_seq OWNED BY translationtemplateitem.id;

CREATE TABLE translator (
    id integer NOT NULL,
    translationgroup integer NOT NULL,
    language integer NOT NULL,
    translator integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    style_guide_url text
);

CREATE SEQUENCE translator_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translator_id_seq OWNED BY translator.id;

CREATE TABLE usertouseremail (
    id integer NOT NULL,
    sender integer NOT NULL,
    recipient integer NOT NULL,
    date_sent timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subject text NOT NULL,
    message_id text NOT NULL
);

CREATE SEQUENCE usertouseremail_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE usertouseremail_id_seq OWNED BY usertouseremail.id;

CREATE VIEW validpersoncache AS
    SELECT emailaddress.person AS id FROM emailaddress, account WHERE ((((emailaddress.account = account.id) AND (emailaddress.person IS NOT NULL)) AND (emailaddress.status = 4)) AND (account.status = 20));

CREATE VIEW validpersonorteamcache AS
    SELECT person.id FROM ((person LEFT JOIN emailaddress ON ((person.id = emailaddress.person))) LEFT JOIN account ON ((emailaddress.account = account.id))) WHERE (((person.teamowner IS NOT NULL) AND (person.merged IS NULL)) OR (((person.teamowner IS NULL) AND (account.status = 20)) AND (emailaddress.status = 4)));

CREATE TABLE vote (
    id integer NOT NULL,
    person integer,
    poll integer NOT NULL,
    preference integer,
    option integer,
    token text NOT NULL
);

CREATE SEQUENCE vote_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE vote_id_seq OWNED BY vote.id;

CREATE TABLE votecast (
    id integer NOT NULL,
    person integer NOT NULL,
    poll integer NOT NULL
);

CREATE SEQUENCE votecast_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE votecast_id_seq OWNED BY votecast.id;

CREATE TABLE webserviceban (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    person integer,
    consumer integer,
    token integer,
    ip inet,
    active boolean DEFAULT true,
    CONSTRAINT at_least_one_spec CHECK (((ip IS NOT NULL) OR (null_count(ARRAY[person, consumer, token]) < 3))),
    CONSTRAINT person_or_consumer_or_token_or_none CHECK ((null_count(ARRAY[person, consumer, token]) >= 2))
);

CREATE SEQUENCE webserviceban_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE webserviceban_id_seq OWNED BY webserviceban.id;

CREATE TABLE wikiname (
    id integer NOT NULL,
    person integer NOT NULL,
    wiki text NOT NULL,
    wikiname text NOT NULL
);

CREATE SEQUENCE wikiname_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE wikiname_id_seq OWNED BY wikiname.id;

ALTER TABLE account ALTER COLUMN id SET DEFAULT nextval('account_id_seq'::regclass);

ALTER TABLE accountpassword ALTER COLUMN id SET DEFAULT nextval('accountpassword_id_seq'::regclass);

ALTER TABLE announcement ALTER COLUMN id SET DEFAULT nextval('announcement_id_seq'::regclass);

ALTER TABLE answercontact ALTER COLUMN id SET DEFAULT nextval('answercontact_id_seq'::regclass);

ALTER TABLE apportjob ALTER COLUMN id SET DEFAULT nextval('apportjob_id_seq'::regclass);

ALTER TABLE archive ALTER COLUMN id SET DEFAULT nextval('archive_id_seq'::regclass);

ALTER TABLE archivearch ALTER COLUMN id SET DEFAULT nextval('archivearch_id_seq'::regclass);

ALTER TABLE archiveauthtoken ALTER COLUMN id SET DEFAULT nextval('archiveauthtoken_id_seq'::regclass);

ALTER TABLE archivedependency ALTER COLUMN id SET DEFAULT nextval('archivedependency_id_seq'::regclass);

ALTER TABLE archivejob ALTER COLUMN id SET DEFAULT nextval('archivejob_id_seq'::regclass);

ALTER TABLE archivepermission ALTER COLUMN id SET DEFAULT nextval('archivepermission_id_seq'::regclass);

ALTER TABLE archivesubscriber ALTER COLUMN id SET DEFAULT nextval('archivesubscriber_id_seq'::regclass);

ALTER TABLE authtoken ALTER COLUMN id SET DEFAULT nextval('authtoken_id_seq'::regclass);

ALTER TABLE binarypackagebuild ALTER COLUMN id SET DEFAULT nextval('binarypackagebuild_id_seq'::regclass);

ALTER TABLE binarypackagename ALTER COLUMN id SET DEFAULT nextval('binarypackagename_id_seq'::regclass);

ALTER TABLE binarypackagepublishinghistory ALTER COLUMN id SET DEFAULT nextval('binarypackagepublishinghistory_id_seq'::regclass);

ALTER TABLE binarypackagerelease ALTER COLUMN id SET DEFAULT nextval('binarypackagerelease_id_seq'::regclass);

ALTER TABLE binarypackagereleasedownloadcount ALTER COLUMN id SET DEFAULT nextval('binarypackagereleasedownloadcount_id_seq'::regclass);

ALTER TABLE bounty ALTER COLUMN id SET DEFAULT nextval('bounty_id_seq'::regclass);

ALTER TABLE bountymessage ALTER COLUMN id SET DEFAULT nextval('bountymessage_id_seq'::regclass);

ALTER TABLE bountysubscription ALTER COLUMN id SET DEFAULT nextval('bountysubscription_id_seq'::regclass);

ALTER TABLE branch ALTER COLUMN id SET DEFAULT nextval('branch_id_seq'::regclass);

ALTER TABLE branchjob ALTER COLUMN id SET DEFAULT nextval('branchjob_id_seq'::regclass);

ALTER TABLE branchmergeproposal ALTER COLUMN id SET DEFAULT nextval('branchmergeproposal_id_seq'::regclass);

ALTER TABLE branchmergeproposaljob ALTER COLUMN id SET DEFAULT nextval('branchmergeproposaljob_id_seq'::regclass);

ALTER TABLE branchmergerobot ALTER COLUMN id SET DEFAULT nextval('branchmergerobot_id_seq'::regclass);

ALTER TABLE branchrevision ALTER COLUMN id SET DEFAULT nextval('branchrevision_id_seq'::regclass);

ALTER TABLE branchsubscription ALTER COLUMN id SET DEFAULT nextval('branchsubscription_id_seq'::regclass);

ALTER TABLE branchvisibilitypolicy ALTER COLUMN id SET DEFAULT nextval('branchvisibilitypolicy_id_seq'::regclass);

ALTER TABLE bug ALTER COLUMN id SET DEFAULT nextval('bug_id_seq'::regclass);

ALTER TABLE bugactivity ALTER COLUMN id SET DEFAULT nextval('bugactivity_id_seq'::regclass);

ALTER TABLE bugaffectsperson ALTER COLUMN id SET DEFAULT nextval('bugaffectsperson_id_seq'::regclass);

ALTER TABLE bugattachment ALTER COLUMN id SET DEFAULT nextval('bugattachment_id_seq'::regclass);

ALTER TABLE bugbranch ALTER COLUMN id SET DEFAULT nextval('bugbranch_id_seq'::regclass);

ALTER TABLE bugcve ALTER COLUMN id SET DEFAULT nextval('bugcve_id_seq'::regclass);

ALTER TABLE bugjob ALTER COLUMN id SET DEFAULT nextval('bugjob_id_seq'::regclass);

ALTER TABLE bugmessage ALTER COLUMN id SET DEFAULT nextval('bugmessage_id_seq'::regclass);

ALTER TABLE bugnomination ALTER COLUMN id SET DEFAULT nextval('bugnomination_id_seq'::regclass);

ALTER TABLE bugnotification ALTER COLUMN id SET DEFAULT nextval('bugnotification_id_seq'::regclass);

ALTER TABLE bugnotificationattachment ALTER COLUMN id SET DEFAULT nextval('bugnotificationattachment_id_seq'::regclass);

ALTER TABLE bugnotificationrecipient ALTER COLUMN id SET DEFAULT nextval('bugnotificationrecipient_id_seq'::regclass);

ALTER TABLE bugpackageinfestation ALTER COLUMN id SET DEFAULT nextval('bugpackageinfestation_id_seq'::regclass);

ALTER TABLE bugproductinfestation ALTER COLUMN id SET DEFAULT nextval('bugproductinfestation_id_seq'::regclass);

ALTER TABLE bugsubscription ALTER COLUMN id SET DEFAULT nextval('bugsubscription_id_seq'::regclass);

ALTER TABLE bugtag ALTER COLUMN id SET DEFAULT nextval('bugtag_id_seq'::regclass);

ALTER TABLE bugtask ALTER COLUMN id SET DEFAULT nextval('bugtask_id_seq'::regclass);

ALTER TABLE bugtracker ALTER COLUMN id SET DEFAULT nextval('bugtracker_id_seq'::regclass);

ALTER TABLE bugtrackeralias ALTER COLUMN id SET DEFAULT nextval('bugtrackeralias_id_seq'::regclass);

ALTER TABLE bugtrackerperson ALTER COLUMN id SET DEFAULT nextval('bugtrackerperson_id_seq'::regclass);

ALTER TABLE bugwatch ALTER COLUMN id SET DEFAULT nextval('bugwatch_id_seq'::regclass);

ALTER TABLE bugwatchactivity ALTER COLUMN id SET DEFAULT nextval('bugwatchactivity_id_seq'::regclass);

ALTER TABLE builder ALTER COLUMN id SET DEFAULT nextval('builder_id_seq'::regclass);

ALTER TABLE buildfarmjob ALTER COLUMN id SET DEFAULT nextval('buildfarmjob_id_seq'::regclass);

ALTER TABLE buildpackagejob ALTER COLUMN id SET DEFAULT nextval('buildpackagejob_id_seq'::regclass);

ALTER TABLE buildqueue ALTER COLUMN id SET DEFAULT nextval('buildqueue_id_seq'::regclass);

ALTER TABLE codeimport ALTER COLUMN id SET DEFAULT nextval('codeimport_id_seq'::regclass);

ALTER TABLE codeimportevent ALTER COLUMN id SET DEFAULT nextval('codeimportevent_id_seq'::regclass);

ALTER TABLE codeimporteventdata ALTER COLUMN id SET DEFAULT nextval('codeimporteventdata_id_seq'::regclass);

ALTER TABLE codeimportjob ALTER COLUMN id SET DEFAULT nextval('codeimportjob_id_seq'::regclass);

ALTER TABLE codeimportmachine ALTER COLUMN id SET DEFAULT nextval('codeimportmachine_id_seq'::regclass);

ALTER TABLE codeimportresult ALTER COLUMN id SET DEFAULT nextval('codeimportresult_id_seq'::regclass);

ALTER TABLE codereviewmessage ALTER COLUMN id SET DEFAULT nextval('codereviewmessage_id_seq'::regclass);

ALTER TABLE codereviewvote ALTER COLUMN id SET DEFAULT nextval('codereviewvote_id_seq'::regclass);

ALTER TABLE commercialsubscription ALTER COLUMN id SET DEFAULT nextval('commercialsubscription_id_seq'::regclass);

ALTER TABLE component ALTER COLUMN id SET DEFAULT nextval('component_id_seq'::regclass);

ALTER TABLE componentselection ALTER COLUMN id SET DEFAULT nextval('componentselection_id_seq'::regclass);

ALTER TABLE continent ALTER COLUMN id SET DEFAULT nextval('continent_id_seq'::regclass);

ALTER TABLE country ALTER COLUMN id SET DEFAULT nextval('country_id_seq'::regclass);

ALTER TABLE customlanguagecode ALTER COLUMN id SET DEFAULT nextval('customlanguagecode_id_seq'::regclass);

ALTER TABLE cve ALTER COLUMN id SET DEFAULT nextval('cve_id_seq'::regclass);

ALTER TABLE cvereference ALTER COLUMN id SET DEFAULT nextval('cvereference_id_seq'::regclass);

ALTER TABLE diff ALTER COLUMN id SET DEFAULT nextval('diff_id_seq'::regclass);

ALTER TABLE distribution ALTER COLUMN id SET DEFAULT nextval('distribution_id_seq'::regclass);

ALTER TABLE distributionbounty ALTER COLUMN id SET DEFAULT nextval('distributionbounty_id_seq'::regclass);

ALTER TABLE distributionmirror ALTER COLUMN id SET DEFAULT nextval('distributionmirror_id_seq'::regclass);

ALTER TABLE distributionsourcepackage ALTER COLUMN id SET DEFAULT nextval('distributionsourcepackage_id_seq'::regclass);

ALTER TABLE distributionsourcepackagecache ALTER COLUMN id SET DEFAULT nextval('distributionsourcepackagecache_id_seq'::regclass);

ALTER TABLE distroarchseries ALTER COLUMN id SET DEFAULT nextval('distroarchseries_id_seq'::regclass);

ALTER TABLE distrocomponentuploader ALTER COLUMN id SET DEFAULT nextval('distrocomponentuploader_id_seq'::regclass);

ALTER TABLE distroseries ALTER COLUMN id SET DEFAULT nextval('distroseries_id_seq'::regclass);

ALTER TABLE distroserieslanguage ALTER COLUMN id SET DEFAULT nextval('distroserieslanguage_id_seq'::regclass);

ALTER TABLE distroseriespackagecache ALTER COLUMN id SET DEFAULT nextval('distroseriespackagecache_id_seq'::regclass);

ALTER TABLE emailaddress ALTER COLUMN id SET DEFAULT nextval('emailaddress_id_seq'::regclass);

ALTER TABLE entitlement ALTER COLUMN id SET DEFAULT nextval('entitlement_id_seq'::regclass);

ALTER TABLE faq ALTER COLUMN id SET DEFAULT nextval('faq_id_seq'::regclass);

ALTER TABLE featuredproject ALTER COLUMN id SET DEFAULT nextval('featuredproject_id_seq'::regclass);

ALTER TABLE flatpackagesetinclusion ALTER COLUMN id SET DEFAULT nextval('flatpackagesetinclusion_id_seq'::regclass);

ALTER TABLE fticache ALTER COLUMN id SET DEFAULT nextval('fticache_id_seq'::regclass);

ALTER TABLE gpgkey ALTER COLUMN id SET DEFAULT nextval('gpgkey_id_seq'::regclass);

ALTER TABLE hwdevice ALTER COLUMN id SET DEFAULT nextval('hwdevice_id_seq'::regclass);

ALTER TABLE hwdeviceclass ALTER COLUMN id SET DEFAULT nextval('hwdeviceclass_id_seq'::regclass);

ALTER TABLE hwdevicedriverlink ALTER COLUMN id SET DEFAULT nextval('hwdevicedriverlink_id_seq'::regclass);

ALTER TABLE hwdevicenamevariant ALTER COLUMN id SET DEFAULT nextval('hwdevicenamevariant_id_seq'::regclass);

ALTER TABLE hwdmihandle ALTER COLUMN id SET DEFAULT nextval('hwdmihandle_id_seq'::regclass);

ALTER TABLE hwdmivalue ALTER COLUMN id SET DEFAULT nextval('hwdmivalue_id_seq'::regclass);

ALTER TABLE hwdriver ALTER COLUMN id SET DEFAULT nextval('hwdriver_id_seq'::regclass);

ALTER TABLE hwsubmission ALTER COLUMN id SET DEFAULT nextval('hwsubmission_id_seq'::regclass);

ALTER TABLE hwsubmissionbug ALTER COLUMN id SET DEFAULT nextval('hwsubmissionbug_id_seq'::regclass);

ALTER TABLE hwsubmissiondevice ALTER COLUMN id SET DEFAULT nextval('hwsubmissiondevice_id_seq'::regclass);

ALTER TABLE hwsystemfingerprint ALTER COLUMN id SET DEFAULT nextval('hwsystemfingerprint_id_seq'::regclass);

ALTER TABLE hwtest ALTER COLUMN id SET DEFAULT nextval('hwtest_id_seq'::regclass);

ALTER TABLE hwtestanswer ALTER COLUMN id SET DEFAULT nextval('hwtestanswer_id_seq'::regclass);

ALTER TABLE hwtestanswerchoice ALTER COLUMN id SET DEFAULT nextval('hwtestanswerchoice_id_seq'::regclass);

ALTER TABLE hwtestanswercount ALTER COLUMN id SET DEFAULT nextval('hwtestanswercount_id_seq'::regclass);

ALTER TABLE hwtestanswercountdevice ALTER COLUMN id SET DEFAULT nextval('hwtestanswercountdevice_id_seq'::regclass);

ALTER TABLE hwtestanswerdevice ALTER COLUMN id SET DEFAULT nextval('hwtestanswerdevice_id_seq'::regclass);

ALTER TABLE hwvendorid ALTER COLUMN id SET DEFAULT nextval('hwvendorid_id_seq'::regclass);

ALTER TABLE hwvendorname ALTER COLUMN id SET DEFAULT nextval('hwvendorname_id_seq'::regclass);

ALTER TABLE ircid ALTER COLUMN id SET DEFAULT nextval('ircid_id_seq'::regclass);

ALTER TABLE jabberid ALTER COLUMN id SET DEFAULT nextval('jabberid_id_seq'::regclass);

ALTER TABLE job ALTER COLUMN id SET DEFAULT nextval('job_id_seq'::regclass);

ALTER TABLE karma ALTER COLUMN id SET DEFAULT nextval('karma_id_seq'::regclass);

ALTER TABLE karmaaction ALTER COLUMN id SET DEFAULT nextval('karmaaction_id_seq'::regclass);

ALTER TABLE karmacache ALTER COLUMN id SET DEFAULT nextval('karmacache_id_seq'::regclass);

ALTER TABLE karmacategory ALTER COLUMN id SET DEFAULT nextval('karmacategory_id_seq'::regclass);

ALTER TABLE karmatotalcache ALTER COLUMN id SET DEFAULT nextval('karmatotalcache_id_seq'::regclass);

ALTER TABLE language ALTER COLUMN id SET DEFAULT nextval('language_id_seq'::regclass);

ALTER TABLE languagepack ALTER COLUMN id SET DEFAULT nextval('languagepack_id_seq'::regclass);

ALTER TABLE launchpadstatistic ALTER COLUMN id SET DEFAULT nextval('launchpadstatistic_id_seq'::regclass);

ALTER TABLE libraryfilealias ALTER COLUMN id SET DEFAULT nextval('libraryfilealias_id_seq'::regclass);

ALTER TABLE libraryfilecontent ALTER COLUMN id SET DEFAULT nextval('libraryfilecontent_id_seq'::regclass);

ALTER TABLE libraryfiledownloadcount ALTER COLUMN id SET DEFAULT nextval('libraryfiledownloadcount_id_seq'::regclass);

ALTER TABLE logintoken ALTER COLUMN id SET DEFAULT nextval('logintoken_id_seq'::regclass);

ALTER TABLE mailinglist ALTER COLUMN id SET DEFAULT nextval('mailinglist_id_seq'::regclass);

ALTER TABLE mailinglistban ALTER COLUMN id SET DEFAULT nextval('mailinglistban_id_seq'::regclass);

ALTER TABLE mailinglistsubscription ALTER COLUMN id SET DEFAULT nextval('mailinglistsubscription_id_seq'::regclass);

ALTER TABLE mentoringoffer ALTER COLUMN id SET DEFAULT nextval('mentoringoffer_id_seq'::regclass);

ALTER TABLE mergedirectivejob ALTER COLUMN id SET DEFAULT nextval('mergedirectivejob_id_seq'::regclass);

ALTER TABLE message ALTER COLUMN id SET DEFAULT nextval('message_id_seq'::regclass);

ALTER TABLE messageapproval ALTER COLUMN id SET DEFAULT nextval('messageapproval_id_seq'::regclass);

ALTER TABLE messagechunk ALTER COLUMN id SET DEFAULT nextval('messagechunk_id_seq'::regclass);

ALTER TABLE milestone ALTER COLUMN id SET DEFAULT nextval('milestone_id_seq'::regclass);

ALTER TABLE mirror ALTER COLUMN id SET DEFAULT nextval('mirror_id_seq'::regclass);

ALTER TABLE mirrorcdimagedistroseries ALTER COLUMN id SET DEFAULT nextval('mirrorcdimagedistroseries_id_seq'::regclass);

ALTER TABLE mirrorcontent ALTER COLUMN id SET DEFAULT nextval('mirrorcontent_id_seq'::regclass);

ALTER TABLE mirrordistroarchseries ALTER COLUMN id SET DEFAULT nextval('mirrordistroarchseries_id_seq'::regclass);

ALTER TABLE mirrordistroseriessource ALTER COLUMN id SET DEFAULT nextval('mirrordistroseriessource_id_seq'::regclass);

ALTER TABLE mirrorproberecord ALTER COLUMN id SET DEFAULT nextval('mirrorproberecord_id_seq'::regclass);

ALTER TABLE mirrorsourcecontent ALTER COLUMN id SET DEFAULT nextval('mirrorsourcecontent_id_seq'::regclass);

ALTER TABLE nameblacklist ALTER COLUMN id SET DEFAULT nextval('nameblacklist_id_seq'::regclass);

ALTER TABLE oauthaccesstoken ALTER COLUMN id SET DEFAULT nextval('oauthaccesstoken_id_seq'::regclass);

ALTER TABLE oauthconsumer ALTER COLUMN id SET DEFAULT nextval('oauthconsumer_id_seq'::regclass);

ALTER TABLE oauthnonce ALTER COLUMN id SET DEFAULT nextval('oauthnonce_id_seq'::regclass);

ALTER TABLE oauthrequesttoken ALTER COLUMN id SET DEFAULT nextval('oauthrequesttoken_id_seq'::regclass);

ALTER TABLE officialbugtag ALTER COLUMN id SET DEFAULT nextval('officialbugtag_id_seq'::regclass);

ALTER TABLE openidrpconfig ALTER COLUMN id SET DEFAULT nextval('openidrpconfig_id_seq'::regclass);

ALTER TABLE openidrpsummary ALTER COLUMN id SET DEFAULT nextval('openidrpsummary_id_seq'::regclass);

ALTER TABLE packagebugsupervisor ALTER COLUMN id SET DEFAULT nextval('packagebugsupervisor_id_seq'::regclass);

ALTER TABLE packagebuild ALTER COLUMN id SET DEFAULT nextval('packagebuild_id_seq'::regclass);

ALTER TABLE packagecopyrequest ALTER COLUMN id SET DEFAULT nextval('packagecopyrequest_id_seq'::regclass);

ALTER TABLE packagediff ALTER COLUMN id SET DEFAULT nextval('packagediff_id_seq'::regclass);

ALTER TABLE packageselection ALTER COLUMN id SET DEFAULT nextval('packageselection_id_seq'::regclass);

ALTER TABLE packageset ALTER COLUMN id SET DEFAULT nextval('packageset_id_seq'::regclass);

ALTER TABLE packagesetgroup ALTER COLUMN id SET DEFAULT nextval('packagesetgroup_id_seq'::regclass);

ALTER TABLE packagesetinclusion ALTER COLUMN id SET DEFAULT nextval('packagesetinclusion_id_seq'::regclass);

ALTER TABLE packagesetsources ALTER COLUMN id SET DEFAULT nextval('packagesetsources_id_seq'::regclass);

ALTER TABLE packageupload ALTER COLUMN id SET DEFAULT nextval('packageupload_id_seq'::regclass);

ALTER TABLE packageuploadbuild ALTER COLUMN id SET DEFAULT nextval('packageuploadbuild_id_seq'::regclass);

ALTER TABLE packageuploadcustom ALTER COLUMN id SET DEFAULT nextval('packageuploadcustom_id_seq'::regclass);

ALTER TABLE packageuploadsource ALTER COLUMN id SET DEFAULT nextval('packageuploadsource_id_seq'::regclass);

ALTER TABLE parsedapachelog ALTER COLUMN id SET DEFAULT nextval('parsedapachelog_id_seq'::regclass);

ALTER TABLE person ALTER COLUMN id SET DEFAULT nextval('person_id_seq'::regclass);

ALTER TABLE personlanguage ALTER COLUMN id SET DEFAULT nextval('personlanguage_id_seq'::regclass);

ALTER TABLE personlocation ALTER COLUMN id SET DEFAULT nextval('personlocation_id_seq'::regclass);

ALTER TABLE personnotification ALTER COLUMN id SET DEFAULT nextval('personnotification_id_seq'::regclass);

ALTER TABLE pillarname ALTER COLUMN id SET DEFAULT nextval('pillarname_id_seq'::regclass);

ALTER TABLE pocketchroot ALTER COLUMN id SET DEFAULT nextval('pocketchroot_id_seq'::regclass);

ALTER TABLE pocomment ALTER COLUMN id SET DEFAULT nextval('pocomment_id_seq'::regclass);

ALTER TABLE poexportrequest ALTER COLUMN id SET DEFAULT nextval('poexportrequest_id_seq'::regclass);

ALTER TABLE pofile ALTER COLUMN id SET DEFAULT nextval('pofile_id_seq'::regclass);

ALTER TABLE pofiletranslator ALTER COLUMN id SET DEFAULT nextval('pofiletranslator_id_seq'::regclass);

ALTER TABLE poll ALTER COLUMN id SET DEFAULT nextval('poll_id_seq'::regclass);

ALTER TABLE polloption ALTER COLUMN id SET DEFAULT nextval('polloption_id_seq'::regclass);

ALTER TABLE pomsgid ALTER COLUMN id SET DEFAULT nextval('pomsgid_id_seq'::regclass);

ALTER TABLE posubscription ALTER COLUMN id SET DEFAULT nextval('posubscription_id_seq'::regclass);

ALTER TABLE potemplate ALTER COLUMN id SET DEFAULT nextval('potemplate_id_seq'::regclass);

ALTER TABLE potmsgset ALTER COLUMN id SET DEFAULT nextval('potmsgset_id_seq'::regclass);

ALTER TABLE potranslation ALTER COLUMN id SET DEFAULT nextval('potranslation_id_seq'::regclass);

ALTER TABLE previewdiff ALTER COLUMN id SET DEFAULT nextval('previewdiff_id_seq'::regclass);

ALTER TABLE processor ALTER COLUMN id SET DEFAULT nextval('processor_id_seq'::regclass);

ALTER TABLE processorfamily ALTER COLUMN id SET DEFAULT nextval('processorfamily_id_seq'::regclass);

ALTER TABLE product ALTER COLUMN id SET DEFAULT nextval('product_id_seq'::regclass);

ALTER TABLE productbounty ALTER COLUMN id SET DEFAULT nextval('productbounty_id_seq'::regclass);

ALTER TABLE productcvsmodule ALTER COLUMN id SET DEFAULT nextval('productcvsmodule_id_seq'::regclass);

ALTER TABLE productlicense ALTER COLUMN id SET DEFAULT nextval('productlicense_id_seq'::regclass);

ALTER TABLE productrelease ALTER COLUMN id SET DEFAULT nextval('productrelease_id_seq'::regclass);

ALTER TABLE productseries ALTER COLUMN id SET DEFAULT nextval('productseries_id_seq'::regclass);

ALTER TABLE productseriescodeimport ALTER COLUMN id SET DEFAULT nextval('productseriescodeimport_id_seq'::regclass);

ALTER TABLE productsvnmodule ALTER COLUMN id SET DEFAULT nextval('productsvnmodule_id_seq'::regclass);

ALTER TABLE project ALTER COLUMN id SET DEFAULT nextval('project_id_seq'::regclass);

ALTER TABLE projectbounty ALTER COLUMN id SET DEFAULT nextval('projectbounty_id_seq'::regclass);

ALTER TABLE projectrelationship ALTER COLUMN id SET DEFAULT nextval('projectrelationship_id_seq'::regclass);

ALTER TABLE pushmirroraccess ALTER COLUMN id SET DEFAULT nextval('pushmirroraccess_id_seq'::regclass);

ALTER TABLE question ALTER COLUMN id SET DEFAULT nextval('question_id_seq'::regclass);

ALTER TABLE questionbug ALTER COLUMN id SET DEFAULT nextval('questionbug_id_seq'::regclass);

ALTER TABLE questionmessage ALTER COLUMN id SET DEFAULT nextval('questionmessage_id_seq'::regclass);

ALTER TABLE questionreopening ALTER COLUMN id SET DEFAULT nextval('questionreopening_id_seq'::regclass);

ALTER TABLE questionsubscription ALTER COLUMN id SET DEFAULT nextval('questionsubscription_id_seq'::regclass);

ALTER TABLE requestedcds ALTER COLUMN id SET DEFAULT nextval('requestedcds_id_seq'::regclass);

ALTER TABLE revision ALTER COLUMN id SET DEFAULT nextval('revision_id_seq'::regclass);

ALTER TABLE revisionauthor ALTER COLUMN id SET DEFAULT nextval('revisionauthor_id_seq'::regclass);

ALTER TABLE revisioncache ALTER COLUMN id SET DEFAULT nextval('revisioncache_id_seq'::regclass);

ALTER TABLE revisionparent ALTER COLUMN id SET DEFAULT nextval('revisionparent_id_seq'::regclass);

ALTER TABLE revisionproperty ALTER COLUMN id SET DEFAULT nextval('revisionproperty_id_seq'::regclass);

ALTER TABLE scriptactivity ALTER COLUMN id SET DEFAULT nextval('scriptactivity_id_seq'::regclass);

ALTER TABLE section ALTER COLUMN id SET DEFAULT nextval('section_id_seq'::regclass);

ALTER TABLE sectionselection ALTER COLUMN id SET DEFAULT nextval('sectionselection_id_seq'::regclass);

ALTER TABLE seriessourcepackagebranch ALTER COLUMN id SET DEFAULT nextval('seriessourcepackagebranch_id_seq'::regclass);

ALTER TABLE shipitreport ALTER COLUMN id SET DEFAULT nextval('shipitreport_id_seq'::regclass);

ALTER TABLE shipitsurvey ALTER COLUMN id SET DEFAULT nextval('shipitsurvey_id_seq'::regclass);

ALTER TABLE shipitsurveyanswer ALTER COLUMN id SET DEFAULT nextval('shipitsurveyanswer_id_seq'::regclass);

ALTER TABLE shipitsurveyquestion ALTER COLUMN id SET DEFAULT nextval('shipitsurveyquestion_id_seq'::regclass);

ALTER TABLE shipitsurveyresult ALTER COLUMN id SET DEFAULT nextval('shipitsurveyresult_id_seq'::regclass);

ALTER TABLE shipment ALTER COLUMN id SET DEFAULT nextval('shipment_id_seq'::regclass);

ALTER TABLE shippingrequest ALTER COLUMN id SET DEFAULT nextval('shippingrequest_id_seq'::regclass);

ALTER TABLE shippingrun ALTER COLUMN id SET DEFAULT nextval('shippingrun_id_seq'::regclass);

ALTER TABLE signedcodeofconduct ALTER COLUMN id SET DEFAULT nextval('signedcodeofconduct_id_seq'::regclass);

ALTER TABLE sourcepackageformatselection ALTER COLUMN id SET DEFAULT nextval('sourcepackageformatselection_id_seq'::regclass);

ALTER TABLE sourcepackagename ALTER COLUMN id SET DEFAULT nextval('sourcepackagename_id_seq'::regclass);

ALTER TABLE sourcepackagepublishinghistory ALTER COLUMN id SET DEFAULT nextval('sourcepackagepublishinghistory_id_seq'::regclass);

ALTER TABLE sourcepackagerecipe ALTER COLUMN id SET DEFAULT nextval('sourcepackagerecipe_id_seq'::regclass);

ALTER TABLE sourcepackagerecipebuild ALTER COLUMN id SET DEFAULT nextval('sourcepackagerecipebuild_id_seq'::regclass);

ALTER TABLE sourcepackagerecipebuildjob ALTER COLUMN id SET DEFAULT nextval('sourcepackagerecipebuildjob_id_seq'::regclass);

ALTER TABLE sourcepackagerecipedata ALTER COLUMN id SET DEFAULT nextval('sourcepackagerecipedata_id_seq'::regclass);

ALTER TABLE sourcepackagerecipedatainstruction ALTER COLUMN id SET DEFAULT nextval('sourcepackagerecipedatainstruction_id_seq'::regclass);

ALTER TABLE sourcepackagerecipedistroseries ALTER COLUMN id SET DEFAULT nextval('sourcepackagerecipedistroseries_id_seq'::regclass);

ALTER TABLE sourcepackagerelease ALTER COLUMN id SET DEFAULT nextval('sourcepackagerelease_id_seq'::regclass);

ALTER TABLE specification ALTER COLUMN id SET DEFAULT nextval('specification_id_seq'::regclass);

ALTER TABLE specificationbranch ALTER COLUMN id SET DEFAULT nextval('specificationbranch_id_seq'::regclass);

ALTER TABLE specificationbug ALTER COLUMN id SET DEFAULT nextval('specificationbug_id_seq'::regclass);

ALTER TABLE specificationdependency ALTER COLUMN id SET DEFAULT nextval('specificationdependency_id_seq'::regclass);

ALTER TABLE specificationfeedback ALTER COLUMN id SET DEFAULT nextval('specificationfeedback_id_seq'::regclass);

ALTER TABLE specificationmessage ALTER COLUMN id SET DEFAULT nextval('specificationmessage_id_seq'::regclass);

ALTER TABLE specificationsubscription ALTER COLUMN id SET DEFAULT nextval('specificationsubscription_id_seq'::regclass);

ALTER TABLE sprint ALTER COLUMN id SET DEFAULT nextval('sprint_id_seq'::regclass);

ALTER TABLE sprintattendance ALTER COLUMN id SET DEFAULT nextval('sprintattendance_id_seq'::regclass);

ALTER TABLE sprintspecification ALTER COLUMN id SET DEFAULT nextval('sprintspecification_id_seq'::regclass);

ALTER TABLE sshkey ALTER COLUMN id SET DEFAULT nextval('sshkey_id_seq'::regclass);

ALTER TABLE standardshipitrequest ALTER COLUMN id SET DEFAULT nextval('standardshipitrequest_id_seq'::regclass);

ALTER TABLE staticdiff ALTER COLUMN id SET DEFAULT nextval('staticdiff_id_seq'::regclass);

ALTER TABLE structuralsubscription ALTER COLUMN id SET DEFAULT nextval('structuralsubscription_id_seq'::regclass);

ALTER TABLE teammembership ALTER COLUMN id SET DEFAULT nextval('teammembership_id_seq'::regclass);

ALTER TABLE teamparticipation ALTER COLUMN id SET DEFAULT nextval('teamparticipation_id_seq'::regclass);

ALTER TABLE temporaryblobstorage ALTER COLUMN id SET DEFAULT nextval('temporaryblobstorage_id_seq'::regclass);

ALTER TABLE translationgroup ALTER COLUMN id SET DEFAULT nextval('translationgroup_id_seq'::regclass);

ALTER TABLE translationimportqueueentry ALTER COLUMN id SET DEFAULT nextval('translationimportqueueentry_id_seq'::regclass);

ALTER TABLE translationmessage ALTER COLUMN id SET DEFAULT nextval('translationmessage_id_seq'::regclass);

ALTER TABLE translationrelicensingagreement ALTER COLUMN id SET DEFAULT nextval('translationrelicensingagreement_id_seq'::regclass);

ALTER TABLE translationtemplateitem ALTER COLUMN id SET DEFAULT nextval('translationtemplateitem_id_seq'::regclass);

ALTER TABLE translator ALTER COLUMN id SET DEFAULT nextval('translator_id_seq'::regclass);

ALTER TABLE usertouseremail ALTER COLUMN id SET DEFAULT nextval('usertouseremail_id_seq'::regclass);

ALTER TABLE vote ALTER COLUMN id SET DEFAULT nextval('vote_id_seq'::regclass);

ALTER TABLE votecast ALTER COLUMN id SET DEFAULT nextval('votecast_id_seq'::regclass);

ALTER TABLE webserviceban ALTER COLUMN id SET DEFAULT nextval('webserviceban_id_seq'::regclass);

ALTER TABLE wikiname ALTER COLUMN id SET DEFAULT nextval('wikiname_id_seq'::regclass);

ALTER TABLE ONLY account
    ADD CONSTRAINT account_openid_identifier_key UNIQUE (openid_identifier);

ALTER TABLE ONLY account
    ADD CONSTRAINT account_pkey PRIMARY KEY (id);

ALTER TABLE ONLY accountpassword
    ADD CONSTRAINT accountpassword_account_key UNIQUE (account);

ALTER TABLE ONLY accountpassword
    ADD CONSTRAINT accountpassword_pkey PRIMARY KEY (id);

ALTER TABLE ONLY announcement
    ADD CONSTRAINT announcement_pkey PRIMARY KEY (id);

ALTER TABLE ONLY apportjob
    ADD CONSTRAINT apportjob__job__key UNIQUE (job);

ALTER TABLE ONLY apportjob
    ADD CONSTRAINT apportjob_pkey PRIMARY KEY (id);

ALTER TABLE apportjob CLUSTER ON apportjob_pkey;

ALTER TABLE ONLY archive
    ADD CONSTRAINT archive_pkey PRIMARY KEY (id);

ALTER TABLE ONLY archivearch
    ADD CONSTRAINT archivearch__processorfamily__archive__key UNIQUE (processorfamily, archive);

ALTER TABLE ONLY archivearch
    ADD CONSTRAINT archivearch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY archiveauthtoken
    ADD CONSTRAINT archiveauthtoken_pkey PRIMARY KEY (id);

ALTER TABLE ONLY archiveauthtoken
    ADD CONSTRAINT archiveauthtoken_token_key UNIQUE (token);

ALTER TABLE ONLY archivedependency
    ADD CONSTRAINT archivedependency__unique UNIQUE (archive, dependency);

ALTER TABLE ONLY archivedependency
    ADD CONSTRAINT archivedependency_pkey PRIMARY KEY (id);

ALTER TABLE ONLY archivejob
    ADD CONSTRAINT archivejob__job__key UNIQUE (job);

ALTER TABLE ONLY archivejob
    ADD CONSTRAINT archivejob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY archivepermission
    ADD CONSTRAINT archivepermission_pkey PRIMARY KEY (id);

ALTER TABLE ONLY archivesubscriber
    ADD CONSTRAINT archivesubscriber_pkey PRIMARY KEY (id);

ALTER TABLE ONLY revisionauthor
    ADD CONSTRAINT archuserid_archuserid_key UNIQUE (name);

ALTER TABLE ONLY revisionauthor
    ADD CONSTRAINT archuserid_pkey PRIMARY KEY (id);

ALTER TABLE ONLY authtoken
    ADD CONSTRAINT authtoken__token__key UNIQUE (token);

ALTER TABLE ONLY authtoken
    ADD CONSTRAINT authtoken_pkey PRIMARY KEY (id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_pkey PRIMARY KEY (id);

ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_pkey PRIMARY KEY (id);

ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_name_key UNIQUE (name);

ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_pkey PRIMARY KEY (id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_binarypackagename_key UNIQUE (binarypackagename, build, version);

ALTER TABLE binarypackagerelease CLUSTER ON binarypackagerelease_binarypackagename_key;

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_build_name_uniq UNIQUE (build, binarypackagename);

ALTER TABLE ONLY binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount__archive__binary_package_rele UNIQUE (archive, binary_package_release, day, country);

ALTER TABLE ONLY binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_name_key UNIQUE (name);

ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bountymessage
    ADD CONSTRAINT bountymessage_message_bounty_uniq UNIQUE (message, bounty);

ALTER TABLE ONLY bountymessage
    ADD CONSTRAINT bountymessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_person_key UNIQUE (person, bounty);

ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch__unique_name__key UNIQUE (unique_name);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_url_unique UNIQUE (url);

ALTER TABLE ONLY branchjob
    ADD CONSTRAINT branchjob_job_key UNIQUE (job);

ALTER TABLE ONLY branchjob
    ADD CONSTRAINT branchjob_pkey PRIMARY KEY (id);

ALTER TABLE branchjob CLUSTER ON branchjob_pkey;

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_job_key UNIQUE (job);

ALTER TABLE ONLY branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchmergerobot
    ADD CONSTRAINT branchmergerobot_name_key UNIQUE (name);

ALTER TABLE ONLY branchmergerobot
    ADD CONSTRAINT branchmergerobot_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchsubscription
    ADD CONSTRAINT branchsubscription__person__branch__key UNIQUE (person, branch);

ALTER TABLE ONLY branchsubscription
    ADD CONSTRAINT branchsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchvisibilitypolicy
    ADD CONSTRAINT branchvisibilitypolicy_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugbranch
    ADD CONSTRAINT bug_branch_unique UNIQUE (bug, branch);

ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_name_key UNIQUE (name);

ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT bugactivity_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_bug_person_uniq UNIQUE (bug, person);

ALTER TABLE ONLY bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugbranch
    ADD CONSTRAINT bugbranch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_bug_cve_uniq UNIQUE (bug, cve);

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugjob
    ADD CONSTRAINT bugjob__job__key UNIQUE (job);

ALTER TABLE ONLY bugjob
    ADD CONSTRAINT bugjob_pkey PRIMARY KEY (id);

ALTER TABLE bugjob CLUSTER ON bugjob_pkey;

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage__bug__message__key UNIQUE (bug, message);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage__bugwatch__remote_comment_id__key UNIQUE (bugwatch, remote_comment_id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification__bug__message__unq UNIQUE (bug, message);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification_pkey PRIMARY KEY (id);

ALTER TABLE bugnotification CLUSTER ON bugnotification_pkey;

ALTER TABLE ONLY bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive__bug__message__key UNIQUE (bug, message);

ALTER TABLE ONLY bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive_pk PRIMARY KEY (id);

ALTER TABLE ONLY bugnotificationattachment
    ADD CONSTRAINT bugnotificationattachment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient__bug_notificaion__person__key UNIQUE (bug_notification, person);

ALTER TABLE ONLY bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugnotificationrecipientarchive
    ADD CONSTRAINT bugnotificationrecipientarchive_pk PRIMARY KEY (id);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_bug_key UNIQUE (bug, sourcepackagerelease);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_bug_key UNIQUE (bug, productrelease);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT bugsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT bugsystem_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugtag
    ADD CONSTRAINT bugtag__tag__bug__key UNIQUE (tag, bug);

ALTER TABLE ONLY bugtag
    ADD CONSTRAINT bugtag_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugtrackeralias
    ADD CONSTRAINT bugtracker__base_url__key UNIQUE (base_url);

ALTER TABLE ONLY bugtrackeralias
    ADD CONSTRAINT bugtrackeralias_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugtrackerperson
    ADD CONSTRAINT bugtrackerperson__bugtracker__name__key UNIQUE (bugtracker, name);

ALTER TABLE ONLY bugtrackerperson
    ADD CONSTRAINT bugtrackerperson_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bugtask_target UNIQUE (id, bug);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugwatchactivity
    ADD CONSTRAINT bugwatchactivity_pkey PRIMARY KEY (id);

ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_pkey PRIMARY KEY (id);

ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_url_key UNIQUE (url);

ALTER TABLE ONLY buildfarmjob
    ADD CONSTRAINT buildfarmjob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY buildpackagejob
    ADD CONSTRAINT buildpackagejob__build__key UNIQUE (build);

ALTER TABLE ONLY buildpackagejob
    ADD CONSTRAINT buildpackagejob__job__key UNIQUE (job);

ALTER TABLE ONLY buildpackagejob
    ADD CONSTRAINT buildpackagejob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT buildqueue__job__key UNIQUE (job);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT buildqueue_pkey PRIMARY KEY (id);

ALTER TABLE ONLY revision
    ADD CONSTRAINT changeset_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_branch_key UNIQUE (branch);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codeimportevent
    ADD CONSTRAINT codeimportevent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codeimporteventdata
    ADD CONSTRAINT codeimporteventdata__event__data_type__key UNIQUE (event, data_type);

ALTER TABLE ONLY codeimporteventdata
    ADD CONSTRAINT codeimporteventdata_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codeimportjob
    ADD CONSTRAINT codeimportjob__code_import__key UNIQUE (code_import);

ALTER TABLE ONLY codeimportjob
    ADD CONSTRAINT codeimportjob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codeimportmachine
    ADD CONSTRAINT codeimportmachine_hostname_key UNIQUE (hostname);

ALTER TABLE ONLY codeimportmachine
    ADD CONSTRAINT codeimportmachine_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codeimportresult
    ADD CONSTRAINT codeimportresult_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codereviewmessage
    ADD CONSTRAINT codereviewmessage__branch_merge_proposal__id_key UNIQUE (branch_merge_proposal, id);

ALTER TABLE ONLY codereviewmessage
    ADD CONSTRAINT codereviewmessage_message_key UNIQUE (message);

ALTER TABLE ONLY codereviewmessage
    ADD CONSTRAINT codereviewmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY codereviewvote
    ADD CONSTRAINT codereviewvote_pkey PRIMARY KEY (id);

ALTER TABLE ONLY commercialsubscription
    ADD CONSTRAINT commercialsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY component
    ADD CONSTRAINT component_name_key UNIQUE (name);

ALTER TABLE ONLY component
    ADD CONSTRAINT component_pkey PRIMARY KEY (id);

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT componentselection__distroseries__component__key UNIQUE (distroseries, component);

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT componentselection_pkey PRIMARY KEY (id);

ALTER TABLE ONLY continent
    ADD CONSTRAINT continent_code_key UNIQUE (code);

ALTER TABLE ONLY continent
    ADD CONSTRAINT continent_name_key UNIQUE (name);

ALTER TABLE ONLY continent
    ADD CONSTRAINT continent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY country
    ADD CONSTRAINT country_code2_uniq UNIQUE (iso3166code2);

ALTER TABLE ONLY country
    ADD CONSTRAINT country_code3_uniq UNIQUE (iso3166code3);

ALTER TABLE ONLY country
    ADD CONSTRAINT country_name_uniq UNIQUE (name);

ALTER TABLE ONLY country
    ADD CONSTRAINT country_pkey PRIMARY KEY (id);

ALTER TABLE ONLY customlanguagecode
    ADD CONSTRAINT customlanguagecode_pkey PRIMARY KEY (id);

ALTER TABLE ONLY cve
    ADD CONSTRAINT cve_pkey PRIMARY KEY (id);

ALTER TABLE ONLY cve
    ADD CONSTRAINT cve_sequence_uniq UNIQUE (sequence);

ALTER TABLE ONLY cvereference
    ADD CONSTRAINT cvereference_pkey PRIMARY KEY (id);

ALTER TABLE ONLY databasecpustats
    ADD CONSTRAINT databasecpustats_pkey PRIMARY KEY (date_created, username);

ALTER TABLE ONLY databasereplicationlag
    ADD CONSTRAINT databasereplicationlag_pkey PRIMARY KEY (node);

ALTER TABLE ONLY databasetablestats
    ADD CONSTRAINT databasetablestats_pkey PRIMARY KEY (date_created, schemaname, relname);

ALTER TABLE databasetablestats CLUSTER ON databasetablestats_pkey;

ALTER TABLE ONLY diff
    ADD CONSTRAINT diff_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_name_key UNIQUE (name);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distributionbounty
    ADD CONSTRAINT distributionbounty_bounty_distribution_uniq UNIQUE (bounty, distribution);

ALTER TABLE ONLY distributionbounty
    ADD CONSTRAINT distributionbounty_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_ftp_base_url_key UNIQUE (ftp_base_url);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_http_base_url_key UNIQUE (http_base_url);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_name_key UNIQUE (name);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_rsync_base_url_key UNIQUE (rsync_base_url);

ALTER TABLE ONLY distributionsourcepackage
    ADD CONSTRAINT distributionpackage__sourcepackagename__distribution__key UNIQUE (sourcepackagename, distribution);

ALTER TABLE distributionsourcepackage CLUSTER ON distributionpackage__sourcepackagename__distribution__key;

ALTER TABLE ONLY distributionsourcepackage
    ADD CONSTRAINT distributionsourcepackage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache__distribution__sourcepackagename UNIQUE (distribution, sourcepackagename, archive);

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroarchseries
    ADD CONSTRAINT distroarchrelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroarchseries
    ADD CONSTRAINT distroarchseries__architecturetag__distroseries__key UNIQUE (architecturetag, distroseries);

ALTER TABLE ONLY distroarchseries
    ADD CONSTRAINT distroarchseries__processorfamily__distroseries__key UNIQUE (processorfamily, distroseries);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_distro_component_uniq UNIQUE (distribution, component);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distrorelease_distribution_key UNIQUE (distribution, name);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distrorelease_distro_release_unique UNIQUE (distribution, id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distrorelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroserieslanguage
    ADD CONSTRAINT distroreleaselanguage_distrorelease_language_uniq UNIQUE (distroseries, language);

ALTER TABLE ONLY distroserieslanguage
    ADD CONSTRAINT distroreleaselanguage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroseriespackagecache
    ADD CONSTRAINT distroreleasepackagecache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT distroreleasequeue_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageuploadbuild
    ADD CONSTRAINT distroreleasequeuebuild__distroreleasequeue__build__unique UNIQUE (packageupload, build);

ALTER TABLE ONLY packageuploadbuild
    ADD CONSTRAINT distroreleasequeuebuild_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageuploadcustom
    ADD CONSTRAINT distroreleasequeuecustom_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageuploadsource
    ADD CONSTRAINT distroreleasequeuesource_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__distroseries__binarypackagename__arch UNIQUE (distroseries, binarypackagename, archive);

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress_pkey PRIMARY KEY (id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_pkey PRIMARY KEY (id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_pkey PRIMARY KEY (id);

ALTER TABLE ONLY featureflag
    ADD CONSTRAINT feature_flag_pkey PRIMARY KEY (scope, flag);

ALTER TABLE ONLY featureflag
    ADD CONSTRAINT feature_flag_unique_priority_per_flag UNIQUE (flag, priority);

ALTER TABLE ONLY featuredproject
    ADD CONSTRAINT featuredproject_pkey PRIMARY KEY (id);

ALTER TABLE ONLY flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion__parent__child__key UNIQUE (parent, child);

ALTER TABLE ONLY flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion_pkey PRIMARY KEY (id);

ALTER TABLE ONLY fticache
    ADD CONSTRAINT fticache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY fticache
    ADD CONSTRAINT fticache_tablename_key UNIQUE (tablename);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_fingerprint_key UNIQUE (fingerprint);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_owner_key UNIQUE (owner, id);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwdevice
    ADD CONSTRAINT hwdevice__bus_vendor_id__bus_product_id__variant__key UNIQUE (bus_vendor_id, bus_product_id, variant);

ALTER TABLE ONLY hwdevice
    ADD CONSTRAINT hwdevice_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwdeviceclass
    ADD CONSTRAINT hwdeviceclass_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwdevicedriverlink
    ADD CONSTRAINT hwdevicedriverlink_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant__vendor_name__product_name__device__key UNIQUE (vendor_name, product_name, device);

ALTER TABLE ONLY hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwdmihandle
    ADD CONSTRAINT hwdmihandle_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwdmivalue
    ADD CONSTRAINT hwdmivalue_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwdriver
    ADD CONSTRAINT hwdriver__package_name__name__key UNIQUE (package_name, name);

ALTER TABLE ONLY hwdriver
    ADD CONSTRAINT hwdriver_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__submission_key__key UNIQUE (submission_key);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug__submission__bug__key UNIQUE (submission, bug);

ALTER TABLE ONLY hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwsystemfingerprint
    ADD CONSTRAINT hwsystemfingerprint__fingerprint__key UNIQUE (fingerprint);

ALTER TABLE ONLY hwsystemfingerprint
    ADD CONSTRAINT hwsystemfingerprint_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwtest
    ADD CONSTRAINT hwtest_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwtestanswer
    ADD CONSTRAINT hwtestanswer_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice__choice__test__key UNIQUE (choice, test);

ALTER TABLE ONLY hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice__test__id__key UNIQUE (test, id);

ALTER TABLE ONLY hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice__answer__device_driver__key UNIQUE (answer, device_driver);

ALTER TABLE ONLY hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice__answer__device_driver__key UNIQUE (answer, device_driver);

ALTER TABLE ONLY hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwvendorid
    ADD CONSTRAINT hwvendorid__bus_vendor_id__vendor_name__key UNIQUE (bus, vendor_id_for_bus, vendor_name);

ALTER TABLE ONLY hwvendorid
    ADD CONSTRAINT hwvendorid_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwvendorname
    ADD CONSTRAINT hwvendorname_pkey PRIMARY KEY (id);

ALTER TABLE ONLY ircid
    ADD CONSTRAINT ircid_pkey PRIMARY KEY (id);

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_jabberid_key UNIQUE (jabberid);

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_pkey PRIMARY KEY (id);

ALTER TABLE ONLY job
    ADD CONSTRAINT job__status__id__key UNIQUE (status, id);

ALTER TABLE ONLY job
    ADD CONSTRAINT job_pkey PRIMARY KEY (id);

ALTER TABLE job CLUSTER ON job_pkey;

ALTER TABLE ONLY karma
    ADD CONSTRAINT karma_pkey PRIMARY KEY (id);

ALTER TABLE ONLY karmaaction
    ADD CONSTRAINT karmaaction_name_uniq UNIQUE (name);

ALTER TABLE ONLY karmaaction
    ADD CONSTRAINT karmaaction_pkey PRIMARY KEY (id);

ALTER TABLE ONLY karmacache
    ADD CONSTRAINT karmacache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY karmacategory
    ADD CONSTRAINT karmacategory_pkey PRIMARY KEY (id);

ALTER TABLE ONLY karmatotalcache
    ADD CONSTRAINT karmatotalcache_person_key UNIQUE (person);

ALTER TABLE ONLY karmatotalcache
    ADD CONSTRAINT karmatotalcache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY language
    ADD CONSTRAINT language_code_key UNIQUE (code);

ALTER TABLE ONLY language
    ADD CONSTRAINT language_pkey PRIMARY KEY (id);

ALTER TABLE ONLY languagepack
    ADD CONSTRAINT languagepack_pkey PRIMARY KEY (id);

ALTER TABLE ONLY launchpaddatabaserevision
    ADD CONSTRAINT launchpaddatabaserevision_pkey PRIMARY KEY (major, minor, patch);

ALTER TABLE ONLY launchpadstatistic
    ADD CONSTRAINT launchpadstatistic_pkey PRIMARY KEY (id);

ALTER TABLE ONLY launchpadstatistic
    ADD CONSTRAINT launchpadstatistics_uniq_name UNIQUE (name);

ALTER TABLE ONLY libraryfilealias
    ADD CONSTRAINT libraryfilealias_pkey PRIMARY KEY (id);

ALTER TABLE libraryfilealias CLUSTER ON libraryfilealias_pkey;

ALTER TABLE ONLY libraryfilecontent
    ADD CONSTRAINT libraryfilecontent_pkey PRIMARY KEY (id);

ALTER TABLE libraryfilecontent CLUSTER ON libraryfilecontent_pkey;

ALTER TABLE ONLY libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount__libraryfilealias__day__country__key UNIQUE (libraryfilealias, day, country);

ALTER TABLE ONLY libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount_pkey PRIMARY KEY (id);

ALTER TABLE ONLY logintoken
    ADD CONSTRAINT logintoken_pkey PRIMARY KEY (id);

ALTER TABLE ONLY logintoken
    ADD CONSTRAINT logintoken_token_key UNIQUE (token);

ALTER TABLE ONLY lp_account
    ADD CONSTRAINT lp_account__openid_identifier__key UNIQUE (openid_identifier);

ALTER TABLE ONLY lp_account
    ADD CONSTRAINT lp_account_pkey PRIMARY KEY (id);

ALTER TABLE ONLY lp_person
    ADD CONSTRAINT lp_person__account__key UNIQUE (account);

ALTER TABLE ONLY lp_person
    ADD CONSTRAINT lp_person__name__key UNIQUE (name);

ALTER TABLE ONLY lp_person
    ADD CONSTRAINT lp_person_pkey PRIMARY KEY (id);

ALTER TABLE ONLY lp_personlocation
    ADD CONSTRAINT lp_personlocation__person__key UNIQUE (person);

ALTER TABLE ONLY lp_personlocation
    ADD CONSTRAINT lp_personlocation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY lp_teamparticipation
    ADD CONSTRAINT lp_teamparticipation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY lp_teamparticipation
    ADD CONSTRAINT lp_teamperticipation__team__person__key UNIQUE (team, person);

ALTER TABLE ONLY mailinglist
    ADD CONSTRAINT mailinglist_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mailinglist
    ADD CONSTRAINT mailinglist_team_key UNIQUE (team);

ALTER TABLE ONLY mailinglistban
    ADD CONSTRAINT mailinglistban_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT membership_person_key UNIQUE (person, team);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT membership_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mergedirectivejob
    ADD CONSTRAINT mergedirectivejob_job_key UNIQUE (job);

ALTER TABLE ONLY mergedirectivejob
    ADD CONSTRAINT mergedirectivejob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_pkey PRIMARY KEY (id);

ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_message_idx UNIQUE (message, sequence);

ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_pkey PRIMARY KEY (id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_distribution_id_key UNIQUE (distribution, id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_name_distribution_key UNIQUE (name, distribution);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_name_product_key UNIQUE (name, product);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_pkey PRIMARY KEY (id);

ALTER TABLE milestone CLUSTER ON milestone_pkey;

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_id_key UNIQUE (product, id);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_name_key UNIQUE (name);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistrorelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistroseries__unq UNIQUE (distroseries, flavour, distribution_mirror);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchrelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrordistroseriessource
    ADD CONSTRAINT mirrordistroreleasesource_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY nameblacklist
    ADD CONSTRAINT nameblacklist__regexp__key UNIQUE (regexp);

ALTER TABLE ONLY nameblacklist
    ADD CONSTRAINT nameblacklist_pkey PRIMARY KEY (id);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_key_key UNIQUE (key);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_pkey PRIMARY KEY (id);

ALTER TABLE ONLY oauthconsumer
    ADD CONSTRAINT oauthconsumer_key_key UNIQUE (key);

ALTER TABLE ONLY oauthconsumer
    ADD CONSTRAINT oauthconsumer_pkey PRIMARY KEY (id);

ALTER TABLE ONLY oauthnonce
    ADD CONSTRAINT oauthnonce__access_token__request_timestamp__nonce__key UNIQUE (access_token, request_timestamp, nonce);

ALTER TABLE ONLY oauthnonce
    ADD CONSTRAINT oauthnonce_pkey PRIMARY KEY (id);

ALTER TABLE oauthnonce CLUSTER ON oauthnonce_pkey;

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_key_key UNIQUE (key);

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_pkey PRIMARY KEY (id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_pkey PRIMARY KEY (id);

ALTER TABLE ONLY openidassociation
    ADD CONSTRAINT openidassociation_pkey PRIMARY KEY (server_url, handle);

ALTER TABLE ONLY openidconsumerassociation
    ADD CONSTRAINT openidconsumerassociation_pkey PRIMARY KEY (server_url, handle);

ALTER TABLE ONLY openidconsumernonce
    ADD CONSTRAINT openidconsumernonce_pkey PRIMARY KEY (server_url, "timestamp", salt);

ALTER TABLE ONLY openidrpconfig
    ADD CONSTRAINT openidrpconfig_pkey PRIMARY KEY (id);

ALTER TABLE ONLY openidrpsummary
    ADD CONSTRAINT openidrpsummary__account__trust_root__openid_identifier__key UNIQUE (account, trust_root, openid_identifier);

ALTER TABLE ONLY openidrpsummary
    ADD CONSTRAINT openidrpsummary_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagebugsupervisor
    ADD CONSTRAINT packagebugsupervisor__sourcepackagename__distribution__key UNIQUE (sourcepackagename, distribution);

ALTER TABLE ONLY packagebugsupervisor
    ADD CONSTRAINT packagebugsupervisor_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagebuild
    ADD CONSTRAINT packagebuild_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagediff
    ADD CONSTRAINT packagediff_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagesetinclusion
    ADD CONSTRAINT packagepayerinclusion__parent__child__key UNIQUE (parent, child);

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT packagepublishinghistory_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageset
    ADD CONSTRAINT packageset__name__distroseries__key UNIQUE (name, distroseries);

ALTER TABLE ONLY packageset
    ADD CONSTRAINT packageset_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagesetgroup
    ADD CONSTRAINT packagesetgroup_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagesetinclusion
    ADD CONSTRAINT packagesetinclusion_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagesetsources
    ADD CONSTRAINT packagesetsources__packageset__sourcepackagename__key UNIQUE (packageset, sourcepackagename);

ALTER TABLE ONLY packagesetsources
    ADD CONSTRAINT packagesetsources_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageuploadsource
    ADD CONSTRAINT packageuploadsource__packageupload__key UNIQUE (packageupload);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging__distroseries__sourcepackagename__key UNIQUE (distroseries, sourcepackagename);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_pkey PRIMARY KEY (id);

ALTER TABLE ONLY parsedapachelog
    ADD CONSTRAINT parsedapachelog_pkey PRIMARY KEY (id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__account__key UNIQUE (account);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__name__key UNIQUE (name);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);

ALTER TABLE person CLUSTER ON person_pkey;

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_person_key UNIQUE (person, language);

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY personlocation
    ADD CONSTRAINT personlocation_person_key UNIQUE (person);

ALTER TABLE ONLY personlocation
    ADD CONSTRAINT personlocation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY personnotification
    ADD CONSTRAINT personnotification_pkey PRIMARY KEY (id);

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_name_key UNIQUE (name);

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_pkey PRIMARY KEY (id);

ALTER TABLE pillarname CLUSTER ON pillarname_pkey;

ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot_distroarchrelease_key UNIQUE (distroarchseries, pocket);

ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot_pkey PRIMARY KEY (id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT pocomment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_pkey PRIMARY KEY (id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_pkey PRIMARY KEY (id);

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT pofiletranslator__person__pofile__key UNIQUE (person, pofile);

ALTER TABLE pofiletranslator CLUSTER ON pofiletranslator__person__pofile__key;

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT pofiletranslator_pkey PRIMARY KEY (id);

ALTER TABLE ONLY poll
    ADD CONSTRAINT poll_pkey PRIMARY KEY (id);

ALTER TABLE ONLY poll
    ADD CONSTRAINT poll_team_key UNIQUE (team, name);

ALTER TABLE ONLY polloption
    ADD CONSTRAINT polloption_name_key UNIQUE (name, poll);

ALTER TABLE ONLY polloption
    ADD CONSTRAINT polloption_pkey PRIMARY KEY (id);

ALTER TABLE ONLY polloption
    ADD CONSTRAINT polloption_poll_key UNIQUE (poll, id);

ALTER TABLE ONLY pomsgid
    ADD CONSTRAINT pomsgid_pkey PRIMARY KEY (id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_person_key UNIQUE (person, potemplate, language);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_pkey PRIMARY KEY (id);

ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_pkey PRIMARY KEY (id);

ALTER TABLE ONLY potranslation
    ADD CONSTRAINT potranslation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY previewdiff
    ADD CONSTRAINT previewdiff_pkey PRIMARY KEY (id);

ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_name_key UNIQUE (name);

ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_pkey PRIMARY KEY (id);

ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_name_key UNIQUE (name);

ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_pkey PRIMARY KEY (id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_name_key UNIQUE (name);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_bounty_key UNIQUE (bounty, product);

ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productcvsmodule
    ADD CONSTRAINT productcvsmodule_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productlicense
    ADD CONSTRAINT productlicense__product__license__key UNIQUE (product, license);

ALTER TABLE ONLY productlicense
    ADD CONSTRAINT productlicense_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_milestone_key UNIQUE (milestone);

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_pkey PRIMARY KEY (id);

ALTER TABLE productrelease CLUSTER ON productrelease_pkey;

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT productreleasefile_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries__product__name__key UNIQUE (product, name);

ALTER TABLE productseries CLUSTER ON productseries__product__name__key;

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_series_uniq UNIQUE (product, id);

ALTER TABLE ONLY productseriescodeimport
    ADD CONSTRAINT productseriescodeimport_codeimport_key UNIQUE (codeimport);

ALTER TABLE ONLY productseriescodeimport
    ADD CONSTRAINT productseriescodeimport_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productseriescodeimport
    ADD CONSTRAINT productseriescodeimport_productseries_key UNIQUE (productseries);

ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT productsvnmodule_pkey PRIMARY KEY (id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_name_key UNIQUE (name);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);

ALTER TABLE project CLUSTER ON project_pkey;

ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_bounty_key UNIQUE (bounty, project);

ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_pkey PRIMARY KEY (id);

ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT projectrelationship_pkey PRIMARY KEY (id);

ALTER TABLE ONLY pushmirroraccess
    ADD CONSTRAINT pushmirroraccess_name_key UNIQUE (name);

ALTER TABLE ONLY pushmirroraccess
    ADD CONSTRAINT pushmirroraccess_pkey PRIMARY KEY (id);

ALTER TABLE ONLY requestedcds
    ADD CONSTRAINT requestedcds__ds__arch__flav__request__key UNIQUE (distroseries, architecture, flavour, request);

ALTER TABLE ONLY requestedcds
    ADD CONSTRAINT requestedcds_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revision__branch__revision__key UNIQUE (branch, revision);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision__id__revision_date__key UNIQUE (id, revision_date);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revision__revision__branch__key UNIQUE (revision, branch);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision_revision_id_unique UNIQUE (revision_id);

ALTER TABLE ONLY revisioncache
    ADD CONSTRAINT revisioncache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revisionnumber_branch_id_unique UNIQUE (branch, id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revisionnumber_branch_sequence_unique UNIQUE (branch, sequence);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revisionnumber_pkey PRIMARY KEY (id);

ALTER TABLE ONLY revisionparent
    ADD CONSTRAINT revisionparent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY revisionparent
    ADD CONSTRAINT revisionparent_unique UNIQUE (revision, parent_id);

ALTER TABLE ONLY revisionproperty
    ADD CONSTRAINT revisionproperty__revision__name__key UNIQUE (revision, name);

ALTER TABLE ONLY revisionproperty
    ADD CONSTRAINT revisionproperty_pkey PRIMARY KEY (id);

ALTER TABLE ONLY scriptactivity
    ADD CONSTRAINT scriptactivity_pkey PRIMARY KEY (id);

ALTER TABLE ONLY section
    ADD CONSTRAINT section_name_key UNIQUE (name);

ALTER TABLE ONLY section
    ADD CONSTRAINT section_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT sectionselection_pkey PRIMARY KEY (id);

ALTER TABLE ONLY seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch__ds__spn__pocket__key UNIQUE (distroseries, sourcepackagename, pocket);

ALTER TABLE ONLY seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shipitreport
    ADD CONSTRAINT shipitreport_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shipitsurvey
    ADD CONSTRAINT shipitsurvey_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shipitsurveyanswer
    ADD CONSTRAINT shipitsurveyanswer_answer_key UNIQUE (answer);

ALTER TABLE ONLY shipitsurveyanswer
    ADD CONSTRAINT shipitsurveyanswer_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shipitsurveyquestion
    ADD CONSTRAINT shipitsurveyquestion_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shipitsurveyquestion
    ADD CONSTRAINT shipitsurveyquestion_question_key UNIQUE (question);

ALTER TABLE ONLY shipitsurveyresult
    ADD CONSTRAINT shipitsurveyresult_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shipment
    ADD CONSTRAINT shipment_logintoken_key UNIQUE (logintoken);

ALTER TABLE ONLY shipment
    ADD CONSTRAINT shipment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_shipment_key UNIQUE (shipment);

ALTER TABLE ONLY shippingrun
    ADD CONSTRAINT shippingrun_csvfile_uniq UNIQUE (csvfile);

ALTER TABLE ONLY shippingrun
    ADD CONSTRAINT shippingrun_pkey PRIMARY KEY (id);

ALTER TABLE ONLY signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT single_offer_per_bug_key UNIQUE (bug, owner);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT single_offer_per_spec_key UNIQUE (specification, owner);

ALTER TABLE ONLY sourcepackageformatselection
    ADD CONSTRAINT sourceformatselection__distroseries__format__key UNIQUE (distroseries, format);

ALTER TABLE ONLY sourcepackageformatselection
    ADD CONSTRAINT sourcepackageformatselection_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_name_key UNIQUE (name);

ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe__owner__name__key UNIQUE (owner, name);

ALTER TABLE ONLY sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipe_distroseries_unique UNIQUE (sourcepackagerecipe, distroseries);

ALTER TABLE ONLY sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagerecipebuildjob
    ADD CONSTRAINT sourcepackagerecipebuildjob__job__key UNIQUE (job);

ALTER TABLE ONLY sourcepackagerecipebuildjob
    ADD CONSTRAINT sourcepackagerecipebuildjob__sourcepackage_recipe_build__key UNIQUE (sourcepackage_recipe_build);

ALTER TABLE ONLY sourcepackagerecipebuildjob
    ADD CONSTRAINT sourcepackagerecipebuildjob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction__name__recipe_data__key UNIQUE (name, recipe_data);

ALTER TABLE ONLY sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction__recipe_data__line_number__k UNIQUE (recipe_data, line_number);

ALTER TABLE ONLY sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipedistroseries_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT sourcepackagereleasefile_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationbug
    ADD CONSTRAINT specification_bug_uniq UNIQUE (specification, bug);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_distribution_name_uniq UNIQUE (distribution, name);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_product_name_uniq UNIQUE (name, product);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_specurl_uniq UNIQUE (specurl);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specificationbranch__spec_branch_unique UNIQUE (branch, specification);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specificationbranch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationbug
    ADD CONSTRAINT specificationbug_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationdependency
    ADD CONSTRAINT specificationdependency_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationdependency
    ADD CONSTRAINT specificationdependency_uniq UNIQUE (specification, dependency);

ALTER TABLE ONLY specificationfeedback
    ADD CONSTRAINT specificationfeedback_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage__specification__message__key UNIQUE (specification, message);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationsubscription
    ADD CONSTRAINT specificationsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationsubscription
    ADD CONSTRAINT specificationsubscription_spec_person_uniq UNIQUE (specification, person);

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT spokenin__country__language__key UNIQUE (language, country);

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT spokenin_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sprint
    ADD CONSTRAINT sprint_name_uniq UNIQUE (name);

ALTER TABLE ONLY sprint
    ADD CONSTRAINT sprint_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sprintattendance
    ADD CONSTRAINT sprintattendance_attendance_uniq UNIQUE (attendee, sprint);

ALTER TABLE ONLY sprintattendance
    ADD CONSTRAINT sprintattendance_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sprintspecification
    ADD CONSTRAINT sprintspec_uniq UNIQUE (specification, sprint);

ALTER TABLE ONLY sprintspecification
    ADD CONSTRAINT sprintspecification_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sshkey
    ADD CONSTRAINT sshkey_pkey PRIMARY KEY (id);

ALTER TABLE ONLY standardshipitrequest
    ADD CONSTRAINT standardshipitrequest_flavour_quantity_key UNIQUE (flavour, quantityx86, quantityppc, quantityamd64);

ALTER TABLE ONLY standardshipitrequest
    ADD CONSTRAINT standardshipitrequest_pkey PRIMARY KEY (id);

ALTER TABLE ONLY staticdiff
    ADD CONSTRAINT staticdiff_from_revision_id_key UNIQUE (from_revision_id, to_revision_id);

ALTER TABLE ONLY staticdiff
    ADD CONSTRAINT staticdiff_pkey PRIMARY KEY (id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY suggestivepotemplate
    ADD CONSTRAINT suggestivepotemplate_pkey PRIMARY KEY (potemplate);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT supportcontact__distribution__sourcepackagename__person__key UNIQUE (distribution, sourcepackagename, person);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT supportcontact__product__person__key UNIQUE (product, person);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT supportcontact_pkey PRIMARY KEY (id);

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_team_key UNIQUE (team, person);

ALTER TABLE ONLY temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_file_alias_key UNIQUE (file_alias);

ALTER TABLE ONLY temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_pkey PRIMARY KEY (id);

ALTER TABLE temporaryblobstorage CLUSTER ON temporaryblobstorage_pkey;

ALTER TABLE ONLY temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_uuid_key UNIQUE (uuid);

ALTER TABLE ONLY question
    ADD CONSTRAINT ticket_pkey PRIMARY KEY (id);

ALTER TABLE ONLY questionbug
    ADD CONSTRAINT ticketbug_bug_ticket_uniq UNIQUE (bug, question);

ALTER TABLE ONLY questionbug
    ADD CONSTRAINT ticketbug_pkey PRIMARY KEY (id);

ALTER TABLE ONLY questionmessage
    ADD CONSTRAINT ticketmessage_message_ticket_uniq UNIQUE (message, question);

ALTER TABLE ONLY questionmessage
    ADD CONSTRAINT ticketmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY questionreopening
    ADD CONSTRAINT ticketreopening_pkey PRIMARY KEY (id);

ALTER TABLE ONLY questionsubscription
    ADD CONSTRAINT ticketsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY questionsubscription
    ADD CONSTRAINT ticketsubscription_ticket_person_uniq UNIQUE (question, person);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translation_translationgroup_key UNIQUE (translationgroup, language);

ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_name_key UNIQUE (name);

ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_pkey PRIMARY KEY (id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry_pkey PRIMARY KEY (id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY translationrelicensingagreement
    ADD CONSTRAINT translationrelicensingagreement__person__key UNIQUE (person);

ALTER TABLE ONLY translationrelicensingagreement
    ADD CONSTRAINT translationrelicensingagreement_pkey PRIMARY KEY (id);

ALTER TABLE ONLY translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_pkey PRIMARY KEY (id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationfeedback
    ADD CONSTRAINT unique_spec_requestor_provider UNIQUE (specification, requester, reviewer);

ALTER TABLE ONLY usertouseremail
    ADD CONSTRAINT usertouseremail_pkey PRIMARY KEY (id);

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_pkey PRIMARY KEY (id);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_person_key UNIQUE (person, poll);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_pkey PRIMARY KEY (id);

ALTER TABLE ONLY webserviceban
    ADD CONSTRAINT webserviceban_pkey PRIMARY KEY (id);

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_pkey PRIMARY KEY (id);

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_wikiname_key UNIQUE (wikiname, wiki);

CREATE INDEX account__old_openid_identifier__idx ON account USING btree (old_openid_identifier);

CREATE INDEX announcement__distribution__active__idx ON announcement USING btree (distribution, active) WHERE (distribution IS NOT NULL);

CREATE INDEX announcement__product__active__idx ON announcement USING btree (product, active) WHERE (product IS NOT NULL);

CREATE INDEX announcement__project__active__idx ON announcement USING btree (project, active) WHERE (project IS NOT NULL);

CREATE INDEX announcement__registrant__idx ON announcement USING btree (registrant);

CREATE UNIQUE INDEX answercontact__distribution__person__key ON answercontact USING btree (distribution, person) WHERE (sourcepackagename IS NULL);

CREATE INDEX answercontact__person__idx ON answercontact USING btree (person);

CREATE INDEX apportjob__blob__idx ON apportjob USING btree (blob);

CREATE INDEX archive__commercial__idx ON archive USING btree (commercial);

CREATE UNIQUE INDEX archive__distribution__purpose__key ON archive USING btree (distribution, purpose) WHERE (purpose = ANY (ARRAY[1, 4]));

CREATE INDEX archive__owner__idx ON archive USING btree (owner);

CREATE UNIQUE INDEX archive__owner__key ON archive USING btree (owner, distribution, name);

CREATE INDEX archive__require_virtualized__idx ON archive USING btree (require_virtualized);

CREATE INDEX archive__signing_key__idx ON archive USING btree (signing_key) WHERE (signing_key IS NOT NULL);

CREATE INDEX archive__status__idx ON archive USING btree (status);

CREATE INDEX archive_fti ON archive USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX archiveauthtoken__archive__idx ON archiveauthtoken USING btree (archive);

CREATE INDEX archiveauthtoken__date_created__idx ON archiveauthtoken USING btree (date_created);

CREATE INDEX archiveauthtoken__person__idx ON archiveauthtoken USING btree (person);

CREATE INDEX archivedependency__archive__idx ON archivedependency USING btree (archive);

CREATE INDEX archivedependency__component__idx ON archivedependency USING btree (component);

CREATE INDEX archivedependency__dependency__idx ON archivedependency USING btree (dependency);

CREATE INDEX archivejob__archive__job_type__idx ON archivejob USING btree (archive, job_type);

CREATE INDEX archivepermission__archive__component__permission__idx ON archivepermission USING btree (archive, component, permission);

CREATE INDEX archivepermission__archive__sourcepackagename__permission__idx ON archivepermission USING btree (archive, sourcepackagename, permission);

CREATE INDEX archivepermission__packageset__idx ON archivepermission USING btree (packageset) WHERE (packageset IS NOT NULL);

CREATE INDEX archivepermission__person__archive__idx ON archivepermission USING btree (person, archive);

CREATE INDEX archivesubscriber__archive__idx ON archivesubscriber USING btree (archive);

CREATE INDEX archivesubscriber__cancelled_by__idx ON archivesubscriber USING btree (cancelled_by) WHERE (cancelled_by IS NOT NULL);

CREATE INDEX archivesubscriber__date_created__idx ON archivesubscriber USING btree (date_created);

CREATE INDEX archivesubscriber__date_expires__idx ON archivesubscriber USING btree (date_expires) WHERE (date_expires IS NOT NULL);

CREATE INDEX archivesubscriber__registrant__idx ON archivesubscriber USING btree (registrant);

CREATE INDEX archivesubscriber__subscriber__idx ON archivesubscriber USING btree (subscriber);

CREATE INDEX authtoken__date_consumed__idx ON authtoken USING btree (date_consumed);

CREATE INDEX authtoken__date_created__idx ON authtoken USING btree (date_created);

CREATE INDEX authtoken__requester__idx ON authtoken USING btree (requester);

CREATE INDEX binarypackagebuild__distro_arch_series__idx ON binarypackagebuild USING btree (distro_arch_series);

CREATE UNIQUE INDEX binarypackagebuild__package_build__idx ON binarypackagebuild USING btree (package_build);

CREATE INDEX binarypackagebuild__source_package_release_idx ON binarypackagebuild USING btree (source_package_release);

CREATE INDEX binarypackagefile_binarypackage_idx ON binarypackagefile USING btree (binarypackagerelease);

CREATE INDEX binarypackagefile_libraryfile_idx ON binarypackagefile USING btree (libraryfile);

CREATE UNIQUE INDEX binarypackagerelease__debug_package__key ON binarypackagerelease USING btree (debug_package);

CREATE INDEX binarypackagerelease_build_idx ON binarypackagerelease USING btree (build);

CREATE INDEX binarypackagerelease_fti ON binarypackagerelease USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX binarypackagerelease_version_idx ON binarypackagerelease USING btree (version);

CREATE INDEX binarypackagerelease_version_sort ON binarypackagerelease USING btree (debversion_sort_key(version));

CREATE INDEX bounty__claimant__idx ON bounty USING btree (claimant);

CREATE INDEX bounty__owner__idx ON bounty USING btree (owner);

CREATE INDEX bounty__reviewer__idx ON bounty USING btree (reviewer);

CREATE INDEX bounty_usdvalue_idx ON bounty USING btree (usdvalue);

CREATE INDEX bountymessage_bounty_idx ON bountymessage USING btree (bounty);

CREATE INDEX branch__date_created__idx ON branch USING btree (date_created);

CREATE UNIQUE INDEX branch__ds__spn__owner__name__key ON branch USING btree (distroseries, sourcepackagename, owner, name) WHERE (distroseries IS NOT NULL);

CREATE INDEX branch__last_scanned__owner__idx ON branch USING btree (last_scanned, owner) WHERE (last_scanned IS NOT NULL);

CREATE INDEX branch__next_mirror_time__idx ON branch USING btree (next_mirror_time) WHERE (next_mirror_time IS NOT NULL);

CREATE UNIQUE INDEX branch__owner__name__key ON branch USING btree (owner, name) WHERE ((product IS NULL) AND (distroseries IS NULL));

CREATE INDEX branch__owner_name__idx ON branch USING btree (owner_name);

CREATE INDEX branch__private__idx ON branch USING btree (private);

CREATE INDEX branch__product__id__idx ON branch USING btree (product, id);

ALTER TABLE branch CLUSTER ON branch__product__id__idx;

CREATE UNIQUE INDEX branch__product__owner__name__key ON branch USING btree (product, owner, name) WHERE (product IS NOT NULL);

CREATE INDEX branch__registrant__idx ON branch USING btree (registrant);

CREATE INDEX branch__reviewer__idx ON branch USING btree (reviewer);

CREATE INDEX branch__stacked_on__idx ON branch USING btree (stacked_on) WHERE (stacked_on IS NOT NULL);

CREATE INDEX branch__target_suffix__idx ON branch USING btree (target_suffix);

CREATE INDEX branch_author_idx ON branch USING btree (author);

CREATE INDEX branch_owner_idx ON branch USING btree (owner);

CREATE INDEX branchjob__branch__idx ON branchjob USING btree (branch);

CREATE INDEX branchmergeproposal__dependent_branch__idx ON branchmergeproposal USING btree (dependent_branch);

CREATE INDEX branchmergeproposal__merge_diff__idx ON branchmergeproposal USING btree (merge_diff);

CREATE INDEX branchmergeproposal__merge_log_file__idx ON branchmergeproposal USING btree (merge_log_file);

CREATE INDEX branchmergeproposal__merge_reporter__idx ON branchmergeproposal USING btree (merge_reporter) WHERE (merge_reporter IS NOT NULL);

CREATE INDEX branchmergeproposal__merger__idx ON branchmergeproposal USING btree (merger);

CREATE INDEX branchmergeproposal__queuer__idx ON branchmergeproposal USING btree (queuer);

CREATE INDEX branchmergeproposal__registrant__idx ON branchmergeproposal USING btree (registrant);

CREATE INDEX branchmergeproposal__review_diff__idx ON branchmergeproposal USING btree (review_diff);

CREATE INDEX branchmergeproposal__reviewer__idx ON branchmergeproposal USING btree (reviewer);

CREATE INDEX branchmergeproposal__source_branch__idx ON branchmergeproposal USING btree (source_branch);

CREATE INDEX branchmergeproposal__superseded_by__idx ON branchmergeproposal USING btree (superseded_by) WHERE (superseded_by IS NOT NULL);

CREATE INDEX branchmergeproposal__target_branch__idx ON branchmergeproposal USING btree (target_branch);

CREATE INDEX branchmergeproposaljob__branch_merge_proposal__idx ON branchmergeproposaljob USING btree (branch_merge_proposal);

CREATE INDEX branchmergerobot__owner__idx ON branchmergerobot USING btree (owner);

CREATE INDEX branchmergerobot__registrant__idx ON branchmergerobot USING btree (registrant);

CREATE INDEX branchsubscription__branch__idx ON branchsubscription USING btree (branch);

CREATE INDEX branchsubscription__subscribed_by__idx ON branchsubscription USING btree (subscribed_by);

CREATE INDEX branchvisibilitypolicy__product__idx ON branchvisibilitypolicy USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX branchvisibilitypolicy__project__idx ON branchvisibilitypolicy USING btree (project) WHERE (project IS NOT NULL);

CREATE INDEX branchvisibilitypolicy__team__idx ON branchvisibilitypolicy USING btree (team) WHERE (team IS NOT NULL);

CREATE UNIQUE INDEX branchvisibilitypolicy__unq ON branchvisibilitypolicy USING btree ((COALESCE(product, (-1))), (COALESCE(project, (-1))), (COALESCE(team, (-1))));

CREATE INDEX bug__date_last_message__idx ON bug USING btree (date_last_message);

CREATE INDEX bug__date_last_updated__idx ON bug USING btree (date_last_updated);

ALTER TABLE bug CLUSTER ON bug__date_last_updated__idx;

CREATE INDEX bug__datecreated__idx ON bug USING btree (datecreated);

CREATE INDEX bug__heat__idx ON bug USING btree (heat);

CREATE INDEX bug__heat_last_updated__idx ON bug USING btree (heat_last_updated);

CREATE INDEX bug__latest_patch_uploaded__idx ON bug USING btree (latest_patch_uploaded);

CREATE INDEX bug__users_affected_count__idx ON bug USING btree (users_affected_count);

CREATE INDEX bug__users_unaffected_count__idx ON bug USING btree (users_unaffected_count);

CREATE INDEX bug__who_made_private__idx ON bug USING btree (who_made_private) WHERE (who_made_private IS NOT NULL);

CREATE INDEX bug_duplicateof_idx ON bug USING btree (duplicateof);

CREATE INDEX bug_fti ON bug USING gist (fti);

CREATE INDEX bug_owner_idx ON bug USING btree (owner);

CREATE INDEX bugactivity_bug_datechanged_idx ON bugactivity USING btree (bug, datechanged);

CREATE INDEX bugactivity_datechanged_idx ON bugactivity USING btree (datechanged);

CREATE INDEX bugactivity_person_datechanged_idx ON bugactivity USING btree (person, datechanged);

CREATE INDEX bugaffectsperson__person__idx ON bugaffectsperson USING btree (person);

CREATE INDEX bugattachment__bug__idx ON bugattachment USING btree (bug);

CREATE INDEX bugattachment_libraryfile_idx ON bugattachment USING btree (libraryfile);

CREATE INDEX bugattachment_message_idx ON bugattachment USING btree (message);

CREATE INDEX bugbranch__registrant__idx ON bugbranch USING btree (registrant);

CREATE INDEX bugcve_cve_index ON bugcve USING btree (cve);

CREATE INDEX bugjob__bug__job_type__idx ON bugjob USING btree (bug, job_type);

CREATE INDEX bugmessage_message_idx ON bugmessage USING btree (message);

CREATE INDEX bugnomination__bug__idx ON bugnomination USING btree (bug);

CREATE INDEX bugnomination__decider__idx ON bugnomination USING btree (decider) WHERE (decider IS NOT NULL);

CREATE UNIQUE INDEX bugnomination__distroseries__bug__key ON bugnomination USING btree (distroseries, bug) WHERE (distroseries IS NOT NULL);

CREATE INDEX bugnomination__owner__idx ON bugnomination USING btree (owner);

CREATE UNIQUE INDEX bugnomination__productseries__bug__key ON bugnomination USING btree (productseries, bug) WHERE (productseries IS NOT NULL);

CREATE INDEX bugnotification__date_emailed__idx ON bugnotification USING btree (date_emailed);

CREATE INDEX bugnotificationattachment__bug_notification__idx ON bugnotificationattachment USING btree (bug_notification);

CREATE INDEX bugnotificationattachment__message__idx ON bugnotificationattachment USING btree (message);

CREATE INDEX bugnotificationrecipient__person__idx ON bugnotificationrecipient USING btree (person);

CREATE INDEX bugnotificationrecipientarchive__bug_notification__idx ON bugnotificationrecipientarchive USING btree (bug_notification);

CREATE INDEX bugnotificationrecipientarchive__person__idx ON bugnotificationrecipientarchive USING btree (person);

CREATE INDEX bugpackageinfestation__creator__idx ON bugpackageinfestation USING btree (creator);

CREATE INDEX bugpackageinfestation__lastmodifiedby__idx ON bugpackageinfestation USING btree (lastmodifiedby);

CREATE INDEX bugpackageinfestation__verifiedby__idx ON bugpackageinfestation USING btree (verifiedby);

CREATE INDEX bugproductinfestation__creator__idx ON bugproductinfestation USING btree (creator);

CREATE INDEX bugproductinfestation__lastmodifiedby__idx ON bugproductinfestation USING btree (lastmodifiedby);

CREATE INDEX bugproductinfestation__verifiedby__idx ON bugproductinfestation USING btree (verifiedby);

CREATE INDEX bugsubscription__subscribed_by__idx ON bugsubscription USING btree (subscribed_by);

CREATE INDEX bugsubscription_bug_idx ON bugsubscription USING btree (bug);

ALTER TABLE bugsubscription CLUSTER ON bugsubscription_bug_idx;

CREATE INDEX bugsubscription_person_idx ON bugsubscription USING btree (person);

CREATE INDEX bugtag__bug__idx ON bugtag USING btree (bug);

CREATE INDEX bugtask__assignee__idx ON bugtask USING btree (assignee);

CREATE INDEX bugtask__binarypackagename__idx ON bugtask USING btree (binarypackagename) WHERE (binarypackagename IS NOT NULL);

CREATE INDEX bugtask__bug__idx ON bugtask USING btree (bug);

CREATE INDEX bugtask__bugwatch__idx ON bugtask USING btree (bugwatch) WHERE (bugwatch IS NOT NULL);

CREATE UNIQUE INDEX bugtask__date_closed__id__idx ON bugtask USING btree (date_closed, id) WHERE (status = 30);

CREATE INDEX bugtask__date_incomplete__idx ON bugtask USING btree (date_incomplete) WHERE (date_incomplete IS NOT NULL);

CREATE INDEX bugtask__datecreated__idx ON bugtask USING btree (datecreated);

CREATE INDEX bugtask__distribution__sourcepackagename__idx ON bugtask USING btree (distribution, sourcepackagename);

ALTER TABLE bugtask CLUSTER ON bugtask__distribution__sourcepackagename__idx;

CREATE INDEX bugtask__distroseries__sourcepackagename__idx ON bugtask USING btree (distroseries, sourcepackagename);

CREATE INDEX bugtask__milestone__idx ON bugtask USING btree (milestone);

CREATE INDEX bugtask__owner__idx ON bugtask USING btree (owner);

CREATE UNIQUE INDEX bugtask__product__bug__key ON bugtask USING btree (product, bug) WHERE (product IS NOT NULL);

CREATE UNIQUE INDEX bugtask__productseries__bug__key ON bugtask USING btree (productseries, bug) WHERE (productseries IS NOT NULL);

CREATE INDEX bugtask__sourcepackagename__idx ON bugtask USING btree (sourcepackagename) WHERE (sourcepackagename IS NOT NULL);

CREATE INDEX bugtask__status__idx ON bugtask USING btree (status);

CREATE UNIQUE INDEX bugtask_distinct_sourcepackage_assignment ON bugtask USING btree (bug, (COALESCE(sourcepackagename, (-1))), (COALESCE(distroseries, (-1))), (COALESCE(distribution, (-1)))) WHERE ((product IS NULL) AND (productseries IS NULL));

CREATE INDEX bugtask_fti ON bugtask USING gist (fti ts2.gist_tsvector_ops);

CREATE UNIQUE INDEX bugtracker_name_key ON bugtracker USING btree (name);

CREATE INDEX bugtracker_owner_idx ON bugtracker USING btree (owner);

CREATE INDEX bugtrackeralias__bugtracker__idx ON bugtrackeralias USING btree (bugtracker);

CREATE INDEX bugtrackerperson__person__idx ON bugtrackerperson USING btree (person);

CREATE INDEX bugwatch__lastchecked__idx ON bugwatch USING btree (lastchecked);

CREATE INDEX bugwatch__next_check__idx ON bugwatch USING btree (next_check);

CREATE INDEX bugwatch__remote_lp_bug_id__idx ON bugwatch USING btree (remote_lp_bug_id) WHERE (remote_lp_bug_id IS NOT NULL);

CREATE INDEX bugwatch__remotebug__idx ON bugwatch USING btree (remotebug);

CREATE INDEX bugwatch_bug_idx ON bugwatch USING btree (bug);

CREATE INDEX bugwatch_bugtracker_idx ON bugwatch USING btree (bugtracker);

CREATE INDEX bugwatch_datecreated_idx ON bugwatch USING btree (datecreated);

CREATE INDEX bugwatch_owner_idx ON bugwatch USING btree (owner);

CREATE INDEX bugwatchactivity__bug_watch__idx ON bugwatchactivity USING btree (bug_watch);

ALTER TABLE bugwatchactivity CLUSTER ON bugwatchactivity__bug_watch__idx;

CREATE INDEX bugwatchactivity__date__idx ON bugwatchactivity USING btree (activity_date);

CREATE INDEX builder__owner__idx ON builder USING btree (owner);

CREATE INDEX buildfarmjob__builder_and_status__idx ON buildfarmjob USING btree (builder, status);

CREATE INDEX buildfarmjob__date_created__idx ON buildfarmjob USING btree (date_created);

CREATE INDEX buildfarmjob__date_finished__idx ON buildfarmjob USING btree (date_finished);

CREATE INDEX buildfarmjob__date_started__idx ON buildfarmjob USING btree (date_started);

CREATE INDEX buildfarmjob__log__idx ON buildfarmjob USING btree (log) WHERE (log IS NOT NULL);

CREATE INDEX buildfarmjob__status__idx ON buildfarmjob USING btree (status);

CREATE UNIQUE INDEX buildqueue__builder__id__idx ON buildqueue USING btree (builder, id);

ALTER TABLE buildqueue CLUSTER ON buildqueue__builder__id__idx;

CREATE UNIQUE INDEX buildqueue__builder__unq ON buildqueue USING btree (builder) WHERE (builder IS NOT NULL);

CREATE INDEX buildqueue__job_type__idx ON buildqueue USING btree (job_type);

CREATE INDEX buildqueue__processor__virtualized__idx ON buildqueue USING btree (processor, virtualized) WHERE (processor IS NOT NULL);

CREATE INDEX changeset_datecreated_idx ON revision USING btree (date_created);

CREATE INDEX codeimport__assignee__idx ON codeimport USING btree (assignee);

CREATE UNIQUE INDEX codeimport__cvs_root__cvs_module__key ON codeimport USING btree (cvs_root, cvs_module) WHERE (cvs_root IS NOT NULL);

CREATE INDEX codeimport__owner__idx ON codeimport USING btree (owner);

CREATE INDEX codeimport__registrant__idx ON codeimport USING btree (registrant);

CREATE UNIQUE INDEX codeimport__url__idx ON codeimport USING btree (url) WHERE (url IS NOT NULL);

CREATE INDEX codeimportevent__code_import__date_created__id__idx ON codeimportevent USING btree (code_import, date_created, id);

CREATE INDEX codeimportevent__date_created__id__idx ON codeimportevent USING btree (date_created, id);

CREATE INDEX codeimportevent__message__date_created__idx ON codeimportevent USING btree (machine, date_created) WHERE (machine IS NOT NULL);

CREATE INDEX codeimportevent__person__idx ON codeimportevent USING btree (person) WHERE (person IS NOT NULL);

CREATE INDEX codeimportjob__code_import__date_created__idx ON codeimportjob USING btree (code_import, date_created);

CREATE INDEX codeimportjob__machine__date_created__idx ON codeimportjob USING btree (machine, date_created);

CREATE INDEX codeimportjob__requesting_user__idx ON codeimportjob USING btree (requesting_user);

CREATE INDEX codeimportresult__code_import__date_created__idx ON codeimportresult USING btree (code_import, date_created);

CREATE INDEX codeimportresult__log_file__idx ON codeimportresult USING btree (log_file);

CREATE INDEX codeimportresult__machine__date_created__idx ON codeimportresult USING btree (machine, date_created);

CREATE INDEX codeimportresult__requesting_user__idx ON codeimportresult USING btree (requesting_user);

CREATE INDEX codereviewvote__branch_merge_proposal__idx ON codereviewvote USING btree (branch_merge_proposal);

CREATE INDEX codereviewvote__registrant__idx ON codereviewvote USING btree (registrant);

CREATE INDEX codereviewvote__reviewer__idx ON codereviewvote USING btree (reviewer);

CREATE INDEX codereviewvote__vote_message__idx ON codereviewvote USING btree (vote_message);

CREATE INDEX commercialsubscription__product__idx ON commercialsubscription USING btree (product);

CREATE INDEX commercialsubscription__purchaser__idx ON commercialsubscription USING btree (purchaser);

CREATE INDEX commercialsubscription__registrant__idx ON commercialsubscription USING btree (registrant);

CREATE INDEX commercialsubscription__sales_system_id__idx ON commercialsubscription USING btree (sales_system_id);

CREATE UNIQUE INDEX customlanguagecode__distribution__sourcepackagename__code__key ON customlanguagecode USING btree (distribution, sourcepackagename, language_code) WHERE (distribution IS NOT NULL);

CREATE UNIQUE INDEX customlanguagecode__product__code__key ON customlanguagecode USING btree (product, language_code) WHERE (product IS NOT NULL);

CREATE INDEX cve_datecreated_idx ON cve USING btree (datecreated);

CREATE INDEX cve_datemodified_idx ON cve USING btree (datemodified);

CREATE INDEX cve_fti ON cve USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX cvereference_cve_idx ON cvereference USING btree (cve);

CREATE INDEX diff__diff_text__idx ON diff USING btree (diff_text);

CREATE INDEX distribution__bug_supervisor__idx ON distribution USING btree (bug_supervisor) WHERE (bug_supervisor IS NOT NULL);

CREATE INDEX distribution__driver__idx ON distribution USING btree (driver);

CREATE INDEX distribution__icon__idx ON distribution USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX distribution__language_pack_admin__idx ON distribution USING btree (language_pack_admin);

CREATE INDEX distribution__logo__idx ON distribution USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX distribution__members__idx ON distribution USING btree (members);

CREATE INDEX distribution__mirror_admin__idx ON distribution USING btree (mirror_admin);

CREATE INDEX distribution__mugshot__idx ON distribution USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX distribution__owner__idx ON distribution USING btree (owner);

CREATE INDEX distribution__security_contact__idx ON distribution USING btree (security_contact);

CREATE INDEX distribution__upload_admin__idx ON distribution USING btree (upload_admin);

CREATE INDEX distribution_fti ON distribution USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX distribution_translationgroup_idx ON distribution USING btree (translationgroup);

CREATE INDEX distributionbounty_distribution_idx ON distributionbounty USING btree (distribution);

CREATE UNIQUE INDEX distributionmirror__archive__distribution__country__key ON distributionmirror USING btree (distribution, country, content) WHERE ((country_dns_mirror IS TRUE) AND (content = 1));

CREATE INDEX distributionmirror__country__status__idx ON distributionmirror USING btree (country, status);

CREATE INDEX distributionmirror__owner__idx ON distributionmirror USING btree (owner);

CREATE UNIQUE INDEX distributionmirror__releases__distribution__country__key ON distributionmirror USING btree (distribution, country, content) WHERE ((country_dns_mirror IS TRUE) AND (content = 2));

CREATE INDEX distributionmirror__reviewer__idx ON distributionmirror USING btree (reviewer);

CREATE INDEX distributionmirror__status__idx ON distributionmirror USING btree (status);

CREATE INDEX distributionsourcepackagecache__archive__idx ON distributionsourcepackagecache USING btree (archive);

CREATE INDEX distributionsourcepackagecache_fti ON distributionsourcepackagecache USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX distroarchseries__distroseries__idx ON distroarchseries USING btree (distroseries);

CREATE INDEX distroarchseries__owner__idx ON distroarchseries USING btree (owner);

CREATE INDEX distrocomponentuploader_uploader_idx ON distrocomponentuploader USING btree (uploader);

CREATE INDEX distroseries__driver__idx ON distroseries USING btree (driver) WHERE (driver IS NOT NULL);

CREATE INDEX distroseries__owner__idx ON distroseries USING btree (owner);

CREATE INDEX distroseriespackagecache__archive__idx ON distroseriespackagecache USING btree (archive);

CREATE INDEX distroseriespackagecache__distroseries__idx ON distroseriespackagecache USING btree (distroseries);

CREATE INDEX distroseriespackagecache_fti ON distroseriespackagecache USING gist (fti ts2.gist_tsvector_ops);

CREATE UNIQUE INDEX emailaddress__account__key ON emailaddress USING btree (account) WHERE ((status = 4) AND (account IS NOT NULL));

CREATE INDEX emailaddress__account__status__idx ON emailaddress USING btree (account, status);

CREATE UNIQUE INDEX emailaddress__lower_email__key ON emailaddress USING btree (lower(email));

CREATE UNIQUE INDEX emailaddress__person__key ON emailaddress USING btree (person) WHERE ((status = 4) AND (person IS NOT NULL));

CREATE INDEX emailaddress__person__status__idx ON emailaddress USING btree (person, status);

CREATE INDEX entitlement__approved_by__idx ON entitlement USING btree (approved_by) WHERE (approved_by IS NOT NULL);

CREATE INDEX entitlement__distribution__idx ON entitlement USING btree (distribution) WHERE (distribution IS NOT NULL);

CREATE INDEX entitlement__person__idx ON entitlement USING btree (person);

CREATE INDEX entitlement__product__idx ON entitlement USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX entitlement__project__idx ON entitlement USING btree (project) WHERE (project IS NOT NULL);

CREATE INDEX entitlement__registrant__idx ON entitlement USING btree (registrant) WHERE (registrant IS NOT NULL);

CREATE INDEX entitlement_lookup_idx ON entitlement USING btree (entitlement_type, date_starts, date_expires, person, state);

CREATE INDEX faq__distribution__idx ON faq USING btree (distribution) WHERE (distribution IS NOT NULL);

CREATE INDEX faq__last_updated_by__idx ON faq USING btree (last_updated_by);

CREATE INDEX faq__owner__idx ON faq USING btree (owner);

CREATE INDEX faq__product__idx ON faq USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX faq_fti ON faq USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX featuredproject__pillar_name__idx ON featuredproject USING btree (pillar_name);

CREATE INDEX flatpackagesetinclusion__child__idx ON flatpackagesetinclusion USING btree (child);

CREATE INDEX hwdevice__bus_product_id__idx ON hwdevice USING btree (bus_product_id);

CREATE UNIQUE INDEX hwdevice__bus_vendor_id__bus_product_id__key ON hwdevice USING btree (bus_vendor_id, bus_product_id) WHERE (variant IS NULL);

CREATE INDEX hwdevice__name__idx ON hwdevice USING btree (name);

CREATE UNIQUE INDEX hwdeviceclass__device__main_class__key ON hwdeviceclass USING btree (device, main_class) WHERE (sub_class IS NULL);

CREATE UNIQUE INDEX hwdeviceclass__device__main_class__sub_class__key ON hwdeviceclass USING btree (device, main_class, sub_class) WHERE (sub_class IS NOT NULL);

CREATE INDEX hwdeviceclass__main_class__idx ON hwdeviceclass USING btree (main_class);

CREATE INDEX hwdeviceclass__sub_class__idx ON hwdeviceclass USING btree (sub_class);

CREATE UNIQUE INDEX hwdevicedriverlink__device__driver__key ON hwdevicedriverlink USING btree (device, driver) WHERE (driver IS NOT NULL);

CREATE INDEX hwdevicedriverlink__device__idx ON hwdevicedriverlink USING btree (device);

CREATE UNIQUE INDEX hwdevicedriverlink__device__key ON hwdevicedriverlink USING btree (device) WHERE (driver IS NULL);

CREATE INDEX hwdevicedriverlink__driver__idx ON hwdevicedriverlink USING btree (driver);

CREATE INDEX hwdevicenamevariant__device__idx ON hwdevicenamevariant USING btree (device);

CREATE INDEX hwdevicenamevariant__product_name__idx ON hwdevicenamevariant USING btree (product_name);

CREATE INDEX hwdmihandle__submission__idx ON hwdmihandle USING btree (submission);

CREATE INDEX hwdmivalue__hanlde__idx ON hwdmivalue USING btree (handle);

CREATE INDEX hwdriver__name__idx ON hwdriver USING btree (name);

CREATE UNIQUE INDEX hwdriver__name__key ON hwdriver USING btree (name) WHERE (package_name IS NULL);

CREATE INDEX hwsubmission__lower_raw_emailaddress__idx ON hwsubmission USING btree (lower(raw_emailaddress));

CREATE INDEX hwsubmission__owner__idx ON hwsubmission USING btree (owner);

CREATE INDEX hwsubmission__raw_emailaddress__idx ON hwsubmission USING btree (raw_emailaddress);

CREATE INDEX hwsubmission__raw_submission__idx ON hwsubmission USING btree (raw_submission);

CREATE INDEX hwsubmission__status__idx ON hwsubmission USING btree (status);

CREATE INDEX hwsubmission__system_fingerprint__idx ON hwsubmission USING btree (system_fingerprint);

CREATE INDEX hwsubmissionbug__bug ON hwsubmissionbug USING btree (bug);

CREATE INDEX hwsubmissiondevice__device_driver_link__idx ON hwsubmissiondevice USING btree (device_driver_link);

CREATE INDEX hwsubmissiondevice__submission__idx ON hwsubmissiondevice USING btree (submission);

CREATE UNIQUE INDEX hwtest__name__version__key ON hwtest USING btree (name, version) WHERE (namespace IS NULL);

CREATE UNIQUE INDEX hwtest__namespace__name__version__key ON hwtest USING btree (namespace, name, version) WHERE (namespace IS NOT NULL);

CREATE INDEX hwtestanswer__choice__idx ON hwtestanswer USING btree (choice);

CREATE INDEX hwtestanswer__submission__idx ON hwtestanswer USING btree (submission);

CREATE INDEX hwtestanswer__test__idx ON hwtestanswer USING btree (test);

CREATE INDEX hwtestanswerchoice__test__idx ON hwtestanswerchoice USING btree (test);

CREATE INDEX hwtestanswercount__choice__idx ON hwtestanswercount USING btree (choice);

CREATE INDEX hwtestanswercount__distroarchrelease__idx ON hwtestanswercount USING btree (distroarchseries) WHERE (distroarchseries IS NOT NULL);

CREATE INDEX hwtestanswercount__test__idx ON hwtestanswercount USING btree (test);

CREATE INDEX hwtestanswercountdevice__device_driver__idx ON hwtestanswercountdevice USING btree (device_driver);

CREATE INDEX hwtestanswerdevice__device_driver__idx ON hwtestanswerdevice USING btree (device_driver);

CREATE INDEX hwvendorid__vendor_id_for_bus__idx ON hwvendorid USING btree (vendor_id_for_bus);

CREATE INDEX hwvendorid__vendorname__idx ON hwvendorid USING btree (vendor_name);

CREATE UNIQUE INDEX hwvendorname__lc_vendor_name__idx ON hwvendorname USING btree (ulower(name));

CREATE INDEX hwvendorname__name__idx ON hwdriver USING btree (name);

CREATE INDEX ircid_person_idx ON ircid USING btree (person);

CREATE INDEX jabberid_person_idx ON jabberid USING btree (person);

CREATE INDEX job__date_finished__idx ON job USING btree (date_finished) WHERE (date_finished IS NOT NULL);

CREATE INDEX job__lease_expires__idx ON job USING btree (lease_expires);

CREATE INDEX job__requester__key ON job USING btree (requester) WHERE (requester IS NOT NULL);

CREATE INDEX job__scheduled_start__idx ON job USING btree (scheduled_start);

CREATE INDEX karma_person_datecreated_idx ON karma USING btree (person, datecreated);

ALTER TABLE karma CLUSTER ON karma_person_datecreated_idx;

CREATE INDEX karmacache__category__karmavalue__idx ON karmacache USING btree (category, karmavalue) WHERE ((((category IS NOT NULL) AND (product IS NULL)) AND (project IS NULL)) AND (distribution IS NULL));

CREATE INDEX karmacache__distribution__category__karmavalue__idx ON karmacache USING btree (distribution, category, karmavalue) WHERE (((category IS NOT NULL) AND (distribution IS NOT NULL)) AND (sourcepackagename IS NULL));

CREATE INDEX karmacache__distribution__karmavalue__idx ON karmacache USING btree (distribution, karmavalue) WHERE (((category IS NULL) AND (distribution IS NOT NULL)) AND (sourcepackagename IS NULL));

CREATE INDEX karmacache__karmavalue__idx ON karmacache USING btree (karmavalue) WHERE ((((category IS NULL) AND (product IS NULL)) AND (project IS NULL)) AND (distribution IS NULL));

CREATE INDEX karmacache__person__category__idx ON karmacache USING btree (person, category);

CREATE INDEX karmacache__product__category__karmavalue__idx ON karmacache USING btree (product, category, karmavalue) WHERE ((category IS NOT NULL) AND (product IS NOT NULL));

CREATE INDEX karmacache__product__karmavalue__idx ON karmacache USING btree (product, karmavalue) WHERE ((category IS NULL) AND (product IS NOT NULL));

CREATE INDEX karmacache__project__category__karmavalue__idx ON karmacache USING btree (project, category, karmavalue) WHERE (project IS NOT NULL);

CREATE INDEX karmacache__project__karmavalue__idx ON karmacache USING btree (project, karmavalue) WHERE ((category IS NULL) AND (project IS NOT NULL));

CREATE INDEX karmacache__sourcepackagename__category__karmavalue__idx ON karmacache USING btree (sourcepackagename, distribution, category, karmavalue) WHERE ((category IS NOT NULL) AND (sourcepackagename IS NOT NULL));

CREATE INDEX karmacache__sourcepackagename__distribution__karmavalue__idx ON karmacache USING btree (sourcepackagename, distribution, karmavalue) WHERE (sourcepackagename IS NOT NULL);

CREATE INDEX karmacache__sourcepackagename__karmavalue__idx ON karmacache USING btree (sourcepackagename, distribution, karmavalue) WHERE ((category IS NULL) AND (sourcepackagename IS NOT NULL));

CREATE UNIQUE INDEX karmacache__unq ON karmacache USING btree (person, (COALESCE(product, (-1))), (COALESCE(sourcepackagename, (-1))), (COALESCE(project, (-1))), (COALESCE(category, (-1))), (COALESCE(distribution, (-1))));

CREATE INDEX karmacache_person_idx ON karmacache USING btree (person);

CREATE INDEX karmacache_top_in_category_idx ON karmacache USING btree (person, category, karmavalue) WHERE ((((product IS NULL) AND (project IS NULL)) AND (sourcepackagename IS NULL)) AND (distribution IS NULL));

CREATE UNIQUE INDEX karmatotalcache_karma_total_person_idx ON karmatotalcache USING btree (karma_total, person);

CREATE INDEX languagepack__file__idx ON languagepack USING btree (file);

CREATE INDEX libraryfilealias__expires__idx ON libraryfilealias USING btree (expires);

CREATE INDEX libraryfilealias__filename__idx ON libraryfilealias USING btree (filename);

CREATE INDEX libraryfilealias_content_idx ON libraryfilealias USING btree (content);

CREATE INDEX libraryfilecontent__md5__idx ON libraryfilecontent USING btree (md5);

CREATE INDEX libraryfilecontent__sha256__idx ON libraryfilecontent USING btree (sha256);

CREATE INDEX libraryfilecontent_sha1_filesize_idx ON libraryfilecontent USING btree (sha1, filesize);

CREATE INDEX logintoken_requester_idx ON logintoken USING btree (requester);

CREATE INDEX lp_teamparticipation__person__idx ON lp_teamparticipation USING btree (person);

CREATE INDEX mailinglist__date_registered__idx ON mailinglist USING btree (status, date_registered);

CREATE INDEX mailinglist__registrant__idx ON mailinglist USING btree (registrant);

CREATE INDEX mailinglist__reviewer__idx ON mailinglist USING btree (reviewer);

CREATE UNIQUE INDEX mailinglist__team__status__key ON mailinglist USING btree (team, status);

CREATE INDEX mailinglistban__banned_by__idx ON mailinglistban USING btree (banned_by);

CREATE INDEX mailinglistban__person__idx ON mailinglistban USING btree (person);

CREATE INDEX mailinglistsubscription__email_address__idx ON mailinglistsubscription USING btree (email_address) WHERE (email_address IS NOT NULL);

CREATE INDEX mailinglistsubscription__mailing_list__idx ON mailinglistsubscription USING btree (mailing_list);

CREATE UNIQUE INDEX mailinglistsubscription__person__mailing_list__key ON mailinglistsubscription USING btree (person, mailing_list);

CREATE INDEX mentoringoffer__owner__idx ON mentoringoffer USING btree (owner);

CREATE INDEX mentoringoffer__team__idx ON mentoringoffer USING btree (team);

CREATE INDEX mergedirectivejob__merge_directive__idx ON mergedirectivejob USING btree (merge_directive);

CREATE INDEX message_fti ON message USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX message_owner_idx ON message USING btree (owner);

CREATE INDEX message_parent_idx ON message USING btree (parent);

CREATE INDEX message_raw_idx ON message USING btree (raw) WHERE (raw IS NOT NULL);

CREATE INDEX message_rfc822msgid_idx ON message USING btree (rfc822msgid);

CREATE INDEX messageapproval__disposed_by__idx ON messageapproval USING btree (disposed_by) WHERE (disposed_by IS NOT NULL);

CREATE INDEX messageapproval__mailing_list__status__posted_date__idx ON messageapproval USING btree (mailing_list, status, posted_date);

CREATE INDEX messageapproval__message__idx ON messageapproval USING btree (message);

CREATE INDEX messageapproval__posted_by__idx ON messageapproval USING btree (posted_by);

CREATE INDEX messageapproval__posted_message__idx ON messageapproval USING btree (posted_message);

CREATE INDEX messagechunk_blob_idx ON messagechunk USING btree (blob) WHERE (blob IS NOT NULL);

CREATE INDEX messagechunk_fti ON messagechunk USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX mirror__owner__idx ON mirror USING btree (owner);

CREATE UNIQUE INDEX mirrordistroarchseries_uniq ON mirrordistroarchseries USING btree (distribution_mirror, distroarchseries, component, pocket);

CREATE UNIQUE INDEX mirrordistroseriessource_uniq ON mirrordistroseriessource USING btree (distribution_mirror, distroseries, component, pocket);

CREATE INDEX mirrorproberecord__date_created__idx ON mirrorproberecord USING btree (date_created);

CREATE INDEX mirrorproberecord__distribution_mirror__date_created__idx ON mirrorproberecord USING btree (distribution_mirror, date_created);

CREATE INDEX mirrorproberecord__log_file__idx ON mirrorproberecord USING btree (log_file) WHERE (log_file IS NOT NULL);

CREATE INDEX oauthaccesstoken__consumer__idx ON oauthaccesstoken USING btree (consumer);

CREATE INDEX oauthaccesstoken__date_expires__idx ON oauthaccesstoken USING btree (date_expires) WHERE (date_expires IS NOT NULL);

CREATE INDEX oauthaccesstoken__distribution__sourcepackagename__idx ON oauthaccesstoken USING btree (distribution, sourcepackagename) WHERE (distribution IS NOT NULL);

CREATE INDEX oauthaccesstoken__person__idx ON oauthaccesstoken USING btree (person);

CREATE INDEX oauthaccesstoken__product__idx ON oauthaccesstoken USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX oauthaccesstoken__project__idx ON oauthaccesstoken USING btree (project) WHERE (project IS NOT NULL);

CREATE INDEX oauthnonce__access_token__idx ON oauthnonce USING btree (access_token);

CREATE INDEX oauthnonce__request_timestamp__idx ON oauthnonce USING btree (request_timestamp);

CREATE INDEX oauthrequesttoken__consumer__idx ON oauthrequesttoken USING btree (consumer);

CREATE INDEX oauthrequesttoken__date_created__idx ON oauthrequesttoken USING btree (date_created);

CREATE INDEX oauthrequesttoken__distribution__sourcepackagename__idx ON oauthrequesttoken USING btree (distribution, sourcepackagename) WHERE (distribution IS NOT NULL);

CREATE INDEX oauthrequesttoken__person__idx ON oauthrequesttoken USING btree (person) WHERE (person IS NOT NULL);

CREATE INDEX oauthrequesttoken__product__idx ON oauthrequesttoken USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX oauthrequesttoken__project__idx ON oauthrequesttoken USING btree (project) WHERE (project IS NOT NULL);

CREATE UNIQUE INDEX officialbugtag__distribution__tag__key ON officialbugtag USING btree (distribution, tag) WHERE (distribution IS NOT NULL);

CREATE UNIQUE INDEX officialbugtag__product__tag__key ON officialbugtag USING btree (product, tag) WHERE (product IS NOT NULL);

CREATE UNIQUE INDEX officialbugtag__project__tag__key ON officialbugtag USING btree (project, tag) WHERE (product IS NOT NULL);

CREATE INDEX openidrpconfig__logo__idx ON openidrpconfig USING btree (logo);

CREATE UNIQUE INDEX openidrpconfig__trust_root__key ON openidrpconfig USING btree (trust_root);

CREATE INDEX openidrpsummary__openid_identifier__idx ON openidrpsummary USING btree (openid_identifier);

CREATE INDEX openidrpsummary__trust_root__idx ON openidrpsummary USING btree (trust_root);

CREATE INDEX packagebugsupervisor__bug_supervisor__idx ON packagebugsupervisor USING btree (bug_supervisor);

CREATE INDEX packagebuild__archive__idx ON packagebuild USING btree (archive);

CREATE UNIQUE INDEX packagebuild__build_farm_job__idx ON packagebuild USING btree (build_farm_job);

CREATE INDEX packagebuild__upload_log__idx ON packagebuild USING btree (upload_log) WHERE (upload_log IS NOT NULL);

CREATE INDEX packagecopyrequest__datecreated__idx ON packagecopyrequest USING btree (date_created);

CREATE INDEX packagecopyrequest__requester__idx ON packagecopyrequest USING btree (requester);

CREATE INDEX packagecopyrequest__targetarchive__idx ON packagecopyrequest USING btree (target_archive);

CREATE INDEX packagecopyrequest__targetdistroseries__idx ON packagecopyrequest USING btree (target_distroseries) WHERE (target_distroseries IS NOT NULL);

CREATE INDEX packagediff__diff_content__idx ON packagediff USING btree (diff_content);

CREATE INDEX packagediff__from_source__idx ON packagediff USING btree (from_source);

CREATE INDEX packagediff__requester__idx ON packagediff USING btree (requester);

CREATE INDEX packagediff__status__idx ON packagediff USING btree (status);

CREATE INDEX packagediff__to_source__idx ON packagediff USING btree (to_source);

CREATE INDEX packageset__distroseries__idx ON packageset USING btree (distroseries);

CREATE INDEX packageset__owner__idx ON packageset USING btree (owner);

CREATE INDEX packageset__packagesetgroup__idx ON packageset USING btree (packagesetgroup);

CREATE INDEX packagesetgroup__owner__idx ON packagesetgroup USING btree (owner);

CREATE INDEX packagesetinclusion__child__idx ON packagesetinclusion USING btree (child);

CREATE INDEX packagesetsources__sourcepackagename__idx ON packagesetsources USING btree (sourcepackagename);

CREATE INDEX packageupload__changesfile__idx ON packageupload USING btree (changesfile);

CREATE INDEX packageupload__distroseries__key ON packageupload USING btree (distroseries);

CREATE INDEX packageupload__distroseries__status__idx ON packageupload USING btree (distroseries, status);

CREATE INDEX packageupload__signing_key__idx ON packageupload USING btree (signing_key);

CREATE INDEX packageuploadbuild__build__idx ON packageuploadbuild USING btree (build);

CREATE INDEX packageuploadcustom__libraryfilealias__idx ON packageuploadcustom USING btree (libraryfilealias);

CREATE INDEX packageuploadcustom__packageupload__idx ON packageuploadcustom USING btree (packageupload);

CREATE INDEX packageuploadsource__sourcepackagerelease__idx ON packageuploadsource USING btree (sourcepackagerelease);

CREATE INDEX packaging__distroseries__sourcepackagename__idx ON packaging USING btree (distroseries, sourcepackagename);

CREATE INDEX packaging__owner__idx ON packaging USING btree (owner);

CREATE INDEX packaging_sourcepackagename_idx ON packaging USING btree (sourcepackagename);

CREATE INDEX parsedapachelog__first_line__idx ON parsedapachelog USING btree (first_line);

CREATE INDEX person__icon__idx ON person USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX person__logo__idx ON person USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX person__merged__idx ON person USING btree (merged) WHERE (merged IS NOT NULL);

CREATE INDEX person__mugshot__idx ON person USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX person__registrant__idx ON person USING btree (registrant);

CREATE INDEX person__teamowner__idx ON person USING btree (teamowner) WHERE (teamowner IS NOT NULL);

CREATE INDEX person_datecreated_idx ON person USING btree (datecreated);

CREATE INDEX person_fti ON person USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX person_sorting_idx ON person USING btree (person_sort_key(displayname, name));

CREATE INDEX personlocation__last_modified_by__idx ON personlocation USING btree (last_modified_by);

CREATE INDEX personnotification__date_emailed__idx ON personnotification USING btree (date_emailed);

CREATE INDEX personnotification__person__idx ON personnotification USING btree (person);

CREATE INDEX pillarname__alias_for__idx ON pillarname USING btree (alias_for) WHERE (alias_for IS NOT NULL);

CREATE UNIQUE INDEX pillarname__distribution__key ON pillarname USING btree (distribution) WHERE (distribution IS NOT NULL);

CREATE UNIQUE INDEX pillarname__product__key ON pillarname USING btree (product) WHERE (product IS NOT NULL);

CREATE UNIQUE INDEX pillarname__project__key ON pillarname USING btree (project) WHERE (project IS NOT NULL);

CREATE INDEX pocketchroot__chroot__idx ON pocketchroot USING btree (chroot);

CREATE INDEX pocomment_person_idx ON pocomment USING btree (person);

CREATE INDEX poexportrequest__person__idx ON poexportrequest USING btree (person);

CREATE UNIQUE INDEX poexportrequest_duplicate_key ON poexportrequest USING btree (potemplate, person, format, (COALESCE(pofile, (-1))));

CREATE INDEX pofile__from_sourcepackagename__idx ON pofile USING btree (from_sourcepackagename) WHERE (from_sourcepackagename IS NOT NULL);

CREATE UNIQUE INDEX pofile__potemplate__path__key ON pofile USING btree (potemplate, path);

CREATE UNIQUE INDEX pofile__unreviewed_count__id__key ON pofile USING btree (unreviewed_count, id);

CREATE INDEX pofile_datecreated_idx ON pofile USING btree (datecreated);

CREATE INDEX pofile_language_idx ON pofile USING btree (language);

CREATE INDEX pofile_lasttranslator_idx ON pofile USING btree (lasttranslator);

CREATE INDEX pofile_owner_idx ON pofile USING btree (owner);

CREATE UNIQUE INDEX pofile_template_and_language_idx ON pofile USING btree (potemplate, language, (COALESCE(variant, ''::text)));

ALTER TABLE pofile CLUSTER ON pofile_template_and_language_idx;

CREATE INDEX pofile_variant_idx ON pofile USING btree (variant);

CREATE INDEX pofiletranslator__date_last_touched__idx ON pofiletranslator USING btree (date_last_touched);

CREATE INDEX pofiletranslator__latest_message__idx ON pofiletranslator USING btree (latest_message);

CREATE INDEX pofiletranslator__pofile__idx ON pofiletranslator USING btree (pofile);

CREATE INDEX polloption_poll_idx ON polloption USING btree (poll);

CREATE UNIQUE INDEX pomsgid_msgid_key ON pomsgid USING btree (sha1(msgid));

CREATE INDEX potemplate__date_last_updated__idx ON potemplate USING btree (date_last_updated);

CREATE UNIQUE INDEX potemplate__distroseries__sourcepackagename__name__key ON potemplate USING btree (distroseries, sourcepackagename, name);

CREATE INDEX potemplate__name__idx ON potemplate USING btree (name);

CREATE UNIQUE INDEX potemplate__productseries__name__key ON potemplate USING btree (productseries, name);

CREATE INDEX potemplate__source_file__idx ON potemplate USING btree (source_file) WHERE (source_file IS NOT NULL);

CREATE INDEX potemplate_languagepack_idx ON potemplate USING btree (languagepack);

CREATE INDEX potemplate_owner_idx ON potemplate USING btree (owner);

CREATE INDEX potmsgset__context__msgid_singular__msgid_plural__idx ON potmsgset USING btree (context, msgid_singular, msgid_plural) WHERE ((context IS NOT NULL) AND (msgid_plural IS NOT NULL));

CREATE INDEX potmsgset__context__msgid_singular__no_msgid_plural__idx ON potmsgset USING btree (context, msgid_singular) WHERE ((context IS NOT NULL) AND (msgid_plural IS NULL));

CREATE INDEX potmsgset__no_context__msgid_singular__msgid_plural__idx ON potmsgset USING btree (msgid_singular, msgid_plural) WHERE ((context IS NULL) AND (msgid_plural IS NOT NULL));

CREATE INDEX potmsgset__no_context__msgid_singular__no_msgid_plural__idx ON potmsgset USING btree (msgid_singular) WHERE ((context IS NULL) AND (msgid_plural IS NULL));

CREATE INDEX potmsgset_primemsgid_idx ON potmsgset USING btree (msgid_singular);

CREATE INDEX potmsgset_sequence_idx ON potmsgset USING btree (sequence);

CREATE UNIQUE INDEX potranslation_translation_key ON potranslation USING btree (sha1(translation));

CREATE INDEX previewdiff__diff__idx ON previewdiff USING btree (diff);

CREATE INDEX product__bug_supervisor__idx ON product USING btree (bug_supervisor) WHERE (bug_supervisor IS NOT NULL);

CREATE INDEX product__driver__idx ON product USING btree (driver) WHERE (driver IS NOT NULL);

CREATE INDEX product__icon__idx ON product USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX product__logo__idx ON product USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX product__mugshot__idx ON product USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX product__registrant__idx ON product USING btree (registrant);

CREATE INDEX product__security_contact__idx ON product USING btree (security_contact) WHERE (security_contact IS NOT NULL);

CREATE INDEX product_active_idx ON product USING btree (active);

CREATE INDEX product_bugcontact_idx ON product USING btree (bug_supervisor);

CREATE INDEX product_fti ON product USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX product_owner_idx ON product USING btree (owner);

CREATE INDEX product_project_idx ON product USING btree (project);

CREATE INDEX product_translationgroup_idx ON product USING btree (translationgroup);

CREATE INDEX productlicense__license__idx ON productlicense USING btree (license);

CREATE INDEX productrelease_datecreated_idx ON productrelease USING btree (datecreated);

CREATE INDEX productrelease_owner_idx ON productrelease USING btree (owner);

CREATE INDEX productreleasefile__libraryfile__idx ON productreleasefile USING btree (libraryfile);

CREATE INDEX productreleasefile__signature__idx ON productreleasefile USING btree (signature) WHERE (signature IS NOT NULL);

CREATE INDEX productreleasefile__uploader__idx ON productreleasefile USING btree (uploader);

CREATE INDEX productreleasefile_fti ON productreleasefile USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX productseries__branch__idx ON productseries USING btree (branch) WHERE (branch IS NOT NULL);

CREATE INDEX productseries__driver__idx ON productseries USING btree (driver);

CREATE INDEX productseries__owner__idx ON productseries USING btree (owner);

CREATE INDEX productseries__translations_branch__idx ON productseries USING btree (translations_branch);

CREATE INDEX productseries_datecreated_idx ON productseries USING btree (datecreated);

CREATE INDEX project__driver__idx ON project USING btree (driver);

CREATE INDEX project__icon__idx ON project USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX project__logo__idx ON project USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX project__mugshot__idx ON project USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX project__registrant__idx ON project USING btree (registrant);

CREATE INDEX project_fti ON project USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX project_owner_idx ON project USING btree (owner);

CREATE INDEX project_translationgroup_idx ON project USING btree (translationgroup);

CREATE INDEX pushmirroraccess_person_idx ON pushmirroraccess USING btree (person);

CREATE INDEX question__answerer__idx ON question USING btree (answerer);

CREATE INDEX question__assignee__idx ON question USING btree (assignee);

CREATE INDEX question__distribution__sourcepackagename__idx ON question USING btree (distribution, sourcepackagename);

CREATE INDEX question__distro__datecreated__idx ON question USING btree (distribution, datecreated);

CREATE INDEX question__faq__idx ON question USING btree (faq) WHERE (faq IS NOT NULL);

CREATE INDEX question__owner__idx ON question USING btree (owner);

CREATE INDEX question__product__datecreated__idx ON question USING btree (product, datecreated);

CREATE INDEX question__product__idx ON question USING btree (product);

CREATE INDEX question__status__datecreated__idx ON question USING btree (status, datecreated);

CREATE INDEX question_fti ON question USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX questionbug__question__idx ON questionbug USING btree (question);

CREATE INDEX questionmessage__question__idx ON questionmessage USING btree (question);

CREATE INDEX questionreopening__answerer__idx ON questionreopening USING btree (answerer);

CREATE INDEX questionreopening__datecreated__idx ON questionreopening USING btree (datecreated);

CREATE INDEX questionreopening__question__idx ON questionreopening USING btree (question);

CREATE INDEX questionreopening__reopener__idx ON questionreopening USING btree (reopener);

CREATE INDEX questionsubscription__subscriber__idx ON questionsubscription USING btree (person);

CREATE INDEX requestedcds_request_architecture_idx ON requestedcds USING btree (request, architecture);

CREATE INDEX revision__gpgkey__idx ON revision USING btree (gpgkey) WHERE (gpgkey IS NOT NULL);

CREATE INDEX revision__karma_allocated__idx ON revision USING btree (karma_allocated) WHERE (karma_allocated IS FALSE);

CREATE INDEX revision__revision_author__idx ON revision USING btree (revision_author);

CREATE INDEX revision__revision_date__idx ON revision USING btree (revision_date);

CREATE INDEX revisionauthor__email__idx ON revisionauthor USING btree (email);

CREATE INDEX revisionauthor__lower_email__idx ON revisionauthor USING btree (lower(email));

CREATE INDEX revisionauthor__person__idx ON revisionauthor USING btree (person);

CREATE UNIQUE INDEX revisioncache__distroseries__sourcepackagename__revision__priva ON revisioncache USING btree (distroseries, sourcepackagename, revision, private) WHERE (distroseries IS NOT NULL);

CREATE UNIQUE INDEX revisioncache__product__revision__private__key ON revisioncache USING btree (product, revision, private) WHERE (product IS NOT NULL);

CREATE INDEX revisioncache__revision__idx ON revisioncache USING btree (revision);

CREATE INDEX revisioncache__revision_author__idx ON revisioncache USING btree (revision_author);

CREATE INDEX revisioncache__revision_date__idx ON revisioncache USING btree (revision_date);

CREATE INDEX sbpph__dateremoved__idx ON binarypackagepublishinghistory USING btree (dateremoved) WHERE (dateremoved IS NOT NULL);

CREATE INDEX scriptactivity__name__date_started__idx ON scriptactivity USING btree (name, date_started);

CREATE INDEX securebinarypackagepublishinghistory__archive__status__idx ON binarypackagepublishinghistory USING btree (archive, status);

CREATE INDEX securebinarypackagepublishinghistory__distroarchseries__idx ON binarypackagepublishinghistory USING btree (distroarchseries);

CREATE INDEX securebinarypackagepublishinghistory__removed_by__idx ON binarypackagepublishinghistory USING btree (removed_by) WHERE (removed_by IS NOT NULL);

CREATE INDEX securebinarypackagepublishinghistory__supersededby__idx ON binarypackagepublishinghistory USING btree (supersededby);

CREATE INDEX securebinarypackagepublishinghistory_binarypackagerelease_idx ON binarypackagepublishinghistory USING btree (binarypackagerelease);

CREATE INDEX securebinarypackagepublishinghistory_component_idx ON binarypackagepublishinghistory USING btree (component);

CREATE INDEX securebinarypackagepublishinghistory_pocket_idx ON binarypackagepublishinghistory USING btree (pocket);

CREATE INDEX securebinarypackagepublishinghistory_section_idx ON binarypackagepublishinghistory USING btree (section);

CREATE INDEX securebinarypackagepublishinghistory_status_idx ON binarypackagepublishinghistory USING btree (status);

CREATE INDEX securesourcepackagepublishinghistory__archive__status__idx ON sourcepackagepublishinghistory USING btree (archive, status);

CREATE INDEX securesourcepackagepublishinghistory__distroseries__idx ON sourcepackagepublishinghistory USING btree (distroseries);

CREATE INDEX securesourcepackagepublishinghistory__removed_by__idx ON sourcepackagepublishinghistory USING btree (removed_by) WHERE (removed_by IS NOT NULL);

CREATE INDEX securesourcepackagepublishinghistory_component_idx ON sourcepackagepublishinghistory USING btree (component);

CREATE INDEX securesourcepackagepublishinghistory_pocket_idx ON sourcepackagepublishinghistory USING btree (pocket);

CREATE INDEX securesourcepackagepublishinghistory_section_idx ON sourcepackagepublishinghistory USING btree (section);

CREATE INDEX securesourcepackagepublishinghistory_sourcepackagerelease_idx ON sourcepackagepublishinghistory USING btree (sourcepackagerelease);

CREATE INDEX securesourcepackagepublishinghistory_status_idx ON sourcepackagepublishinghistory USING btree (status);

CREATE INDEX seriessourcepackagebranch__branch__idx ON seriessourcepackagebranch USING btree (branch);

CREATE INDEX seriessourcepackagebranch__registrant__key ON seriessourcepackagebranch USING btree (registrant);

CREATE INDEX shipitreport__csvfile__idx ON shipitreport USING btree (csvfile);

CREATE INDEX shipitsurvey__account__idx ON shipitsurvey USING btree (account);

CREATE UNIQUE INDEX shipitsurvey__unexported__key ON shipitsurvey USING btree (id) WHERE (exported IS FALSE);

CREATE INDEX shipitsurveyresult__survey__question__answer__idx ON shipitsurveyresult USING btree (survey, question, answer);

CREATE INDEX shipment_shippingrun_idx ON shipment USING btree (shippingrun);

CREATE INDEX shippingrequest__daterequested__approved__idx ON shippingrequest USING btree (daterequested) WHERE (status = 1);

CREATE INDEX shippingrequest__daterequested__unapproved__idx ON shippingrequest USING btree (daterequested) WHERE (status = 0);

CREATE INDEX shippingrequest__normalized_address__idx ON shippingrequest USING btree (normalized_address);

CREATE INDEX shippingrequest__whocancelled__idx ON shippingrequest USING btree (whocancelled) WHERE (whocancelled IS NOT NULL);

CREATE INDEX shippingrequest_daterequested_idx ON shippingrequest USING btree (daterequested);

ALTER TABLE shippingrequest CLUSTER ON shippingrequest_daterequested_idx;

CREATE INDEX shippingrequest_fti ON shippingrequest USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX shippingrequest_highpriority_idx ON shippingrequest USING btree (highpriority);

CREATE UNIQUE INDEX shippingrequest_one_outstanding_request_unique ON shippingrequest USING btree (recipient) WHERE (((shipment IS NULL) AND (is_admin_request IS NOT TRUE)) AND (status <> ALL (ARRAY[2, 3])));

CREATE INDEX shippingrequest_recipient_idx ON shippingrequest USING btree (recipient);

CREATE INDEX shippingrequest_whoapproved_idx ON shippingrequest USING btree (whoapproved);

CREATE INDEX signedcodeofconduct_owner_idx ON signedcodeofconduct USING btree (owner);

CREATE INDEX sourcepackagerecipe__daily_build_archive__idx ON sourcepackagerecipe USING btree (daily_build_archive);

CREATE INDEX sourcepackagerecipe__is_stale__build_daily__idx ON sourcepackagerecipe USING btree (is_stale, build_daily);

CREATE INDEX sourcepackagerecipe__registrant__idx ON sourcepackagerecipe USING btree (registrant);

CREATE INDEX sourcepackagerecipebuild__distroseries__idx ON sourcepackagerecipebuild USING btree (distroseries);

CREATE INDEX sourcepackagerecipebuild__manifest__idx ON sourcepackagerecipebuild USING btree (manifest);

CREATE INDEX sourcepackagerecipebuild__recipe__idx ON sourcepackagerecipebuild USING btree (recipe);

CREATE INDEX sourcepackagerecipebuild__requester__idx ON sourcepackagerecipebuild USING btree (requester);

CREATE INDEX sourcepackagerecipedata__base_branch__idx ON sourcepackagerecipedata USING btree (base_branch);

CREATE UNIQUE INDEX sourcepackagerecipedata__sourcepackage_recipe__key ON sourcepackagerecipedata USING btree (sourcepackage_recipe) WHERE (sourcepackage_recipe IS NOT NULL);

CREATE UNIQUE INDEX sourcepackagerecipedata__sourcepackage_recipe_build__key ON sourcepackagerecipedata USING btree (sourcepackage_recipe_build) WHERE (sourcepackage_recipe_build IS NOT NULL);

CREATE INDEX sourcepackagerecipedatainstruction__branch__idx ON sourcepackagerecipedatainstruction USING btree (branch);

CREATE INDEX sourcepackagerelease__changelog__idx ON sourcepackagerelease USING btree (changelog);

CREATE INDEX sourcepackagerelease__sourcepackage_recipe_build__idx ON sourcepackagerelease USING btree (sourcepackage_recipe_build);

CREATE INDEX sourcepackagerelease__upload_archive__idx ON sourcepackagerelease USING btree (upload_archive);

CREATE INDEX sourcepackagerelease_creator_idx ON sourcepackagerelease USING btree (creator);

CREATE INDEX sourcepackagerelease_maintainer_idx ON sourcepackagerelease USING btree (maintainer);

CREATE INDEX sourcepackagerelease_sourcepackagename_idx ON sourcepackagerelease USING btree (sourcepackagename);

CREATE INDEX sourcepackagerelease_version_sort ON sourcepackagerelease USING btree (debversion_sort_key(version));

CREATE INDEX sourcepackagereleasefile_libraryfile_idx ON sourcepackagereleasefile USING btree (libraryfile);

CREATE INDEX sourcepackagereleasefile_sourcepackagerelease_idx ON sourcepackagereleasefile USING btree (sourcepackagerelease);

CREATE INDEX specification__completer__idx ON specification USING btree (completer);

CREATE INDEX specification__goal_decider__idx ON specification USING btree (goal_decider);

CREATE INDEX specification__goal_proposer__idx ON specification USING btree (goal_proposer);

CREATE INDEX specification__starter__idx ON specification USING btree (starter);

CREATE INDEX specification_approver_idx ON specification USING btree (approver);

CREATE INDEX specification_assignee_idx ON specification USING btree (assignee);

CREATE INDEX specification_datecreated_idx ON specification USING btree (datecreated);

CREATE INDEX specification_drafter_idx ON specification USING btree (drafter);

CREATE INDEX specification_fti ON specification USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX specification_owner_idx ON specification USING btree (owner);

CREATE INDEX specificationbranch__registrant__idx ON specificationbranch USING btree (registrant);

CREATE INDEX specificationbranch__specification__idx ON specificationbranch USING btree (specification);

CREATE INDEX specificationbug_bug_idx ON specificationbug USING btree (bug);

CREATE INDEX specificationbug_specification_idx ON specificationbug USING btree (specification);

CREATE INDEX specificationdependency_dependency_idx ON specificationdependency USING btree (dependency);

CREATE INDEX specificationdependency_specification_idx ON specificationdependency USING btree (specification);

CREATE INDEX specificationfeedback_requester_idx ON specificationfeedback USING btree (requester);

CREATE INDEX specificationfeedback_reviewer_idx ON specificationfeedback USING btree (reviewer);

CREATE INDEX specificationsubscription_specification_idx ON specificationsubscription USING btree (specification);

CREATE INDEX specificationsubscription_subscriber_idx ON specificationsubscription USING btree (person);

CREATE INDEX sprint__driver__idx ON sprint USING btree (driver);

CREATE INDEX sprint__icon__idx ON sprint USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX sprint__logo__idx ON sprint USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX sprint__mugshot__idx ON sprint USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX sprint__owner__idx ON sprint USING btree (owner);

CREATE INDEX sprint_datecreated_idx ON sprint USING btree (datecreated);

CREATE INDEX sprintattendance_sprint_idx ON sprintattendance USING btree (sprint);

CREATE INDEX sprintspec_sprint_idx ON sprintspecification USING btree (sprint);

CREATE INDEX sprintspecification__decider__idx ON sprintspecification USING btree (decider);

CREATE INDEX sprintspecification__registrant__idx ON sprintspecification USING btree (registrant);

CREATE INDEX sshkey_person_key ON sshkey USING btree (person);

CREATE INDEX staticdiff__diff__idx ON staticdiff USING btree (diff);

CREATE INDEX structuralsubscription__blueprint_notification_level__idx ON structuralsubscription USING btree (blueprint_notification_level);

CREATE INDEX structuralsubscription__bug_notification_level__idx ON structuralsubscription USING btree (bug_notification_level);

CREATE INDEX structuralsubscription__distribution__sourcepackagename__idx ON structuralsubscription USING btree (distribution, sourcepackagename) WHERE (distribution IS NOT NULL);

CREATE INDEX structuralsubscription__distroseries__idx ON structuralsubscription USING btree (distroseries) WHERE (distroseries IS NOT NULL);

CREATE INDEX structuralsubscription__milestone__idx ON structuralsubscription USING btree (milestone) WHERE (milestone IS NOT NULL);

CREATE INDEX structuralsubscription__product__idx ON structuralsubscription USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX structuralsubscription__productseries__idx ON structuralsubscription USING btree (productseries) WHERE (productseries IS NOT NULL);

CREATE INDEX structuralsubscription__project__idx ON structuralsubscription USING btree (project) WHERE (project IS NOT NULL);

CREATE INDEX structuralsubscription__subscribed_by__idx ON structuralsubscription USING btree (subscribed_by);

CREATE INDEX structuralsubscription__subscriber__idx ON structuralsubscription USING btree (subscriber);

CREATE INDEX teammembership__acknowledged_by__idx ON teammembership USING btree (acknowledged_by) WHERE (acknowledged_by IS NOT NULL);

CREATE INDEX teammembership__last_changed_by__idx ON teammembership USING btree (last_changed_by) WHERE (last_changed_by IS NOT NULL);

CREATE INDEX teammembership__proposed_by__idx ON teammembership USING btree (proposed_by) WHERE (proposed_by IS NOT NULL);

CREATE INDEX teammembership__reviewed_by__idx ON teammembership USING btree (reviewed_by) WHERE (reviewed_by IS NOT NULL);

CREATE INDEX teammembership__team__idx ON teammembership USING btree (team);

CREATE INDEX teamparticipation_person_idx ON teamparticipation USING btree (person);

ALTER TABLE teamparticipation CLUSTER ON teamparticipation_person_idx;

CREATE UNIQUE INDEX tm__potmsgset__language__no_variant__shared__current__key ON translationmessage USING btree (potmsgset, language) WHERE (((is_current IS TRUE) AND (potemplate IS NULL)) AND (variant IS NULL));

CREATE UNIQUE INDEX tm__potmsgset__language__no_variant__shared__imported__key ON translationmessage USING btree (potmsgset, language) WHERE (((is_imported IS TRUE) AND (potemplate IS NULL)) AND (variant IS NULL));

CREATE INDEX tm__potmsgset__language__variant__not_used__idx ON translationmessage USING btree (potmsgset, language, variant) WHERE (NOT ((is_current IS TRUE) AND (is_imported IS TRUE)));

CREATE UNIQUE INDEX tm__potmsgset__language__variant__shared__current__key ON translationmessage USING btree (potmsgset, language, variant) WHERE (((is_current IS TRUE) AND (potemplate IS NULL)) AND (variant IS NOT NULL));

CREATE UNIQUE INDEX tm__potmsgset__language__variant__shared__imported__key ON translationmessage USING btree (potmsgset, language, variant) WHERE (((is_imported IS TRUE) AND (potemplate IS NULL)) AND (variant IS NOT NULL));

CREATE UNIQUE INDEX tm__potmsgset__potemplate__language__no_variant__diverged__curr ON translationmessage USING btree (potmsgset, potemplate, language) WHERE (((is_current IS TRUE) AND (potemplate IS NOT NULL)) AND (variant IS NULL));

CREATE UNIQUE INDEX tm__potmsgset__potemplate__language__no_variant__diverged__impo ON translationmessage USING btree (potmsgset, potemplate, language) WHERE (((is_imported IS TRUE) AND (potemplate IS NOT NULL)) AND (variant IS NULL));

CREATE UNIQUE INDEX tm__potmsgset__potemplate__language__variant__diverged__current ON translationmessage USING btree (potmsgset, potemplate, language, variant) WHERE (((is_current IS TRUE) AND (potemplate IS NOT NULL)) AND (variant IS NOT NULL));

CREATE UNIQUE INDEX tm__potmsgset__potemplate__language__variant__diverged__importe ON translationmessage USING btree (potmsgset, potemplate, language, variant) WHERE (((is_imported IS TRUE) AND (potemplate IS NOT NULL)) AND (variant IS NOT NULL));

CREATE INDEX translationgroup__owner__idx ON translationgroup USING btree (owner);

CREATE INDEX translationimportqueueentry__content__idx ON translationimportqueueentry USING btree (content) WHERE (content IS NOT NULL);

CREATE INDEX translationimportqueueentry__context__path__idx ON translationimportqueueentry USING btree (distroseries, sourcepackagename, productseries, path);

CREATE UNIQUE INDEX translationimportqueueentry__entry_per_importer__unq ON translationimportqueueentry USING btree (importer, path, (COALESCE(potemplate, (-1))), (COALESCE(distroseries, (-1))), (COALESCE(sourcepackagename, (-1))), (COALESCE(productseries, (-1))));

CREATE INDEX translationimportqueueentry__path__idx ON translationimportqueueentry USING btree (path);

CREATE INDEX translationimportqueueentry__pofile__idx ON translationimportqueueentry USING btree (pofile) WHERE (pofile IS NOT NULL);

CREATE INDEX translationimportqueueentry__potemplate__idx ON translationimportqueueentry USING btree (potemplate) WHERE (potemplate IS NOT NULL);

CREATE INDEX translationimportqueueentry__productseries__idx ON translationimportqueueentry USING btree (productseries) WHERE (productseries IS NOT NULL);

CREATE INDEX translationimportqueueentry__sourcepackagename__idx ON translationimportqueueentry USING btree (sourcepackagename) WHERE (sourcepackagename IS NOT NULL);

CREATE UNIQUE INDEX translationimportqueueentry__status__dateimported__id__idx ON translationimportqueueentry USING btree (status, dateimported, id);

CREATE INDEX translationmessage__language__no_variant__submitter__idx ON translationmessage USING btree (language, submitter) WHERE (variant IS NULL);

CREATE INDEX translationmessage__language__variant__submitter__idx ON translationmessage USING btree (language, variant, submitter) WHERE (variant IS NOT NULL);

CREATE INDEX translationmessage__msgstr0__idx ON translationmessage USING btree (msgstr0);

CREATE INDEX translationmessage__msgstr1__idx ON translationmessage USING btree (msgstr1) WHERE (msgstr1 IS NOT NULL);

CREATE INDEX translationmessage__msgstr2__idx ON translationmessage USING btree (msgstr2) WHERE (msgstr2 IS NOT NULL);

CREATE INDEX translationmessage__msgstr3__idx ON translationmessage USING btree (msgstr3) WHERE (msgstr3 IS NOT NULL);

CREATE INDEX translationmessage__msgstr4__idx ON translationmessage USING btree (msgstr4) WHERE (msgstr4 IS NOT NULL);

CREATE INDEX translationmessage__msgstr5__idx ON translationmessage USING btree (msgstr5) WHERE (msgstr5 IS NOT NULL);

CREATE INDEX translationmessage__pofile__idx ON translationmessage USING btree (pofile);

CREATE INDEX translationmessage__potmsgset__idx ON translationmessage USING btree (potmsgset);

CREATE INDEX translationmessage__potmsgset__language__idx ON translationmessage USING btree (potmsgset, language);

CREATE INDEX translationmessage__reviewer__idx ON translationmessage USING btree (reviewer);

CREATE INDEX translationmessage__submitter__idx ON translationmessage USING btree (submitter);

CREATE UNIQUE INDEX translationtemplateitem__potemplate__potmsgset__key ON translationtemplateitem USING btree (potemplate, potmsgset);

CREATE INDEX translationtemplateitem__potemplate__sequence__idx ON translationtemplateitem USING btree (potemplate, sequence);

CREATE UNIQUE INDEX translationtemplateitem__potemplate__sequence__key ON translationtemplateitem USING btree (potemplate, sequence) WHERE (sequence > 0);

CREATE INDEX translationtemplateitem__potmsgset__idx ON translationtemplateitem USING btree (potmsgset);

CREATE INDEX translator__translator__idx ON translator USING btree (translator);

CREATE INDEX usertouseremail__recipient__idx ON usertouseremail USING btree (recipient);

CREATE INDEX usertouseremail__sender__date_sent__idx ON usertouseremail USING btree (sender, date_sent);

CREATE INDEX vote__person__idx ON vote USING btree (person);

CREATE INDEX votecast_poll_idx ON votecast USING btree (poll);

CREATE UNIQUE INDEX webserviceban__consumer__ip__key ON webserviceban USING btree (consumer, ip) WHERE ((consumer IS NOT NULL) AND (ip IS NOT NULL));

CREATE UNIQUE INDEX webserviceban__consumer__key ON webserviceban USING btree (consumer) WHERE ((consumer IS NOT NULL) AND (ip IS NULL));

CREATE UNIQUE INDEX webserviceban__ip__key ON webserviceban USING btree (ip) WHERE ((((person IS NULL) AND (consumer IS NULL)) AND (token IS NULL)) AND (ip IS NOT NULL));

CREATE UNIQUE INDEX webserviceban__person__ip__key ON webserviceban USING btree (person, ip) WHERE ((person IS NOT NULL) AND (ip IS NOT NULL));

CREATE UNIQUE INDEX webserviceban__person__key ON webserviceban USING btree (person) WHERE ((person IS NOT NULL) AND (ip IS NULL));

CREATE UNIQUE INDEX webserviceban__token__ip__key ON webserviceban USING btree (token, ip) WHERE ((token IS NOT NULL) AND (ip IS NOT NULL));

CREATE UNIQUE INDEX webserviceban__token__key ON webserviceban USING btree (token) WHERE ((token IS NOT NULL) AND (ip IS NULL));

CREATE INDEX wikiname_person_idx ON wikiname USING btree (person);

CREATE RULE delete_rule AS ON DELETE TO revisionnumber DO INSTEAD DELETE FROM branchrevision WHERE (branchrevision.id = old.id);

CREATE RULE insert_rule AS ON INSERT TO revisionnumber DO INSTEAD INSERT INTO branchrevision (id, sequence, branch, revision) VALUES (new.id, new.sequence, new.branch, new.revision);

CREATE RULE update_rule AS ON UPDATE TO revisionnumber DO INSTEAD UPDATE branchrevision SET id = new.id, sequence = new.sequence, branch = new.branch, revision = new.revision WHERE (branchrevision.id = old.id);

CREATE TRIGGER bug_latest_patch_uploaded_on_delete_t
    AFTER DELETE ON bugattachment
    FOR EACH ROW
    EXECUTE PROCEDURE bug_update_latest_patch_uploaded_on_delete();

CREATE TRIGGER bug_latest_patch_uploaded_on_insert_update_t
    AFTER INSERT OR UPDATE ON bugattachment
    FOR EACH ROW
    EXECUTE PROCEDURE bug_update_latest_patch_uploaded_on_insert_update();

CREATE TRIGGER lp_mirror_account_del_t
    AFTER DELETE ON account
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_account_ins_t
    AFTER INSERT ON account
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_account_ins();

CREATE TRIGGER lp_mirror_account_upd_t
    AFTER UPDATE ON account
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_account_upd();

CREATE TRIGGER lp_mirror_person_del_t
    AFTER DELETE ON person
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_person_ins_t
    AFTER INSERT ON person
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_person_ins();

CREATE TRIGGER lp_mirror_person_upd_t
    AFTER UPDATE ON person
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_person_upd();

CREATE TRIGGER lp_mirror_personlocation_del_t
    AFTER DELETE ON teamparticipation
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_personlocation_ins_t
    AFTER INSERT ON personlocation
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_personlocation_ins();

CREATE TRIGGER lp_mirror_personlocation_upd_t
    AFTER UPDATE ON personlocation
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_personlocation_upd();

CREATE TRIGGER lp_mirror_teamparticipation_del_t
    AFTER DELETE ON teamparticipation
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_teamparticipation_ins_t
    AFTER INSERT ON teamparticipation
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_teamparticipation_ins();

CREATE TRIGGER lp_mirror_teamparticipation_upd_t
    AFTER UPDATE ON teamparticipation
    FOR EACH ROW
    EXECUTE PROCEDURE lp_mirror_teamparticipation_upd();

CREATE TRIGGER mv_branch_distribution_update_t
    AFTER UPDATE ON distribution
    FOR EACH ROW
    EXECUTE PROCEDURE mv_branch_distribution_update();

CREATE TRIGGER mv_branch_distroseries_update_t
    AFTER UPDATE ON distroseries
    FOR EACH ROW
    EXECUTE PROCEDURE mv_branch_distroseries_update();

CREATE TRIGGER mv_branch_person_update_t
    AFTER UPDATE ON person
    FOR EACH ROW
    EXECUTE PROCEDURE mv_branch_person_update();

CREATE TRIGGER mv_branch_product_update_t
    AFTER UPDATE ON product
    FOR EACH ROW
    EXECUTE PROCEDURE mv_branch_product_update();

CREATE TRIGGER mv_pillarname_distribution_t
    AFTER INSERT OR UPDATE ON distribution
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pillarname_distribution();

CREATE TRIGGER mv_pillarname_product_t
    AFTER INSERT OR UPDATE ON product
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pillarname_product();

CREATE TRIGGER mv_pillarname_project_t
    AFTER INSERT OR UPDATE ON project
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pillarname_project();

CREATE TRIGGER mv_pofiletranslator_translationmessage
    AFTER INSERT OR DELETE OR UPDATE ON translationmessage
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pofiletranslator_translationmessage();

CREATE TRIGGER packageset_deleted_trig
    BEFORE DELETE ON packageset
    FOR EACH ROW
    EXECUTE PROCEDURE packageset_deleted_trig();

CREATE TRIGGER packageset_inserted_trig
    AFTER INSERT ON packageset
    FOR EACH ROW
    EXECUTE PROCEDURE packageset_inserted_trig();

CREATE TRIGGER packagesetinclusion_deleted_trig
    BEFORE DELETE ON packagesetinclusion
    FOR EACH ROW
    EXECUTE PROCEDURE packagesetinclusion_deleted_trig();

CREATE TRIGGER packagesetinclusion_inserted_trig
    AFTER INSERT ON packagesetinclusion
    FOR EACH ROW
    EXECUTE PROCEDURE packagesetinclusion_inserted_trig();

CREATE TRIGGER set_bug_message_count_t
    AFTER INSERT OR DELETE OR UPDATE ON bugmessage
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_message_count();

CREATE TRIGGER set_bug_number_of_duplicates_t
    AFTER INSERT OR DELETE OR UPDATE ON bug
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_number_of_duplicates();

CREATE TRIGGER set_bug_users_affected_count_t
    AFTER INSERT OR DELETE OR UPDATE ON bugaffectsperson
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_users_affected_count();

CREATE TRIGGER set_bugtask_date_milestone_set_t
    AFTER INSERT OR UPDATE ON bugtask
    FOR EACH ROW
    EXECUTE PROCEDURE set_bugtask_date_milestone_set();

CREATE TRIGGER set_date_last_message_t
    AFTER INSERT OR DELETE OR UPDATE ON bugmessage
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_date_last_message();

CREATE TRIGGER set_date_status_set_t
    BEFORE UPDATE ON account
    FOR EACH ROW
    EXECUTE PROCEDURE set_date_status_set();

CREATE TRIGGER set_normalized_address
    BEFORE INSERT OR UPDATE ON shippingrequest
    FOR EACH ROW
    EXECUTE PROCEDURE set_shipit_normalized_address();

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON bugtask
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('targetnamecache', 'b', 'statusexplanation', 'c');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON binarypackagerelease
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('summary', 'b', 'description', 'c');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON cve
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('sequence', 'a', 'description', 'b');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON distroseriespackagecache
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'summaries', 'b', 'descriptions', 'c');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON message
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('subject', 'b');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON messagechunk
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('content', 'c');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON product
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON project
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON shippingrequest
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('recipientdisplayname', 'a');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON question
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('title', 'a', 'description', 'b', 'whiteboard', 'b');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON bug
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'title', 'b', 'description', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON person
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'displayname', 'a');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON specification
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'title', 'a', 'summary', 'b', 'whiteboard', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON distribution
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON distributionsourcepackagecache
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'binpkgnames', 'b', 'binpkgsummaries', 'c', 'binpkgdescriptions', 'd', 'changelog', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON productreleasefile
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('description', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON faq
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('title', 'a', 'tags', 'b', 'content', 'd');

CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON archive
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('description', 'a', 'package_description_cache', 'b');

CREATE TRIGGER update_branch_name_cache_t
    BEFORE INSERT OR UPDATE ON branch
    FOR EACH ROW
    EXECUTE PROCEDURE update_branch_name_cache();

CREATE TRIGGER you_are_your_own_member
    AFTER INSERT ON person
    FOR EACH ROW
    EXECUTE PROCEDURE you_are_your_own_member();

ALTER TABLE ONLY processor
    ADD CONSTRAINT "$1" FOREIGN KEY (family) REFERENCES processorfamily(id);

ALTER TABLE ONLY builder
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES processor(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$1" FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY libraryfilealias
    ADD CONSTRAINT "$1" FOREIGN KEY (content) REFERENCES libraryfilecontent(id);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (productrelease) REFERENCES productrelease(id);

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$1" FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$1" FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY sshkey
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY pushmirroraccess
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY polloption
    ADD CONSTRAINT "$1" FOREIGN KEY (poll) REFERENCES poll(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT "$1" FOREIGN KEY (bug_supervisor) REFERENCES person(id);

ALTER TABLE ONLY shipitreport
    ADD CONSTRAINT "$1" FOREIGN KEY (csvfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY country
    ADD CONSTRAINT "$1" FOREIGN KEY (continent) REFERENCES continent(id);

ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id) ON DELETE CASCADE;

ALTER TABLE ONLY builder
    ADD CONSTRAINT "$2" FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$2" FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT "$2" FOREIGN KEY (builder) REFERENCES builder(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$2" FOREIGN KEY (members) REFERENCES person(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$3" FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$3" FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$3" FOREIGN KEY (bug_supervisor) REFERENCES person(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$3" FOREIGN KEY (from_sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$4" FOREIGN KEY (potranslation) REFERENCES potranslation(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$5" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY accountpassword
    ADD CONSTRAINT accountpassword_account_fkey FOREIGN KEY (account) REFERENCES account(id) ON DELETE CASCADE;

ALTER TABLE ONLY karma
    ADD CONSTRAINT action_fkey FOREIGN KEY (action) REFERENCES karmaaction(id);

ALTER TABLE ONLY announcement
    ADD CONSTRAINT announcement_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY announcement
    ADD CONSTRAINT announcement_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY announcement
    ADD CONSTRAINT announcement_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY announcement
    ADD CONSTRAINT announcement_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__distribution__fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__person__fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__product__fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__sourcepackagename__fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY apportjob
    ADD CONSTRAINT apportjob_blob_fkey FOREIGN KEY (blob) REFERENCES temporaryblobstorage(id);

ALTER TABLE ONLY apportjob
    ADD CONSTRAINT apportjob_job_fkey FOREIGN KEY (job) REFERENCES job(id);

ALTER TABLE ONLY archive
    ADD CONSTRAINT archive__distribution__fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY archive
    ADD CONSTRAINT archive__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY archive
    ADD CONSTRAINT archive_signing_key_fkey FOREIGN KEY (signing_key) REFERENCES gpgkey(id);

ALTER TABLE ONLY archivearch
    ADD CONSTRAINT archivearch__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY archivearch
    ADD CONSTRAINT archivearch__processorfamily__fk FOREIGN KEY (processorfamily) REFERENCES processorfamily(id);

ALTER TABLE ONLY archiveauthtoken
    ADD CONSTRAINT archiveauthtoken__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY archiveauthtoken
    ADD CONSTRAINT archiveauthtoken_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY archivedependency
    ADD CONSTRAINT archivedependency__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY archivedependency
    ADD CONSTRAINT archivedependency__dependency__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY archivedependency
    ADD CONSTRAINT archivedependency_component_fkey FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY archivejob
    ADD CONSTRAINT archivejob__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY archivejob
    ADD CONSTRAINT archivejob__job__fk FOREIGN KEY (job) REFERENCES job(id) ON DELETE CASCADE;

ALTER TABLE ONLY archivepermission
    ADD CONSTRAINT archivepermission__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY archivepermission
    ADD CONSTRAINT archivepermission__component__fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY archivepermission
    ADD CONSTRAINT archivepermission__packageset__fk FOREIGN KEY (packageset) REFERENCES packageset(id);

ALTER TABLE ONLY archivepermission
    ADD CONSTRAINT archivepermission__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY archivepermission
    ADD CONSTRAINT archivepermission__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY archivesubscriber
    ADD CONSTRAINT archivesubscriber__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY archivesubscriber
    ADD CONSTRAINT archivesubscriber_cancelled_by_fkey FOREIGN KEY (cancelled_by) REFERENCES person(id);

ALTER TABLE ONLY archivesubscriber
    ADD CONSTRAINT archivesubscriber_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY archivesubscriber
    ADD CONSTRAINT archivesubscriber_subscriber_fkey FOREIGN KEY (subscriber) REFERENCES person(id);

ALTER TABLE ONLY authtoken
    ADD CONSTRAINT authtoken__requester__fk FOREIGN KEY (requester) REFERENCES account(id);

ALTER TABLE ONLY binarypackagebuild
    ADD CONSTRAINT binarypackagebuild__distro_arch_series__fk FOREIGN KEY (distro_arch_series) REFERENCES distroarchseries(id);

ALTER TABLE ONLY binarypackagebuild
    ADD CONSTRAINT binarypackagebuild__package_build__fk FOREIGN KEY (package_build) REFERENCES packagebuild(id);

ALTER TABLE ONLY binarypackagebuild
    ADD CONSTRAINT binarypackagebuild__source_package_release__fk FOREIGN KEY (source_package_release) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_binarypackagerelease_fk FOREIGN KEY (binarypackagerelease) REFERENCES binarypackagerelease(id) ON DELETE CASCADE;

ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_libraryfile_fk FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT binarypackagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES binarypackagebuild(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_build_fk FOREIGN KEY (build) REFERENCES binarypackagebuild(id) ON DELETE CASCADE;

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_debug_package_fkey FOREIGN KEY (debug_package) REFERENCES binarypackagerelease(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_section_fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_archive_fkey FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_binary_package_release_fkey FOREIGN KEY (binary_package_release) REFERENCES binarypackagerelease(id);

ALTER TABLE ONLY binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_country_fkey FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_claimant_fk FOREIGN KEY (claimant) REFERENCES person(id);

ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_reviewer_fk FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY bountymessage
    ADD CONSTRAINT bountymessage_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);

ALTER TABLE ONLY bountymessage
    ADD CONSTRAINT bountymessage_message_fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);

ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_author_fk FOREIGN KEY (author) REFERENCES person(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_merge_robot_fkey FOREIGN KEY (merge_robot) REFERENCES branchmergerobot(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_stacked_on_fkey FOREIGN KEY (stacked_on) REFERENCES branch(id);

ALTER TABLE ONLY branchjob
    ADD CONSTRAINT branchjob_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY branchjob
    ADD CONSTRAINT branchjob_job_fkey FOREIGN KEY (job) REFERENCES job(id) ON DELETE CASCADE;

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_dependent_branch_fkey FOREIGN KEY (dependent_branch) REFERENCES branch(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merge_diff_fkey FOREIGN KEY (merge_diff) REFERENCES previewdiff(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merge_log_file_fkey FOREIGN KEY (merge_log_file) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merge_reporter_fkey FOREIGN KEY (merge_reporter) REFERENCES person(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merger_fkey FOREIGN KEY (merger) REFERENCES person(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_queuer_fkey FOREIGN KEY (queuer) REFERENCES person(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_review_diff_fkey FOREIGN KEY (review_diff) REFERENCES staticdiff(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_source_branch_fkey FOREIGN KEY (source_branch) REFERENCES branch(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_superseded_by_fkey FOREIGN KEY (superseded_by) REFERENCES branchmergeproposal(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_target_branch_fkey FOREIGN KEY (target_branch) REFERENCES branch(id);

ALTER TABLE ONLY branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_branch_merge_proposal_fkey FOREIGN KEY (branch_merge_proposal) REFERENCES branchmergeproposal(id);

ALTER TABLE ONLY branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_job_fkey FOREIGN KEY (job) REFERENCES job(id) ON DELETE CASCADE;

ALTER TABLE ONLY branchmergerobot
    ADD CONSTRAINT branchmergerobot_owner_fkey FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY branchmergerobot
    ADD CONSTRAINT branchmergerobot_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT branchrevision__branch__fk FOREIGN KEY (branch) REFERENCES branch(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT branchrevision__revision__fk FOREIGN KEY (revision) REFERENCES revision(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY branchsubscription
    ADD CONSTRAINT branchsubscription_branch_fk FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY branchsubscription
    ADD CONSTRAINT branchsubscription_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY branchsubscription
    ADD CONSTRAINT branchsubscription_subscribed_by_fkey FOREIGN KEY (subscribed_by) REFERENCES person(id);

ALTER TABLE ONLY branchvisibilitypolicy
    ADD CONSTRAINT branchvisibilitypolicy_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY branchvisibilitypolicy
    ADD CONSTRAINT branchvisibilitypolicy_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY branchvisibilitypolicy
    ADD CONSTRAINT branchvisibilitypolicy_team_fkey FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY bug
    ADD CONSTRAINT bug__who_made_private__fk FOREIGN KEY (who_made_private) REFERENCES person(id);

ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_duplicateof_fk FOREIGN KEY (duplicateof) REFERENCES bug(id);

ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT bugactivity__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_libraryfile_fk FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_message_fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY bugbranch
    ADD CONSTRAINT bugbranch_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY bugbranch
    ADD CONSTRAINT bugbranch_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugbranch
    ADD CONSTRAINT bugbranch_fixed_in_revision_fkey FOREIGN KEY (revision_hint) REFERENCES revision(id);

ALTER TABLE ONLY bugbranch
    ADD CONSTRAINT bugbranch_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_cve_fk FOREIGN KEY (cve) REFERENCES cve(id);

ALTER TABLE ONLY bugjob
    ADD CONSTRAINT bugjob_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugjob
    ADD CONSTRAINT bugjob_job_fkey FOREIGN KEY (job) REFERENCES job(id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage__bug__fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_bugwatch_fkey FOREIGN KEY (bugwatch) REFERENCES bugwatch(id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_message_fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__bug__fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__decider__fk FOREIGN KEY (decider) REFERENCES person(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__productseries__fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification_message_fkey FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive__bug__fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive__message__fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY bugnotificationattachment
    ADD CONSTRAINT bugnotificationattachment__bug_notification__fk FOREIGN KEY (bug_notification) REFERENCES bugnotification(id) ON DELETE CASCADE;

ALTER TABLE ONLY bugnotificationattachment
    ADD CONSTRAINT bugnotificationattachment_message_fkey FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient__bug_notification__fk FOREIGN KEY (bug_notification) REFERENCES bugnotification(id) ON DELETE CASCADE;

ALTER TABLE ONLY bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugnotificationrecipientarchive
    ADD CONSTRAINT bugnotificationrecipientarchive__bug_notification__fk FOREIGN KEY (bug_notification) REFERENCES bugnotificationarchive(id);

ALTER TABLE ONLY bugnotificationrecipientarchive
    ADD CONSTRAINT bugnotificationrecipientarchive__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_creator_fk FOREIGN KEY (creator) REFERENCES person(id);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_lastmodifiedby_fk FOREIGN KEY (lastmodifiedby) REFERENCES person(id);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_sourcepackagerelease_fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_verifiedby_fk FOREIGN KEY (verifiedby) REFERENCES person(id);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_creator_fk FOREIGN KEY (creator) REFERENCES person(id);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_lastmodifiedby_fk FOREIGN KEY (lastmodifiedby) REFERENCES person(id);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_productrelease_fk FOREIGN KEY (productrelease) REFERENCES productrelease(id);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_verifiedby_fk FOREIGN KEY (verifiedby) REFERENCES person(id);

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT bugsubscription_subscribed_by_fkey FOREIGN KEY (subscribed_by) REFERENCES person(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__assignee__fk FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__binarypackagename__fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__bug__fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__bugwatch__fk FOREIGN KEY (bugwatch) REFERENCES bugwatch(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__distribution__fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__distribution__milestone__fk FOREIGN KEY (distribution, milestone) REFERENCES milestone(distribution, id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__product__fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__product__milestone__fk FOREIGN KEY (product, milestone) REFERENCES milestone(product, id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__productseries__fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT bugtracker_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY bugtrackeralias
    ADD CONSTRAINT bugtrackeralias__bugtracker__fk FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);

ALTER TABLE ONLY bugtrackerperson
    ADD CONSTRAINT bugtrackerperson_bugtracker_fkey FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);

ALTER TABLE ONLY bugtrackerperson
    ADD CONSTRAINT bugtrackerperson_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bugtracker_fk FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY bugwatchactivity
    ADD CONSTRAINT bugwatchactivity_bug_watch_fkey FOREIGN KEY (bug_watch) REFERENCES bugwatch(id);

ALTER TABLE ONLY buildfarmjob
    ADD CONSTRAINT buildfarmjob__builder__fk FOREIGN KEY (builder) REFERENCES builder(id);

ALTER TABLE ONLY buildfarmjob
    ADD CONSTRAINT buildfarmjob__log__fk FOREIGN KEY (log) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY buildfarmjob
    ADD CONSTRAINT buildfarmjob__processor__fk FOREIGN KEY (processor) REFERENCES processor(id);

ALTER TABLE ONLY buildpackagejob
    ADD CONSTRAINT buildpackagejob__job__fk FOREIGN KEY (job) REFERENCES job(id);

ALTER TABLE ONLY buildpackagejob
    ADD CONSTRAINT buildpackagejob_build_fk FOREIGN KEY (build) REFERENCES binarypackagebuild(id);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT buildqueue__job__fk FOREIGN KEY (job) REFERENCES job(id);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT buildqueue__processor__fk FOREIGN KEY (processor) REFERENCES processor(id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_assignee_fkey FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_owner_fkey FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY codeimportevent
    ADD CONSTRAINT codeimportevent__code_import__fk FOREIGN KEY (code_import) REFERENCES codeimport(id) ON DELETE CASCADE;

ALTER TABLE ONLY codeimportevent
    ADD CONSTRAINT codeimportevent__machine__fk FOREIGN KEY (machine) REFERENCES codeimportmachine(id);

ALTER TABLE ONLY codeimportevent
    ADD CONSTRAINT codeimportevent__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY codeimporteventdata
    ADD CONSTRAINT codeimporteventdata__event__fk FOREIGN KEY (event) REFERENCES codeimportevent(id) ON DELETE CASCADE;

ALTER TABLE ONLY codeimportjob
    ADD CONSTRAINT codeimportjob__code_import__fk FOREIGN KEY (code_import) REFERENCES codeimport(id);

ALTER TABLE ONLY codeimportjob
    ADD CONSTRAINT codeimportjob__machine__fk FOREIGN KEY (machine) REFERENCES codeimportmachine(id);

ALTER TABLE ONLY codeimportjob
    ADD CONSTRAINT codeimportjob__requesting_user__fk FOREIGN KEY (requesting_user) REFERENCES person(id);

ALTER TABLE ONLY codeimportresult
    ADD CONSTRAINT codeimportresult__code_import__fk FOREIGN KEY (code_import) REFERENCES codeimport(id) ON DELETE CASCADE;

ALTER TABLE ONLY codeimportresult
    ADD CONSTRAINT codeimportresult__log_file__fk FOREIGN KEY (log_file) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY codeimportresult
    ADD CONSTRAINT codeimportresult__machine__fk FOREIGN KEY (machine) REFERENCES codeimportmachine(id);

ALTER TABLE ONLY codeimportresult
    ADD CONSTRAINT codeimportresult__requesting_user__fk FOREIGN KEY (requesting_user) REFERENCES person(id);

ALTER TABLE ONLY codereviewmessage
    ADD CONSTRAINT codereviewmessage_branch_merge_proposal_fkey FOREIGN KEY (branch_merge_proposal) REFERENCES branchmergeproposal(id);

ALTER TABLE ONLY codereviewmessage
    ADD CONSTRAINT codereviewmessage_message_fkey FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY codereviewvote
    ADD CONSTRAINT codereviewvote_branch_merge_proposal_fkey FOREIGN KEY (branch_merge_proposal) REFERENCES branchmergeproposal(id);

ALTER TABLE ONLY codereviewvote
    ADD CONSTRAINT codereviewvote_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY codereviewvote
    ADD CONSTRAINT codereviewvote_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY codereviewvote
    ADD CONSTRAINT codereviewvote_vote_message_fkey FOREIGN KEY (vote_message) REFERENCES codereviewmessage(id);

ALTER TABLE ONLY commercialsubscription
    ADD CONSTRAINT commercialsubscription__product__fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY commercialsubscription
    ADD CONSTRAINT commercialsubscription__purchaser__fk FOREIGN KEY (purchaser) REFERENCES person(id);

ALTER TABLE ONLY commercialsubscription
    ADD CONSTRAINT commercialsubscription__registrant__fk FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT componentselection__component__fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT componentselection__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY customlanguagecode
    ADD CONSTRAINT customlanguagecode_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY customlanguagecode
    ADD CONSTRAINT customlanguagecode_language_fkey FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY customlanguagecode
    ADD CONSTRAINT customlanguagecode_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY customlanguagecode
    ADD CONSTRAINT customlanguagecode_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY cvereference
    ADD CONSTRAINT cvereference_cve_fk FOREIGN KEY (cve) REFERENCES cve(id);

ALTER TABLE ONLY diff
    ADD CONSTRAINT diff_diff_text_fkey FOREIGN KEY (diff_text) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution__icon__fk FOREIGN KEY (icon) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution__mugshot__fk FOREIGN KEY (mugshot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_language_pack_admin_fkey FOREIGN KEY (language_pack_admin) REFERENCES person(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_mirror_admin_fkey FOREIGN KEY (mirror_admin) REFERENCES person(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_security_contact_fkey FOREIGN KEY (security_contact) REFERENCES person(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_translation_focus_fkey FOREIGN KEY (translation_focus) REFERENCES distroseries(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_upload_admin_fk FOREIGN KEY (upload_admin) REFERENCES person(id);

ALTER TABLE ONLY distributionbounty
    ADD CONSTRAINT distributionbounty_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);

ALTER TABLE ONLY distributionbounty
    ADD CONSTRAINT distributionbounty_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_country_fkey FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_owner_fkey FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY distributionmirror
    ADD CONSTRAINT distributionmirror_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY distributionsourcepackage
    ADD CONSTRAINT distributionpackage__distribution__fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distributionsourcepackage
    ADD CONSTRAINT distributionpackage__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY distroarchseries
    ADD CONSTRAINT distroarchseries__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY distroarchseries
    ADD CONSTRAINT distroarchseries__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY distroarchseries
    ADD CONSTRAINT distroarchseries__processorfamily__fk FOREIGN KEY (processorfamily) REFERENCES processorfamily(id);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_uploader_fk FOREIGN KEY (uploader) REFERENCES person(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distrorelease_parentrelease_fk FOREIGN KEY (parent_series) REFERENCES distroseries(id);

ALTER TABLE ONLY distroserieslanguage
    ADD CONSTRAINT distroreleaselanguage_language_fk FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__distribution__fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__driver__fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__language_pack_base__fk FOREIGN KEY (language_pack_base) REFERENCES languagepack(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__language_pack_delta__fk FOREIGN KEY (language_pack_delta) REFERENCES languagepack(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__language_pack_proposed__fk FOREIGN KEY (language_pack_proposed) REFERENCES languagepack(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__nominatedarchindep__fk FOREIGN KEY (nominatedarchindep) REFERENCES distroarchseries(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY distroseries
    ADD CONSTRAINT distroseries__parent_series__fk FOREIGN KEY (parent_series) REFERENCES distroseries(id);

ALTER TABLE ONLY distroserieslanguage
    ADD CONSTRAINT distroserieslanguage__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY distroserieslanguage
    ADD CONSTRAINT distroserieslanguage__language__fk FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__binarypackagename__fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress__account__fk FOREIGN KEY (account) REFERENCES account(id) ON DELETE SET NULL;

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES person(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_last_updated_by_fkey FOREIGN KEY (last_updated_by) REFERENCES person(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_owner_fkey FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY featuredproject
    ADD CONSTRAINT featuredproject_pillar_name_fkey FOREIGN KEY (pillar_name) REFERENCES pillarname(id);

ALTER TABLE ONLY flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion__child__fk FOREIGN KEY (child) REFERENCES packageset(id);

ALTER TABLE ONLY flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion__parent__fk FOREIGN KEY (parent) REFERENCES packageset(id);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY hwdevice
    ADD CONSTRAINT hwdevice_bus_vendor_id_fkey FOREIGN KEY (bus_vendor_id) REFERENCES hwvendorid(id);

ALTER TABLE ONLY hwdeviceclass
    ADD CONSTRAINT hwdeviceclass_device_fkey FOREIGN KEY (device) REFERENCES hwdevice(id);

ALTER TABLE ONLY hwdevicedriverlink
    ADD CONSTRAINT hwdevicedriverlink_device_fkey FOREIGN KEY (device) REFERENCES hwdevice(id);

ALTER TABLE ONLY hwdevicedriverlink
    ADD CONSTRAINT hwdevicedriverlink_driver_fkey FOREIGN KEY (driver) REFERENCES hwdriver(id);

ALTER TABLE ONLY hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant_device_fkey FOREIGN KEY (device) REFERENCES hwdevice(id);

ALTER TABLE ONLY hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant_vendor_name_fkey FOREIGN KEY (vendor_name) REFERENCES hwvendorname(id);

ALTER TABLE ONLY hwdmihandle
    ADD CONSTRAINT hwdmihandle_submission_fkey FOREIGN KEY (submission) REFERENCES hwsubmission(id);

ALTER TABLE ONLY hwdmivalue
    ADD CONSTRAINT hwdmivalue_handle_fkey FOREIGN KEY (handle) REFERENCES hwdmihandle(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES distroarchseries(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__owned__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__raw_submission__fk FOREIGN KEY (raw_submission) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__system_fingerprint__fk FOREIGN KEY (system_fingerprint) REFERENCES hwsystemfingerprint(id);

ALTER TABLE ONLY hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug_submission_fkey FOREIGN KEY (submission) REFERENCES hwsubmission(id);

ALTER TABLE ONLY hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_device_driver_link_fkey FOREIGN KEY (device_driver_link) REFERENCES hwdevicedriverlink(id);

ALTER TABLE ONLY hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_parent_fkey FOREIGN KEY (parent) REFERENCES hwsubmissiondevice(id);

ALTER TABLE ONLY hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_submission_fkey FOREIGN KEY (submission) REFERENCES hwsubmission(id);

ALTER TABLE ONLY hwtestanswer
    ADD CONSTRAINT hwtestanswer__choice__test__fk FOREIGN KEY (test, choice) REFERENCES hwtestanswerchoice(test, id);

ALTER TABLE ONLY hwtestanswer
    ADD CONSTRAINT hwtestanswer_choice_fkey FOREIGN KEY (choice) REFERENCES hwtestanswerchoice(id);

ALTER TABLE ONLY hwtestanswer
    ADD CONSTRAINT hwtestanswer_language_fkey FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY hwtestanswer
    ADD CONSTRAINT hwtestanswer_submission_fkey FOREIGN KEY (submission) REFERENCES hwsubmission(id);

ALTER TABLE ONLY hwtestanswer
    ADD CONSTRAINT hwtestanswer_test_fkey FOREIGN KEY (test) REFERENCES hwtest(id);

ALTER TABLE ONLY hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice_test_fkey FOREIGN KEY (test) REFERENCES hwtest(id);

ALTER TABLE ONLY hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_choice_fkey FOREIGN KEY (choice) REFERENCES hwtestanswerchoice(id);

ALTER TABLE ONLY hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_distroarchseries_fkey FOREIGN KEY (distroarchseries) REFERENCES distroarchseries(id);

ALTER TABLE ONLY hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_test_fkey FOREIGN KEY (test) REFERENCES hwtest(id);

ALTER TABLE ONLY hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice_answer_fkey FOREIGN KEY (answer) REFERENCES hwtestanswercount(id);

ALTER TABLE ONLY hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice_device_driver_fkey FOREIGN KEY (device_driver) REFERENCES hwdevicedriverlink(id);

ALTER TABLE ONLY hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice_answer_fkey FOREIGN KEY (answer) REFERENCES hwtestanswer(id);

ALTER TABLE ONLY hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice_device_driver_fkey FOREIGN KEY (device_driver) REFERENCES hwdevicedriverlink(id);

ALTER TABLE ONLY hwvendorid
    ADD CONSTRAINT hwvendorid_vendor_name_fkey FOREIGN KEY (vendor_name) REFERENCES hwvendorname(id);

ALTER TABLE ONLY ircid
    ADD CONSTRAINT ircid_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY job
    ADD CONSTRAINT job_requester_fkey FOREIGN KEY (requester) REFERENCES person(id);

ALTER TABLE ONLY karma
    ADD CONSTRAINT karma_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY karma
    ADD CONSTRAINT karma_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY karma
    ADD CONSTRAINT karma_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY karma
    ADD CONSTRAINT karma_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY karmaaction
    ADD CONSTRAINT karmaaction_category_fk FOREIGN KEY (category) REFERENCES karmacategory(id);

ALTER TABLE ONLY karmacache
    ADD CONSTRAINT karmacache_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY karmacache
    ADD CONSTRAINT karmacache_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY karmacache
    ADD CONSTRAINT karmacache_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY karmacache
    ADD CONSTRAINT karmacache_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY karmatotalcache
    ADD CONSTRAINT karmatotalcache_person_fk FOREIGN KEY (person) REFERENCES person(id) ON DELETE CASCADE;

ALTER TABLE ONLY languagepack
    ADD CONSTRAINT languagepack__file__fk FOREIGN KEY (file) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY languagepack
    ADD CONSTRAINT languagepack__updates__fk FOREIGN KEY (updates) REFERENCES languagepack(id);

ALTER TABLE ONLY languagepack
    ADD CONSTRAINT languagepackage__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount__libraryfilealias__fk FOREIGN KEY (libraryfilealias) REFERENCES libraryfilealias(id) ON DELETE CASCADE;

ALTER TABLE ONLY libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount_country_fkey FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY logintoken
    ADD CONSTRAINT logintoken_requester_fk FOREIGN KEY (requester) REFERENCES person(id);

ALTER TABLE ONLY mailinglist
    ADD CONSTRAINT mailinglist_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY mailinglist
    ADD CONSTRAINT mailinglist_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY mailinglist
    ADD CONSTRAINT mailinglist_team_fkey FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY mailinglistban
    ADD CONSTRAINT mailinglistban_banned_by_fkey FOREIGN KEY (banned_by) REFERENCES person(id);

ALTER TABLE ONLY mailinglistban
    ADD CONSTRAINT mailinglistban_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription__email_address_fk FOREIGN KEY (email_address) REFERENCES emailaddress(id) ON DELETE CASCADE;

ALTER TABLE ONLY mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_mailing_list_fkey FOREIGN KEY (mailing_list) REFERENCES mailinglist(id);

ALTER TABLE ONLY mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_owner_fkey FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_specification_fkey FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_team_fkey FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY mergedirectivejob
    ADD CONSTRAINT mergedirectivejob_job_fkey FOREIGN KEY (job) REFERENCES job(id) ON DELETE CASCADE;

ALTER TABLE ONLY mergedirectivejob
    ADD CONSTRAINT mergedirectivejob_merge_directive_fkey FOREIGN KEY (merge_directive) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_parent_fk FOREIGN KEY (parent) REFERENCES message(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_raw_fk FOREIGN KEY (raw) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_disposed_by_fkey FOREIGN KEY (disposed_by) REFERENCES person(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_mailing_list_fkey FOREIGN KEY (mailing_list) REFERENCES mailinglist(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_message_fkey FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_posted_by_fkey FOREIGN KEY (posted_by) REFERENCES person(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_posted_message_fkey FOREIGN KEY (posted_message) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_blob_fk FOREIGN KEY (blob) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_message_fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone__distroseries__distribution__fk FOREIGN KEY (distroseries, distribution) REFERENCES distroseries(id, distribution);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_series_fk FOREIGN KEY (product, productseries) REFERENCES productseries(product, id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_country_fk FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistroseries__distribution_mirror__fk FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistroseries__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES distroarchseries(id);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_mirror_fk FOREIGN KEY (mirror) REFERENCES mirror(id);

ALTER TABLE ONLY mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchseries__component__fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchseries__distribution_mirror__fk FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchseries__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES distroarchseries(id);

ALTER TABLE ONLY mirrordistroseriessource
    ADD CONSTRAINT mirrordistroseriessource__component__fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrordistroseriessource
    ADD CONSTRAINT mirrordistroseriessource__distribution_mirror__fk FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrordistroseriessource
    ADD CONSTRAINT mirrordistroseriessource__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_distribution_mirror_fkey FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_log_file_fkey FOREIGN KEY (log_file) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_mirror_fk FOREIGN KEY (mirror) REFERENCES mirror(id);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_consumer_fkey FOREIGN KEY (consumer) REFERENCES oauthconsumer(id);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY oauthnonce
    ADD CONSTRAINT oauthnonce__access_token__fk FOREIGN KEY (access_token) REFERENCES oauthaccesstoken(id) ON DELETE CASCADE;

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_consumer_fkey FOREIGN KEY (consumer) REFERENCES oauthconsumer(id);

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY openidrpconfig
    ADD CONSTRAINT openidrpconfig__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY openidrpsummary
    ADD CONSTRAINT openidrpsummary_account_fkey FOREIGN KEY (account) REFERENCES account(id);

ALTER TABLE ONLY packagebugsupervisor
    ADD CONSTRAINT packagebugsupervisor__bug_supervisor__fk FOREIGN KEY (bug_supervisor) REFERENCES person(id);

ALTER TABLE ONLY packagebuild
    ADD CONSTRAINT packagebuild__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY packagebuild
    ADD CONSTRAINT packagebuild__build_farm_job__fk FOREIGN KEY (build_farm_job) REFERENCES buildfarmjob(id);

ALTER TABLE ONLY packagebuild
    ADD CONSTRAINT packagebuild__log__fk FOREIGN KEY (upload_log) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest__sourcearchive__fk FOREIGN KEY (source_archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest__targetarchive__fk FOREIGN KEY (target_archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_requester_fk FOREIGN KEY (requester) REFERENCES person(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_sourcecomponent_fk FOREIGN KEY (source_component) REFERENCES component(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_sourcedistroseries_fk FOREIGN KEY (source_distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_targetcomponent_fk FOREIGN KEY (target_component) REFERENCES component(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_targetdistroseries_fk FOREIGN KEY (target_distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packagediff
    ADD CONSTRAINT packagediff_diff_content_fkey FOREIGN KEY (diff_content) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packagediff
    ADD CONSTRAINT packagediff_from_source_fkey FOREIGN KEY (from_source) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY packagediff
    ADD CONSTRAINT packagediff_requester_fkey FOREIGN KEY (requester) REFERENCES person(id);

ALTER TABLE ONLY packagediff
    ADD CONSTRAINT packagediff_to_source_fkey FOREIGN KEY (to_source) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection__binarypackagename__fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection__component__fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection__section__fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY packageset
    ADD CONSTRAINT packageset__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packageset
    ADD CONSTRAINT packageset__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY packageset
    ADD CONSTRAINT packageset__packagesetgroup__fk FOREIGN KEY (packagesetgroup) REFERENCES packagesetgroup(id);

ALTER TABLE ONLY packagesetgroup
    ADD CONSTRAINT packagesetgroup__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY packagesetinclusion
    ADD CONSTRAINT packagesetinclusion__child__fk FOREIGN KEY (child) REFERENCES packageset(id);

ALTER TABLE ONLY packagesetinclusion
    ADD CONSTRAINT packagesetinclusion__parent__fk FOREIGN KEY (parent) REFERENCES packageset(id);

ALTER TABLE ONLY packagesetsources
    ADD CONSTRAINT packagesetsources__packageset__fk FOREIGN KEY (packageset) REFERENCES packageset(id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__changesfile__fk FOREIGN KEY (changesfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__signing_key__fk FOREIGN KEY (signing_key) REFERENCES gpgkey(id);

ALTER TABLE ONLY packageuploadbuild
    ADD CONSTRAINT packageuploadbuild__packageupload__fk FOREIGN KEY (packageupload) REFERENCES packageupload(id) ON DELETE CASCADE;

ALTER TABLE ONLY packageuploadbuild
    ADD CONSTRAINT packageuploadbuild_build_fk FOREIGN KEY (build) REFERENCES binarypackagebuild(id);

ALTER TABLE ONLY packageuploadcustom
    ADD CONSTRAINT packageuploadcustom_libraryfilealias_fk FOREIGN KEY (libraryfilealias) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packageuploadcustom
    ADD CONSTRAINT packageuploadcustom_packageupload_fk FOREIGN KEY (packageupload) REFERENCES packageupload(id);

ALTER TABLE ONLY packageuploadsource
    ADD CONSTRAINT packageuploadsource__packageupload__fk FOREIGN KEY (packageupload) REFERENCES packageupload(id) ON DELETE CASCADE;

ALTER TABLE ONLY packageuploadsource
    ADD CONSTRAINT packageuploadsource__sourcepackagerelease__fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__account__fk FOREIGN KEY (account) REFERENCES account(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__icon__fk FOREIGN KEY (icon) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__mugshot__fk FOREIGN KEY (mugshot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY karmacache
    ADD CONSTRAINT person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_language_fk FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_merged_fk FOREIGN KEY (merged) REFERENCES person(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_registrant_fk FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_teamowner_fk FOREIGN KEY (teamowner) REFERENCES person(id);

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_language_fk FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY personlocation
    ADD CONSTRAINT personlocation_last_modified_by_fkey FOREIGN KEY (last_modified_by) REFERENCES person(id);

ALTER TABLE ONLY personlocation
    ADD CONSTRAINT personlocation_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY personnotification
    ADD CONSTRAINT personnotification_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname__alias_for__fk FOREIGN KEY (alias_for) REFERENCES pillarname(id);

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id) ON DELETE CASCADE;

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_product_fkey FOREIGN KEY (product) REFERENCES product(id) ON DELETE CASCADE;

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_project_fkey FOREIGN KEY (project) REFERENCES project(id) ON DELETE CASCADE;

ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES distroarchseries(id);

ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot__libraryfilealias__fk FOREIGN KEY (chroot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poeportrequest_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_pofile_fk FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_language_fk FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_lasttranslator_fk FOREIGN KEY (lasttranslator) REFERENCES person(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT pofiletranslator__latest_message__fk FOREIGN KEY (latest_message) REFERENCES translationmessage(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT pofiletranslator__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT pofiletranslator__pofile__fk FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY poll
    ADD CONSTRAINT poll_team_fk FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate__distrorelease__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate__from_sourcepackagename__fk FOREIGN KEY (from_sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate__source_file__fk FOREIGN KEY (source_file) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset__msgid_plural__fk FOREIGN KEY (msgid_plural) REFERENCES pomsgid(id);

ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_primemsgid_fk FOREIGN KEY (msgid_singular) REFERENCES pomsgid(id);

ALTER TABLE ONLY previewdiff
    ADD CONSTRAINT previewdiff_diff_fkey FOREIGN KEY (diff) REFERENCES diff(id) ON DELETE CASCADE;

ALTER TABLE ONLY product
    ADD CONSTRAINT product__development_focus__fk FOREIGN KEY (development_focus) REFERENCES productseries(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__icon__fk FOREIGN KEY (icon) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__mugshot__fk FOREIGN KEY (mugshot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__translation_focus__fk FOREIGN KEY (translation_focus) REFERENCES productseries(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_bugtracker_fkey FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_project_fk FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_security_contact_fkey FOREIGN KEY (security_contact) REFERENCES person(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);

ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);

ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY productcvsmodule
    ADD CONSTRAINT productcvsmodule_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY productlicense
    ADD CONSTRAINT productlicense_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_milestone_fkey FOREIGN KEY (milestone) REFERENCES milestone(id);

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT productreleasefile__signature__fk FOREIGN KEY (signature) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT productreleasefile__uploader__fk FOREIGN KEY (uploader) REFERENCES person(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_translations_branch_fkey FOREIGN KEY (translations_branch) REFERENCES branch(id);

ALTER TABLE ONLY productseriescodeimport
    ADD CONSTRAINT productseriescodeimport_codeimport_fkey FOREIGN KEY (codeimport) REFERENCES codeimport(id);

ALTER TABLE ONLY productseriescodeimport
    ADD CONSTRAINT productseriescodeimport_productseries_fkey FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT productsvnmodule_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project__icon__fk FOREIGN KEY (icon) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project__mugshot__fk FOREIGN KEY (mugshot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_bugtracker_fkey FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);

ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);

ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_project_fk FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT projectrelationship_object_fk FOREIGN KEY (object) REFERENCES project(id);

ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT projectrelationship_subject_fk FOREIGN KEY (subject) REFERENCES project(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__answer__fk FOREIGN KEY (answer) REFERENCES questionmessage(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__answerer__fk FOREIGN KEY (answerer) REFERENCES person(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__assignee__fk FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__distribution__fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__faq__fk FOREIGN KEY (faq) REFERENCES faq(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__language__fkey FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__owner__fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__product__fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY questionbug
    ADD CONSTRAINT questionbug__bug__fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY questionbug
    ADD CONSTRAINT questionbug__question__fk FOREIGN KEY (question) REFERENCES question(id);

ALTER TABLE ONLY questionmessage
    ADD CONSTRAINT questionmessage__message__fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY questionmessage
    ADD CONSTRAINT questionmessage__question__fk FOREIGN KEY (question) REFERENCES question(id);

ALTER TABLE ONLY questionreopening
    ADD CONSTRAINT questionreopening__answerer__fk FOREIGN KEY (answerer) REFERENCES person(id);

ALTER TABLE ONLY questionreopening
    ADD CONSTRAINT questionreopening__question__fk FOREIGN KEY (question) REFERENCES question(id);

ALTER TABLE ONLY questionreopening
    ADD CONSTRAINT questionreopening__reopener__fk FOREIGN KEY (reopener) REFERENCES person(id);

ALTER TABLE ONLY questionsubscription
    ADD CONSTRAINT questionsubscription__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY questionsubscription
    ADD CONSTRAINT questionsubscription__question__fk FOREIGN KEY (question) REFERENCES question(id);

ALTER TABLE ONLY requestedcds
    ADD CONSTRAINT requestedcds_request_fk FOREIGN KEY (request) REFERENCES shippingrequest(id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT reviewer_fk FOREIGN KEY (last_changed_by) REFERENCES person(id);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision_gpgkey_fk FOREIGN KEY (gpgkey) REFERENCES gpgkey(id);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision_revision_author_fk FOREIGN KEY (revision_author) REFERENCES revisionauthor(id);

ALTER TABLE ONLY revisionauthor
    ADD CONSTRAINT revisionauthor_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY revisioncache
    ADD CONSTRAINT revisioncache__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY revisioncache
    ADD CONSTRAINT revisioncache__product__fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY revisioncache
    ADD CONSTRAINT revisioncache__revision__fk FOREIGN KEY (revision) REFERENCES revision(id);

ALTER TABLE ONLY revisioncache
    ADD CONSTRAINT revisioncache__revision_author__fk FOREIGN KEY (revision_author) REFERENCES revisionauthor(id);

ALTER TABLE ONLY revisioncache
    ADD CONSTRAINT revisioncache__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY revisionparent
    ADD CONSTRAINT revisionparent_revision_fk FOREIGN KEY (revision) REFERENCES revision(id);

ALTER TABLE ONLY revisionproperty
    ADD CONSTRAINT revisionproperty__revision__fk FOREIGN KEY (revision) REFERENCES revision(id);

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT sectionselection__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT sectionselection__section__fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES distroarchseries(id);

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_binarypackagerelease_fk FOREIGN KEY (binarypackagerelease) REFERENCES binarypackagerelease(id);

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_removedby_fk FOREIGN KEY (removed_by) REFERENCES person(id);

ALTER TABLE ONLY binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_removedby_fk FOREIGN KEY (removed_by) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_sourcepackagerelease_fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY shipitsurveyresult
    ADD CONSTRAINT shipitsurveyresult_answer_fkey FOREIGN KEY (answer) REFERENCES shipitsurveyanswer(id);

ALTER TABLE ONLY shipitsurveyresult
    ADD CONSTRAINT shipitsurveyresult_question_fkey FOREIGN KEY (question) REFERENCES shipitsurveyquestion(id);

ALTER TABLE ONLY shipitsurveyresult
    ADD CONSTRAINT shipitsurveyresult_survey_fkey FOREIGN KEY (survey) REFERENCES shipitsurvey(id);

ALTER TABLE ONLY shipment
    ADD CONSTRAINT shipment_shippingrun_fk FOREIGN KEY (shippingrun) REFERENCES shippingrun(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest__country__fk FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_shipment_fk FOREIGN KEY (shipment) REFERENCES shipment(id);

ALTER TABLE ONLY shippingrun
    ADD CONSTRAINT shippingrun_csvfile_fk FOREIGN KEY (csvfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_signingkey_fk FOREIGN KEY (owner, signingkey) REFERENCES gpgkey(owner, id) ON UPDATE CASCADE;

ALTER TABLE ONLY sourcepackageformatselection
    ADD CONSTRAINT sourceformatselection__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packagesetsources
    ADD CONSTRAINT sourcepackagenamesources__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory__archive__fk FOREIGN KEY (archive) REFERENCES archive(id) ON DELETE CASCADE;

ALTER TABLE ONLY sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_daily_build_archive_fkey FOREIGN KEY (daily_build_archive) REFERENCES archive(id);

ALTER TABLE ONLY sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_owner_fkey FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_manifest_fkey FOREIGN KEY (manifest) REFERENCES sourcepackagerecipedata(id);

ALTER TABLE ONLY sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_package_build_fkey FOREIGN KEY (package_build) REFERENCES packagebuild(id);

ALTER TABLE ONLY sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_recipe_fkey FOREIGN KEY (recipe) REFERENCES sourcepackagerecipe(id);

ALTER TABLE ONLY sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_requester_fkey FOREIGN KEY (requester) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagerecipebuildjob
    ADD CONSTRAINT sourcepackagerecipebuildjob_job_fkey FOREIGN KEY (job) REFERENCES job(id);

ALTER TABLE ONLY sourcepackagerecipebuildjob
    ADD CONSTRAINT sourcepackagerecipebuildjob_sourcepackage_recipe_build_fkey FOREIGN KEY (sourcepackage_recipe_build) REFERENCES sourcepackagerecipebuild(id);

ALTER TABLE ONLY sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_base_branch_fkey FOREIGN KEY (base_branch) REFERENCES branch(id);

ALTER TABLE ONLY sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_sourcepackage_recipe_build_fkey FOREIGN KEY (sourcepackage_recipe_build) REFERENCES sourcepackagerecipebuild(id);

ALTER TABLE ONLY sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_sourcepackage_recipe_fkey FOREIGN KEY (sourcepackage_recipe) REFERENCES sourcepackagerecipe(id);

ALTER TABLE ONLY sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_parent_instruction_fkey FOREIGN KEY (parent_instruction) REFERENCES sourcepackagerecipedatainstruction(id);

ALTER TABLE ONLY sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_recipe_data_fkey FOREIGN KEY (recipe_data) REFERENCES sourcepackagerecipedata(id);

ALTER TABLE ONLY sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipedistroseries_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipedistroseries_sourcepackagerecipe_fkey FOREIGN KEY (sourcepackagerecipe) REFERENCES sourcepackagerecipe(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__creator__fk FOREIGN KEY (creator) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__dscsigningkey FOREIGN KEY (dscsigningkey) REFERENCES gpgkey(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__upload_archive__fk FOREIGN KEY (upload_archive) REFERENCES archive(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__upload_distroseries__fk FOREIGN KEY (upload_distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_changelog_fkey FOREIGN KEY (changelog) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_maintainer_fk FOREIGN KEY (maintainer) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_section FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_sourcepackage_recipe_build_fkey FOREIGN KEY (sourcepackage_recipe_build) REFERENCES sourcepackagerecipebuild(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification__distroseries__distribution__fk FOREIGN KEY (distroseries, distribution) REFERENCES distroseries(id, distribution);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_approver_fk FOREIGN KEY (approver) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_assignee_fk FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_completer_fkey FOREIGN KEY (completer) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_distribution_milestone_fk FOREIGN KEY (distribution, milestone) REFERENCES milestone(distribution, id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_drafter_fk FOREIGN KEY (drafter) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_goal_decider_fkey FOREIGN KEY (goal_decider) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_goal_proposer_fkey FOREIGN KEY (goal_proposer) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_product_milestone_fk FOREIGN KEY (product, milestone) REFERENCES milestone(product, id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_productseries_valid FOREIGN KEY (product, productseries) REFERENCES productseries(product, id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_starter_fkey FOREIGN KEY (starter) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_superseded_by_fk FOREIGN KEY (superseded_by) REFERENCES specification(id);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specificationbranch__branch__fk FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specificationbranch__specification__fk FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY specificationbranch
    ADD CONSTRAINT specificationbranch_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY specificationbug
    ADD CONSTRAINT specificationbug_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY specificationbug
    ADD CONSTRAINT specificationbug_specification_fk FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY specificationdependency
    ADD CONSTRAINT specificationdependency_dependency_fk FOREIGN KEY (dependency) REFERENCES specification(id);

ALTER TABLE ONLY specificationdependency
    ADD CONSTRAINT specificationdependency_specification_fk FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY specificationfeedback
    ADD CONSTRAINT specificationfeedback_provider_fk FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY specificationfeedback
    ADD CONSTRAINT specificationfeedback_requester_fk FOREIGN KEY (requester) REFERENCES person(id);

ALTER TABLE ONLY specificationfeedback
    ADD CONSTRAINT specificationfeedback_specification_fk FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage__message__fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage__specification__fk FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY specificationsubscription
    ADD CONSTRAINT specificationsubscription_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY specificationsubscription
    ADD CONSTRAINT specificationsubscription_specification_fk FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY sprint
    ADD CONSTRAINT sprint__icon__fk FOREIGN KEY (icon) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY sprint
    ADD CONSTRAINT sprint__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY sprint
    ADD CONSTRAINT sprint__mugshot__fk FOREIGN KEY (mugshot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY sprint
    ADD CONSTRAINT sprint_driver_fkey FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY sprint
    ADD CONSTRAINT sprint_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY sprintattendance
    ADD CONSTRAINT sprintattendance_attendee_fk FOREIGN KEY (attendee) REFERENCES person(id);

ALTER TABLE ONLY sprintattendance
    ADD CONSTRAINT sprintattendance_sprint_fk FOREIGN KEY (sprint) REFERENCES sprint(id);

ALTER TABLE ONLY sprintspecification
    ADD CONSTRAINT sprintspec_spec_fk FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY sprintspecification
    ADD CONSTRAINT sprintspec_sprint_fk FOREIGN KEY (sprint) REFERENCES sprint(id);

ALTER TABLE ONLY sprintspecification
    ADD CONSTRAINT sprintspecification__nominator__fk FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY sprintspecification
    ADD CONSTRAINT sprintspecification_decider_fkey FOREIGN KEY (decider) REFERENCES person(id);

ALTER TABLE ONLY staticdiff
    ADD CONSTRAINT staticdiff_diff_fkey FOREIGN KEY (diff) REFERENCES diff(id) ON DELETE CASCADE;

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_milestone_fkey FOREIGN KEY (milestone) REFERENCES milestone(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_productseries_fkey FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_subscribed_by_fkey FOREIGN KEY (subscribed_by) REFERENCES person(id);

ALTER TABLE ONLY structuralsubscription
    ADD CONSTRAINT structuralsubscription_subscriber_fkey FOREIGN KEY (subscriber) REFERENCES person(id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT teammembership_acknowledged_by_fkey FOREIGN KEY (acknowledged_by) REFERENCES person(id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT teammembership_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT teammembership_proposed_by_fkey FOREIGN KEY (proposed_by) REFERENCES person(id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT teammembership_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES person(id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT teammembership_team_fk FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_team_fk FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_file_alias_fkey FOREIGN KEY (file_alias) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_owner_fk FOREIGN KEY (owner) REFERENCES person(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__content__fk FOREIGN KEY (content) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__importer__fk FOREIGN KEY (importer) REFERENCES person(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__pofile__fk FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__potemplate__fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__productseries__fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__msgstr0__fk FOREIGN KEY (msgstr0) REFERENCES potranslation(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__msgstr1__fk FOREIGN KEY (msgstr1) REFERENCES potranslation(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__msgstr2__fk FOREIGN KEY (msgstr2) REFERENCES potranslation(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__msgstr3__fk FOREIGN KEY (msgstr3) REFERENCES potranslation(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__msgstr4__fk FOREIGN KEY (msgstr4) REFERENCES potranslation(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__msgstr5__fk FOREIGN KEY (msgstr5) REFERENCES potranslation(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__pofile__fk FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__potmsgset__fk FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__reviewer__fk FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage__submitter__fk FOREIGN KEY (submitter) REFERENCES person(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage_language_fkey FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY translationmessage
    ADD CONSTRAINT translationmessage_potemplate_fkey FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY translationrelicensingagreement
    ADD CONSTRAINT translationrelicensingagreement__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_potemplate_fkey FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_potmsgset_fkey FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_language_fk FOREIGN KEY (language) REFERENCES language(id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_person_fk FOREIGN KEY (translator) REFERENCES person(id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);

ALTER TABLE ONLY usertouseremail
    ADD CONSTRAINT usertouseremail__recipient__fk FOREIGN KEY (recipient) REFERENCES person(id);

ALTER TABLE ONLY usertouseremail
    ADD CONSTRAINT usertouseremail__sender__fk FOREIGN KEY (sender) REFERENCES person(id);

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_poll_fk FOREIGN KEY (poll) REFERENCES poll(id);

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_poll_option_fk FOREIGN KEY (poll, option) REFERENCES polloption(poll, id);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_poll_fk FOREIGN KEY (poll) REFERENCES poll(id);

ALTER TABLE ONLY webserviceban
    ADD CONSTRAINT webserviceban_consumer_fkey FOREIGN KEY (consumer) REFERENCES oauthconsumer(id);

ALTER TABLE ONLY webserviceban
    ADD CONSTRAINT webserviceban_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY webserviceban
    ADD CONSTRAINT webserviceban_token_fkey FOREIGN KEY (token) REFERENCES oauthaccesstoken(id);

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_person_fk FOREIGN KEY (person) REFERENCES person(id);

-- debversion datatype, which will be added to production manually
\i /usr/share/postgresql/8.4/contrib/debversion.sql

