SET client_min_messages = ERROR;

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET search_path = public, pg_catalog;

/*
CREATE FUNCTION plpython_call_handler() RETURNS language_handler
    AS '$libdir/plpython', 'plpython_call_handler'
    LANGUAGE c;



CREATE PROCEDURAL LANGUAGE plpythonu HANDLER plpython_call_handler;
*/


CREATE TABLE person (
    id serial NOT NULL,
    displayname text,
    givenname text,
    familyname text,
    "password" text,
    teamowner integer,
    teamdescription text,
    karma integer DEFAULT 0 NOT NULL,
    karmatimestamp timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    name text NOT NULL,
    "language" integer,
    CONSTRAINT no_loops CHECK ((id <> teamowner)),
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE emailaddress (
    id serial NOT NULL,
    email text NOT NULL,
    person integer NOT NULL,
    status integer NOT NULL
);



CREATE TABLE gpgkey (
    id serial NOT NULL,
    person integer NOT NULL,
    keyid text NOT NULL,
    fingerprint text NOT NULL,
    pubkey text NOT NULL,
    revoked boolean NOT NULL,
    algorithm integer NOT NULL,
    keysize integer NOT NULL
);



CREATE TABLE archuserid (
    id serial NOT NULL,
    person integer NOT NULL,
    archuserid text NOT NULL
);



CREATE TABLE wikiname (
    id serial NOT NULL,
    person integer NOT NULL,
    wiki text NOT NULL,
    wikiname text NOT NULL
);



CREATE TABLE jabberid (
    id serial NOT NULL,
    person integer NOT NULL,
    jabberid text NOT NULL
);



CREATE TABLE ircid (
    id serial NOT NULL,
    person integer NOT NULL,
    network text NOT NULL,
    nickname text NOT NULL
);



CREATE TABLE membership (
    id serial NOT NULL,
    person integer NOT NULL,
    team integer NOT NULL,
    role integer NOT NULL,
    status integer NOT NULL
);



CREATE TABLE teamparticipation (
    id serial NOT NULL,
    team integer NOT NULL,
    person integer NOT NULL
);



CREATE TABLE "schema" (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL,
    extensible boolean DEFAULT false NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE label (
    id serial NOT NULL,
    "schema" integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE personlabel (
    person integer NOT NULL,
    label integer NOT NULL
);



CREATE TABLE project (
    id serial NOT NULL,
    "owner" integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    title text NOT NULL,
    shortdesc text NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    homepageurl text,
    wikiurl text,
    lastdoap text,
    sourceforgeproject text,
    freshmeatproject text,
    reviewed boolean DEFAULT false NOT NULL,
    active boolean DEFAULT true NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE projectrelationship (
    id serial NOT NULL,
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);



CREATE TABLE projectrole (
    id serial NOT NULL,
    person integer NOT NULL,
    role integer NOT NULL,
    project integer NOT NULL
);



CREATE TABLE product (
    id serial NOT NULL,
    project integer NOT NULL,
    "owner" integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    title text NOT NULL,
    shortdesc text NOT NULL,
    description text NOT NULL,
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
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE productlabel (
    id serial NOT NULL,
    product integer NOT NULL,
    label integer NOT NULL
);



CREATE TABLE productrole (
    id serial NOT NULL,
    person integer NOT NULL,
    role integer NOT NULL,
    product integer NOT NULL
);



CREATE TABLE productseries (
    id serial NOT NULL,
    product integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    shortdesc text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE productrelease (
    id serial NOT NULL,
    product integer NOT NULL,
    datereleased timestamp without time zone NOT NULL,
    "version" text NOT NULL,
    title text,
    description text,
    changelog text,
    "owner" integer NOT NULL,
    shortdesc text,
    productseries integer,
    CONSTRAINT valid_version CHECK (valid_version("version"))
);



CREATE TABLE productcvsmodule (
    id serial NOT NULL,
    product integer NOT NULL,
    anonroot text NOT NULL,
    module text NOT NULL,
    weburl text
);



CREATE TABLE productbkbranch (
    id serial NOT NULL,
    product integer NOT NULL,
    locationurl text NOT NULL,
    weburl text
);



CREATE TABLE productsvnmodule (
    id serial NOT NULL,
    product integer NOT NULL,
    locationurl text NOT NULL,
    weburl text
);



CREATE TABLE archarchive (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    visible boolean NOT NULL,
    "owner" integer
);



CREATE TABLE archarchivelocation (
    id serial NOT NULL,
    archive integer NOT NULL,
    archivetype integer NOT NULL,
    url text NOT NULL,
    gpgsigned boolean NOT NULL
);



CREATE TABLE archarchivelocationsigner (
    archarchivelocation integer NOT NULL,
    gpgkey integer NOT NULL
);



CREATE TABLE archnamespace (
    id serial NOT NULL,
    archarchive integer NOT NULL,
    category text NOT NULL,
    branch text,
    "version" text,
    visible boolean NOT NULL
);



CREATE TABLE branch (
    id serial NOT NULL,
    archnamespace integer NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer,
    product integer
);



CREATE TABLE changeset (
    id serial NOT NULL,
    branch integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    name text NOT NULL,
    logmessage text NOT NULL,
    archid integer,
    gpgkey integer
);



CREATE TABLE changesetfilename (
    id serial NOT NULL,
    filename text NOT NULL
);



CREATE TABLE changesetfile (
    id serial NOT NULL,
    changeset integer NOT NULL,
    changesetfilename integer NOT NULL,
    filecontents bytea NOT NULL,
    filesize integer NOT NULL
);



CREATE TABLE changesetfilehash (
    id serial NOT NULL,
    changesetfile integer NOT NULL,
    hashalg integer NOT NULL,
    hash bytea NOT NULL
);



CREATE TABLE branchrelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);



CREATE TABLE branchlabel (
    branch integer NOT NULL,
    label integer NOT NULL
);



CREATE TABLE productbranchrelationship (
    id serial NOT NULL,
    product integer NOT NULL,
    branch integer NOT NULL,
    label integer NOT NULL
);



CREATE TABLE manifest (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE manifestentry (
    id serial NOT NULL,
    manifest integer NOT NULL,
    "sequence" integer NOT NULL,
    branch integer NOT NULL,
    changeset integer,
    entrytype integer NOT NULL,
    "path" text NOT NULL,
    patchon integer,
    dirname text,
    CONSTRAINT "$1" CHECK (("sequence" > 0)),
    CONSTRAINT "$2" CHECK ((patchon <> "sequence"))
);



CREATE TABLE archconfig (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    productrelease integer,
    "owner" integer
);



CREATE TABLE archconfigentry (
    archconfig integer NOT NULL,
    "path" text NOT NULL,
    branch integer NOT NULL,
    changeset integer
);



CREATE TABLE processorfamily (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE processor (
    id serial NOT NULL,
    family integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE builder (
    id serial NOT NULL,
    processor integer NOT NULL,
    fqdn text NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE component (
    id serial NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE section (
    id serial NOT NULL,
    name text NOT NULL
);



CREATE TABLE distribution (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    domainname text NOT NULL,
    "owner" integer NOT NULL,
    lucilleconfig text,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE distributionrole (
    person integer NOT NULL,
    distribution integer NOT NULL,
    role integer NOT NULL,
    id integer DEFAULT nextval('DistributionRole_id_seq'::text) NOT NULL
);



CREATE TABLE distrorelease (
    id serial NOT NULL,
    distribution integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "version" text NOT NULL,
    components integer NOT NULL,
    sections integer NOT NULL,
    releasestate integer NOT NULL,
    datereleased timestamp without time zone,
    parentrelease integer,
    "owner" integer NOT NULL,
    lucilleconfig text,
    shortdesc text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_version CHECK (valid_version("version"))
);



CREATE TABLE distroreleaserole (
    person integer NOT NULL,
    distrorelease integer NOT NULL,
    role integer NOT NULL,
    id integer DEFAULT nextval('DistroreleaseRole_id_seq'::text) NOT NULL
);



CREATE TABLE distroarchrelease (
    id serial NOT NULL,
    distrorelease integer NOT NULL,
    processorfamily integer NOT NULL,
    architecturetag text NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE libraryfilecontent (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datemirrored timestamp without time zone,
    filesize integer NOT NULL,
    sha1 character(40) NOT NULL
);



CREATE TABLE libraryfilealias (
    id serial NOT NULL,
    content integer NOT NULL,
    filename text NOT NULL,
    mimetype text NOT NULL
);



CREATE TABLE productreleasefile (
    productrelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL
);



CREATE TABLE sourcepackagename (
    id serial NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE sourcepackage (
    id serial NOT NULL,
    maintainer integer NOT NULL,
    shortdesc text NOT NULL,
    description text NOT NULL,
    manifest integer,
    distro integer,
    sourcepackagename integer NOT NULL,
    srcpackageformat integer NOT NULL
);



CREATE TABLE sourcepackagerelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL,
    CONSTRAINT "$1" CHECK ((subject <> object))
);



CREATE TABLE sourcepackagelabel (
    sourcepackage integer NOT NULL,
    label integer NOT NULL
);



CREATE TABLE packaging (
    sourcepackage integer NOT NULL,
    packaging integer NOT NULL,
    product integer NOT NULL
);



CREATE TABLE sourcepackagerelease (
    id serial NOT NULL,
    sourcepackage integer NOT NULL,
    creator integer NOT NULL,
    "version" text NOT NULL,
    dateuploaded timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    urgency integer NOT NULL,
    dscsigningkey integer,
    component integer,
    changelog text,
    builddepends text,
    builddependsindep text,
    architecturehintlist text,
    dsc text,
    section integer NOT NULL,
    CONSTRAINT valid_version CHECK (valid_version("version"))
);



CREATE TABLE sourcepackagereleasefile (
    sourcepackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval('sourcepackagereleasefile_id_seq'::text) NOT NULL
);



CREATE TABLE sourcepackagepublishing (
    distrorelease integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    status integer NOT NULL,
    id integer DEFAULT nextval('sourcepackagepublishing_id_seq'::text) NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    datepublished timestamp without time zone,
    scheduleddeletiondate timestamp without time zone
);



CREATE TABLE build (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    processor integer NOT NULL,
    distroarchrelease integer NOT NULL,
    buildstate integer NOT NULL,
    datebuilt timestamp without time zone,
    buildduration interval,
    buildlog integer,
    builder integer,
    gpgsigningkey integer,
    changes text,
    sourcepackagerelease integer NOT NULL
);



CREATE TABLE binarypackagename (
    id serial NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE binarypackage (
    id serial NOT NULL,
    binarypackagename integer NOT NULL,
    "version" text NOT NULL,
    shortdesc text NOT NULL,
    description text NOT NULL,
    build integer NOT NULL,
    binpackageformat integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer,
    shlibdeps text,
    depends text,
    recommends text,
    suggests text,
    conflicts text,
    replaces text,
    provides text,
    essential boolean,
    installedsize integer,
    copyright text,
    licence text,
    architecturespecific boolean NOT NULL,
    CONSTRAINT valid_version CHECK (valid_version("version"))
);



CREATE TABLE binarypackagefile (
    binarypackage integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval('binarypackagefile_id_seq'::text) NOT NULL
);



CREATE TABLE packagepublishing (
    id serial NOT NULL,
    binarypackage integer NOT NULL,
    distroarchrelease integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer NOT NULL,
    scheduleddeletiondate timestamp without time zone,
    status integer NOT NULL
);



CREATE TABLE packageselection (
    id serial NOT NULL,
    distrorelease integer NOT NULL,
    sourcepackagename integer,
    binarypackagename integer,
    "action" integer NOT NULL,
    component integer,
    section integer,
    priority integer
);



CREATE TABLE coderelease (
    id serial NOT NULL,
    productrelease integer,
    sourcepackagerelease integer,
    manifest integer,
    CONSTRAINT either_or CHECK (((productrelease IS NULL) <> (sourcepackagerelease IS NULL)))
);



CREATE TABLE codereleaserelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL,
    CONSTRAINT no_loops CHECK ((subject <> object))
);



CREATE TABLE osfile (
    id serial NOT NULL,
    "path" text NOT NULL
);



CREATE TABLE osfileinpackage (
    osfile integer NOT NULL,
    binarypackage integer NOT NULL,
    unixperms integer NOT NULL,
    conffile boolean NOT NULL,
    createdoninstall boolean NOT NULL
);



CREATE TABLE pomsgid (
    id serial NOT NULL,
    msgid text NOT NULL
);



CREATE TABLE potranslation (
    id serial NOT NULL,
    translation text NOT NULL
);



CREATE TABLE "language" (
    id serial NOT NULL,
    code text NOT NULL,
    englishname text,
    nativename text,
    pluralforms integer,
    pluralexpression text,
    CONSTRAINT "$1" CHECK ((((pluralforms IS NOT NULL) AND (pluralexpression IS NOT NULL)) OR ((pluralforms IS NULL) AND (pluralexpression IS NULL))))
);



CREATE TABLE country (
    id serial NOT NULL,
    iso3166code2 character(2) NOT NULL,
    iso3166code3 character(3) NOT NULL,
    name text NOT NULL,
    title text,
    description text
);



CREATE TABLE spokenin (
    "language" integer NOT NULL,
    country integer NOT NULL
);



CREATE TABLE license (
    id serial NOT NULL,
    legalese text NOT NULL
);



CREATE TABLE potemplate (
    id serial NOT NULL,
    product integer NOT NULL,
    priority integer NOT NULL,
    branch integer NOT NULL,
    changeset integer,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    copyright text NOT NULL,
    license integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "path" text NOT NULL,
    iscurrent boolean NOT NULL,
    messagecount integer NOT NULL,
    "owner" integer,
    rawfile text,
    rawimporter integer,
    daterawimport timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    rawimportstatus integer,
    CONSTRAINT potemplate_rawimportstatus_valid CHECK ((((rawfile IS NULL) AND (rawimportstatus <> 0)) OR ((rawfile IS NOT NULL) AND (rawimportstatus IS NOT NULL)))),
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE pofile (
    id serial NOT NULL,
    potemplate integer NOT NULL,
    "language" integer NOT NULL,
    title text,
    description text,
    topcomment text,
    header text,
    fuzzyheader boolean NOT NULL,
    lasttranslator integer,
    license integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    lastparsed timestamp without time zone,
    "owner" integer,
    pluralforms integer NOT NULL,
    variant text,
    filename text,
    rawfile text,
    rawimporter integer,
    daterawimport timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    rawimportstatus integer,
    CONSTRAINT potemplate_rawimportstatus_valid CHECK ((((rawfile IS NULL) AND (rawimportstatus <> 0)) OR ((rawfile IS NOT NULL) AND (rawimportstatus IS NOT NULL))))
);



CREATE TABLE pomsgset (
    id serial NOT NULL,
    "sequence" integer NOT NULL,
    pofile integer NOT NULL,
    iscomplete boolean NOT NULL,
    obsolete boolean NOT NULL,
    fuzzy boolean NOT NULL,
    commenttext text,
    potmsgset integer NOT NULL
);



CREATE TABLE pomsgidsighting (
    id serial NOT NULL,
    potmsgset integer NOT NULL,
    pomsgid integer NOT NULL,
    datefirstseen timestamp without time zone NOT NULL,
    datelastseen timestamp without time zone NOT NULL,
    inlastrevision boolean NOT NULL,
    pluralform integer NOT NULL
);



CREATE TABLE potranslationsighting (
    id serial NOT NULL,
    pomsgset integer NOT NULL,
    potranslation integer NOT NULL,
    license integer NOT NULL,
    datefirstseen timestamp without time zone NOT NULL,
    datelastactive timestamp without time zone NOT NULL,
    inlastrevision boolean NOT NULL,
    pluralform integer NOT NULL,
    active boolean DEFAULT true NOT NULL,
    origin integer NOT NULL,
    person integer,
    CONSTRAINT "$1" CHECK ((pluralform >= 0))
);



CREATE TABLE pocomment (
    id serial NOT NULL,
    potemplate integer NOT NULL,
    pomsgid integer,
    "language" integer,
    potranslation integer,
    commenttext text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer
);



CREATE TABLE translationeffort (
    id serial NOT NULL,
    "owner" integer NOT NULL,
    project integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    shortdesc text NOT NULL,
    description text NOT NULL,
    categories integer,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE translationeffortpotemplate (
    translationeffort integer NOT NULL,
    potemplate integer NOT NULL,
    priority integer NOT NULL,
    category integer
);



CREATE TABLE posubscription (
    id serial NOT NULL,
    person integer NOT NULL,
    potemplate integer NOT NULL,
    "language" integer,
    notificationinterval interval,
    lastnotified timestamp without time zone
);



CREATE TABLE bug (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    name text,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL,
    duplicateof integer,
    communityscore integer DEFAULT 0 NOT NULL,
    communitytimestamp timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    activityscore integer DEFAULT 0 NOT NULL,
    activitytimestamp timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    hits integer DEFAULT 0 NOT NULL,
    hitstimestamp timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    shortdesc text NOT NULL,
    CONSTRAINT notduplicateofself CHECK ((NOT (id = duplicateof))),
    CONSTRAINT valid_bug_name CHECK (valid_bug_name(name))
);



CREATE TABLE bugsubscription (
    id serial NOT NULL,
    person integer NOT NULL,
    bug integer NOT NULL,
    subscription integer NOT NULL
);



CREATE TABLE sourcepackagebugassignment (
    id serial NOT NULL,
    bug integer NOT NULL,
    sourcepackage integer NOT NULL,
    bugstatus integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    binarypackagename integer,
    assignee integer,
    dateassigned timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE productbugassignment (
    id serial NOT NULL,
    bug integer NOT NULL,
    product integer NOT NULL,
    bugstatus integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    assignee integer,
    dateassigned timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE bugactivity (
    id serial NOT NULL,
    bug integer NOT NULL,
    datechanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    whatchanged text NOT NULL,
    oldvalue text NOT NULL,
    newvalue text NOT NULL,
    message text
);



CREATE TABLE bugexternalref (
    id serial NOT NULL,
    bug integer NOT NULL,
    url text NOT NULL,
    title text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE bugtrackertype (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    homepage text,
    "owner" integer NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE bugtracker (
    id serial NOT NULL,
    bugtrackertype integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    shortdesc text NOT NULL,
    baseurl text NOT NULL,
    "owner" integer NOT NULL,
    contactdetails text,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE bugwatch (
    id serial NOT NULL,
    bug integer NOT NULL,
    bugtracker integer NOT NULL,
    remotebug text NOT NULL,
    remotestatus text,
    lastchanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    lastchecked timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE projectbugtracker (
    project integer NOT NULL,
    bugtracker integer NOT NULL,
    id integer DEFAULT nextval('projectbugtracker_id_seq'::text) NOT NULL
);



CREATE TABLE buglabel (
    bug integer NOT NULL,
    label integer NOT NULL
);



CREATE TABLE bugrelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);



CREATE TABLE message (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    title text NOT NULL,
    contents text NOT NULL,
    "owner" integer,
    parent integer,
    distribution integer,
    rfc822msgid text NOT NULL
);



CREATE TABLE bugattachment (
    id serial NOT NULL,
    bugmessage integer NOT NULL,
    name text,
    description text,
    libraryfile integer NOT NULL,
    datedeactivated timestamp without time zone,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE sourcesource (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    product integer NOT NULL,
    cvsroot text,
    cvsmodule text,
    cvstarfile integer,
    cvstarfileurl text,
    cvsbranch text,
    svnrepository text,
    releaseroot text,
    releaseverstyle integer,
    releasefileglob text,
    releaseparentbranch integer,
    sourcepackage integer,
    branch integer,
    lastsynced timestamp without time zone,
    syncinterval interval,
    rcstype integer NOT NULL,
    hosted text,
    upstreamname text,
    processingapproved timestamp without time zone,
    syncingapproved timestamp without time zone,
    newarchive text,
    newbranchcategory text,
    newbranchbranch text,
    newbranchversion text,
    packagedistro text,
    packagefiles_collapsed text,
    "owner" integer NOT NULL,
    currentgpgkey text,
    fileidreference text,
    branchpoint text,
    autotested integer DEFAULT 0 NOT NULL,
    datestarted timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    datefinished timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
);



CREATE SEQUENCE projectbugtracker_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE SEQUENCE distributionrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE SEQUENCE distroreleaserole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE TABLE componentselection (
    id serial NOT NULL,
    distrorelease integer NOT NULL,
    component integer NOT NULL
);



CREATE TABLE sectionselection (
    id serial NOT NULL,
    distrorelease integer NOT NULL,
    section integer NOT NULL
);


/*
CREATE FUNCTION valid_name(text) RETURNS boolean
    AS '
    import re
    name = args[0]
    pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
    if name is None or re.match(pat, name):
        return True
    return False
'
    LANGUAGE plpythonu;



CREATE FUNCTION valid_bug_name(text) RETURNS boolean
    AS '
    import re
    name = args[0]
    pat = r"^[a-z][a-z0-9\\+\\.\\-]+$"
    if name is None or re.match(pat, name):
        return True
    return False
'
    LANGUAGE plpythonu;
*/


CREATE SEQUENCE sourcepackagepublishing_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE TABLE bugproductinfestation (
    id serial NOT NULL,
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



CREATE TABLE bugpackageinfestation (
    id serial NOT NULL,
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



CREATE TABLE distroreleasequeue (
    id serial NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    distrorelease integer NOT NULL
);



CREATE TABLE distroreleasequeuesource (
    id serial NOT NULL,
    distroreleasequeue integer NOT NULL,
    sourcepackagerelease integer NOT NULL
);



CREATE TABLE distroreleasequeuebuild (
    id serial NOT NULL,
    distroreleasequeue integer NOT NULL,
    build integer NOT NULL
);



CREATE SEQUENCE sourcepackagereleasefile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE SEQUENCE binarypackagefile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE TABLE personlanguage (
    id serial NOT NULL,
    person integer NOT NULL,
    "language" integer NOT NULL
);



CREATE TABLE potmsgset (
    id serial NOT NULL,
    primemsgid integer NOT NULL,
    "sequence" integer NOT NULL,
    potemplate integer NOT NULL,
    commenttext text,
    filereferences text,
    sourcecomment text,
    flagscomment text
);



CREATE TABLE launchpaddatabaserevision (
    major integer,
    minor integer,
    patch integer
);


/*
CREATE FUNCTION valid_version(text) RETURNS boolean
    AS '
    import re
    name = args[0]
    pat = r"^[A-Za-z0-9\\+:\\.\\-]+$"
    if name is None or re.match(pat, name):
        return True
    return False
'
    LANGUAGE plpythonu;
*/


CREATE VIEW vsourcepackageindistro AS
    SELECT DISTINCT sourcepackage.id, sourcepackage.shortdesc, sourcepackage.description, sourcepackage.distro, sourcepackage.manifest, sourcepackage.maintainer, sourcepackagename.id AS sourcepackagename, sourcepackagename.name, distrorelease.id AS distrorelease FROM sourcepackagepublishing, sourcepackagerelease, sourcepackage, distrorelease, sourcepackagename WHERE ((((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id) AND (sourcepackagerelease.sourcepackage = sourcepackage.id)) AND (sourcepackagepublishing.distrorelease = distrorelease.id)) AND (sourcepackage.sourcepackagename = sourcepackagename.id)) ORDER BY sourcepackage.id, sourcepackage.shortdesc, sourcepackage.description, sourcepackage.distro, sourcepackage.manifest, sourcepackage.maintainer, sourcepackagename.id, sourcepackagename.name, distrorelease.id;



CREATE VIEW vsourcepackagereleasepublishing AS
    SELECT sourcepackagerelease.id, sourcepackagename.name, sourcepackage.shortdesc, sourcepackage.maintainer, sourcepackage.description, sourcepackage.id AS sourcepackage, sourcepackagepublishing.status AS publishingstatus, sourcepackagepublishing.datepublished, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, distrorelease.id AS distrorelease, component.name AS componentname FROM sourcepackagepublishing, sourcepackagerelease, component, sourcepackage, distrorelease, sourcepackagename WHERE (((((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id) AND (sourcepackagerelease.sourcepackage = sourcepackage.id)) AND (sourcepackagepublishing.distrorelease = distrorelease.id)) AND (sourcepackage.sourcepackagename = sourcepackagename.id)) AND (component.id = sourcepackagerelease.component));



CREATE TABLE bounty (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    usdvalue numeric(10,2) NOT NULL,
    difficulty integer NOT NULL,
    duration interval NOT NULL,
    reviewer integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    "owner" integer NOT NULL,
    deadline timestamp without time zone,
    claimant integer,
    dateclaimed timestamp without time zone
);



CREATE TABLE bugmessage (
    id serial NOT NULL,
    bug integer NOT NULL,
    message integer NOT NULL
);



CREATE VIEW sourcepackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishing.id)::text) AS id, distrorelease.distribution, sourcepackagepublishing.id AS sourcepackagepublishing, sourcepackagereleasefile.libraryfile AS libraryfilealias, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, distrorelease.name AS distroreleasename, sourcepackagepublishing.status AS publishingstatus FROM sourcepackagepublishing, sourcepackagerelease, sourcepackagereleasefile, libraryfilealias, distrorelease, sourcepackage, sourcepackagename, component WHERE (((((((sourcepackagepublishing.distrorelease = distrorelease.id) AND (sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id)) AND (sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id)) AND (libraryfilealias.id = sourcepackagereleasefile.libraryfile)) AND (sourcepackagerelease.sourcepackage = sourcepackage.id)) AND (sourcepackagename.id = sourcepackage.sourcepackagename)) AND (component.id = sourcepackagepublishing.component));



CREATE VIEW binarypackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (packagepublishing.id)::text) AS id, distrorelease.distribution, packagepublishing.id AS packagepublishing, component.name AS componentname, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, binarypackagefile.libraryfile AS libraryfilealias, distrorelease.name AS distroreleasename, distroarchrelease.architecturetag, packagepublishing.status AS publishingstatus FROM packagepublishing, sourcepackage, sourcepackagerelease, sourcepackagename, build, binarypackage, binarypackagefile, libraryfilealias, distroarchrelease, distrorelease, component WHERE ((((((((((distrorelease.id = distroarchrelease.distrorelease) AND (packagepublishing.distroarchrelease = distroarchrelease.id)) AND (packagepublishing.binarypackage = binarypackage.id)) AND (binarypackagefile.binarypackage = binarypackage.id)) AND (binarypackagefile.libraryfile = libraryfilealias.id)) AND (binarypackage.build = build.id)) AND (build.sourcepackagerelease = sourcepackagerelease.id)) AND (sourcepackagerelease.sourcepackage = sourcepackage.id)) AND (component.id = packagepublishing.component)) AND (sourcepackagename.id = sourcepackage.sourcepackagename));



CREATE VIEW sourcepackagepublishingview AS
    SELECT sourcepackagepublishing.id, distrorelease.name AS distroreleasename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, section.name AS sectionname, distrorelease.distribution, sourcepackagepublishing.status AS publishingstatus FROM sourcepackagepublishing, distrorelease, sourcepackagerelease, sourcepackage, sourcepackagename, component, section WHERE ((((((sourcepackagepublishing.distrorelease = distrorelease.id) AND (sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id)) AND (sourcepackagerelease.sourcepackage = sourcepackage.id)) AND (sourcepackage.sourcepackagename = sourcepackagename.id)) AND (sourcepackagepublishing.component = component.id)) AND (sourcepackagepublishing.section = section.id));



CREATE VIEW binarypackagepublishingview AS
    SELECT packagepublishing.id, distrorelease.name AS distroreleasename, binarypackagename.name AS binarypackagename, component.name AS componentname, section.name AS sectionname, packagepublishing.priority, distrorelease.distribution, packagepublishing.status AS publishingstatus FROM packagepublishing, distrorelease, distroarchrelease, binarypackage, binarypackagename, component, section WHERE ((((((packagepublishing.distroarchrelease = distroarchrelease.id) AND (distroarchrelease.distrorelease = distrorelease.id)) AND (packagepublishing.binarypackage = binarypackage.id)) AND (binarypackage.binarypackagename = binarypackagename.id)) AND (packagepublishing.component = component.id)) AND (packagepublishing.section = section.id));



CREATE TABLE cveref (
    id serial NOT NULL,
    bug integer NOT NULL,
    cveref text NOT NULL,
    title text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    "owner" integer NOT NULL
);



CREATE INDEX idx_libraryfilecontent_sha1 ON libraryfilecontent USING btree (sha1);



CREATE UNIQUE INDEX idx_emailaddress_email ON emailaddress USING btree (lower(email));



CREATE INDEX pomsgidsighting_pomsgset_idx ON pomsgidsighting USING btree (potmsgset);



CREATE INDEX pomsgidsighting_pomsgid_idx ON pomsgidsighting USING btree (pomsgid);



CREATE INDEX pomsgidsighting_inlastrevision_idx ON pomsgidsighting USING btree (inlastrevision);



CREATE INDEX pomsgidsighting_pluralform_idx ON pomsgidsighting USING btree (pluralform);



CREATE INDEX pomsgset_index_pofile ON pomsgset USING btree (pofile);



CREATE UNIQUE INDEX person_name_key ON person USING btree (name);



CREATE UNIQUE INDEX schema_name_key ON "schema" USING btree (name);



CREATE INDEX packagepublishing_binarypackage_key ON packagepublishing USING btree (binarypackage);



CREATE INDEX binarypackage_binarypackagename_key2 ON binarypackage USING btree (binarypackagename);



CREATE INDEX sourcepackageupload_sourcepackagerelease_key ON sourcepackagepublishing USING btree (sourcepackagerelease);



CREATE INDEX sourcepackagerelease_sourcepackage_key ON sourcepackagerelease USING btree (sourcepackage);



CREATE INDEX sourcepackage_sourcepackagename_key ON sourcepackage USING btree (sourcepackagename);



CREATE UNIQUE INDEX bugtracker_name_key ON bugtracker USING btree (name);



CREATE INDEX distroreleasequeue_distrorelease_key ON distroreleasequeue USING btree (distrorelease);



CREATE INDEX sourcepackage_maintainer_key ON sourcepackage USING btree (maintainer);



CREATE INDEX sourcepackagepublishing_distrorelease_key ON sourcepackagepublishing USING btree (distrorelease);



CREATE INDEX sourcepackagepublishing_status_key ON sourcepackagepublishing USING btree (status);



CREATE INDEX productbugassignment_owner_idx ON productbugassignment USING btree ("owner");



CREATE INDEX sourcepackagebugassignment_owner_idx ON sourcepackagebugassignment USING btree ("owner");



ALTER TABLE ONLY person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);



ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress_pkey PRIMARY KEY (id);



ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_pkey PRIMARY KEY (id);



ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_fingerprint_key UNIQUE (fingerprint);



ALTER TABLE ONLY archuserid
    ADD CONSTRAINT archuserid_pkey PRIMARY KEY (id);



ALTER TABLE ONLY archuserid
    ADD CONSTRAINT archuserid_archuserid_key UNIQUE (archuserid);



ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_pkey PRIMARY KEY (id);



ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_wiki_key UNIQUE (wiki, wikiname);



ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_pkey PRIMARY KEY (id);



ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_jabberid_key UNIQUE (jabberid);



ALTER TABLE ONLY ircid
    ADD CONSTRAINT ircid_pkey PRIMARY KEY (id);



ALTER TABLE ONLY membership
    ADD CONSTRAINT membership_pkey PRIMARY KEY (id);



ALTER TABLE ONLY membership
    ADD CONSTRAINT membership_person_key UNIQUE (person, team);



ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_pkey PRIMARY KEY (id);



ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_team_key UNIQUE (team, person);



ALTER TABLE ONLY "schema"
    ADD CONSTRAINT schema_pkey PRIMARY KEY (id);



ALTER TABLE ONLY label
    ADD CONSTRAINT label_pkey PRIMARY KEY (id);



ALTER TABLE ONLY project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);



ALTER TABLE ONLY project
    ADD CONSTRAINT project_name_key UNIQUE (name);



ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT projectrelationship_pkey PRIMARY KEY (id);



ALTER TABLE ONLY projectrole
    ADD CONSTRAINT projectrole_pkey PRIMARY KEY (id);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_project_key UNIQUE (project, name);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_id_key UNIQUE (id, project);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT productlabel_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT productlabel_product_key UNIQUE (product, label);



ALTER TABLE ONLY productrole
    ADD CONSTRAINT productrole_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_key UNIQUE (product, name);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_product_key UNIQUE (product, "version");



ALTER TABLE ONLY productcvsmodule
    ADD CONSTRAINT productcvsmodule_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productbkbranch
    ADD CONSTRAINT productbkbranch_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT productsvnmodule_pkey PRIMARY KEY (id);



ALTER TABLE ONLY archarchive
    ADD CONSTRAINT archarchive_pkey PRIMARY KEY (id);



ALTER TABLE ONLY archarchivelocation
    ADD CONSTRAINT archarchivelocation_pkey PRIMARY KEY (id);



ALTER TABLE ONLY archnamespace
    ADD CONSTRAINT archnamespace_pkey PRIMARY KEY (id);



ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_pkey PRIMARY KEY (id);



ALTER TABLE ONLY changeset
    ADD CONSTRAINT changeset_pkey PRIMARY KEY (id);



ALTER TABLE ONLY changeset
    ADD CONSTRAINT changeset_id_key UNIQUE (id, branch);



ALTER TABLE ONLY changesetfilename
    ADD CONSTRAINT changesetfilename_pkey PRIMARY KEY (id);



ALTER TABLE ONLY changesetfilename
    ADD CONSTRAINT changesetfilename_filename_key UNIQUE (filename);



ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT changesetfile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT changesetfile_changeset_key UNIQUE (changeset, changesetfilename);



ALTER TABLE ONLY changesetfilehash
    ADD CONSTRAINT changesetfilehash_pkey PRIMARY KEY (id);



ALTER TABLE ONLY changesetfilehash
    ADD CONSTRAINT changesetfilehash_changesetfile_key UNIQUE (changesetfile, hashalg);



ALTER TABLE ONLY branchrelationship
    ADD CONSTRAINT branchrelationship_pkey PRIMARY KEY (subject, object);



ALTER TABLE ONLY productbranchrelationship
    ADD CONSTRAINT productbranchrelationship_pkey PRIMARY KEY (id);



ALTER TABLE ONLY manifest
    ADD CONSTRAINT manifest_pkey PRIMARY KEY (id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT manifestentry_pkey PRIMARY KEY (id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT manifestentry_manifest_key UNIQUE (manifest, "sequence");



ALTER TABLE ONLY archconfig
    ADD CONSTRAINT archconfig_pkey PRIMARY KEY (id);



ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_pkey PRIMARY KEY (id);



ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_name_key UNIQUE (name);



ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_pkey PRIMARY KEY (id);



ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_name_key UNIQUE (name);



ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_pkey PRIMARY KEY (id);



ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_fqdn_key UNIQUE (fqdn, name);



ALTER TABLE ONLY component
    ADD CONSTRAINT component_pkey PRIMARY KEY (id);



ALTER TABLE ONLY component
    ADD CONSTRAINT component_name_key UNIQUE (name);



ALTER TABLE ONLY section
    ADD CONSTRAINT section_pkey PRIMARY KEY (id);



ALTER TABLE ONLY section
    ADD CONSTRAINT section_name_key UNIQUE (name);



ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT distroarchrelease_pkey PRIMARY KEY (id);



ALTER TABLE ONLY libraryfilecontent
    ADD CONSTRAINT libraryfilecontent_pkey PRIMARY KEY (id);



ALTER TABLE ONLY libraryfilealias
    ADD CONSTRAINT libraryfilealias_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_name_key UNIQUE (name);



ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT sourcepackage_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcepackagerelationship
    ADD CONSTRAINT sourcepackagerelationship_pkey PRIMARY KEY (subject, object);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_pkey PRIMARY KEY (id);



ALTER TABLE ONLY build
    ADD CONSTRAINT build_pkey PRIMARY KEY (id);



ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_pkey PRIMARY KEY (id);



ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_name_key UNIQUE (name);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_pkey PRIMARY KEY (id);



ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT packagepublishing_pkey PRIMARY KEY (id);



ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection_pkey PRIMARY KEY (id);



ALTER TABLE ONLY coderelease
    ADD CONSTRAINT coderelease_pkey PRIMARY KEY (id);



ALTER TABLE ONLY codereleaserelationship
    ADD CONSTRAINT codereleaserelationship_pkey PRIMARY KEY (subject, object);



ALTER TABLE ONLY osfile
    ADD CONSTRAINT osfile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY osfile
    ADD CONSTRAINT osfile_path_key UNIQUE ("path");



ALTER TABLE ONLY pomsgid
    ADD CONSTRAINT pomsgid_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pomsgid
    ADD CONSTRAINT pomsgid_msgid_key UNIQUE (msgid);



ALTER TABLE ONLY potranslation
    ADD CONSTRAINT potranslation_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potranslation
    ADD CONSTRAINT potranslation_translation_key UNIQUE (translation);



ALTER TABLE ONLY "language"
    ADD CONSTRAINT language_pkey PRIMARY KEY (id);



ALTER TABLE ONLY "language"
    ADD CONSTRAINT language_code_key UNIQUE (code);



ALTER TABLE ONLY country
    ADD CONSTRAINT country_pkey PRIMARY KEY (id);



ALTER TABLE ONLY spokenin
    ADD CONSTRAINT spokenin_pkey PRIMARY KEY ("language", country);



ALTER TABLE ONLY license
    ADD CONSTRAINT license_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_product_key UNIQUE (product, name);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_id_key UNIQUE (id, potemplate);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT potranslationsighting_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pocomment
    ADD CONSTRAINT pocomment_pkey PRIMARY KEY (id);



ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT translationeffort_pkey PRIMARY KEY (id);



ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT translationeffort_name_key UNIQUE (name);



ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT translationeffortpotemplate_translationeffort_key UNIQUE (translationeffort, potemplate);



ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_pkey PRIMARY KEY (id);



ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_person_key UNIQUE (person, potemplate, "language");



ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT bugsubscription_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT sourcepackagebugassignment_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT sourcepackagebugassignment_bug_key UNIQUE (bug, sourcepackage);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT productbugassignment_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT productbugassignment_bug_key UNIQUE (bug, product);



ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT bugactivity_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT bugexternalref_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugtrackertype
    ADD CONSTRAINT bugsystemtype_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugtrackertype
    ADD CONSTRAINT bugsystemtype_name_key UNIQUE (name);



ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT bugsystem_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_pkey PRIMARY KEY (id);



ALTER TABLE ONLY buglabel
    ADD CONSTRAINT buglabel_pkey PRIMARY KEY (bug, label);



ALTER TABLE ONLY message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT sourcesource_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT sourcesource_branch_key UNIQUE (branch);



ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT projectbugsystem_pkey PRIMARY KEY (id);



ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT projectbugsystem_project_key UNIQUE (project, bugtracker);



ALTER TABLE ONLY message
    ADD CONSTRAINT bugmessage_rfc822msgid_key UNIQUE (rfc822msgid);



ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT potranslationsighting_pomsgset_key UNIQUE (pomsgset, potranslation, license, person, pluralform);



ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_name_key UNIQUE (name);



ALTER TABLE ONLY distributionrole
    ADD CONSTRAINT distributionrole_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distroreleaserole
    ADD CONSTRAINT distroreleaserole_pkey PRIMARY KEY (id);



ALTER TABLE ONLY componentselection
    ADD CONSTRAINT componentselection_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT sectionselection_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_name_key UNIQUE (name);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_distribution_key UNIQUE (distribution, name);



ALTER TABLE ONLY label
    ADD CONSTRAINT label_schema_key UNIQUE ("schema", name);



ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_bug_key UNIQUE (bug, productrelease);



ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_bug_key UNIQUE (bug, sourcepackagerelease);



ALTER TABLE ONLY distroreleasequeue
    ADD CONSTRAINT distroreleasequeue_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distroreleasequeuesource
    ADD CONSTRAINT distroreleasequeuesource_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distroreleasequeuebuild
    ADD CONSTRAINT distroreleasequeuebuild_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcepackagepublishing
    ADD CONSTRAINT sourcepackagepublishing_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT sourcepackagereleasefile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_pkey PRIMARY KEY (id);



ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_person_key UNIQUE (person, "language");



ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_potemplate_key UNIQUE (potemplate, primemsgid);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pofile_key UNIQUE (pofile, potmsgset);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_name_key UNIQUE (name);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_bug_key UNIQUE (bug, message);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_binarypackagename_key UNIQUE (binarypackagename, build, "version");



ALTER TABLE ONLY cveref
    ADD CONSTRAINT cveref_pkey PRIMARY KEY (id);



ALTER TABLE ONLY person
    ADD CONSTRAINT "$1" FOREIGN KEY (teamowner) REFERENCES person(id);



ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY archuserid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY wikiname
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY jabberid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY ircid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY membership
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY membership
    ADD CONSTRAINT "$2" FOREIGN KEY (team) REFERENCES person(id);



ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT "$1" FOREIGN KEY (team) REFERENCES person(id);



ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT "$2" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY "schema"
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY label
    ADD CONSTRAINT "$1" FOREIGN KEY ("schema") REFERENCES "schema"(id);



ALTER TABLE ONLY personlabel
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY personlabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);



ALTER TABLE ONLY project
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES project(id);



ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES project(id);



ALTER TABLE ONLY projectrole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY projectrole
    ADD CONSTRAINT "$2" FOREIGN KEY (project) REFERENCES project(id);



ALTER TABLE ONLY product
    ADD CONSTRAINT "$1" FOREIGN KEY (project) REFERENCES project(id);



ALTER TABLE ONLY product
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);



ALTER TABLE ONLY productrole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY productrole
    ADD CONSTRAINT "$2" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY productcvsmodule
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productbkbranch
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY archarchive
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY archarchivelocation
    ADD CONSTRAINT "$1" FOREIGN KEY (archive) REFERENCES archarchive(id);



ALTER TABLE ONLY archarchivelocationsigner
    ADD CONSTRAINT "$1" FOREIGN KEY (archarchivelocation) REFERENCES archarchivelocation(id);



ALTER TABLE ONLY archarchivelocationsigner
    ADD CONSTRAINT "$2" FOREIGN KEY (gpgkey) REFERENCES gpgkey(id);



ALTER TABLE ONLY archnamespace
    ADD CONSTRAINT "$1" FOREIGN KEY (archarchive) REFERENCES archarchive(id);



ALTER TABLE ONLY branch
    ADD CONSTRAINT "$1" FOREIGN KEY (archnamespace) REFERENCES archnamespace(id);



ALTER TABLE ONLY branch
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY branch
    ADD CONSTRAINT "$3" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY changeset
    ADD CONSTRAINT "$1" FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY changeset
    ADD CONSTRAINT "$2" FOREIGN KEY (archid) REFERENCES archuserid(id);



ALTER TABLE ONLY changeset
    ADD CONSTRAINT "$3" FOREIGN KEY (gpgkey) REFERENCES gpgkey(id);



ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT "$1" FOREIGN KEY (changeset) REFERENCES changeset(id);



ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT "$2" FOREIGN KEY (changesetfilename) REFERENCES changesetfilename(id);



ALTER TABLE ONLY changesetfilehash
    ADD CONSTRAINT "$1" FOREIGN KEY (changesetfile) REFERENCES changesetfile(id);



ALTER TABLE ONLY branchrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES branch(id);



ALTER TABLE ONLY branchrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES branch(id);



ALTER TABLE ONLY branchlabel
    ADD CONSTRAINT "$1" FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY branchlabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);



ALTER TABLE ONLY productbranchrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productbranchrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY manifest
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$3" FOREIGN KEY (manifest) REFERENCES manifest(id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$4" FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$5" FOREIGN KEY (changeset) REFERENCES changeset(id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$6" FOREIGN KEY (branch, changeset) REFERENCES changeset(branch, id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$7" FOREIGN KEY (manifest, patchon) REFERENCES manifestentry(manifest, "sequence");



ALTER TABLE ONLY archconfig
    ADD CONSTRAINT "$1" FOREIGN KEY (productrelease) REFERENCES productrelease(id);



ALTER TABLE ONLY archconfig
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$1" FOREIGN KEY (archconfig) REFERENCES archconfig(id);



ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$2" FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$3" FOREIGN KEY (changeset) REFERENCES changeset(id);



ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$4" FOREIGN KEY (branch, changeset) REFERENCES changeset(branch, id);



ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY processor
    ADD CONSTRAINT "$1" FOREIGN KEY (family) REFERENCES processorfamily(id);



ALTER TABLE ONLY processor
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY builder
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES processor(id);



ALTER TABLE ONLY builder
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY distributionrole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY distributionrole
    ADD CONSTRAINT "$2" FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$1" FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$2" FOREIGN KEY (components) REFERENCES "schema"(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$3" FOREIGN KEY (sections) REFERENCES "schema"(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$4" FOREIGN KEY (parentrelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$5" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY distroreleaserole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY distroreleaserole
    ADD CONSTRAINT "$2" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$2" FOREIGN KEY (processorfamily) REFERENCES processorfamily(id);



ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$3" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY libraryfilealias
    ADD CONSTRAINT "$1" FOREIGN KEY (content) REFERENCES libraryfilecontent(id);



ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (productrelease) REFERENCES productrelease(id);



ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$1" FOREIGN KEY (maintainer) REFERENCES person(id);



ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$2" FOREIGN KEY (manifest) REFERENCES manifest(id);



ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$3" FOREIGN KEY (distro) REFERENCES distribution(id);



ALTER TABLE ONLY sourcepackagerelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (subject) REFERENCES sourcepackage(id);



ALTER TABLE ONLY sourcepackagerelationship
    ADD CONSTRAINT "$3" FOREIGN KEY (object) REFERENCES sourcepackage(id);



ALTER TABLE ONLY sourcepackagelabel
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);



ALTER TABLE ONLY sourcepackagelabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT "$2" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$2" FOREIGN KEY (creator) REFERENCES person(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$3" FOREIGN KEY (dscsigningkey) REFERENCES gpgkey(id);



ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY sourcepackagepublishing
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY sourcepackagepublishing
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY build
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES processor(id);



ALTER TABLE ONLY build
    ADD CONSTRAINT "$2" FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);



ALTER TABLE ONLY build
    ADD CONSTRAINT "$3" FOREIGN KEY (buildlog) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY build
    ADD CONSTRAINT "$4" FOREIGN KEY (builder) REFERENCES builder(id);



ALTER TABLE ONLY build
    ADD CONSTRAINT "$5" FOREIGN KEY (gpgsigningkey) REFERENCES gpgkey(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$2" FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$3" FOREIGN KEY (build) REFERENCES build(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$4" FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$5" FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT "$1" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);



ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$1" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);



ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$2" FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);



ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$3" FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$4" FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);



ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$3" FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);



ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$4" FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$5" FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY coderelease
    ADD CONSTRAINT "$3" FOREIGN KEY (productrelease) REFERENCES productrelease(id);



ALTER TABLE ONLY coderelease
    ADD CONSTRAINT "$4" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY coderelease
    ADD CONSTRAINT "$5" FOREIGN KEY (manifest) REFERENCES manifest(id);



ALTER TABLE ONLY codereleaserelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (subject) REFERENCES coderelease(id);



ALTER TABLE ONLY codereleaserelationship
    ADD CONSTRAINT "$3" FOREIGN KEY (object) REFERENCES coderelease(id);



ALTER TABLE ONLY osfileinpackage
    ADD CONSTRAINT "$1" FOREIGN KEY (osfile) REFERENCES osfile(id);



ALTER TABLE ONLY osfileinpackage
    ADD CONSTRAINT "$2" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);



ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$1" FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$2" FOREIGN KEY (country) REFERENCES country(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$2" FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$3" FOREIGN KEY (changeset) REFERENCES changeset(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$4" FOREIGN KEY (license) REFERENCES license(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$5" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$6" FOREIGN KEY (changeset, branch) REFERENCES changeset(id, branch);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$1" FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$2" FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$3" FOREIGN KEY (lasttranslator) REFERENCES person(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$4" FOREIGN KEY (license) REFERENCES license(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$5" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$3" FOREIGN KEY (pofile) REFERENCES pofile(id);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);



ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);



ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$3" FOREIGN KEY (potranslation) REFERENCES potranslation(id);



ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$4" FOREIGN KEY (license) REFERENCES license(id);



ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$5" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$1" FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);



ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$3" FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$4" FOREIGN KEY (potranslation) REFERENCES potranslation(id);



ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$5" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT "$2" FOREIGN KEY (project) REFERENCES project(id);



ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT "$3" FOREIGN KEY (categories) REFERENCES "schema"(id);



ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT "$1" FOREIGN KEY (translationeffort) REFERENCES translationeffort(id) ON DELETE CASCADE;



ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT "$3" FOREIGN KEY (category) REFERENCES label(id);



ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$3" FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY bug
    ADD CONSTRAINT "$1" FOREIGN KEY (duplicateof) REFERENCES bug(id);



ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugtrackertype
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT "$1" FOREIGN KEY (bugtrackertype) REFERENCES bugtrackertype(id);



ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$2" FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$3" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT "$1" FOREIGN KEY (project) REFERENCES project(id);



ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT "$2" FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);



ALTER TABLE ONLY buglabel
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY buglabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);



ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES bug(id);



ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES bug(id);



ALTER TABLE ONLY message
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY message
    ADD CONSTRAINT "$3" FOREIGN KEY (parent) REFERENCES message(id);



ALTER TABLE ONLY message
    ADD CONSTRAINT "$4" FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT "$1" FOREIGN KEY (bugmessage) REFERENCES message(id);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$2" FOREIGN KEY (cvstarfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$3" FOREIGN KEY (releaseparentbranch) REFERENCES branch(id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$4" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$5" FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$6" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$4" FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);



ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$2" FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$2" FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$3" FOREIGN KEY (assignee) REFERENCES person(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$4" FOREIGN KEY (assignee) REFERENCES person(id);



ALTER TABLE ONLY build
    ADD CONSTRAINT "$6" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$2" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$3" FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);



ALTER TABLE ONLY sourcepackagepublishing
    ADD CONSTRAINT sourcepackagepublishing_component_fk FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY sourcepackagepublishing
    ADD CONSTRAINT sourcepackagepublishing_section_fk FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_productrelease_fk FOREIGN KEY (productrelease) REFERENCES productrelease(id);



ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_creator_fk FOREIGN KEY (creator) REFERENCES person(id);



ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_verifiedby_fk FOREIGN KEY (verifiedby) REFERENCES person(id);



ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_lastmodifiedby_fk FOREIGN KEY (lastmodifiedby) REFERENCES person(id);



ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_sourcepackagerelease_fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_creator_fk FOREIGN KEY (creator) REFERENCES person(id);



ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_verifiedby_fk FOREIGN KEY (verifiedby) REFERENCES person(id);



ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_lastmodifiedby_fk FOREIGN KEY (lastmodifiedby) REFERENCES person(id);



ALTER TABLE ONLY distroreleasequeue
    ADD CONSTRAINT distroreleasequeue_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY distroreleasequeuesource
    ADD CONSTRAINT distroreleasequeuesource_distroreleasequeue_fk FOREIGN KEY (distroreleasequeue) REFERENCES distroreleasequeue(id);



ALTER TABLE ONLY distroreleasequeuesource
    ADD CONSTRAINT distroreleasequeuesource_sourcepackagerelease_fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY distroreleasequeuebuild
    ADD CONSTRAINT distroreleasequeuebuild_distroreleasequeue_fk FOREIGN KEY (distroreleasequeue) REFERENCES distroreleasequeue(id);



ALTER TABLE ONLY distroreleasequeuebuild
    ADD CONSTRAINT distroreleasequeuebuild_build_fk FOREIGN KEY (build) REFERENCES build(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_section FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT "$3" FOREIGN KEY (productseries) REFERENCES productseries(id);



ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_person_fk FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY personlanguage
    ADD CONSTRAINT personlanguage_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_primemsgid_fk FOREIGN KEY (primemsgid) REFERENCES pomsgid(id);



ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_potmsgset_fk FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_potmsgset_fk FOREIGN KEY (potmsgset) REFERENCES potmsgset(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_component_fk FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT "$1" FOREIGN KEY (reviewer) REFERENCES person(id);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT "$3" FOREIGN KEY (claimant) REFERENCES person(id);



ALTER TABLE ONLY person
    ADD CONSTRAINT person_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT productbugassignment_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT sourcepackagebugassignment_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$2" FOREIGN KEY (message) REFERENCES message(id);



ALTER TABLE ONLY cveref
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY cveref
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$7" FOREIGN KEY (rawimporter) REFERENCES person(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$6" FOREIGN KEY (rawimporter) REFERENCES person(id);



COMMENT ON SCHEMA public IS 'Standard public schema';



COMMENT ON COLUMN sourcesource.autotested IS 'This flag gives the results of an automatic attempt to import the revision control repository.';



COMMENT ON COLUMN sourcesource.datestarted IS 'The timestamp of the last time an import or sync was started on this sourcesource.';



COMMENT ON COLUMN sourcesource.datefinished IS 'The timestamp of the last time an import or sync finished on this sourcesource.';



COMMENT ON FUNCTION valid_name(text) IS 'validate a name.

    Names must contain only lowercase letters, numbers, ., & -. They
    must start with an alphanumeric. They are ASCII only. Names are useful 
    for mneumonic identifiers such as nicknames and as URL components.
    This specification is the same as the Debian product naming policy.

    Note that a valid name might be all integers, so there is a possible
    namespace conflict if URL traversal is possible by name as well as id.';



COMMENT ON FUNCTION valid_bug_name(text) IS 'validate a bug name

    As per valid_name, except numeric-only names are not allowed (including
    names that look like floats).';



COMMENT ON FUNCTION valid_version(text) IS 'validate a version number

    Note that this is more flexible that the Debian naming policy,
    as it states ''SHOULD'' rather than ''MUST'', and we have already
    imported packages that don''t match it. Note that versions
    may contain both uppercase and lowercase letters so we can''t use them
    in URLs. Also note that both a product name and a version may contain
    hypens, so we cannot join the product name and the version with a hypen
    to form a unique string (we need to use a space or some other character
    disallowed in the product name spec instead';


