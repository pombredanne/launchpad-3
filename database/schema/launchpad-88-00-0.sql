-- Generated Wed Oct 10 11:18:51 2007 UTC

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
    "owner" integer NOT NULL,
    revision_id text NOT NULL,
    revision_date timestamp without time zone
);

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

CREATE TABLE archive (
    id integer NOT NULL,
    "owner" integer,
    description text,
    enabled boolean DEFAULT true NOT NULL,
    authorized_size integer,
    whiteboard text,
    distribution integer,
    purpose integer NOT NULL
);

CREATE SEQUENCE archive_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archive_id_seq OWNED BY archive.id;

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

CREATE TABLE securebinarypackagepublishinghistory (
    id integer NOT NULL,
    binarypackagerelease integer NOT NULL,
    distroarchrelease integer NOT NULL,
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
    embargo boolean DEFAULT false NOT NULL,
    embargolifted timestamp without time zone,
    archive integer NOT NULL
);

CREATE VIEW binarypackagepublishinghistory AS
    SELECT securebinarypackagepublishinghistory.id, securebinarypackagepublishinghistory.archive, securebinarypackagepublishinghistory.binarypackagerelease, securebinarypackagepublishinghistory.distroarchrelease, securebinarypackagepublishinghistory.status, securebinarypackagepublishinghistory.component, securebinarypackagepublishinghistory.section, securebinarypackagepublishinghistory.priority, securebinarypackagepublishinghistory.datecreated, securebinarypackagepublishinghistory.datepublished, securebinarypackagepublishinghistory.datesuperseded, securebinarypackagepublishinghistory.supersededby, securebinarypackagepublishinghistory.datemadepending, securebinarypackagepublishinghistory.scheduleddeletiondate, securebinarypackagepublishinghistory.dateremoved, securebinarypackagepublishinghistory.pocket, securebinarypackagepublishinghistory.embargo, securebinarypackagepublishinghistory.embargolifted FROM securebinarypackagepublishinghistory WHERE (securebinarypackagepublishinghistory.embargo = false);

CREATE VIEW binarypackagepublishing AS
    SELECT binarypackagepublishinghistory.id, binarypackagepublishinghistory.archive, binarypackagepublishinghistory.binarypackagerelease, binarypackagepublishinghistory.distroarchrelease, binarypackagepublishinghistory.status, binarypackagepublishinghistory.component, binarypackagepublishinghistory.section, binarypackagepublishinghistory.priority, binarypackagepublishinghistory.datecreated, binarypackagepublishinghistory.datepublished, binarypackagepublishinghistory.datesuperseded, binarypackagepublishinghistory.supersededby, binarypackagepublishinghistory.datemadepending, binarypackagepublishinghistory.scheduleddeletiondate, binarypackagepublishinghistory.dateremoved, binarypackagepublishinghistory.pocket, binarypackagepublishinghistory.embargo, binarypackagepublishinghistory.embargolifted FROM binarypackagepublishinghistory WHERE (binarypackagepublishinghistory.status < 7);

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
    CONSTRAINT valid_version CHECK (valid_debian_version(version))
);

CREATE TABLE build (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    processor integer NOT NULL,
    distroarchrelease integer NOT NULL,
    buildstate integer NOT NULL,
    datebuilt timestamp without time zone,
    buildduration interval,
    buildlog integer,
    builder integer,
    sourcepackagerelease integer NOT NULL,
    pocket integer DEFAULT 0 NOT NULL,
    dependencies text,
    archive integer NOT NULL
);

CREATE TABLE component (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE TABLE distroarchrelease (
    id integer NOT NULL,
    distrorelease integer NOT NULL,
    processorfamily integer NOT NULL,
    architecturetag text NOT NULL,
    "owner" integer NOT NULL,
    official boolean NOT NULL,
    package_count integer DEFAULT 0 NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE TABLE distrorelease (
    id integer NOT NULL,
    distribution integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    version text NOT NULL,
    releasestatus integer NOT NULL,
    datereleased timestamp without time zone,
    parentrelease integer,
    "owner" integer NOT NULL,
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
    content integer NOT NULL,
    filename text NOT NULL,
    mimetype text NOT NULL,
    expires timestamp without time zone,
    last_accessed timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    CONSTRAINT valid_filename CHECK ((filename !~~ '%/%'::text))
);

CREATE TABLE sourcepackagerelease (
    id integer NOT NULL,
    creator integer NOT NULL,
    version text NOT NULL,
    dateuploaded timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    urgency integer NOT NULL,
    dscsigningkey integer,
    component integer,
    changelog text,
    builddepends text,
    builddependsindep text,
    architecturehintlist text NOT NULL,
    dsc text,
    section integer NOT NULL,
    maintainer integer NOT NULL,
    sourcepackagename integer NOT NULL,
    uploaddistrorelease integer NOT NULL,
    format integer NOT NULL,
    dsc_maintainer_rfc822 text,
    dsc_standards_version text,
    dsc_format text,
    dsc_binaries text,
    upload_archive integer NOT NULL,
    copyright text,
    CONSTRAINT valid_version CHECK (valid_debian_version(version))
);

CREATE VIEW binarypackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (binarypackagepublishing.id)::text) AS id, distrorelease.distribution, binarypackagepublishing.id AS binarypackagepublishing, component.name AS componentname, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, binarypackagefile.libraryfile AS libraryfilealias, distrorelease.name AS distroreleasename, distroarchrelease.architecturetag, binarypackagepublishing.status AS publishingstatus, binarypackagepublishing.pocket, binarypackagepublishing.archive FROM (((((((((binarypackagepublishing JOIN binarypackagerelease ON ((binarypackagepublishing.binarypackagerelease = binarypackagerelease.id))) JOIN build ON ((binarypackagerelease.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN binarypackagefile ON ((binarypackagefile.binarypackagerelease = binarypackagerelease.id))) JOIN libraryfilealias ON ((binarypackagefile.libraryfile = libraryfilealias.id))) JOIN distroarchrelease ON ((binarypackagepublishing.distroarchrelease = distroarchrelease.id))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN component ON ((binarypackagepublishing.component = component.id)));

CREATE SEQUENCE binarypackagename_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagename_id_seq OWNED BY binarypackagename.id;

CREATE SEQUENCE binarypackagerelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE binarypackagerelease_id_seq OWNED BY binarypackagerelease.id;

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
    "owner" integer NOT NULL,
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
    "owner" integer NOT NULL,
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
    pull_disabled boolean DEFAULT false NOT NULL,
    mirror_status_message text,
    last_scanned timestamp without time zone,
    last_scanned_id text,
    last_mirrored_id text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    revision_count integer DEFAULT 0 NOT NULL,
    mirror_request_time timestamp without time zone,
    private boolean DEFAULT false NOT NULL,
    branch_type integer NOT NULL,
    CONSTRAINT branch_type_url_consistent CHECK (((((branch_type = 2) AND (url IS NOT NULL)) OR ((branch_type = ANY (ARRAY[1, 3])) AND (url IS NULL))) OR (branch_type = 4))),
    CONSTRAINT branch_url_no_trailing_slash CHECK ((url !~~ '%/'::text)),
    CONSTRAINT branch_url_not_supermirror CHECK ((url !~~ 'http://bazaar.launchpad.net/%'::text)),
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
    CONSTRAINT different_branches CHECK ((((source_branch <> target_branch) AND (dependent_branch <> source_branch)) AND (dependent_branch <> target_branch))),
    CONSTRAINT positive_revno CHECK (((merged_revno IS NULL) OR (merged_revno > 0)))
);

CREATE SEQUENCE branchmergeproposal_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE branchmergeproposal_id_seq OWNED BY branchmergeproposal.id;

CREATE SEQUENCE branchrelationship_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE branchrevision (
    id integer NOT NULL,
    "sequence" integer,
    branch integer NOT NULL,
    revision integer NOT NULL
);

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
    max_diff_lines integer
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

CREATE TABLE bug (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    name text,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL,
    duplicateof integer,
    fti ts2.tsvector,
    private boolean DEFAULT false NOT NULL,
    security_related boolean DEFAULT false NOT NULL,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_made_private timestamp without time zone,
    who_made_private integer,
    date_last_message timestamp without time zone,
    CONSTRAINT no_empty_desctiption CHECK ((btrim(description) <> ''::text)),
    CONSTRAINT notduplicateofself CHECK ((NOT (id = duplicateof))),
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

CREATE TABLE bugattachment (
    id integer NOT NULL,
    message integer NOT NULL,
    name text,
    title text,
    libraryfile integer NOT NULL,
    bug integer NOT NULL,
    "type" integer NOT NULL,
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
    status integer NOT NULL,
    whiteboard text
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

CREATE TABLE bugexternalref (
    id integer NOT NULL,
    bug integer NOT NULL,
    url text NOT NULL,
    title text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);

CREATE SEQUENCE bugexternalref_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugexternalref_id_seq OWNED BY bugexternalref.id;

CREATE TABLE bugmessage (
    id integer NOT NULL,
    bug integer NOT NULL,
    message integer NOT NULL,
    bugwatch integer
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
    distrorelease integer,
    productseries integer,
    status integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    date_decided timestamp without time zone,
    "owner" integer NOT NULL,
    decider integer
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
    START WITH 1
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
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugproductinfestation_id_seq OWNED BY bugproductinfestation.id;

CREATE TABLE bugrelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    "object" integer NOT NULL
);

CREATE TABLE bugsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    bug integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
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
    distrorelease integer,
    sourcepackagename integer,
    binarypackagename integer,
    status integer NOT NULL,
    priority integer,
    importance integer DEFAULT 5 NOT NULL,
    assignee integer,
    date_assigned timestamp without time zone,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    "owner" integer NOT NULL,
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
    CONSTRAINT bugtask_assignment_checks CHECK (CASE WHEN (product IS NOT NULL) THEN ((((productseries IS NULL) AND (distribution IS NULL)) AND (distrorelease IS NULL)) AND (sourcepackagename IS NULL)) WHEN (productseries IS NOT NULL) THEN (((distribution IS NULL) AND (distrorelease IS NULL)) AND (sourcepackagename IS NULL)) WHEN (distribution IS NOT NULL) THEN (distrorelease IS NULL) WHEN (distrorelease IS NOT NULL) THEN true ELSE false END)
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
    "owner" integer NOT NULL,
    contactdetails text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE bugtracker_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugtracker_id_seq OWNED BY bugtracker.id;

CREATE TABLE bugwatch (
    id integer NOT NULL,
    bug integer NOT NULL,
    bugtracker integer NOT NULL,
    remotebug text NOT NULL,
    remotestatus text,
    lastchanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    lastchecked timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);

CREATE SEQUENCE bugwatch_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE bugwatch_id_seq OWNED BY bugwatch.id;

CREATE SEQUENCE build_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE build_id_seq OWNED BY build.id;

CREATE TABLE builder (
    id integer NOT NULL,
    processor integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL,
    speedindex integer,
    builderok boolean NOT NULL,
    failnotes text,
    "trusted" boolean DEFAULT false NOT NULL,
    url text NOT NULL,
    manual boolean DEFAULT false,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_absolute_url CHECK (valid_absolute_url(url))
);

CREATE SEQUENCE builder_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE builder_id_seq OWNED BY builder.id;

CREATE TABLE buildqueue (
    id integer NOT NULL,
    build integer NOT NULL,
    builder integer,
    logtail text,
    created timestamp without time zone NOT NULL,
    buildstart timestamp without time zone,
    lastscore integer,
    manual boolean DEFAULT false NOT NULL
);

CREATE SEQUENCE buildqueue_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE buildqueue_id_seq OWNED BY buildqueue.id;

CREATE TABLE calendar (
    id integer NOT NULL,
    title text NOT NULL,
    revision integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE calendar_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE calendar_id_seq OWNED BY calendar.id;

CREATE TABLE calendarevent (
    id integer NOT NULL,
    uid character varying(255) NOT NULL,
    calendar integer NOT NULL,
    dtstart timestamp without time zone NOT NULL,
    duration interval NOT NULL,
    title text NOT NULL,
    description text,
    "location" text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE calendarevent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE calendarevent_id_seq OWNED BY calendarevent.id;

CREATE TABLE calendarsubscription (
    id integer NOT NULL,
    subject integer NOT NULL,
    "object" integer NOT NULL,
    colour text DEFAULT '#efefef'::text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE calendarsubscription_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE calendarsubscription_id_seq OWNED BY calendarsubscription.id;

CREATE TABLE codeimport (
    id integer NOT NULL,
    branch integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    rcs_type integer NOT NULL,
    svn_branch_url text,
    cvs_root text,
    cvs_module text,
    review_status integer DEFAULT 1 NOT NULL,
    date_last_successful timestamp without time zone,
    "owner" integer NOT NULL,
    assignee integer,
    update_interval interval,
    CONSTRAINT valid_vcs_details CHECK (CASE WHEN (rcs_type = 1) THEN (((((cvs_root IS NOT NULL) AND (cvs_root <> ''::text)) AND (cvs_module IS NOT NULL)) AND (cvs_module <> ''::text)) AND (svn_branch_url IS NULL)) WHEN (rcs_type = 2) THEN ((((cvs_root IS NULL) AND (cvs_module IS NULL)) AND (svn_branch_url IS NOT NULL)) AND valid_absolute_url(svn_branch_url)) ELSE false END)
);

CREATE SEQUENCE codeimport_id_seq
    START WITH 1
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
    START WITH 1
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
    START WITH 1
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
    START WITH 1
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
    START WITH 1
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
    date_started timestamp without time zone
);

CREATE SEQUENCE codeimportresult_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE codeimportresult_id_seq OWNED BY codeimportresult.id;

CREATE SEQUENCE component_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE component_id_seq OWNED BY component.id;

CREATE TABLE componentselection (
    id integer NOT NULL,
    distrorelease integer NOT NULL,
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
    START WITH 1
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

CREATE TABLE cve (
    id integer NOT NULL,
    "sequence" text NOT NULL,
    status integer NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datemodified timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    fti ts2.tsvector,
    CONSTRAINT valid_cve_ref CHECK (valid_cve("sequence"))
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

CREATE TABLE distribution (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    domainname text NOT NULL,
    "owner" integer NOT NULL,
    lucilleconfig text,
    displayname text NOT NULL,
    summary text NOT NULL,
    members integer NOT NULL,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    bugcontact integer,
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
    "owner" integer NOT NULL,
    speed integer NOT NULL,
    country integer NOT NULL,
    content integer NOT NULL,
    official_candidate boolean DEFAULT false NOT NULL,
    official_approved boolean DEFAULT false NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    whiteboard text,
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

CREATE SEQUENCE distributionrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE distributionsourcepackagecache (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    name text,
    binpkgnames text,
    binpkgsummaries text,
    binpkgdescriptions text,
    fti ts2.tsvector,
    changelog text
);

CREATE SEQUENCE distributionsourcepackagecache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distributionsourcepackagecache_id_seq OWNED BY distributionsourcepackagecache.id;

CREATE SEQUENCE distroarchrelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distroarchrelease_id_seq OWNED BY distroarchrelease.id;

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

CREATE SEQUENCE distrorelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distrorelease_id_seq OWNED BY distrorelease.id;

CREATE TABLE distroreleaselanguage (
    id integer NOT NULL,
    distrorelease integer,
    "language" integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    contributorcount integer NOT NULL,
    dateupdated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    unreviewed_count integer DEFAULT 0 NOT NULL
);

CREATE SEQUENCE distroreleaselanguage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distroreleaselanguage_id_seq OWNED BY distroreleaselanguage.id;

CREATE TABLE distroreleasepackagecache (
    id integer NOT NULL,
    distrorelease integer NOT NULL,
    binarypackagename integer NOT NULL,
    name text,
    summary text,
    description text,
    summaries text,
    descriptions text,
    fti ts2.tsvector
);

CREATE SEQUENCE distroreleasepackagecache_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE distroreleasepackagecache_id_seq OWNED BY distroreleasepackagecache.id;

CREATE SEQUENCE distroreleaserole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE emailaddress (
    id integer NOT NULL,
    email text NOT NULL,
    person integer NOT NULL,
    status integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE emailaddress_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE emailaddress_id_seq OWNED BY emailaddress.id;

CREATE TABLE entitlement (
    id integer NOT NULL,
    person integer NOT NULL,
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
    is_dirty boolean DEFAULT true NOT NULL
);

CREATE SEQUENCE entitlement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE entitlement_id_seq OWNED BY entitlement.id;

CREATE TABLE faq (
    id integer NOT NULL,
    title text NOT NULL,
    tags text,
    content text NOT NULL,
    product integer,
    distribution integer,
    "owner" integer NOT NULL,
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
    "owner" integer NOT NULL,
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

CREATE TABLE hwsubmission (
    id integer NOT NULL,
    date_created timestamp without time zone NOT NULL,
    date_submitted timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    format integer NOT NULL,
    status integer DEFAULT 1 NOT NULL,
    private boolean NOT NULL,
    contactable boolean NOT NULL,
    submission_key text NOT NULL,
    "owner" integer NOT NULL,
    distroarchseries integer,
    raw_submission integer NOT NULL,
    system_fingerprint integer NOT NULL
);

CREATE SEQUENCE hwsubmission_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE hwsubmission_id_seq OWNED BY hwsubmission.id;

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

CREATE TABLE karma (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    "action" integer NOT NULL,
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
    START WITH 1
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

CREATE TABLE "language" (
    id integer NOT NULL,
    code text NOT NULL,
    englishname text,
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

ALTER SEQUENCE language_id_seq OWNED BY "language".id;

CREATE TABLE languagepack (
    id integer NOT NULL,
    file integer NOT NULL,
    date_exported timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_used timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    distroseries integer NOT NULL,
    "type" integer DEFAULT 1 NOT NULL,
    updates integer,
    CONSTRAINT valid_updates CHECK (((("type" = 2) AND (updates IS NOT NULL)) OR (("type" = 1) AND (updates IS NULL))))
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
    datemirrored timestamp without time zone,
    filesize integer NOT NULL,
    sha1 character(40) NOT NULL,
    deleted boolean DEFAULT false NOT NULL,
    md5 character(32) NOT NULL
);

CREATE SEQUENCE libraryfilecontent_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE libraryfilecontent_id_seq OWNED BY libraryfilecontent.id;

CREATE TABLE license (
    id integer NOT NULL,
    legalese text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE license_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE license_id_seq OWNED BY license.id;

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

CREATE TABLE mailinglist (
    id integer NOT NULL,
    team integer NOT NULL,
    registrant integer NOT NULL,
    date_registered timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    reviewer integer,
    date_reviewed timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    date_activated timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    status integer DEFAULT 1 NOT NULL,
    welcome_message_text text,
    CONSTRAINT is_team CHECK (is_team(team))
);

CREATE SEQUENCE mailinglist_id_seq
    START WITH 1
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
    reason_text text NOT NULL
);

CREATE SEQUENCE mailinglistban_id_seq
    START WITH 1
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
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mailinglistsubscription_id_seq OWNED BY mailinglistsubscription.id;

CREATE TABLE mentoringoffer (
    id integer NOT NULL,
    "owner" integer NOT NULL,
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

CREATE TABLE message (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    subject text,
    "owner" integer,
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
    message_id text NOT NULL,
    posted_by integer NOT NULL,
    mailing_list integer NOT NULL,
    posted_message integer NOT NULL,
    posted_date timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    disposed_by integer,
    disposal_date timestamp without time zone DEFAULT timezone('UTC'::text, now())
);

CREATE SEQUENCE messageapproval_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE messageapproval_id_seq OWNED BY messageapproval.id;

CREATE TABLE messagechunk (
    id integer NOT NULL,
    message integer NOT NULL,
    "sequence" integer NOT NULL,
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
    visible boolean DEFAULT true NOT NULL,
    productseries integer,
    distrorelease integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
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
    "owner" integer NOT NULL,
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
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirror_id_seq OWNED BY mirror.id;

CREATE TABLE mirrorcdimagedistrorelease (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distrorelease integer NOT NULL,
    flavour text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrorcdimagedistrorelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrorcdimagedistrorelease_id_seq OWNED BY mirrorcdimagedistrorelease.id;

CREATE TABLE mirrorcontent (
    id integer NOT NULL,
    mirror integer NOT NULL,
    distroarchrelease integer NOT NULL,
    component integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrorcontent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrorcontent_id_seq OWNED BY mirrorcontent.id;

CREATE TABLE mirrordistroarchrelease (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distro_arch_release integer NOT NULL,
    status integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrordistroarchrelease_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrordistroarchrelease_id_seq OWNED BY mirrordistroarchrelease.id;

CREATE TABLE mirrordistroreleasesource (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distrorelease integer NOT NULL,
    status integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrordistroreleasesource_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrordistroreleasesource_id_seq OWNED BY mirrordistroreleasesource.id;

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
    distrorelease integer NOT NULL,
    component integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE mirrorsourcecontent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE mirrorsourcecontent_id_seq OWNED BY mirrorsourcecontent.id;

CREATE TABLE nameblacklist (
    id integer NOT NULL,
    regexp text NOT NULL,
    "comment" text,
    CONSTRAINT valid_regexp CHECK (valid_regexp(regexp))
);

CREATE SEQUENCE nameblacklist_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE nameblacklist_id_seq OWNED BY nameblacklist.id;

CREATE TABLE officialbugtag (
    id integer NOT NULL,
    tag text NOT NULL,
    distribution integer,
    project integer,
    product integer,
    CONSTRAINT context_required CHECK (((product IS NOT NULL) OR (distribution IS NOT NULL)))
);

CREATE SEQUENCE officialbugtag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE officialbugtag_id_seq OWNED BY officialbugtag.id;

CREATE TABLE openidassociations (
    server_url character varying(2047) NOT NULL,
    handle character varying(255) NOT NULL,
    secret bytea,
    issued integer,
    lifetime integer,
    assoc_type character varying(64),
    CONSTRAINT secret_length_constraint CHECK ((length(secret) <= 128))
);

CREATE TABLE openidauthorization (
    id integer NOT NULL,
    person integer NOT NULL,
    client_id text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_expires timestamp without time zone NOT NULL,
    trust_root text NOT NULL
);

CREATE SEQUENCE openidauthorization_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE openidauthorization_id_seq OWNED BY openidauthorization.id;

CREATE TABLE openidrpconfig (
    id integer NOT NULL,
    trust_root text NOT NULL,
    displayname text NOT NULL,
    description text NOT NULL,
    logo integer,
    allowed_sreg text,
    creation_rationale integer DEFAULT 13 NOT NULL
);

CREATE SEQUENCE openidrpconfig_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE openidrpconfig_id_seq OWNED BY openidrpconfig.id;

CREATE TABLE packagebugcontact (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bugcontact integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packagebugcontact_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packagebugcontact_id_seq OWNED BY packagebugcontact.id;

CREATE TABLE packageselection (
    id integer NOT NULL,
    distrorelease integer NOT NULL,
    sourcepackagename integer,
    binarypackagename integer,
    "action" integer NOT NULL,
    component integer,
    section integer,
    priority integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packageselection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE packageselection_id_seq OWNED BY packageselection.id;

CREATE TABLE packageupload (
    id integer NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    distrorelease integer NOT NULL,
    pocket integer NOT NULL,
    changesfile integer NOT NULL,
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
    distrorelease integer,
    productseries integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE packaging_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE person (
    id integer NOT NULL,
    displayname text NOT NULL,
    "password" text,
    teamowner integer,
    teamdescription text,
    name text NOT NULL,
    "language" integer,
    fti ts2.tsvector,
    defaultmembershipperiod integer,
    defaultrenewalperiod integer,
    subscriptionpolicy integer DEFAULT 1 NOT NULL,
    merged integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    calendar integer,
    timezone text DEFAULT 'UTC'::text NOT NULL,
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
    hide_email_addresses boolean DEFAULT false NOT NULL,
    creation_rationale integer,
    creation_comment text,
    registrant integer,
    logo integer,
    renewal_policy integer DEFAULT 10 NOT NULL,
    openid_identifier text NOT NULL,
    account_status_comment text,
    account_status integer DEFAULT 10 NOT NULL,
    personal_standing integer DEFAULT 0 NOT NULL,
    personal_standing_reason_text text,
    mail_resumption_date date,
    mailing_list_auto_subscribe_policy integer DEFAULT 1 NOT NULL,
    mailing_list_receive_duplicates boolean DEFAULT true NOT NULL,
    CONSTRAINT creation_rationale_not_null_for_people CHECK (((creation_rationale IS NULL) = (teamowner IS NOT NULL))),
    CONSTRAINT no_loops CHECK ((id <> teamowner)),
    CONSTRAINT non_empty_displayname CHECK ((btrim(displayname) <> ''::text)),
    CONSTRAINT people_have_no_emblems CHECK (((icon IS NULL) OR (teamowner IS NOT NULL))),
    CONSTRAINT sane_defaultrenewalperiod CHECK (CASE WHEN (teamowner IS NULL) THEN (defaultrenewalperiod IS NULL) WHEN (renewal_policy = ANY (ARRAY[20, 30])) THEN ((defaultrenewalperiod IS NOT NULL) AND (defaultrenewalperiod > 0)) ELSE ((defaultrenewalperiod IS NULL) OR (defaultrenewalperiod > 0)) END),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE SEQUENCE person_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE person_id_seq OWNED BY person.id;

CREATE TABLE personlanguage (
    id integer NOT NULL,
    person integer NOT NULL,
    "language" integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE personlanguage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE personlanguage_id_seq OWNED BY personlanguage.id;

CREATE TABLE pillarname (
    id integer NOT NULL,
    name text NOT NULL,
    product integer,
    project integer,
    distribution integer,
    active boolean DEFAULT true NOT NULL,
    CONSTRAINT only_one_target CHECK ((((((product IS NOT NULL) AND (project IS NULL)) AND (distribution IS NULL)) OR (((product IS NULL) AND (project IS NOT NULL)) AND (distribution IS NULL))) OR (((product IS NULL) AND (project IS NULL)) AND (distribution IS NOT NULL)))),
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
    distroarchrelease integer,
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
    "language" integer,
    potranslation integer,
    commenttext text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer
);

CREATE SEQUENCE pocomment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pocomment_id_seq OWNED BY pocomment.id;

CREATE TABLE pofile (
    id integer NOT NULL,
    potemplate integer NOT NULL,
    "language" integer NOT NULL,
    description text,
    topcomment text,
    "header" text,
    fuzzyheader boolean NOT NULL,
    lasttranslator integer,
    license integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    lastparsed timestamp without time zone,
    "owner" integer NOT NULL,
    variant text,
    path text NOT NULL,
    exportfile integer,
    exporttime timestamp without time zone,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    from_sourcepackagename integer,
    last_touched_pomsgset integer,
    unreviewed_count integer DEFAULT 0 NOT NULL,
    CONSTRAINT valid_variant CHECK ((variant <> ''::text))
);

CREATE TABLE pomsgid (
    id integer NOT NULL,
    msgid text NOT NULL
);

CREATE TABLE pomsgidsighting (
    id integer NOT NULL,
    potmsgset integer NOT NULL,
    pomsgid integer NOT NULL,
    datefirstseen timestamp without time zone NOT NULL,
    datelastseen timestamp without time zone NOT NULL,
    inlastrevision boolean NOT NULL,
    pluralform integer NOT NULL
);

CREATE TABLE pomsgset (
    id integer NOT NULL,
    "sequence" integer NOT NULL,
    pofile integer NOT NULL,
    iscomplete boolean NOT NULL,
    obsolete boolean NOT NULL,
    isfuzzy boolean NOT NULL,
    commenttext text,
    potmsgset integer NOT NULL,
    publishedfuzzy boolean DEFAULT false NOT NULL,
    publishedcomplete boolean DEFAULT false NOT NULL,
    isupdated boolean DEFAULT false NOT NULL,
    date_reviewed timestamp without time zone,
    reviewer integer,
    "language" integer,
    CONSTRAINT pomsgset__reviewer__date_reviewed__valid CHECK (((reviewer IS NULL) = (date_reviewed IS NULL)))
);

CREATE TABLE posubmission (
    id integer NOT NULL,
    pomsgset integer NOT NULL,
    pluralform integer NOT NULL,
    potranslation integer NOT NULL,
    origin integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    validationstatus integer DEFAULT 0 NOT NULL,
    active boolean DEFAULT false NOT NULL,
    published boolean DEFAULT false NOT NULL,
    CONSTRAINT posubmission_valid_pluralform CHECK ((pluralform >= 0))
);

CREATE TABLE potemplate (
    id integer NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    description text,
    copyright text,
    license integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    path text NOT NULL,
    iscurrent boolean NOT NULL,
    messagecount integer NOT NULL,
    "owner" integer NOT NULL,
    sourcepackagename integer,
    distrorelease integer,
    sourcepackageversion text,
    "header" text,
    potemplatename integer NOT NULL,
    binarypackagename integer,
    languagepack boolean DEFAULT false NOT NULL,
    productseries integer,
    from_sourcepackagename integer,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    source_file integer,
    source_file_format integer DEFAULT 1 NOT NULL,
    CONSTRAINT valid_from_sourcepackagename CHECK (((sourcepackagename IS NOT NULL) OR (from_sourcepackagename IS NULL))),
    CONSTRAINT valid_link CHECK ((((productseries IS NULL) <> (distrorelease IS NULL)) AND ((distrorelease IS NULL) = (sourcepackagename IS NULL))))
);

CREATE TABLE potemplatename (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text,
    translationdomain text NOT NULL,
    CONSTRAINT potemplate_valid_name CHECK (valid_name(name))
);

CREATE TABLE potmsgset (
    id integer NOT NULL,
    primemsgid integer NOT NULL,
    "sequence" integer NOT NULL,
    potemplate integer NOT NULL,
    commenttext text,
    filereferences text,
    sourcecomment text,
    flagscomment text,
    alternative_msgid text,
    context text
);

CREATE TABLE potranslation (
    id integer NOT NULL,
    translation text NOT NULL
);

CREATE VIEW poexport AS
    SELECT ((((((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) || COALESCE((pomsgset.id)::text, 'X'::text)) || '.'::text) || COALESCE((pomsgidsighting.id)::text, 'X'::text)) || '.'::text) || COALESCE((posubmission.id)::text, 'X'::text)) AS id, potemplatename.name, potemplatename.translationdomain, potemplate.id AS potemplate, potemplate.productseries, potemplate.sourcepackagename, potemplate.distrorelease, potemplate."header" AS potheader, potemplate.languagepack, pofile.id AS pofile, pofile."language", pofile.variant, pofile.topcomment AS potopcomment, pofile."header" AS poheader, pofile.fuzzyheader AS pofuzzyheader, potmsgset.id AS potmsgset, potmsgset."sequence" AS potsequence, potmsgset.commenttext AS potcommenttext, potmsgset.sourcecomment, potmsgset.flagscomment, potmsgset.filereferences, pomsgset.id AS pomsgset, pomsgset."sequence" AS posequence, pomsgset.iscomplete, pomsgset.obsolete, pomsgset.isfuzzy, pomsgset.commenttext AS pocommenttext, pomsgidsighting.pluralform AS msgidpluralform, posubmission.pluralform AS translationpluralform, posubmission.id AS activesubmission, potmsgset.context, pomsgid.msgid, potranslation.translation FROM ((((((((pomsgid JOIN pomsgidsighting ON ((pomsgid.id = pomsgidsighting.pomsgid))) JOIN potmsgset ON ((potmsgset.id = pomsgidsighting.potmsgset))) JOIN potemplate ON ((potemplate.id = potmsgset.potemplate))) JOIN potemplatename ON ((potemplatename.id = potemplate.potemplatename))) JOIN pofile ON ((potemplate.id = pofile.potemplate))) LEFT JOIN pomsgset ON (((potmsgset.id = pomsgset.potmsgset) AND (pomsgset.pofile = pofile.id)))) LEFT JOIN posubmission ON (((pomsgset.id = posubmission.pomsgset) AND posubmission.active))) LEFT JOIN potranslation ON ((potranslation.id = posubmission.potranslation)));

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
    latest_posubmission integer NOT NULL,
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
    "type" integer NOT NULL,
    allowspoilt boolean DEFAULT false NOT NULL,
    secrecy integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT is_team CHECK (is_team(team)),
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

CREATE SEQUENCE pomsgid_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pomsgid_id_seq OWNED BY pomsgid.id;

CREATE SEQUENCE pomsgidsighting_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pomsgidsighting_id_seq OWNED BY pomsgidsighting.id;

CREATE SEQUENCE pomsgset_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE pomsgset_id_seq OWNED BY pomsgset.id;

CREATE SEQUENCE posubmission_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE posubmission_id_seq OWNED BY posubmission.id;

CREATE TABLE posubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    potemplate integer NOT NULL,
    "language" integer,
    notificationinterval interval,
    lastnotified timestamp without time zone,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE posubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE posubscription_id_seq OWNED BY posubscription.id;

CREATE SEQUENCE potemplate_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE potemplate_id_seq OWNED BY potemplate.id;

CREATE SEQUENCE potemplatename_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE potemplatename_id_seq OWNED BY potemplatename.id;

CREATE VIEW potexport AS
    SELECT (((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) || COALESCE((pomsgidsighting.id)::text, 'X'::text)) || '.'::text) AS id, potemplatename.name, potemplatename.translationdomain, potemplate.id AS potemplate, potemplate.productseries, potemplate.sourcepackagename, potemplate.distrorelease, potemplate."header", potemplate.languagepack, potmsgset.id AS potmsgset, potmsgset."sequence", potmsgset.commenttext, potmsgset.sourcecomment, potmsgset.flagscomment, potmsgset.filereferences, pomsgidsighting.pluralform, potmsgset.context, pomsgid.msgid FROM ((((pomsgid JOIN pomsgidsighting ON ((pomsgid.id = pomsgidsighting.pomsgid))) JOIN potmsgset ON ((potmsgset.id = pomsgidsighting.potmsgset))) JOIN potemplate ON ((potemplate.id = potmsgset.potemplate))) JOIN potemplatename ON ((potemplatename.id = potemplate.potemplatename)));

CREATE SEQUENCE potmsgset_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE potmsgset_id_seq OWNED BY potmsgset.id;

CREATE SEQUENCE potranslation_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE potranslation_id_seq OWNED BY potranslation.id;

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
    description text NOT NULL
);

CREATE SEQUENCE processorfamily_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE processorfamily_id_seq OWNED BY processorfamily.id;

CREATE TABLE product (
    id integer NOT NULL,
    project integer,
    "owner" integer NOT NULL,
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
    calendar integer,
    official_rosetta boolean DEFAULT false NOT NULL,
    official_malone boolean DEFAULT false NOT NULL,
    bugcontact integer,
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
    CONSTRAINT private_bugs_need_contact CHECK (((private_bugs IS FALSE) OR (bugcontact IS NOT NULL))),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

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
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productcvsmodule_id_seq OWNED BY productcvsmodule.id;

CREATE TABLE productrelease (
    id integer NOT NULL,
    datereleased timestamp without time zone NOT NULL,
    version text NOT NULL,
    codename text,
    description text,
    changelog text,
    "owner" integer NOT NULL,
    summary text,
    productseries integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    CONSTRAINT valid_version CHECK (sane_version(version))
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
    fti ts2.tsvector
);

CREATE SEQUENCE productreleasefile_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE productseries (
    id integer NOT NULL,
    product integer NOT NULL,
    name text NOT NULL,
    summary text NOT NULL,
    import_branch integer,
    importstatus integer,
    datelastsynced timestamp without time zone,
    syncinterval interval,
    rcstype integer,
    cvsroot text,
    cvsmodule text,
    cvsbranch text,
    cvstarfileurl text,
    svnrepository text,
    releasefileglob text,
    releaseverstyle integer,
    dateautotested timestamp without time zone,
    dateprocessapproved timestamp without time zone,
    datesyncapproved timestamp without time zone,
    datestarted timestamp without time zone,
    datefinished timestamp without time zone,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    driver integer,
    "owner" integer NOT NULL,
    user_branch integer,
    date_published_sync timestamp without time zone,
    CONSTRAINT complete_cvs CHECK ((((cvsroot IS NULL) = (cvsmodule IS NULL)) AND ((cvsroot IS NULL) = (cvsbranch IS NULL)))),
    CONSTRAINT no_empty_strings CHECK (((((cvsroot <> ''::text) AND (cvsmodule <> ''::text)) AND (cvsbranch <> ''::text)) AND (svnrepository <> ''::text))),
    CONSTRAINT valid_importseries CHECK (((importstatus IS NULL) OR (rcstype IS NOT NULL))),
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_releasefileglob CHECK (valid_absolute_url(releasefileglob))
);

CREATE SEQUENCE productseries_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productseries_id_seq OWNED BY productseries.id;

CREATE TABLE productsvnmodule (
    id integer NOT NULL,
    product integer NOT NULL,
    locationurl text NOT NULL,
    weburl text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE productsvnmodule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE productsvnmodule_id_seq OWNED BY productsvnmodule.id;

CREATE TABLE project (
    id integer NOT NULL,
    "owner" integer NOT NULL,
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
    calendar integer,
    driver integer,
    bugtracker integer,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
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

CREATE SEQUENCE projectbugtracker_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE projectrelationship (
    id integer NOT NULL,
    subject integer NOT NULL,
    label integer NOT NULL,
    "object" integer NOT NULL
);

CREATE SEQUENCE projectrelationship_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE projectrelationship_id_seq OWNED BY projectrelationship.id;

CREATE TABLE section (
    id integer NOT NULL,
    name text NOT NULL
);

CREATE VIEW publishedpackageview AS
    SELECT binarypackagepublishing.id, binarypackagepublishing.archive, distroarchrelease.id AS distroarchrelease, distrorelease.distribution, distrorelease.id AS distrorelease, distrorelease.name AS distroreleasename, processorfamily.id AS processorfamily, processorfamily.name AS processorfamilyname, binarypackagepublishing.status AS packagepublishingstatus, component.name AS component, section.name AS section, binarypackagerelease.id AS binarypackagerelease, binarypackagename.name AS binarypackagename, binarypackagerelease.summary AS binarypackagesummary, binarypackagerelease.description AS binarypackagedescription, binarypackagerelease.version AS binarypackageversion, build.id AS build, build.datebuilt, sourcepackagerelease.id AS sourcepackagerelease, sourcepackagerelease.version AS sourcepackagereleaseversion, sourcepackagename.name AS sourcepackagename, binarypackagepublishing.pocket, binarypackagerelease.fti AS binarypackagefti FROM ((((((((((binarypackagepublishing JOIN distroarchrelease ON ((distroarchrelease.id = binarypackagepublishing.distroarchrelease))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN processorfamily ON ((distroarchrelease.processorfamily = processorfamily.id))) JOIN component ON ((binarypackagepublishing.component = component.id))) JOIN binarypackagerelease ON ((binarypackagepublishing.binarypackagerelease = binarypackagerelease.id))) JOIN section ON ((binarypackagepublishing.section = section.id))) JOIN binarypackagename ON ((binarypackagerelease.binarypackagename = binarypackagename.id))) JOIN build ON ((binarypackagerelease.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));

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
    "owner" integer NOT NULL,
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
    "language" integer NOT NULL,
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
    "action" integer NOT NULL,
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
    distrorelease integer NOT NULL,
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
    name text NOT NULL
);

CREATE SEQUENCE revisionauthor_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE revisionauthor_id_seq OWNED BY revisionauthor.id;

CREATE VIEW revisionnumber AS
    SELECT branchrevision.id, branchrevision."sequence", branchrevision.branch, branchrevision.revision FROM branchrevision;

CREATE TABLE revisionparent (
    id integer NOT NULL,
    "sequence" integer NOT NULL,
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

CREATE SEQUENCE section_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE section_id_seq OWNED BY section.id;

CREATE TABLE sectionselection (
    id integer NOT NULL,
    distrorelease integer NOT NULL,
    section integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE sectionselection_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sectionselection_id_seq OWNED BY sectionselection.id;

CREATE SEQUENCE securebinarypackagepublishinghistory_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE securebinarypackagepublishinghistory_id_seq OWNED BY securebinarypackagepublishinghistory.id;

CREATE TABLE securesourcepackagepublishinghistory (
    id integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    distrorelease integer NOT NULL,
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
    embargo boolean DEFAULT false NOT NULL,
    embargolifted timestamp without time zone,
    archive integer NOT NULL
);

CREATE SEQUENCE securesourcepackagepublishinghistory_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE securesourcepackagepublishinghistory_id_seq OWNED BY securesourcepackagepublishinghistory.id;

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
    shockandawe integer,
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
    "type" integer,
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

CREATE TABLE shockandawe (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE shockandawe_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE shockandawe_id_seq OWNED BY shockandawe.id;

CREATE TABLE signedcodeofconduct (
    id integer NOT NULL,
    "owner" integer NOT NULL,
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

CREATE VIEW sourcepackagepublishinghistory AS
    SELECT securesourcepackagepublishinghistory.id, securesourcepackagepublishinghistory.archive, securesourcepackagepublishinghistory.sourcepackagerelease, securesourcepackagepublishinghistory.distrorelease, securesourcepackagepublishinghistory.status, securesourcepackagepublishinghistory.component, securesourcepackagepublishinghistory.section, securesourcepackagepublishinghistory.datecreated, securesourcepackagepublishinghistory.datepublished, securesourcepackagepublishinghistory.datesuperseded, securesourcepackagepublishinghistory.supersededby, securesourcepackagepublishinghistory.datemadepending, securesourcepackagepublishinghistory.scheduleddeletiondate, securesourcepackagepublishinghistory.dateremoved, securesourcepackagepublishinghistory.pocket, securesourcepackagepublishinghistory.embargo, securesourcepackagepublishinghistory.embargolifted FROM securesourcepackagepublishinghistory WHERE (securesourcepackagepublishinghistory.embargo = false);

CREATE VIEW sourcepackagepublishing AS
    SELECT sourcepackagepublishinghistory.id, sourcepackagepublishinghistory.archive, sourcepackagepublishinghistory.sourcepackagerelease, sourcepackagepublishinghistory.distrorelease, sourcepackagepublishinghistory.status, sourcepackagepublishinghistory.component, sourcepackagepublishinghistory.section, sourcepackagepublishinghistory.datecreated, sourcepackagepublishinghistory.datepublished, sourcepackagepublishinghistory.datesuperseded, sourcepackagepublishinghistory.supersededby, sourcepackagepublishinghistory.datemadepending, sourcepackagepublishinghistory.scheduleddeletiondate, sourcepackagepublishinghistory.dateremoved, sourcepackagepublishinghistory.pocket, sourcepackagepublishinghistory.embargo, sourcepackagepublishinghistory.embargolifted FROM sourcepackagepublishinghistory WHERE (sourcepackagepublishinghistory.status < 7);

CREATE TABLE sourcepackagereleasefile (
    sourcepackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval(('sourcepackagereleasefile_id_seq'::text)::regclass) NOT NULL
);

CREATE VIEW sourcepackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishing.id)::text) AS id, distrorelease.distribution, sourcepackagepublishing.id AS sourcepackagepublishing, sourcepackagereleasefile.libraryfile AS libraryfilealias, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, distrorelease.name AS distroreleasename, sourcepackagepublishing.status AS publishingstatus, sourcepackagepublishing.pocket, sourcepackagepublishing.archive FROM ((((((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN sourcepackagereleasefile ON ((sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id))) JOIN libraryfilealias ON ((libraryfilealias.id = sourcepackagereleasefile.libraryfile))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN component ON ((sourcepackagepublishing.component = component.id)));

CREATE SEQUENCE sourcepackagename_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE sourcepackagename_id_seq OWNED BY sourcepackagename.id;

CREATE SEQUENCE sourcepackagerelationship_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

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

CREATE TABLE specification (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text,
    "owner" integer NOT NULL,
    assignee integer,
    drafter integer,
    approver integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    product integer,
    productseries integer,
    distribution integer,
    distrorelease integer,
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
    CONSTRAINT distribution_and_distrorelease CHECK (((distrorelease IS NULL) OR (distribution IS NOT NULL))),
    CONSTRAINT product_and_productseries CHECK (((productseries IS NULL) OR (product IS NOT NULL))),
    CONSTRAINT product_xor_distribution CHECK (((product IS NULL) <> (distribution IS NULL))),
    CONSTRAINT specification_completion_fully_recorded_chk CHECK (((date_completed IS NULL) = (completer IS NULL))),
    CONSTRAINT specification_completion_recorded_chk CHECK (((date_completed IS NULL) <> (((implementation_status = 90) OR (definition_status = ANY (ARRAY[60, 70]))) OR ((implementation_status = 95) AND (definition_status = 10))))),
    CONSTRAINT specification_decision_recorded CHECK (((goalstatus = 30) OR ((goal_decider IS NOT NULL) AND (date_goal_decided IS NOT NULL)))),
    CONSTRAINT specification_goal_nomination_chk CHECK ((((productseries IS NULL) AND (distrorelease IS NULL)) OR ((goal_proposer IS NOT NULL) AND (date_goal_proposed IS NOT NULL)))),
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
    summary text
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
    message integer
);

CREATE SEQUENCE specificationmessage_id_seq
    START WITH 1
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
    "language" integer NOT NULL,
    country integer NOT NULL,
    id integer DEFAULT nextval(('spokenin_id_seq'::text)::regclass) NOT NULL
);

CREATE SEQUENCE spokenin_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE sprint (
    id integer NOT NULL,
    "owner" integer NOT NULL,
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
    "comment" text NOT NULL,
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

CREATE TABLE teammembership (
    id integer NOT NULL,
    person integer NOT NULL,
    team integer NOT NULL,
    status integer NOT NULL,
    datejoined timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    dateexpires timestamp without time zone,
    reviewer integer,
    reviewercomment text
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
    "owner" integer NOT NULL
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
    distrorelease integer,
    sourcepackagename integer,
    productseries integer,
    is_published boolean NOT NULL,
    pofile integer,
    potemplate integer,
    status integer DEFAULT 5 NOT NULL,
    date_status_changed timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    format integer DEFAULT 1 NOT NULL,
    CONSTRAINT valid_link CHECK ((((productseries IS NULL) <> (distrorelease IS NULL)) AND ((distrorelease IS NULL) = (sourcepackagename IS NULL))))
);

CREATE SEQUENCE translationimportqueueentry_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translationimportqueueentry_id_seq OWNED BY translationimportqueueentry.id;

CREATE TABLE translator (
    id integer NOT NULL,
    translationgroup integer NOT NULL,
    "language" integer NOT NULL,
    translator integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);

CREATE SEQUENCE translator_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE translator_id_seq OWNED BY translator.id;

CREATE TABLE validpersonorteamcache (
    id integer NOT NULL
);

CREATE TABLE vote (
    id integer NOT NULL,
    person integer,
    poll integer NOT NULL,
    preference integer,
    "option" integer,
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

ALTER TABLE answercontact ALTER COLUMN id SET DEFAULT nextval('answercontact_id_seq'::regclass);

ALTER TABLE archive ALTER COLUMN id SET DEFAULT nextval('archive_id_seq'::regclass);

ALTER TABLE binarypackagename ALTER COLUMN id SET DEFAULT nextval('binarypackagename_id_seq'::regclass);

ALTER TABLE binarypackagerelease ALTER COLUMN id SET DEFAULT nextval('binarypackagerelease_id_seq'::regclass);

ALTER TABLE bounty ALTER COLUMN id SET DEFAULT nextval('bounty_id_seq'::regclass);

ALTER TABLE bountymessage ALTER COLUMN id SET DEFAULT nextval('bountymessage_id_seq'::regclass);

ALTER TABLE bountysubscription ALTER COLUMN id SET DEFAULT nextval('bountysubscription_id_seq'::regclass);

ALTER TABLE branch ALTER COLUMN id SET DEFAULT nextval('branch_id_seq'::regclass);

ALTER TABLE branchmergeproposal ALTER COLUMN id SET DEFAULT nextval('branchmergeproposal_id_seq'::regclass);

ALTER TABLE branchrevision ALTER COLUMN id SET DEFAULT nextval('branchrevision_id_seq'::regclass);

ALTER TABLE branchsubscription ALTER COLUMN id SET DEFAULT nextval('branchsubscription_id_seq'::regclass);

ALTER TABLE branchvisibilitypolicy ALTER COLUMN id SET DEFAULT nextval('branchvisibilitypolicy_id_seq'::regclass);

ALTER TABLE bug ALTER COLUMN id SET DEFAULT nextval('bug_id_seq'::regclass);

ALTER TABLE bugactivity ALTER COLUMN id SET DEFAULT nextval('bugactivity_id_seq'::regclass);

ALTER TABLE bugattachment ALTER COLUMN id SET DEFAULT nextval('bugattachment_id_seq'::regclass);

ALTER TABLE bugbranch ALTER COLUMN id SET DEFAULT nextval('bugbranch_id_seq'::regclass);

ALTER TABLE bugcve ALTER COLUMN id SET DEFAULT nextval('bugcve_id_seq'::regclass);

ALTER TABLE bugexternalref ALTER COLUMN id SET DEFAULT nextval('bugexternalref_id_seq'::regclass);

ALTER TABLE bugmessage ALTER COLUMN id SET DEFAULT nextval('bugmessage_id_seq'::regclass);

ALTER TABLE bugnomination ALTER COLUMN id SET DEFAULT nextval('bugnomination_id_seq'::regclass);

ALTER TABLE bugnotification ALTER COLUMN id SET DEFAULT nextval('bugnotification_id_seq'::regclass);

ALTER TABLE bugpackageinfestation ALTER COLUMN id SET DEFAULT nextval('bugpackageinfestation_id_seq'::regclass);

ALTER TABLE bugproductinfestation ALTER COLUMN id SET DEFAULT nextval('bugproductinfestation_id_seq'::regclass);

ALTER TABLE bugsubscription ALTER COLUMN id SET DEFAULT nextval('bugsubscription_id_seq'::regclass);

ALTER TABLE bugtag ALTER COLUMN id SET DEFAULT nextval('bugtag_id_seq'::regclass);

ALTER TABLE bugtask ALTER COLUMN id SET DEFAULT nextval('bugtask_id_seq'::regclass);

ALTER TABLE bugtracker ALTER COLUMN id SET DEFAULT nextval('bugtracker_id_seq'::regclass);

ALTER TABLE bugwatch ALTER COLUMN id SET DEFAULT nextval('bugwatch_id_seq'::regclass);

ALTER TABLE build ALTER COLUMN id SET DEFAULT nextval('build_id_seq'::regclass);

ALTER TABLE builder ALTER COLUMN id SET DEFAULT nextval('builder_id_seq'::regclass);

ALTER TABLE buildqueue ALTER COLUMN id SET DEFAULT nextval('buildqueue_id_seq'::regclass);

ALTER TABLE calendar ALTER COLUMN id SET DEFAULT nextval('calendar_id_seq'::regclass);

ALTER TABLE calendarevent ALTER COLUMN id SET DEFAULT nextval('calendarevent_id_seq'::regclass);

ALTER TABLE calendarsubscription ALTER COLUMN id SET DEFAULT nextval('calendarsubscription_id_seq'::regclass);

ALTER TABLE codeimport ALTER COLUMN id SET DEFAULT nextval('codeimport_id_seq'::regclass);

ALTER TABLE codeimportevent ALTER COLUMN id SET DEFAULT nextval('codeimportevent_id_seq'::regclass);

ALTER TABLE codeimporteventdata ALTER COLUMN id SET DEFAULT nextval('codeimporteventdata_id_seq'::regclass);

ALTER TABLE codeimportjob ALTER COLUMN id SET DEFAULT nextval('codeimportjob_id_seq'::regclass);

ALTER TABLE codeimportmachine ALTER COLUMN id SET DEFAULT nextval('codeimportmachine_id_seq'::regclass);

ALTER TABLE codeimportresult ALTER COLUMN id SET DEFAULT nextval('codeimportresult_id_seq'::regclass);

ALTER TABLE component ALTER COLUMN id SET DEFAULT nextval('component_id_seq'::regclass);

ALTER TABLE componentselection ALTER COLUMN id SET DEFAULT nextval('componentselection_id_seq'::regclass);

ALTER TABLE continent ALTER COLUMN id SET DEFAULT nextval('continent_id_seq'::regclass);

ALTER TABLE country ALTER COLUMN id SET DEFAULT nextval('country_id_seq'::regclass);

ALTER TABLE cve ALTER COLUMN id SET DEFAULT nextval('cve_id_seq'::regclass);

ALTER TABLE cvereference ALTER COLUMN id SET DEFAULT nextval('cvereference_id_seq'::regclass);

ALTER TABLE distribution ALTER COLUMN id SET DEFAULT nextval('distribution_id_seq'::regclass);

ALTER TABLE distributionbounty ALTER COLUMN id SET DEFAULT nextval('distributionbounty_id_seq'::regclass);

ALTER TABLE distributionmirror ALTER COLUMN id SET DEFAULT nextval('distributionmirror_id_seq'::regclass);

ALTER TABLE distributionsourcepackagecache ALTER COLUMN id SET DEFAULT nextval('distributionsourcepackagecache_id_seq'::regclass);

ALTER TABLE distroarchrelease ALTER COLUMN id SET DEFAULT nextval('distroarchrelease_id_seq'::regclass);

ALTER TABLE distrocomponentuploader ALTER COLUMN id SET DEFAULT nextval('distrocomponentuploader_id_seq'::regclass);

ALTER TABLE distrorelease ALTER COLUMN id SET DEFAULT nextval('distrorelease_id_seq'::regclass);

ALTER TABLE distroreleaselanguage ALTER COLUMN id SET DEFAULT nextval('distroreleaselanguage_id_seq'::regclass);

ALTER TABLE distroreleasepackagecache ALTER COLUMN id SET DEFAULT nextval('distroreleasepackagecache_id_seq'::regclass);

ALTER TABLE emailaddress ALTER COLUMN id SET DEFAULT nextval('emailaddress_id_seq'::regclass);

ALTER TABLE entitlement ALTER COLUMN id SET DEFAULT nextval('entitlement_id_seq'::regclass);

ALTER TABLE faq ALTER COLUMN id SET DEFAULT nextval('faq_id_seq'::regclass);

ALTER TABLE fticache ALTER COLUMN id SET DEFAULT nextval('fticache_id_seq'::regclass);

ALTER TABLE gpgkey ALTER COLUMN id SET DEFAULT nextval('gpgkey_id_seq'::regclass);

ALTER TABLE hwsubmission ALTER COLUMN id SET DEFAULT nextval('hwsubmission_id_seq'::regclass);

ALTER TABLE hwsystemfingerprint ALTER COLUMN id SET DEFAULT nextval('hwsystemfingerprint_id_seq'::regclass);

ALTER TABLE ircid ALTER COLUMN id SET DEFAULT nextval('ircid_id_seq'::regclass);

ALTER TABLE jabberid ALTER COLUMN id SET DEFAULT nextval('jabberid_id_seq'::regclass);

ALTER TABLE karma ALTER COLUMN id SET DEFAULT nextval('karma_id_seq'::regclass);

ALTER TABLE karmaaction ALTER COLUMN id SET DEFAULT nextval('karmaaction_id_seq'::regclass);

ALTER TABLE karmacache ALTER COLUMN id SET DEFAULT nextval('karmacache_id_seq'::regclass);

ALTER TABLE karmacategory ALTER COLUMN id SET DEFAULT nextval('karmacategory_id_seq'::regclass);

ALTER TABLE karmatotalcache ALTER COLUMN id SET DEFAULT nextval('karmatotalcache_id_seq'::regclass);

ALTER TABLE "language" ALTER COLUMN id SET DEFAULT nextval('language_id_seq'::regclass);

ALTER TABLE languagepack ALTER COLUMN id SET DEFAULT nextval('languagepack_id_seq'::regclass);

ALTER TABLE launchpadstatistic ALTER COLUMN id SET DEFAULT nextval('launchpadstatistic_id_seq'::regclass);

ALTER TABLE libraryfilealias ALTER COLUMN id SET DEFAULT nextval('libraryfilealias_id_seq'::regclass);

ALTER TABLE libraryfilecontent ALTER COLUMN id SET DEFAULT nextval('libraryfilecontent_id_seq'::regclass);

ALTER TABLE license ALTER COLUMN id SET DEFAULT nextval('license_id_seq'::regclass);

ALTER TABLE logintoken ALTER COLUMN id SET DEFAULT nextval('logintoken_id_seq'::regclass);

ALTER TABLE mailinglist ALTER COLUMN id SET DEFAULT nextval('mailinglist_id_seq'::regclass);

ALTER TABLE mailinglistban ALTER COLUMN id SET DEFAULT nextval('mailinglistban_id_seq'::regclass);

ALTER TABLE mailinglistsubscription ALTER COLUMN id SET DEFAULT nextval('mailinglistsubscription_id_seq'::regclass);

ALTER TABLE mentoringoffer ALTER COLUMN id SET DEFAULT nextval('mentoringoffer_id_seq'::regclass);

ALTER TABLE message ALTER COLUMN id SET DEFAULT nextval('message_id_seq'::regclass);

ALTER TABLE messageapproval ALTER COLUMN id SET DEFAULT nextval('messageapproval_id_seq'::regclass);

ALTER TABLE messagechunk ALTER COLUMN id SET DEFAULT nextval('messagechunk_id_seq'::regclass);

ALTER TABLE milestone ALTER COLUMN id SET DEFAULT nextval('milestone_id_seq'::regclass);

ALTER TABLE mirror ALTER COLUMN id SET DEFAULT nextval('mirror_id_seq'::regclass);

ALTER TABLE mirrorcdimagedistrorelease ALTER COLUMN id SET DEFAULT nextval('mirrorcdimagedistrorelease_id_seq'::regclass);

ALTER TABLE mirrorcontent ALTER COLUMN id SET DEFAULT nextval('mirrorcontent_id_seq'::regclass);

ALTER TABLE mirrordistroarchrelease ALTER COLUMN id SET DEFAULT nextval('mirrordistroarchrelease_id_seq'::regclass);

ALTER TABLE mirrordistroreleasesource ALTER COLUMN id SET DEFAULT nextval('mirrordistroreleasesource_id_seq'::regclass);

ALTER TABLE mirrorproberecord ALTER COLUMN id SET DEFAULT nextval('mirrorproberecord_id_seq'::regclass);

ALTER TABLE mirrorsourcecontent ALTER COLUMN id SET DEFAULT nextval('mirrorsourcecontent_id_seq'::regclass);

ALTER TABLE nameblacklist ALTER COLUMN id SET DEFAULT nextval('nameblacklist_id_seq'::regclass);

ALTER TABLE officialbugtag ALTER COLUMN id SET DEFAULT nextval('officialbugtag_id_seq'::regclass);

ALTER TABLE openidauthorization ALTER COLUMN id SET DEFAULT nextval('openidauthorization_id_seq'::regclass);

ALTER TABLE openidrpconfig ALTER COLUMN id SET DEFAULT nextval('openidrpconfig_id_seq'::regclass);

ALTER TABLE packagebugcontact ALTER COLUMN id SET DEFAULT nextval('packagebugcontact_id_seq'::regclass);

ALTER TABLE packageselection ALTER COLUMN id SET DEFAULT nextval('packageselection_id_seq'::regclass);

ALTER TABLE packageupload ALTER COLUMN id SET DEFAULT nextval('packageupload_id_seq'::regclass);

ALTER TABLE packageuploadbuild ALTER COLUMN id SET DEFAULT nextval('packageuploadbuild_id_seq'::regclass);

ALTER TABLE packageuploadcustom ALTER COLUMN id SET DEFAULT nextval('packageuploadcustom_id_seq'::regclass);

ALTER TABLE packageuploadsource ALTER COLUMN id SET DEFAULT nextval('packageuploadsource_id_seq'::regclass);

ALTER TABLE person ALTER COLUMN id SET DEFAULT nextval('person_id_seq'::regclass);

ALTER TABLE personlanguage ALTER COLUMN id SET DEFAULT nextval('personlanguage_id_seq'::regclass);

ALTER TABLE pillarname ALTER COLUMN id SET DEFAULT nextval('pillarname_id_seq'::regclass);

ALTER TABLE pocketchroot ALTER COLUMN id SET DEFAULT nextval('pocketchroot_id_seq'::regclass);

ALTER TABLE pocomment ALTER COLUMN id SET DEFAULT nextval('pocomment_id_seq'::regclass);

ALTER TABLE poexportrequest ALTER COLUMN id SET DEFAULT nextval('poexportrequest_id_seq'::regclass);

ALTER TABLE pofile ALTER COLUMN id SET DEFAULT nextval('pofile_id_seq'::regclass);

ALTER TABLE pofiletranslator ALTER COLUMN id SET DEFAULT nextval('pofiletranslator_id_seq'::regclass);

ALTER TABLE poll ALTER COLUMN id SET DEFAULT nextval('poll_id_seq'::regclass);

ALTER TABLE polloption ALTER COLUMN id SET DEFAULT nextval('polloption_id_seq'::regclass);

ALTER TABLE pomsgid ALTER COLUMN id SET DEFAULT nextval('pomsgid_id_seq'::regclass);

ALTER TABLE pomsgidsighting ALTER COLUMN id SET DEFAULT nextval('pomsgidsighting_id_seq'::regclass);

ALTER TABLE pomsgset ALTER COLUMN id SET DEFAULT nextval('pomsgset_id_seq'::regclass);

ALTER TABLE posubmission ALTER COLUMN id SET DEFAULT nextval('posubmission_id_seq'::regclass);

ALTER TABLE posubscription ALTER COLUMN id SET DEFAULT nextval('posubscription_id_seq'::regclass);

ALTER TABLE potemplate ALTER COLUMN id SET DEFAULT nextval('potemplate_id_seq'::regclass);

ALTER TABLE potemplatename ALTER COLUMN id SET DEFAULT nextval('potemplatename_id_seq'::regclass);

ALTER TABLE potmsgset ALTER COLUMN id SET DEFAULT nextval('potmsgset_id_seq'::regclass);

ALTER TABLE potranslation ALTER COLUMN id SET DEFAULT nextval('potranslation_id_seq'::regclass);

ALTER TABLE processor ALTER COLUMN id SET DEFAULT nextval('processor_id_seq'::regclass);

ALTER TABLE processorfamily ALTER COLUMN id SET DEFAULT nextval('processorfamily_id_seq'::regclass);

ALTER TABLE product ALTER COLUMN id SET DEFAULT nextval('product_id_seq'::regclass);

ALTER TABLE productbounty ALTER COLUMN id SET DEFAULT nextval('productbounty_id_seq'::regclass);

ALTER TABLE productcvsmodule ALTER COLUMN id SET DEFAULT nextval('productcvsmodule_id_seq'::regclass);

ALTER TABLE productrelease ALTER COLUMN id SET DEFAULT nextval('productrelease_id_seq'::regclass);

ALTER TABLE productseries ALTER COLUMN id SET DEFAULT nextval('productseries_id_seq'::regclass);

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

ALTER TABLE revisionparent ALTER COLUMN id SET DEFAULT nextval('revisionparent_id_seq'::regclass);

ALTER TABLE revisionproperty ALTER COLUMN id SET DEFAULT nextval('revisionproperty_id_seq'::regclass);

ALTER TABLE scriptactivity ALTER COLUMN id SET DEFAULT nextval('scriptactivity_id_seq'::regclass);

ALTER TABLE section ALTER COLUMN id SET DEFAULT nextval('section_id_seq'::regclass);

ALTER TABLE sectionselection ALTER COLUMN id SET DEFAULT nextval('sectionselection_id_seq'::regclass);

ALTER TABLE securebinarypackagepublishinghistory ALTER COLUMN id SET DEFAULT nextval('securebinarypackagepublishinghistory_id_seq'::regclass);

ALTER TABLE securesourcepackagepublishinghistory ALTER COLUMN id SET DEFAULT nextval('securesourcepackagepublishinghistory_id_seq'::regclass);

ALTER TABLE shipitreport ALTER COLUMN id SET DEFAULT nextval('shipitreport_id_seq'::regclass);

ALTER TABLE shipment ALTER COLUMN id SET DEFAULT nextval('shipment_id_seq'::regclass);

ALTER TABLE shippingrequest ALTER COLUMN id SET DEFAULT nextval('shippingrequest_id_seq'::regclass);

ALTER TABLE shippingrun ALTER COLUMN id SET DEFAULT nextval('shippingrun_id_seq'::regclass);

ALTER TABLE shockandawe ALTER COLUMN id SET DEFAULT nextval('shockandawe_id_seq'::regclass);

ALTER TABLE signedcodeofconduct ALTER COLUMN id SET DEFAULT nextval('signedcodeofconduct_id_seq'::regclass);

ALTER TABLE sourcepackagename ALTER COLUMN id SET DEFAULT nextval('sourcepackagename_id_seq'::regclass);

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

ALTER TABLE teammembership ALTER COLUMN id SET DEFAULT nextval('teammembership_id_seq'::regclass);

ALTER TABLE teamparticipation ALTER COLUMN id SET DEFAULT nextval('teamparticipation_id_seq'::regclass);

ALTER TABLE temporaryblobstorage ALTER COLUMN id SET DEFAULT nextval('temporaryblobstorage_id_seq'::regclass);

ALTER TABLE translationgroup ALTER COLUMN id SET DEFAULT nextval('translationgroup_id_seq'::regclass);

ALTER TABLE translationimportqueueentry ALTER COLUMN id SET DEFAULT nextval('translationimportqueueentry_id_seq'::regclass);

ALTER TABLE translator ALTER COLUMN id SET DEFAULT nextval('translator_id_seq'::regclass);

ALTER TABLE vote ALTER COLUMN id SET DEFAULT nextval('vote_id_seq'::regclass);

ALTER TABLE votecast ALTER COLUMN id SET DEFAULT nextval('votecast_id_seq'::regclass);

ALTER TABLE wikiname ALTER COLUMN id SET DEFAULT nextval('wikiname_id_seq'::regclass);

ALTER TABLE ONLY archive
    ADD CONSTRAINT archive_pkey PRIMARY KEY (id);

ALTER TABLE ONLY revisionauthor
    ADD CONSTRAINT archuserid_archuserid_key UNIQUE (name);

ALTER TABLE ONLY revisionauthor
    ADD CONSTRAINT archuserid_pkey PRIMARY KEY (id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackage_pkey PRIMARY KEY (id);

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
    ADD CONSTRAINT branch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_url_unique UNIQUE (url);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_source_branch_key UNIQUE (source_branch, target_branch, date_merged);

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

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_bug_cve_uniq UNIQUE (bug, cve);

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT bugexternalref_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_bug_key UNIQUE (bug, message);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination_pkey PRIMARY KEY (id);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification__bug__message__unq UNIQUE (bug, message);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification_pkey PRIMARY KEY (id);

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

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bugtask_target UNIQUE (id, bug);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_pkey PRIMARY KEY (id);

ALTER TABLE ONLY build
    ADD CONSTRAINT build_pkey PRIMARY KEY (id);

ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_pkey PRIMARY KEY (id);

ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_url_key UNIQUE (url);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT buildqueue_pkey PRIMARY KEY (id);

ALTER TABLE ONLY calendar
    ADD CONSTRAINT calendar_pkey PRIMARY KEY (id);

ALTER TABLE ONLY calendarevent
    ADD CONSTRAINT calendarevent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY calendarevent
    ADD CONSTRAINT calendarevent_uid_key UNIQUE (uid);

ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_subject_key UNIQUE (subject, "object");

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

ALTER TABLE ONLY component
    ADD CONSTRAINT component_name_key UNIQUE (name);

ALTER TABLE ONLY component
    ADD CONSTRAINT component_pkey PRIMARY KEY (id);

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

ALTER TABLE ONLY cve
    ADD CONSTRAINT cve_pkey PRIMARY KEY (id);

ALTER TABLE ONLY cve
    ADD CONSTRAINT cve_sequence_uniq UNIQUE ("sequence");

ALTER TABLE ONLY cvereference
    ADD CONSTRAINT cvereference_pkey PRIMARY KEY (id);

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

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_distribution_sourcepackagename_u UNIQUE (distribution, sourcepackagename);

ALTER TABLE distributionsourcepackagecache CLUSTER ON distributionsourcepackagecache_distribution_sourcepackagename_u;

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT distroarchrelease_distrorelease_architecturetag_unique UNIQUE (distrorelease, architecturetag);

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT distroarchrelease_distrorelease_processorfamily_unique UNIQUE (distrorelease, processorfamily);

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT distroarchrelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_distro_component_uniq UNIQUE (distribution, component);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_distribution_key UNIQUE (distribution, name);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_distro_release_unique UNIQUE (distribution, id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroreleaselanguage
    ADD CONSTRAINT distroreleaselanguage_distrorelease_language_uniq UNIQUE (distrorelease, "language");

ALTER TABLE ONLY distroreleaselanguage
    ADD CONSTRAINT distroreleaselanguage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY distroreleasepackagecache
    ADD CONSTRAINT distroreleasepackagecache_distrorelease_binarypackagename_uniq UNIQUE (distrorelease, binarypackagename);

ALTER TABLE distroreleasepackagecache CLUSTER ON distroreleasepackagecache_distrorelease_binarypackagename_uniq;

ALTER TABLE ONLY distroreleasepackagecache
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
    ADD CONSTRAINT distroreleasequeuesource__distroreleasequeue__sourcepackagerele UNIQUE (packageupload, sourcepackagerelease);

ALTER TABLE ONLY packageuploadsource
    ADD CONSTRAINT distroreleasequeuesource_pkey PRIMARY KEY (id);

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress__person__id__key UNIQUE (person, id);

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress_pkey PRIMARY KEY (id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_pkey PRIMARY KEY (id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_pkey PRIMARY KEY (id);

ALTER TABLE ONLY fticache
    ADD CONSTRAINT fticache_pkey PRIMARY KEY (id);

ALTER TABLE ONLY fticache
    ADD CONSTRAINT fticache_tablename_key UNIQUE (tablename);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_fingerprint_key UNIQUE (fingerprint);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_owner_key UNIQUE ("owner", id);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__submission_key__key UNIQUE (submission_key);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission_pkey PRIMARY KEY (id);

ALTER TABLE ONLY hwsystemfingerprint
    ADD CONSTRAINT hwsystemfingerprint__fingerprint__key UNIQUE (fingerprint);

ALTER TABLE ONLY hwsystemfingerprint
    ADD CONSTRAINT hwsystemfingerprint_pkey PRIMARY KEY (id);

ALTER TABLE ONLY ircid
    ADD CONSTRAINT ircid_pkey PRIMARY KEY (id);

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_jabberid_key UNIQUE (jabberid);

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_pkey PRIMARY KEY (id);

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

ALTER TABLE ONLY "language"
    ADD CONSTRAINT language_code_key UNIQUE (code);

ALTER TABLE ONLY "language"
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

ALTER TABLE ONLY license
    ADD CONSTRAINT license_pkey PRIMARY KEY (id);

ALTER TABLE ONLY logintoken
    ADD CONSTRAINT logintoken_token_key UNIQUE (token);

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

ALTER TABLE ONLY message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_message_id_key UNIQUE (message_id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_pkey PRIMARY KEY (id);

ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_message_idx UNIQUE (message, "sequence");

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

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_id_key UNIQUE (product, id);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_name_key UNIQUE (name);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorcdimagedistrorelease
    ADD CONSTRAINT mirrorcdimagedistrorelease__unq UNIQUE (distrorelease, flavour, distribution_mirror);

ALTER TABLE ONLY mirrorcdimagedistrorelease
    ADD CONSTRAINT mirrorcdimagedistrorelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrordistroarchrelease
    ADD CONSTRAINT mirrordistroarchrelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrordistroreleasesource
    ADD CONSTRAINT mirrordistroreleasesource_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY nameblacklist
    ADD CONSTRAINT nameblacklist__regexp__key UNIQUE (regexp);

ALTER TABLE ONLY nameblacklist
    ADD CONSTRAINT nameblacklist_pkey PRIMARY KEY (id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_pkey PRIMARY KEY (id);

ALTER TABLE ONLY openidassociations
    ADD CONSTRAINT openidassociations_pkey PRIMARY KEY (server_url, handle);

ALTER TABLE ONLY openidauthorization
    ADD CONSTRAINT openidauthorization_pkey PRIMARY KEY (id);

ALTER TABLE ONLY openidrpconfig
    ADD CONSTRAINT openidrpconfig_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packagebugcontact
    ADD CONSTRAINT packagebugcontact_distinct_bugcontact UNIQUE (sourcepackagename, distribution, bugcontact);

ALTER TABLE ONLY packagebugcontact
    ADD CONSTRAINT packagebugcontact_pkey PRIMARY KEY (id);

ALTER TABLE ONLY securebinarypackagepublishinghistory
    ADD CONSTRAINT packagepublishinghistory_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_pkey PRIMARY KEY (id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_uniqueness UNIQUE (distrorelease, sourcepackagename, productseries);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_calendar_key UNIQUE (calendar);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_openid_identifier_key UNIQUE (openid_identifier);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);

ALTER TABLE person CLUSTER ON person_pkey;

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_person_key UNIQUE (person, "language");

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_name_key UNIQUE (name);

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_pkey PRIMARY KEY (id);

ALTER TABLE pillarname CLUSTER ON pillarname_pkey;

ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot_distroarchrelease_key UNIQUE (distroarchrelease, pocket);

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

ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_pkey PRIMARY KEY (id);

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset__potmsgset__pofile__key UNIQUE (potmsgset, pofile);

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pkey PRIMARY KEY (id);

ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__pomsgset__pluralform__id__key UNIQUE (pomsgset, pluralform, id);

ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__potranslation__pomsgset__pluralform__key UNIQUE (potranslation, pomsgset, pluralform);

ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission_pkey PRIMARY KEY (id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_person_key UNIQUE (person, potemplate, "language");

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_distrorelease_key UNIQUE (distrorelease, sourcepackagename, potemplatename);

ALTER TABLE ONLY potemplatename
    ADD CONSTRAINT potemplate_name_key UNIQUE (name);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_pkey PRIMARY KEY (id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_productseries_ptname_uniq UNIQUE (productseries, potemplatename);

ALTER TABLE ONLY potemplatename
    ADD CONSTRAINT potemplate_translationdomain_key UNIQUE (translationdomain);

ALTER TABLE ONLY potemplatename
    ADD CONSTRAINT potemplatename_pkey PRIMARY KEY (id);

ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_pkey PRIMARY KEY (id);

ALTER TABLE ONLY potranslation
    ADD CONSTRAINT potranslation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_name_key UNIQUE (name);

ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_pkey PRIMARY KEY (id);

ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_name_key UNIQUE (name);

ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_pkey PRIMARY KEY (id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_calendar_key UNIQUE (calendar);

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

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_productseries_version_key UNIQUE (productseries, version);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT productreleasefile_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries__import_branch__key UNIQUE (import_branch);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_cvsroot_key UNIQUE (cvsroot, cvsmodule, cvsbranch);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_pkey PRIMARY KEY (id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_key UNIQUE (product, name);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_series_uniq UNIQUE (product, id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_svnrepository_key UNIQUE (svnrepository);

ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT productsvnmodule_pkey PRIMARY KEY (id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_calendar_key UNIQUE (calendar);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_name_key UNIQUE (name);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);

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
    ADD CONSTRAINT requestedcds_pkey PRIMARY KEY (id);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision_revision_id_unique UNIQUE (revision_id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revisionnumber_branch_id_unique UNIQUE (branch, id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revisionnumber_branch_sequence_unique UNIQUE (branch, "sequence");

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revisionnumber_pkey PRIMARY KEY (id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT revisionnumber_revision_branch_unique UNIQUE (revision, branch);

ALTER TABLE ONLY revisionparent
    ADD CONSTRAINT revisionparent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY revisionparent
    ADD CONSTRAINT revisionparent_unique UNIQUE (revision, parent_id);

ALTER TABLE ONLY revisionproperty
    ADD CONSTRAINT revisionproperty__revision__name__key UNIQUE (revision, name);

ALTER TABLE ONLY revisionproperty
    ADD CONSTRAINT revisionproperty_pkey PRIMARY KEY (id);

ALTER TABLE ONLY section
    ADD CONSTRAINT section_name_key UNIQUE (name);

ALTER TABLE ONLY section
    ADD CONSTRAINT section_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT sectionselection_pkey PRIMARY KEY (id);

ALTER TABLE ONLY shipitreport
    ADD CONSTRAINT shipitreport_pkey PRIMARY KEY (id);

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

ALTER TABLE ONLY shockandawe
    ADD CONSTRAINT shockandawe_pkey PRIMARY KEY (id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT single_offer_per_bug_key UNIQUE (bug, "owner");

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT single_offer_per_spec_key UNIQUE (specification, "owner");

ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_name_key UNIQUE (name);

ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_pkey PRIMARY KEY (id);

ALTER TABLE ONLY securesourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_pkey PRIMARY KEY (id);

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
    ADD CONSTRAINT specificationmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationsubscription
    ADD CONSTRAINT specificationsubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationsubscription
    ADD CONSTRAINT specificationsubscription_spec_person_uniq UNIQUE (specification, person);

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT spokenin__country__language__key UNIQUE ("language", country);

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
    ADD CONSTRAINT translation_translationgroup_key UNIQUE (translationgroup, "language");

ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_name_key UNIQUE (name);

ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_pkey PRIMARY KEY (id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry_pkey PRIMARY KEY (id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationfeedback
    ADD CONSTRAINT unique_spec_requestor_provider UNIQUE (specification, requester, reviewer);

ALTER TABLE ONLY validpersonorteamcache
    ADD CONSTRAINT validpersonorteamcache_pkey PRIMARY KEY (id);

ALTER TABLE validpersonorteamcache CLUSTER ON validpersonorteamcache_pkey;

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_pkey PRIMARY KEY (id);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_person_key UNIQUE (person, poll);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_pkey PRIMARY KEY (id);

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_pkey PRIMARY KEY (id);

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_wikiname_key UNIQUE (wikiname, wiki);

CREATE UNIQUE INDEX answercontact__distribution__person__key ON answercontact USING btree (distribution, person) WHERE (sourcepackagename IS NULL);

CREATE INDEX answercontact__person__idx ON answercontact USING btree (person);

CREATE UNIQUE INDEX archive__distribution__purpose__key ON archive USING btree (distribution, purpose) WHERE ((distribution IS NOT NULL) AND ("owner" IS NULL));

CREATE UNIQUE INDEX archive__owner__key ON archive USING btree ("owner");

CREATE INDEX binarypackagefile_binarypackage_idx ON binarypackagefile USING btree (binarypackagerelease);

CREATE INDEX binarypackagefile_libraryfile_idx ON binarypackagefile USING btree (libraryfile);

CREATE INDEX binarypackagerelease_build_idx ON binarypackagerelease USING btree (build);

CREATE INDEX binarypackagerelease_fti ON binarypackagerelease USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX binarypackagerelease_version_idx ON binarypackagerelease USING btree (version);

CREATE INDEX binarypackagerelease_version_sort ON binarypackagerelease USING btree (debversion_sort_key(version));

CREATE INDEX bounty_usdvalue_idx ON bounty USING btree (usdvalue);

CREATE INDEX bountymessage_bounty_idx ON bountymessage USING btree (bounty);

CREATE INDEX branch__date_created__idx ON branch USING btree (date_created);

CREATE INDEX branch__last_scanned__owner__idx ON branch USING btree (last_scanned, "owner") WHERE (last_scanned IS NOT NULL);

CREATE INDEX branch__private__idx ON branch USING btree (private);

CREATE INDEX branch__product__id__idx ON branch USING btree (product, id);

CREATE INDEX branch_author_idx ON branch USING btree (author);

CREATE UNIQUE INDEX branch_name_owner_product_key ON branch USING btree (name, "owner", (COALESCE(product, -1)));

CREATE INDEX branch_owner_idx ON branch USING btree ("owner");

ALTER TABLE branch CLUSTER ON branch_owner_idx;

CREATE INDEX branchmergeproposal__dependent_branch__idx ON branchmergeproposal USING btree (dependent_branch);

CREATE INDEX branchmergeproposal__merge_reporter__idx ON branchmergeproposal USING btree (merge_reporter) WHERE (merge_reporter IS NOT NULL);

CREATE INDEX branchmergeproposal__source_branch__idx ON branchmergeproposal USING btree (source_branch);

CREATE INDEX branchmergeproposal__target_branch__idx ON branchmergeproposal USING btree (target_branch);

CREATE INDEX branchsubscription__branch__idx ON branchsubscription USING btree (branch);

CREATE INDEX branchsubscription__person__idx ON branchsubscription USING btree (person);

CREATE INDEX branchvisibilitypolicy__product__idx ON branchvisibilitypolicy USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX branchvisibilitypolicy__project__idx ON branchvisibilitypolicy USING btree (project) WHERE (project IS NOT NULL);

CREATE INDEX branchvisibilitypolicy__team__idx ON branchvisibilitypolicy USING btree (team) WHERE (team IS NOT NULL);

CREATE UNIQUE INDEX branchvisibilitypolicy__unq ON branchvisibilitypolicy USING btree ((COALESCE(product, -1)), (COALESCE(project, -1)), (COALESCE(team, -1)));

CREATE INDEX bug__date_last_message__idx ON bug USING btree (date_last_message);

CREATE INDEX bug__date_last_updated__idx ON bug USING btree (date_last_updated);

ALTER TABLE bug CLUSTER ON bug__date_last_updated__idx;

CREATE INDEX bug__datecreated__idx ON bug USING btree (datecreated);

CREATE INDEX bug__who_made_private__idx ON bug USING btree (who_made_private) WHERE (who_made_private IS NOT NULL);

CREATE INDEX bug_duplicateof_idx ON bug USING btree (duplicateof);

CREATE INDEX bug_fti ON bug USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX bug_owner_idx ON bug USING btree ("owner");

CREATE INDEX bugactivity_bug_datechanged_idx ON bugactivity USING btree (bug, datechanged);

CREATE INDEX bugactivity_datechanged_idx ON bugactivity USING btree (datechanged);

CREATE INDEX bugactivity_person_datechanged_idx ON bugactivity USING btree (person, datechanged);

CREATE INDEX bugattachment_libraryfile_idx ON bugattachment USING btree (libraryfile);

CREATE INDEX bugattachment_message_idx ON bugattachment USING btree (message);

CREATE INDEX bugcve_cve_index ON bugcve USING btree (cve);

CREATE INDEX bugexternalref_bug_idx ON bugexternalref USING btree (bug);

CREATE INDEX bugexternalref_datecreated_idx ON bugexternalref USING btree (datecreated);

CREATE INDEX bugmessage__bugwatch__idx ON bugmessage USING btree (bugwatch);

CREATE INDEX bugmessage_bug_idx ON bugmessage USING btree (bug);

CREATE INDEX bugmessage_message_idx ON bugmessage USING btree (message);

CREATE INDEX bugnomination__bug__idx ON bugnomination USING btree (bug);

CREATE INDEX bugnomination__decider__idx ON bugnomination USING btree (decider) WHERE (decider IS NOT NULL);

CREATE INDEX bugnomination__owner__idx ON bugnomination USING btree ("owner");

CREATE INDEX bugnotification__date_emailed__idx ON bugnotification USING btree (date_emailed);

CREATE INDEX bugsubscription_bug_idx ON bugsubscription USING btree (bug);

ALTER TABLE bugsubscription CLUSTER ON bugsubscription_bug_idx;

CREATE INDEX bugsubscription_person_idx ON bugsubscription USING btree (person);

CREATE INDEX bugtag__bug__idx ON bugtag USING btree (bug);

CREATE UNIQUE INDEX bugtask__date_closed__id__idx ON bugtask USING btree (date_closed, id) WHERE (status = 30);

CREATE INDEX bugtask__date_incomplete__idx ON bugtask USING btree (date_incomplete) WHERE (date_incomplete IS NOT NULL);

CREATE INDEX bugtask__productseries__idx ON bugtask USING btree (productseries) WHERE (productseries IS NOT NULL);

CREATE INDEX bugtask_assignee_idx ON bugtask USING btree (assignee);

CREATE INDEX bugtask_binarypackagename_idx ON bugtask USING btree (binarypackagename);

CREATE INDEX bugtask_bug_idx ON bugtask USING btree (bug);

CREATE INDEX bugtask_datecreated_idx ON bugtask USING btree (datecreated);

CREATE UNIQUE INDEX bugtask_distinct_sourcepackage_assignment ON bugtask USING btree (bug, (COALESCE(sourcepackagename, -1)), (COALESCE(distrorelease, -1)), (COALESCE(distribution, -1))) WHERE ((product IS NULL) AND (productseries IS NULL));

CREATE INDEX bugtask_distribution_and_sourcepackagename_idx ON bugtask USING btree (distribution, sourcepackagename);

ALTER TABLE bugtask CLUSTER ON bugtask_distribution_and_sourcepackagename_idx;

CREATE INDEX bugtask_distribution_idx ON bugtask USING btree (distribution);

CREATE INDEX bugtask_distrorelease_and_sourcepackagename_idx ON bugtask USING btree (distrorelease, sourcepackagename);

CREATE INDEX bugtask_distrorelease_idx ON bugtask USING btree (distrorelease);

CREATE INDEX bugtask_fti ON bugtask USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX bugtask_milestone_idx ON bugtask USING btree (milestone);

CREATE INDEX bugtask_owner_idx ON bugtask USING btree ("owner");

CREATE UNIQUE INDEX bugtask_product_key ON bugtask USING btree (product, bug) WHERE (product IS NOT NULL);

CREATE INDEX bugtask_sourcepackagename_idx ON bugtask USING btree (sourcepackagename);

CREATE UNIQUE INDEX bugtracker_name_key ON bugtracker USING btree (name);

CREATE INDEX bugtracker_owner_idx ON bugtracker USING btree ("owner");

CREATE INDEX bugwatch_bug_idx ON bugwatch USING btree (bug);

CREATE INDEX bugwatch_bugtracker_idx ON bugwatch USING btree (bugtracker);

CREATE INDEX bugwatch_datecreated_idx ON bugwatch USING btree (datecreated);

CREATE INDEX bugwatch_owner_idx ON bugwatch USING btree ("owner");

CREATE INDEX build__archive__idx ON build USING btree (archive);

CREATE INDEX build_builder_and_buildstate_idx ON build USING btree (builder, buildstate);

CREATE INDEX build_buildlog_idx ON build USING btree (buildlog) WHERE (buildlog IS NOT NULL);

CREATE INDEX build_buildstate_idx ON build USING btree (buildstate);

CREATE INDEX build_datebuilt_idx ON build USING btree (datebuilt);

CREATE INDEX build_datecreated_idx ON build USING btree (datecreated);

CREATE INDEX build_distroarchrelease_and_buildstate_idx ON build USING btree (distroarchrelease, buildstate);

CREATE INDEX build_distroarchrelease_and_datebuilt_idx ON build USING btree (distroarchrelease, datebuilt);

CREATE INDEX build_sourcepackagerelease_idx ON build USING btree (sourcepackagerelease);

CREATE INDEX buildqueue__build__idx ON buildqueue USING btree (build);

CREATE UNIQUE INDEX buildqueue__builder__id__idx ON buildqueue USING btree (builder, id);

ALTER TABLE buildqueue CLUSTER ON buildqueue__builder__id__idx;

CREATE UNIQUE INDEX buildqueue__builder__unq ON buildqueue USING btree (builder) WHERE (builder IS NOT NULL);

CREATE INDEX changeset_datecreated_idx ON revision USING btree (date_created);

CREATE INDEX codeimport__assignee__idx ON codeimport USING btree (assignee);

CREATE UNIQUE INDEX codeimport__cvs_root__cvs_module__key ON codeimport USING btree (cvs_root, cvs_module) WHERE (cvs_root IS NOT NULL);

CREATE INDEX codeimport__owner__idx ON codeimport USING btree ("owner");

CREATE INDEX codeimport__registrant__idx ON codeimport USING btree (registrant);

CREATE UNIQUE INDEX codeimport__svn_branch_url__idx ON codeimport USING btree (svn_branch_url) WHERE (svn_branch_url IS NOT NULL);

CREATE INDEX codeimportevent__code_import__date_created__id__idx ON codeimportevent USING btree (code_import, date_created, id);

CREATE INDEX codeimportevent__date_created__id__idx ON codeimportevent USING btree (date_created, id);

CREATE INDEX codeimportevent__person__idx ON codeimportevent USING btree (person) WHERE (person IS NOT NULL);

CREATE INDEX codeimportjob__code_import__date_created__idx ON codeimportjob USING btree (code_import, date_created);

CREATE INDEX codeimportjob__machine__date_created__idx ON codeimportjob USING btree (machine, date_created);

CREATE INDEX codeimportjob__requesting_user__idx ON codeimportjob USING btree (requesting_user);

CREATE INDEX codeimportresult__code_import__date_created__idx ON codeimportresult USING btree (code_import, date_created);

CREATE INDEX codeimportresult__machine__date_created__idx ON codeimportresult USING btree (machine, date_created);

CREATE INDEX codeimportresult__requesting_user__idx ON codeimportresult USING btree (requesting_user);

CREATE UNIQUE INDEX componentselection__distrorelease__component__uniq ON componentselection USING btree (distrorelease, component);

CREATE INDEX cve_datecreated_idx ON cve USING btree (datecreated);

CREATE INDEX cve_datemodified_idx ON cve USING btree (datemodified);

CREATE INDEX cve_fti ON cve USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX cvereference_cve_idx ON cvereference USING btree (cve);

CREATE INDEX distribution__icon__idx ON distribution USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX distribution__language_pack_admin__idx ON distribution USING btree (language_pack_admin);

CREATE INDEX distribution__logo__idx ON distribution USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX distribution__mugshot__idx ON distribution USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX distribution_bugcontact_idx ON distribution USING btree (bugcontact);

CREATE INDEX distribution_fti ON distribution USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX distribution_translationgroup_idx ON distribution USING btree (translationgroup);

CREATE INDEX distributionbounty_distribution_idx ON distributionbounty USING btree (distribution);

CREATE INDEX distributionsourcepackagecache_fti ON distributionsourcepackagecache USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX distroarchrelease_architecturetag_idx ON distroarchrelease USING btree (architecturetag);

CREATE INDEX distroarchrelease_distrorelease_idx ON distroarchrelease USING btree (distrorelease);

CREATE INDEX distroarchrelease_processorfamily_idx ON distroarchrelease USING btree (processorfamily);

CREATE INDEX distrocomponentuploader_uploader_idx ON distrocomponentuploader USING btree (uploader);

CREATE INDEX distroreleasepackagecache_fti ON distroreleasepackagecache USING gin (fti ts2.gin_tsvector_ops);

CREATE INDEX distroreleasepackagecache_fti_gist ON distroreleasepackagecache USING gist (fti ts2.gist_tsvector_ops);

CREATE UNIQUE INDEX emailaddress_person_key ON emailaddress USING btree (person, (NULLIF((status = 4), false)));

CREATE INDEX emailaddress_person_status_idx ON emailaddress USING btree (person, status);

ALTER TABLE emailaddress CLUSTER ON emailaddress_person_status_idx;

CREATE INDEX entitlement__approved_by__idx ON entitlement USING btree (approved_by) WHERE (approved_by IS NOT NULL);

CREATE INDEX entitlement__person__idx ON entitlement USING btree (person);

CREATE INDEX entitlement__registrant__idx ON entitlement USING btree (registrant) WHERE (registrant IS NOT NULL);

CREATE INDEX entitlement_lookup_idx ON entitlement USING btree (entitlement_type, date_starts, date_expires, person, state);

CREATE INDEX faq__distribution__idx ON faq USING btree (distribution) WHERE (distribution IS NOT NULL);

CREATE INDEX faq__product__idx ON faq USING btree (product) WHERE (product IS NOT NULL);

CREATE INDEX faq_fti ON faq USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX hwsubmission__owner__idx ON hwsubmission USING btree ("owner");

CREATE INDEX hwsubmission__raw_submission__idx ON hwsubmission USING btree (raw_submission);

CREATE INDEX hwsubmission__status__idx ON hwsubmission USING btree (status);

CREATE INDEX hwsubmission__system_fingerprint__idx ON hwsubmission USING btree (system_fingerprint);

CREATE UNIQUE INDEX idx_emailaddress_email ON emailaddress USING btree (lower(email));

CREATE INDEX ircid_person_idx ON ircid USING btree (person);

CREATE INDEX jabberid_person_idx ON jabberid USING btree (person);

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

CREATE UNIQUE INDEX karmacache__unq ON karmacache USING btree (person, (COALESCE(product, -1)), (COALESCE(sourcepackagename, -1)), (COALESCE(project, -1)), (COALESCE(category, -1)), (COALESCE(distribution, -1)));

CREATE INDEX karmacache_person_idx ON karmacache USING btree (person);

CREATE INDEX karmacache_top_in_category_idx ON karmacache USING btree (person, category, karmavalue) WHERE ((((product IS NULL) AND (project IS NULL)) AND (sourcepackagename IS NULL)) AND (distribution IS NULL));

CREATE UNIQUE INDEX karmatotalcache_karma_total_person_idx ON karmatotalcache USING btree (karma_total, person);

CREATE INDEX languagepack__file__idx ON languagepack USING btree (file);

CREATE INDEX libraryfilealias_content_idx ON libraryfilealias USING btree (content);

CREATE INDEX libraryfilecontent__md5__idx ON libraryfilecontent USING btree (md5);

CREATE INDEX libraryfilecontent_sha1_filesize_idx ON libraryfilecontent USING btree (sha1, filesize);

CREATE INDEX logintoken_requester_idx ON logintoken USING btree (requester);

CREATE INDEX mailinglist__date_registered__idx ON mailinglist USING btree (status, date_registered);

CREATE INDEX mailinglist__registrant__idx ON mailinglist USING btree (registrant);

CREATE INDEX mailinglist__reviewer__idx ON mailinglist USING btree (reviewer);

CREATE UNIQUE INDEX mailinglist__team__status__key ON mailinglist USING btree (team, status);

CREATE INDEX mailinglistban__banned_by__idx ON mailinglistban USING btree (banned_by);

CREATE INDEX mailinglistban__person__idx ON mailinglistban USING btree (person);

CREATE INDEX mailinglistsubscription__email_address__idx ON mailinglistsubscription USING btree (email_address) WHERE (email_address IS NOT NULL);

CREATE INDEX mailinglistsubscription__mailing_list__idx ON mailinglistsubscription USING btree (mailing_list);

CREATE UNIQUE INDEX mailinglistsubscription__person__mailing_list__key ON mailinglistsubscription USING btree (person, mailing_list);

CREATE INDEX mentoringoffer__owner__idx ON mentoringoffer USING btree ("owner");

CREATE INDEX mentoringoffer__team__idx ON mentoringoffer USING btree (team);

CREATE INDEX message_fti ON message USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX message_owner_idx ON message USING btree ("owner");

CREATE INDEX message_parent_idx ON message USING btree (parent);

CREATE INDEX message_raw_idx ON message USING btree (raw) WHERE (raw IS NOT NULL);

CREATE INDEX message_rfc822msgid_idx ON message USING btree (rfc822msgid);

CREATE INDEX messageapproval__disposed_by__idx ON messageapproval USING btree (disposed_by) WHERE (disposed_by IS NOT NULL);

CREATE INDEX messageapproval__mailing_list__status__posted_date__idx ON messageapproval USING btree (mailing_list, status, posted_date);

CREATE INDEX messageapproval__posted_by__idx ON messageapproval USING btree (posted_by);

CREATE INDEX messageapproval__posted_message__idx ON messageapproval USING btree (posted_message);

CREATE INDEX messagechunk_blob_idx ON messagechunk USING btree (blob) WHERE (blob IS NOT NULL);

CREATE INDEX messagechunk_fti ON messagechunk USING gist (fti ts2.gist_tsvector_ops);

CREATE UNIQUE INDEX mirrordistroarchrelease_uniq ON mirrordistroarchrelease USING btree (distribution_mirror, distro_arch_release, component, pocket);

CREATE UNIQUE INDEX mirrordistroreleasesource_uniq ON mirrordistroreleasesource USING btree (distribution_mirror, distrorelease, component, pocket);

CREATE INDEX mirrorproberecord__date_created__idx ON mirrorproberecord USING btree (date_created);

CREATE INDEX mirrorproberecord__distribution_mirror__date_created__idx ON mirrorproberecord USING btree (distribution_mirror, date_created);

CREATE INDEX mirrorproberecord__log_file__idx ON mirrorproberecord USING btree (log_file) WHERE (log_file IS NOT NULL);

CREATE UNIQUE INDEX officialbugtag__distribution__tag__key ON officialbugtag USING btree (distribution, tag) WHERE (distribution IS NOT NULL);

CREATE UNIQUE INDEX officialbugtag__product__tag__key ON officialbugtag USING btree (product, tag) WHERE (product IS NOT NULL);

CREATE UNIQUE INDEX officialbugtag__project__tag__key ON officialbugtag USING btree (project, tag) WHERE (product IS NOT NULL);

CREATE UNIQUE INDEX one_launchpad_wikiname ON wikiname USING btree (person) WHERE (wiki = 'https://wiki.ubuntu.com/'::text);

CREATE UNIQUE INDEX openidauthorization__person__client_id__trust_root__unq ON openidauthorization USING btree (person, client_id, trust_root) WHERE (client_id IS NOT NULL);

CREATE INDEX openidauthorization__person__trust_root__date_expires__client_i ON openidauthorization USING btree (person, trust_root, date_expires, client_id);

CREATE UNIQUE INDEX openidauthorization__person__trust_root__unq ON openidauthorization USING btree (person, trust_root) WHERE (client_id IS NULL);

CREATE INDEX openidrpconfig__logo__idx ON openidrpconfig USING btree (logo);

CREATE UNIQUE INDEX openidrpconfig__trust_root__key ON openidrpconfig USING btree (trust_root);

CREATE INDEX packagebugcontact_bugcontact_idx ON packagebugcontact USING btree (bugcontact);

CREATE INDEX packageupload__changesfile__idx ON packageupload USING btree (changesfile);

CREATE INDEX packageupload__distrorelease__key ON packageupload USING btree (distrorelease);

CREATE INDEX packageupload__distrorelease__status__idx ON packageupload USING btree (distrorelease, status);

CREATE INDEX packageupload__signing_key__idx ON packageupload USING btree (signing_key);

CREATE INDEX packageuploadbuild__build__idx ON packageuploadbuild USING btree (build);

CREATE INDEX packageuploadcustom__libraryfilealias__idx ON packageuploadcustom USING btree (libraryfilealias);

CREATE INDEX packageuploadcustom__packageupload__idx ON packageuploadcustom USING btree (packageupload);

CREATE INDEX packageuploadsource__sourcepackagerelease__idx ON packageuploadsource USING btree (sourcepackagerelease);

CREATE INDEX packaging_distrorelease_and_sourcepackagename_idx ON packaging USING btree (distrorelease, sourcepackagename);

CREATE INDEX packaging_sourcepackagename_idx ON packaging USING btree (sourcepackagename);

CREATE INDEX person__icon__idx ON person USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX person__logo__idx ON person USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX person__merged__idx ON person USING btree (merged) WHERE (merged IS NOT NULL);

CREATE INDEX person__mugshot__idx ON person USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX person__teamowner__idx ON person USING btree (teamowner) WHERE (teamowner IS NOT NULL);

CREATE INDEX person_datecreated_idx ON person USING btree (datecreated);

CREATE INDEX person_fti ON person USING gist (fti ts2.gist_tsvector_ops);

CREATE UNIQUE INDEX person_name_key ON person USING btree (name);

CREATE INDEX person_sorting_idx ON person USING btree (person_sort_key(displayname, name));

CREATE UNIQUE INDEX pillarname__distribution__key ON pillarname USING btree (distribution) WHERE (distribution IS NOT NULL);

CREATE UNIQUE INDEX pillarname__product__key ON pillarname USING btree (product) WHERE (product IS NOT NULL);

CREATE UNIQUE INDEX pillarname__project__key ON pillarname USING btree (project) WHERE (project IS NOT NULL);

CREATE INDEX pocomment_person_idx ON pocomment USING btree (person);

CREATE UNIQUE INDEX poexportrequest_duplicate_key ON poexportrequest USING btree (potemplate, person, format, (COALESCE(pofile, -1)));

CREATE UNIQUE INDEX pofile__unreviewed_count__id__key ON pofile USING btree (unreviewed_count, id);

CREATE INDEX pofile_datecreated_idx ON pofile USING btree (datecreated);

CREATE INDEX pofile_exportfile_idx ON pofile USING btree (exportfile);

CREATE INDEX pofile_language_idx ON pofile USING btree ("language");

CREATE INDEX pofile_lasttranslator_idx ON pofile USING btree (lasttranslator);

CREATE INDEX pofile_owner_idx ON pofile USING btree ("owner");

CREATE INDEX pofile_potemplate_idx ON pofile USING btree (potemplate);

CREATE UNIQUE INDEX pofile_template_and_language_idx ON pofile USING btree (potemplate, "language", (COALESCE(variant, ''::text)));

CREATE INDEX pofile_variant_idx ON pofile USING btree (variant);

CREATE INDEX pofiletranslator__date_last_touched__idx ON pofiletranslator USING btree (date_last_touched);

CREATE INDEX polloption_poll_idx ON polloption USING btree (poll);

CREATE UNIQUE INDEX pomsgid_msgid_key ON pomsgid USING btree (sha1(msgid));

CREATE INDEX pomsgidsighting_inlastrevision_idx ON pomsgidsighting USING btree (inlastrevision);

CREATE INDEX pomsgidsighting_pluralform_idx ON pomsgidsighting USING btree (pluralform);

CREATE INDEX pomsgidsighting_pomsgid_idx ON pomsgidsighting USING btree (pomsgid);

CREATE INDEX pomsgidsighting_pomsgset_idx ON pomsgidsighting USING btree (potmsgset);

CREATE UNIQUE INDEX pomsgidsighting_potmsgset_pluralform_uniq ON pomsgidsighting USING btree (potmsgset, pluralform) WHERE (inlastrevision = true);

CREATE INDEX pomsgset__language__idx ON pomsgset USING btree ("language");

CREATE INDEX pomsgset__pofile__sequence__idx ON pomsgset USING btree (pofile, "sequence");

CREATE INDEX pomsgset__reviewer__idx ON pomsgset USING btree (reviewer);

CREATE INDEX pomsgset__sequence__idx ON pomsgset USING btree ("sequence");

CREATE INDEX posubmission__person__idx ON posubmission USING btree (person);

CREATE INDEX posubmission__pomsgset__pluralform__active__idx ON posubmission USING btree (pomsgset, pluralform, active);

CREATE UNIQUE INDEX posubmission__pomsgset__pluralform__active__unique_idx ON posubmission USING btree (pomsgset, pluralform) WHERE (active IS TRUE);

CREATE INDEX posubmission__pomsgset__pluralform__published__idx ON posubmission USING btree (pomsgset, pluralform, published);

CREATE UNIQUE INDEX posubmission__pomsgset__pluralform__published__unique_idx ON posubmission USING btree (pomsgset, pluralform) WHERE (published IS TRUE);

CREATE INDEX potemplate__date_last_updated__idx ON potemplate USING btree (date_last_updated);

CREATE INDEX potemplate__source_file__idx ON potemplate USING btree (source_file) WHERE (source_file IS NOT NULL);

CREATE INDEX potemplate_languagepack_idx ON potemplate USING btree (languagepack);

CREATE INDEX potemplate_owner_idx ON potemplate USING btree ("owner");

CREATE INDEX potemplate_potemplatename_idx ON potemplate USING btree (potemplatename);

CREATE UNIQUE INDEX potmsgset__alternative_msgid__potemplate__key ON potmsgset USING btree (alternative_msgid, potemplate) WHERE (alternative_msgid IS NOT NULL);

CREATE UNIQUE INDEX potmsgset__potemplate__context__primemsgid__key ON potmsgset USING btree (potemplate, context, primemsgid) WHERE (context IS NOT NULL);

CREATE UNIQUE INDEX potmsgset__potemplate__no_context__primemsgid__key ON potmsgset USING btree (potemplate, primemsgid) WHERE (context IS NULL);

CREATE INDEX potmsgset_alternative_msgid_idx ON potmsgset USING btree (alternative_msgid);

CREATE INDEX potmsgset_potemplate_and_sequence_idx ON potmsgset USING btree (potemplate, "sequence");

CREATE INDEX potmsgset_primemsgid_idx ON potmsgset USING btree (primemsgid);

CREATE INDEX potmsgset_sequence_idx ON potmsgset USING btree ("sequence");

CREATE UNIQUE INDEX potranslation_translation_key ON potranslation USING btree (sha1(translation));

CREATE INDEX product__bugcontact__idx ON product USING btree (bugcontact) WHERE (bugcontact IS NOT NULL);

CREATE INDEX product__driver__idx ON product USING btree (driver) WHERE (driver IS NOT NULL);

CREATE INDEX product__icon__idx ON product USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX product__logo__idx ON product USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX product__mugshot__idx ON product USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX product__security_contact__idx ON product USING btree (security_contact) WHERE (security_contact IS NOT NULL);

CREATE INDEX product_active_idx ON product USING btree (active);

CREATE INDEX product_bugcontact_idx ON product USING btree (bugcontact);

CREATE INDEX product_fti ON product USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX product_owner_idx ON product USING btree ("owner");

CREATE INDEX product_project_idx ON product USING btree (project);

CREATE INDEX product_translationgroup_idx ON product USING btree (translationgroup);

CREATE INDEX productrelease_datecreated_idx ON productrelease USING btree (datecreated);

CREATE INDEX productrelease_owner_idx ON productrelease USING btree ("owner");

CREATE INDEX productreleasefile__uploader__idx ON productreleasefile USING btree (uploader);

CREATE INDEX productreleasefile_fti ON productreleasefile USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX productseries_datecreated_idx ON productseries USING btree (datecreated);

CREATE INDEX project__icon__idx ON project USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX project__logo__idx ON project USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX project__mugshot__idx ON project USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX project_fti ON project USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX project_owner_idx ON project USING btree ("owner");

CREATE INDEX project_translationgroup_idx ON project USING btree (translationgroup);

CREATE INDEX pushmirroraccess_person_idx ON pushmirroraccess USING btree (person);

CREATE INDEX question__answerer__idx ON question USING btree (answerer);

CREATE INDEX question__assignee__idx ON question USING btree (assignee);

CREATE INDEX question__distribution__sourcepackagename__idx ON question USING btree (distribution, sourcepackagename);

CREATE INDEX question__distro__datecreated__idx ON question USING btree (distribution, datecreated);

CREATE INDEX question__faq__idx ON question USING btree (faq) WHERE (faq IS NOT NULL);

CREATE INDEX question__owner__idx ON question USING btree (assignee);

CREATE INDEX question__product__datecreated__idx ON question USING btree (product, datecreated);

CREATE INDEX question__product__idx ON question USING btree (product);

CREATE INDEX question_fti ON question USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX questionbug__question__idx ON questionbug USING btree (question);

CREATE INDEX questionmessage__question__idx ON questionmessage USING btree (question);

CREATE INDEX questionreopening__answerer__idx ON questionreopening USING btree (answerer);

CREATE INDEX questionreopening__datecreated__idx ON questionreopening USING btree (datecreated);

CREATE INDEX questionreopening__question__idx ON questionreopening USING btree (question);

CREATE INDEX questionreopening__reopener__idx ON questionreopening USING btree (reopener);

CREATE INDEX questionsubscription__subscriber__idx ON questionsubscription USING btree (person);

CREATE INDEX requestedcds_request_architecture_idx ON requestedcds USING btree (request, architecture);

CREATE INDEX revision_owner_idx ON revision USING btree ("owner");

CREATE INDEX scriptactivity__name__date_started__idx ON scriptactivity USING btree (name, date_started);

CREATE INDEX securebinarypackagepublishinghistory__archive__status__idx ON securebinarypackagepublishinghistory USING btree (archive, status);

CREATE INDEX securebinarypackagepublishinghistory_binarypackagerelease_idx ON securebinarypackagepublishinghistory USING btree (binarypackagerelease);

CREATE INDEX securebinarypackagepublishinghistory_component_idx ON securebinarypackagepublishinghistory USING btree (component);

CREATE INDEX securebinarypackagepublishinghistory_distroarchrelease_idx ON securebinarypackagepublishinghistory USING btree (distroarchrelease);

CREATE INDEX securebinarypackagepublishinghistory_pocket_idx ON securebinarypackagepublishinghistory USING btree (pocket);

CREATE INDEX securebinarypackagepublishinghistory_section_idx ON securebinarypackagepublishinghistory USING btree (section);

CREATE INDEX securebinarypackagepublishinghistory_status_idx ON securebinarypackagepublishinghistory USING btree (status);

CREATE INDEX securesourcepackagepublishinghistory__archive__status__idx ON securesourcepackagepublishinghistory USING btree (archive, status);

CREATE INDEX securesourcepackagepublishinghistory_component_idx ON securesourcepackagepublishinghistory USING btree (component);

CREATE INDEX securesourcepackagepublishinghistory_distrorelease_idx ON securesourcepackagepublishinghistory USING btree (distrorelease);

CREATE INDEX securesourcepackagepublishinghistory_pocket_idx ON securesourcepackagepublishinghistory USING btree (pocket);

CREATE INDEX securesourcepackagepublishinghistory_section_idx ON securesourcepackagepublishinghistory USING btree (section);

CREATE INDEX securesourcepackagepublishinghistory_sourcepackagerelease_idx ON securesourcepackagepublishinghistory USING btree (sourcepackagerelease);

CREATE INDEX securesourcepackagepublishinghistory_status_idx ON securesourcepackagepublishinghistory USING btree (status);

CREATE INDEX shipment_shippingrun_idx ON shipment USING btree (shippingrun);

CREATE INDEX shippingrequest__daterequested__approved__idx ON shippingrequest USING btree (daterequested) WHERE (status = 1);

CREATE INDEX shippingrequest__daterequested__unapproved__idx ON shippingrequest USING btree (daterequested) WHERE (status = 0);

CREATE INDEX shippingrequest__normalized_address__idx ON shippingrequest USING btree (normalized_address);

CREATE INDEX shippingrequest__recipientdisplayname__idx ON shippingrequest USING btree (recipientdisplayname);

CREATE INDEX shippingrequest__whocancelled__idx ON shippingrequest USING btree (whocancelled) WHERE (whocancelled IS NOT NULL);

CREATE INDEX shippingrequest_daterequested_idx ON shippingrequest USING btree (daterequested);

ALTER TABLE shippingrequest CLUSTER ON shippingrequest_daterequested_idx;

CREATE INDEX shippingrequest_fti ON shippingrequest USING gist (fti ts2.gist_tsvector_ops);

CREATE INDEX shippingrequest_highpriority_idx ON shippingrequest USING btree (highpriority);

CREATE UNIQUE INDEX shippingrequest_one_outstanding_request_unique ON shippingrequest USING btree (recipient) WHERE (((shipment IS NULL) AND ((status <> 3) AND (status <> 2))) AND (recipient <> 243601));

CREATE INDEX shippingrequest_recipient_idx ON shippingrequest USING btree (recipient);

CREATE INDEX shippingrequest_whoapproved_idx ON shippingrequest USING btree (whoapproved);

CREATE INDEX signedcodeofconduct_owner_idx ON signedcodeofconduct USING btree ("owner");

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

CREATE INDEX specification_owner_idx ON specification USING btree ("owner");

CREATE INDEX specificationbranch__specification__idx ON specificationbranch USING btree (specification);

CREATE INDEX specificationbug_bug_idx ON specificationbug USING btree (bug);

CREATE INDEX specificationbug_specification_idx ON specificationbug USING btree (specification);

CREATE INDEX specificationdependency_dependency_idx ON specificationdependency USING btree (dependency);

CREATE INDEX specificationdependency_specification_idx ON specificationdependency USING btree (specification);

CREATE INDEX specificationfeedback_requester_idx ON specificationfeedback USING btree (requester);

CREATE INDEX specificationfeedback_reviewer_idx ON specificationfeedback USING btree (reviewer);

CREATE UNIQUE INDEX specificationmessage__specification__message__idx ON specificationmessage USING btree (specification, message);

CREATE INDEX specificationsubscription_specification_idx ON specificationsubscription USING btree (specification);

CREATE INDEX specificationsubscription_subscriber_idx ON specificationsubscription USING btree (person);

CREATE INDEX sprint__driver__idx ON sprint USING btree (driver);

CREATE INDEX sprint__icon__idx ON sprint USING btree (icon) WHERE (icon IS NOT NULL);

CREATE INDEX sprint__logo__idx ON sprint USING btree (logo) WHERE (logo IS NOT NULL);

CREATE INDEX sprint__mugshot__idx ON sprint USING btree (mugshot) WHERE (mugshot IS NOT NULL);

CREATE INDEX sprint_datecreated_idx ON sprint USING btree (datecreated);

CREATE INDEX sprintattendance_sprint_idx ON sprintattendance USING btree (sprint);

CREATE INDEX sprintspec_sprint_idx ON sprintspecification USING btree (sprint);

CREATE INDEX sprintspecification__decider__idx ON sprintspecification USING btree (decider);

CREATE INDEX sprintspecification__registrant__idx ON sprintspecification USING btree (registrant);

CREATE INDEX sshkey_person_key ON sshkey USING btree (person);

CREATE INDEX teamparticipation_person_idx ON teamparticipation USING btree (person);

ALTER TABLE teamparticipation CLUSTER ON teamparticipation_person_idx;

CREATE INDEX translationimportqueueentry__content__idx ON translationimportqueueentry USING btree (content) WHERE (content IS NOT NULL);

CREATE UNIQUE INDEX translationimportqueueentry__entry_per_importer__unq ON translationimportqueueentry USING btree (importer, path, (COALESCE(potemplate, -1)), (COALESCE(distrorelease, -1)), (COALESCE(sourcepackagename, -1)), (COALESCE(productseries, -1)));

CREATE UNIQUE INDEX translationimportqueueentry__status__dateimported__id__idx ON translationimportqueueentry USING btree (status, dateimported, id);

CREATE INDEX votecast_poll_idx ON votecast USING btree (poll);

CREATE INDEX wikiname_person_idx ON wikiname USING btree (person);

CREATE RULE delete_rule AS ON DELETE TO revisionnumber DO INSTEAD DELETE FROM branchrevision WHERE (branchrevision.id = old.id);

CREATE RULE insert_rule AS ON INSERT TO revisionnumber DO INSTEAD INSERT INTO branchrevision (id, "sequence", branch, revision) VALUES (new.id, new."sequence", new.branch, new.revision);

CREATE RULE update_rule AS ON UPDATE TO revisionnumber DO INSTEAD UPDATE branchrevision SET id = new.id, "sequence" = new."sequence", branch = new.branch, revision = new.revision WHERE (branchrevision.id = old.id);

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

CREATE TRIGGER mv_pofiletranslator_pomsgset
    BEFORE DELETE OR UPDATE ON pomsgset
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pofiletranslator_pomsgset();

ALTER TABLE pomsgset DISABLE TRIGGER mv_pofiletranslator_pomsgset;

CREATE TRIGGER mv_pofiletranslator_posubmission
    AFTER INSERT OR DELETE OR UPDATE ON posubmission
    FOR EACH ROW
    EXECUTE PROCEDURE mv_pofiletranslator_posubmission();

CREATE TRIGGER mv_validpersonorteamcache_emailaddress_t
    AFTER INSERT OR DELETE OR UPDATE ON emailaddress
    FOR EACH ROW
    EXECUTE PROCEDURE mv_validpersonorteamcache_emailaddress();

CREATE TRIGGER mv_validpersonorteamcache_person_t
    AFTER INSERT OR UPDATE ON person
    FOR EACH ROW
    EXECUTE PROCEDURE mv_validpersonorteamcache_person();

CREATE TRIGGER set_date_last_message_t
    AFTER INSERT OR DELETE OR UPDATE ON bugmessage
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_date_last_message();

CREATE TRIGGER set_normalized_address
    BEFORE INSERT OR UPDATE ON shippingrequest
    FOR EACH ROW
    EXECUTE PROCEDURE set_shipit_normalized_address();

CREATE TRIGGER set_openid_identifier_t
    BEFORE INSERT ON person
    FOR EACH ROW
    EXECUTE PROCEDURE set_openid_identifier();

CREATE TRIGGER temp_t_set_openid_identifier
    BEFORE UPDATE ON person
    FOR EACH ROW
    EXECUTE PROCEDURE set_openid_identifier();

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
    BEFORE INSERT OR UPDATE ON distroreleasepackagecache
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

CREATE TRIGGER you_are_your_own_member
    AFTER INSERT ON person
    FOR EACH ROW
    EXECUTE PROCEDURE you_are_your_own_member();

ALTER TABLE ONLY processor
    ADD CONSTRAINT "$1" FOREIGN KEY (family) REFERENCES processorfamily(id);

ALTER TABLE ONLY builder
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES processor(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY libraryfilealias
    ADD CONSTRAINT "$1" FOREIGN KEY (content) REFERENCES libraryfilecontent(id);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (productrelease) REFERENCES productrelease(id);

ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY build
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES processor(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$1" FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$1" FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES bug(id);

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY sshkey
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY pushmirroraccess
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT "$1" FOREIGN KEY (build) REFERENCES build(id);

ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT "$1" FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);

ALTER TABLE ONLY polloption
    ADD CONSTRAINT "$1" FOREIGN KEY (poll) REFERENCES poll(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT "$1" FOREIGN KEY (bugcontact) REFERENCES person(id);

ALTER TABLE ONLY shipitreport
    ADD CONSTRAINT "$1" FOREIGN KEY (csvfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY country
    ADD CONSTRAINT "$1" FOREIGN KEY (continent) REFERENCES continent(id);

ALTER TABLE ONLY packagebugcontact
    ADD CONSTRAINT "$1" FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT "$1" FOREIGN KEY (content) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY builder
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$2" FOREIGN KEY (processorfamily) REFERENCES processorfamily(id);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY build
    ADD CONSTRAINT "$2" FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$2" FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY ("object") REFERENCES bug(id);

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$2" FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$2" FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT "$2" FOREIGN KEY (builder) REFERENCES builder(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$2" FOREIGN KEY (members) REFERENCES person(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$2" FOREIGN KEY (exportfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT "$2" FOREIGN KEY (chroot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packagebugcontact
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT "$2" FOREIGN KEY (importer) REFERENCES person(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$2" FOREIGN KEY (from_sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$3" FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY build
    ADD CONSTRAINT "$3" FOREIGN KEY (buildlog) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$3" FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$3" FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$3" FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT "$3" FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$3" FOREIGN KEY (bugcontact) REFERENCES person(id);

ALTER TABLE ONLY packagebugcontact
    ADD CONSTRAINT "$3" FOREIGN KEY (bugcontact) REFERENCES person(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT "$3" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$3" FOREIGN KEY (from_sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY build
    ADD CONSTRAINT "$4" FOREIGN KEY (builder) REFERENCES builder(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$4" FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$4" FOREIGN KEY (potranslation) REFERENCES potranslation(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT "$4" FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$5" FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$5" FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT "$5" FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY build
    ADD CONSTRAINT "$6" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT "$6" FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY translationimportqueueentry
    ADD CONSTRAINT "$7" FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY karma
    ADD CONSTRAINT action_fkey FOREIGN KEY ("action") REFERENCES karmaaction(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__distribution__fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__person__fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__product__fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY answercontact
    ADD CONSTRAINT answercontact__sourcepackagename__fkey FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY archive
    ADD CONSTRAINT archive__distribution__fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY archive
    ADD CONSTRAINT archive__owner__fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_binarypackagerelease_fk FOREIGN KEY (binarypackagerelease) REFERENCES binarypackagerelease(id);

ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_libraryfile_fk FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_build_fk FOREIGN KEY (build) REFERENCES build(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_section_fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_claimant_fk FOREIGN KEY (claimant) REFERENCES person(id);

ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

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
    ADD CONSTRAINT branch_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_dependent_branch_fkey FOREIGN KEY (dependent_branch) REFERENCES branch(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merge_reporter_fkey FOREIGN KEY (merge_reporter) REFERENCES person(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_source_branch_fkey FOREIGN KEY (source_branch) REFERENCES branch(id);

ALTER TABLE ONLY branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_target_branch_fkey FOREIGN KEY (target_branch) REFERENCES branch(id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT branchrevision_branch_fk FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY branchrevision
    ADD CONSTRAINT branchrevision_revision_fk FOREIGN KEY (revision) REFERENCES revision(id);

ALTER TABLE ONLY branchsubscription
    ADD CONSTRAINT branchsubscription_branch_fk FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY branchsubscription
    ADD CONSTRAINT branchsubscription_person_fk FOREIGN KEY (person) REFERENCES person(id);

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
    ADD CONSTRAINT bug_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

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

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugcve
    ADD CONSTRAINT bugcve_cve_fk FOREIGN KEY (cve) REFERENCES cve(id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_bugwatch_fkey FOREIGN KEY (bugwatch) REFERENCES bugwatch(id);

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_message_fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__bug__fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__decider__fk FOREIGN KEY (decider) REFERENCES person(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__distrorelease__fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__owner__fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY bugnomination
    ADD CONSTRAINT bugnomination__productseries__fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugnotification
    ADD CONSTRAINT bugnotification_message_fkey FOREIGN KEY (message) REFERENCES message(id);

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

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_bugwatch_fk FOREIGN KEY (bugwatch, bug) REFERENCES bugwatch(id, bug);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_distribution_milestone_fk FOREIGN KEY (distribution, milestone) REFERENCES milestone(distribution, id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_person_fk FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_product_milestone_fk FOREIGN KEY (product, milestone) REFERENCES milestone(product, id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT bugtracker_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bugtracker_fk FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY build
    ADD CONSTRAINT build__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY calendarevent
    ADD CONSTRAINT calendarevent_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);

ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_object_fk FOREIGN KEY ("object") REFERENCES calendar(id);

ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_subject_fk FOREIGN KEY (subject) REFERENCES calendar(id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_assignee_fkey FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_branch_fkey FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE ONLY codeimport
    ADD CONSTRAINT codeimport_owner_fkey FOREIGN KEY ("owner") REFERENCES person(id);

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

ALTER TABLE ONLY cvereference
    ADD CONSTRAINT cvereference_cve_fk FOREIGN KEY (cve) REFERENCES cve(id);

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
    ADD CONSTRAINT distribution_translation_focus_fkey FOREIGN KEY (translation_focus) REFERENCES distrorelease(id);

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
    ADD CONSTRAINT distributionmirror_owner_fkey FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distrocomponentuploader
    ADD CONSTRAINT distrocomponentuploader_uploader_fk FOREIGN KEY (uploader) REFERENCES person(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_nominatedarchindep_fk FOREIGN KEY (nominatedarchindep) REFERENCES distroarchrelease(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_parentrelease_fk FOREIGN KEY (parentrelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY distroreleaselanguage
    ADD CONSTRAINT distroreleaselanguage_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY distroreleaselanguage
    ADD CONSTRAINT distroreleaselanguage_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY distroreleasepackagecache
    ADD CONSTRAINT distroreleasepackagecache_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY distroreleasepackagecache
    ADD CONSTRAINT distroreleasepackagecache_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distroseries__language_pack_base__fk FOREIGN KEY (language_pack_base) REFERENCES languagepack(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distroseries__language_pack_delta__fk FOREIGN KEY (language_pack_delta) REFERENCES languagepack(id);

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distroseries__language_pack_proposed__fk FOREIGN KEY (language_pack_proposed) REFERENCES languagepack(id);

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES person(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY entitlement
    ADD CONSTRAINT entitlement_registrant_fkey FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_last_updated_by_fkey FOREIGN KEY (last_updated_by) REFERENCES person(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_owner_fkey FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY faq
    ADD CONSTRAINT faq_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES distroarchrelease(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__owned__fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__raw_submission__fk FOREIGN KEY (raw_submission) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY hwsubmission
    ADD CONSTRAINT hwsubmission__system_fingerprint__fk FOREIGN KEY (system_fingerprint) REFERENCES hwsystemfingerprint(id);

ALTER TABLE ONLY ircid
    ADD CONSTRAINT ircid_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_person_fk FOREIGN KEY (person) REFERENCES person(id);

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
    ADD CONSTRAINT languagepackage__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distrorelease(id);

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
    ADD CONSTRAINT mailinglistsubscription__person__email_address__fk FOREIGN KEY (person, email_address) REFERENCES emailaddress(person, id) ON UPDATE CASCADE;

ALTER TABLE ONLY mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_mailing_list_fkey FOREIGN KEY (mailing_list) REFERENCES mailinglist(id);

ALTER TABLE ONLY mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_bug_fkey FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_owner_fkey FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_specification_fkey FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY mentoringoffer
    ADD CONSTRAINT mentoringoffer_team_fkey FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_parent_fk FOREIGN KEY (parent) REFERENCES message(id);

ALTER TABLE ONLY message
    ADD CONSTRAINT message_raw_fk FOREIGN KEY (raw) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_disposed_by_fkey FOREIGN KEY (disposed_by) REFERENCES person(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_mailing_list_fkey FOREIGN KEY (mailing_list) REFERENCES mailinglist(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_posted_by_fkey FOREIGN KEY (posted_by) REFERENCES person(id);

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_posted_message_fkey FOREIGN KEY (posted_message) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_blob_fk FOREIGN KEY (blob) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_message_fk FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_distribution_release_fk FOREIGN KEY (distribution, distrorelease) REFERENCES distrorelease(distribution, id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_fk FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_series_fk FOREIGN KEY (product, productseries) REFERENCES productseries(product, id);

ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_country_fk FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY mirrorcdimagedistrorelease
    ADD CONSTRAINT mirrorcdimagedistrorelease_distribution_mirror_fkey FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrorcdimagedistrorelease
    ADD CONSTRAINT mirrorcdimagedistrorelease_distrorelease_fkey FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_distroarchrelease_fk FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);

ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_mirror_fk FOREIGN KEY (mirror) REFERENCES mirror(id);

ALTER TABLE ONLY mirrordistroarchrelease
    ADD CONSTRAINT mirrordistroarchrelease__component__fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrordistroarchrelease
    ADD CONSTRAINT mirrordistroarchrelease_distribution_mirror_fkey FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrordistroarchrelease
    ADD CONSTRAINT mirrordistroarchrelease_distro_arch_release_fkey FOREIGN KEY (distro_arch_release) REFERENCES distroarchrelease(id);

ALTER TABLE ONLY mirrordistroreleasesource
    ADD CONSTRAINT mirrordistroreleasesource__component__fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrordistroreleasesource
    ADD CONSTRAINT mirrordistroreleasesource_distribution_mirror_fkey FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrordistroreleasesource
    ADD CONSTRAINT mirrordistroreleasesource_distro_release_fkey FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_distribution_mirror_fkey FOREIGN KEY (distribution_mirror) REFERENCES distributionmirror(id);

ALTER TABLE ONLY mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_log_file_fkey FOREIGN KEY (log_file) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_mirror_fk FOREIGN KEY (mirror) REFERENCES mirror(id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_product_fkey FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE ONLY officialbugtag
    ADD CONSTRAINT officialbugtag_project_fkey FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY openidauthorization
    ADD CONSTRAINT openidauthorization_person_fkey FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY openidrpconfig
    ADD CONSTRAINT openidrpconfig__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__changesfile__fk FOREIGN KEY (changesfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__distrorelease__fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY packageupload
    ADD CONSTRAINT packageupload__signing_key__fk FOREIGN KEY (signing_key) REFERENCES gpgkey(id);

ALTER TABLE ONLY packageuploadbuild
    ADD CONSTRAINT packageuploadbuild_build_fk FOREIGN KEY (build) REFERENCES build(id);

ALTER TABLE ONLY packageuploadbuild
    ADD CONSTRAINT packageuploadbuild_packageupload_fk FOREIGN KEY (packageupload) REFERENCES packageupload(id);

ALTER TABLE ONLY packageuploadcustom
    ADD CONSTRAINT packageuploadcustom_libraryfilealias_fk FOREIGN KEY (libraryfilealias) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY packageuploadcustom
    ADD CONSTRAINT packageuploadcustom_packageupload_fk FOREIGN KEY (packageupload) REFERENCES packageupload(id);

ALTER TABLE ONLY packageuploadsource
    ADD CONSTRAINT packageuploadsource__packageupload__fk FOREIGN KEY (packageupload) REFERENCES packageupload(id);

ALTER TABLE ONLY packageuploadsource
    ADD CONSTRAINT packageuploadsource__sourcepackagerelease__fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__icon__fk FOREIGN KEY (icon) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person__mugshot__fk FOREIGN KEY (mugshot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_country_fk FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY karmacache
    ADD CONSTRAINT person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_merged_fk FOREIGN KEY (merged) REFERENCES person(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_registrant_fk FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_teamowner_fk FOREIGN KEY (teamowner) REFERENCES person(id);

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT personpofile__latest_posubmission__fk FOREIGN KEY (latest_posubmission) REFERENCES posubmission(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_distribution_fkey FOREIGN KEY (distribution) REFERENCES distribution(id) ON DELETE CASCADE;

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_product_fkey FOREIGN KEY (product) REFERENCES product(id) ON DELETE CASCADE;

ALTER TABLE ONLY pillarname
    ADD CONSTRAINT pillarname_project_fkey FOREIGN KEY (project) REFERENCES project(id) ON DELETE CASCADE;

ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poeportrequest_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_pofile_fk FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_last_touched_pomsgset_fkey FOREIGN KEY (last_touched_pomsgset) REFERENCES pomsgset(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_lasttranslator_fk FOREIGN KEY (lasttranslator) REFERENCES person(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_license_fk FOREIGN KEY (license) REFERENCES license(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT pofiletranslator__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY pofiletranslator
    ADD CONSTRAINT pofiletranslator__pofile__fk FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY poll
    ADD CONSTRAINT poll_team_fk FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_potmsgset_fk FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset__person__fk FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset__pofile__fk FOREIGN KEY (pofile) REFERENCES pofile(id);

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset__potmsgset__fk FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_language_fkey FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__person__fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__pomsgset__fk FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);

ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission__potranslation__fk FOREIGN KEY (potranslation) REFERENCES potranslation(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate__source_file__fk FOREIGN KEY (source_file) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_license_fk FOREIGN KEY (license) REFERENCES license(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_potemplatename_fk FOREIGN KEY (potemplatename) REFERENCES potemplatename(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);

ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_primemsgid_fk FOREIGN KEY (primemsgid) REFERENCES pomsgid(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__development_focus__fk FOREIGN KEY (development_focus) REFERENCES productseries(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__icon__fk FOREIGN KEY (icon) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__logo__fk FOREIGN KEY (logo) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product__mugshot__fk FOREIGN KEY (mugshot) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_bugtracker_fkey FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY product
    ADD CONSTRAINT product_project_fk FOREIGN KEY (project) REFERENCES project(id);

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

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT productreleasefile__uploader__fk FOREIGN KEY (uploader) REFERENCES person(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries__import_branch__fk FOREIGN KEY (import_branch) REFERENCES branch(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries__user_branch__fk FOREIGN KEY (user_branch) REFERENCES branch(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_fk FOREIGN KEY (product) REFERENCES product(id);

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
    ADD CONSTRAINT project_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_driver_fk FOREIGN KEY (driver) REFERENCES person(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY project
    ADD CONSTRAINT project_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);

ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);

ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_project_fk FOREIGN KEY (project) REFERENCES project(id);

ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT projectrelationship_object_fk FOREIGN KEY ("object") REFERENCES project(id);

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
    ADD CONSTRAINT question__language__fkey FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY question
    ADD CONSTRAINT question__owner__fk FOREIGN KEY ("owner") REFERENCES person(id);

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
    ADD CONSTRAINT reviewer_fk FOREIGN KEY (reviewer) REFERENCES person(id);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision_gpgkey_fk FOREIGN KEY (gpgkey) REFERENCES gpgkey(id);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY revision
    ADD CONSTRAINT revision_revision_author_fk FOREIGN KEY (revision_author) REFERENCES revisionauthor(id);

ALTER TABLE ONLY revisionparent
    ADD CONSTRAINT revisionparent_revision_fk FOREIGN KEY (revision) REFERENCES revision(id);

ALTER TABLE ONLY revisionproperty
    ADD CONSTRAINT revisionproperty__revision__fk FOREIGN KEY (revision) REFERENCES revision(id);

ALTER TABLE ONLY securebinarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY securebinarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_binarypackagerelease_fk FOREIGN KEY (binarypackagerelease) REFERENCES binarypackagerelease(id);

ALTER TABLE ONLY securebinarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY securebinarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_distroarchrelease_fk FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);

ALTER TABLE ONLY securebinarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY securebinarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES build(id);

ALTER TABLE ONLY securesourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY securesourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY securesourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);

ALTER TABLE ONLY securesourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY securesourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_sourcepackagerelease_fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY securesourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES sourcepackagerelease(id);

ALTER TABLE ONLY shipment
    ADD CONSTRAINT shipment_shippingrun_fk FOREIGN KEY (shippingrun) REFERENCES shippingrun(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest__country__fk FOREIGN KEY (country) REFERENCES country(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_recipient_fk FOREIGN KEY (recipient) REFERENCES person(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_shipment_fk FOREIGN KEY (shipment) REFERENCES shipment(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_shockandawe_fk FOREIGN KEY (shockandawe) REFERENCES shockandawe(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_whoapproved_fk FOREIGN KEY (whoapproved) REFERENCES person(id);

ALTER TABLE ONLY shippingrequest
    ADD CONSTRAINT shippingrequest_whocancelled_fk FOREIGN KEY (whocancelled) REFERENCES person(id);

ALTER TABLE ONLY shippingrun
    ADD CONSTRAINT shippingrun_csvfile_fk FOREIGN KEY (csvfile) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_signingkey_fk FOREIGN KEY ("owner", signingkey) REFERENCES gpgkey("owner", id) ON UPDATE CASCADE;

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__creator__fk FOREIGN KEY (creator) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__dscsigningkey FOREIGN KEY (dscsigningkey) REFERENCES gpgkey(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__upload_archive__fk FOREIGN KEY (upload_archive) REFERENCES archive(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_component_fk FOREIGN KEY (component) REFERENCES component(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_maintainer_fk FOREIGN KEY (maintainer) REFERENCES person(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_section FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_uploaddistrorelease_fk FOREIGN KEY (uploaddistrorelease) REFERENCES distrorelease(id);

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
    ADD CONSTRAINT specification_distrorelease_valid FOREIGN KEY (distribution, distrorelease) REFERENCES distrorelease(distribution, id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_drafter_fk FOREIGN KEY (drafter) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_goal_decider_fkey FOREIGN KEY (goal_decider) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_goal_proposer_fkey FOREIGN KEY (goal_proposer) REFERENCES person(id);

ALTER TABLE ONLY specification
    ADD CONSTRAINT specification_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

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
    ADD CONSTRAINT sprint_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

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

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT teammembership_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY teammembership
    ADD CONSTRAINT teammembership_team_fk FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_team_fk FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_file_alias_fkey FOREIGN KEY (file_alias) REFERENCES libraryfilealias(id);

ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_person_fk FOREIGN KEY (translator) REFERENCES person(id);

ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);

ALTER TABLE ONLY validpersonorteamcache
    ADD CONSTRAINT validpersonorteamcache_id_fkey FOREIGN KEY (id) REFERENCES person(id) ON DELETE CASCADE;

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_poll_fk FOREIGN KEY (poll) REFERENCES poll(id);

ALTER TABLE ONLY vote
    ADD CONSTRAINT vote_poll_option_fk FOREIGN KEY (poll, "option") REFERENCES polloption(poll, id);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_person_fk FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY votecast
    ADD CONSTRAINT votecast_poll_fk FOREIGN KEY (poll) REFERENCES poll(id);

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_person_fk FOREIGN KEY (person) REFERENCES person(id);


