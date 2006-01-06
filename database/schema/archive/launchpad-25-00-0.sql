-- Generated Tue Jul 12 14:11:26 BST 2005
SET client_min_messages=ERROR;

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET search_path = public, pg_catalog;


CREATE TABLE person (
    id serial NOT NULL,
    displayname text NOT NULL,
    givenname text,
    familyname text,
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
    timezone text,
    CONSTRAINT no_loops CHECK ((id <> teamowner)),
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_team_fields CHECK (((teamowner IS NULL) OR ((((givenname IS NULL) AND (familyname IS NULL)) AND ("password" IS NULL)) AND ("language" IS NULL))))
);



CREATE TABLE emailaddress (
    id serial NOT NULL,
    email text NOT NULL,
    person integer NOT NULL,
    status integer NOT NULL
);



CREATE TABLE gpgkey (
    id serial NOT NULL,
    "owner" integer NOT NULL,
    keyid text NOT NULL,
    fingerprint text NOT NULL,
    active boolean NOT NULL,
    algorithm integer NOT NULL,
    keysize integer NOT NULL,
    CONSTRAINT valid_fingerprint CHECK (valid_fingerprint(fingerprint)),
    CONSTRAINT valid_keyid CHECK (valid_keyid(keyid))
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



CREATE TABLE teammembership (
    id serial NOT NULL,
    person integer NOT NULL,
    team integer NOT NULL,
    status integer NOT NULL,
    datejoined timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    dateexpires timestamp without time zone,
    reviewer integer,
    reviewercomment text
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
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE projectrelationship (
    id serial NOT NULL,
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);



CREATE TABLE product (
    id serial NOT NULL,
    project integer,
    "owner" integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
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
    fti ts2.tsvector,
    autoupdate boolean DEFAULT false NOT NULL,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    releaseroot text,
    calendar integer,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE productlabel (
    id serial NOT NULL,
    product integer NOT NULL,
    label integer NOT NULL
);



CREATE TABLE productseries (
    id serial NOT NULL,
    product integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    summary text NOT NULL,
    branch integer,
    importstatus integer,
    datelastsynced timestamp without time zone,
    syncinterval interval,
    rcstype integer,
    cvsroot text,
    cvsmodule text,
    cvsbranch text,
    cvstarfileurl text,
    svnrepository text,
    bkrepository text,
    releaseroot text,
    releasefileglob text,
    releaseverstyle integer,
    targetarcharchive text,
    targetarchcategory text,
    targetarchbranch text,
    targetarchversion text,
    dateautotested timestamp without time zone,
    dateprocessapproved timestamp without time zone,
    datesyncapproved timestamp without time zone,
    datestarted timestamp without time zone,
    datefinished timestamp without time zone,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    CONSTRAINT complete_cvs CHECK ((((cvsroot IS NULL) = (cvsmodule IS NULL)) AND ((cvsroot IS NULL) = (cvsbranch IS NULL)))),
    CONSTRAINT complete_targetarch CHECK (((((targetarcharchive IS NULL) = (targetarchcategory IS NULL)) AND ((targetarcharchive IS NULL) = (targetarchbranch IS NULL))) AND ((targetarcharchive IS NULL) = (targetarchversion IS NULL)))),
    CONSTRAINT no_empty_strings CHECK ((((((((((targetarcharchive <> ''::text) AND (targetarchcategory <> ''::text)) AND (targetarchbranch <> ''::text)) AND (targetarchversion <> ''::text)) AND (cvsroot <> ''::text)) AND (cvsmodule <> ''::text)) AND (cvsbranch <> ''::text)) AND (svnrepository <> ''::text)) AND (bkrepository <> ''::text))),
    CONSTRAINT valid_importseries CHECK (((importstatus IS NULL) OR (rcstype IS NOT NULL))),
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE productrelease (
    id serial NOT NULL,
    datereleased timestamp without time zone NOT NULL,
    "version" text NOT NULL,
    title text,
    description text,
    changelog text,
    "owner" integer NOT NULL,
    summary text,
    productseries integer NOT NULL,
    manifest integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
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
    object integer NOT NULL,
    id integer DEFAULT nextval('branchrelationship_id_seq'::text) NOT NULL
);



CREATE TABLE branchlabel (
    branch integer NOT NULL,
    label integer NOT NULL,
    id integer DEFAULT nextval('branchlabel_id_seq'::text) NOT NULL
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
    uuid text NOT NULL
);



CREATE TABLE manifestentry (
    id serial NOT NULL,
    manifest integer NOT NULL,
    "sequence" integer NOT NULL,
    branch integer,
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
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL,
    speedindex integer,
    builderok boolean NOT NULL,
    failnotes text,
    "trusted" boolean DEFAULT false NOT NULL,
    url text NOT NULL,
    CONSTRAINT valid_absolute_url CHECK (valid_absolute_url(url))
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
    displayname text NOT NULL,
    summary text NOT NULL,
    members integer NOT NULL,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
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
    releasestatus integer NOT NULL,
    datereleased timestamp without time zone,
    parentrelease integer,
    "owner" integer NOT NULL,
    lucilleconfig text,
    summary text NOT NULL,
    displayname text NOT NULL,
    datelastlangpack timestamp without time zone,
    messagecount integer DEFAULT 0 NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_version CHECK (valid_version("version"))
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
    mimetype text NOT NULL,
    expires timestamp without time zone
);



CREATE TABLE productreleasefile (
    productrelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval('productreleasefile_id_seq'::text) NOT NULL
);



CREATE TABLE sourcepackagename (
    id serial NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE packaging (
    packaging integer NOT NULL,
    id integer DEFAULT nextval('packaging_id_seq'::text) NOT NULL,
    sourcepackagename integer,
    distrorelease integer,
    productseries integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer
);



CREATE TABLE sourcepackagerelease (
    id serial NOT NULL,
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
    manifest integer,
    maintainer integer NOT NULL,
    sourcepackagename integer NOT NULL,
    uploaddistrorelease integer NOT NULL,
    format integer NOT NULL,
    CONSTRAINT valid_version CHECK (valid_version("version"))
);



CREATE TABLE sourcepackagereleasefile (
    sourcepackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval('sourcepackagereleasefile_id_seq'::text) NOT NULL
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
    summary text NOT NULL,
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
    fti ts2.tsvector,
    CONSTRAINT valid_version CHECK (valid_version("version"))
);



CREATE TABLE binarypackagefile (
    binarypackage integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval('binarypackagefile_id_seq'::text) NOT NULL
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
    visible boolean NOT NULL,
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
    country integer NOT NULL,
    id integer DEFAULT nextval('spokenin_id_seq'::text) NOT NULL
);



CREATE TABLE license (
    id serial NOT NULL,
    legalese text NOT NULL
);



CREATE TABLE potemplate (
    id serial NOT NULL,
    priority integer,
    description text,
    copyright text,
    license integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "path" text,
    iscurrent boolean NOT NULL,
    messagecount integer NOT NULL,
    "owner" integer NOT NULL,
    rawimporter integer NOT NULL,
    daterawimport timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    rawimportstatus integer DEFAULT 1 NOT NULL,
    sourcepackagename integer,
    distrorelease integer,
    sourcepackageversion text,
    header text,
    potemplatename integer NOT NULL,
    binarypackagename integer,
    languagepack boolean DEFAULT false NOT NULL,
    filename text,
    rawfile integer NOT NULL,
    productseries integer,
    CONSTRAINT valid_link CHECK ((((productseries IS NULL) <> (distrorelease IS NULL)) AND ((distrorelease IS NULL) = (sourcepackagename IS NULL))))
);



CREATE TABLE pofile (
    id serial NOT NULL,
    potemplate integer NOT NULL,
    "language" integer NOT NULL,
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
    "owner" integer NOT NULL,
    pluralforms integer NOT NULL,
    variant text,
    filename text,
    rawimporter integer,
    daterawimport timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    rawimportstatus integer DEFAULT 1 NOT NULL,
    rawfile integer,
    exportfile integer,
    exporttime timestamp without time zone,
    rawfilepublished boolean,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    CONSTRAINT pofile_rawimportstatus_valid CHECK ((((rawfile IS NULL) AND (rawimportstatus <> 2)) OR (rawfile IS NOT NULL))),
    CONSTRAINT valid_variant CHECK ((variant <> ''::text))
);



CREATE TABLE pomsgset (
    id serial NOT NULL,
    "sequence" integer NOT NULL,
    pofile integer NOT NULL,
    iscomplete boolean NOT NULL,
    obsolete boolean NOT NULL,
    isfuzzy boolean NOT NULL,
    commenttext text,
    potmsgset integer NOT NULL,
    publishedfuzzy boolean DEFAULT false NOT NULL,
    publishedcomplete boolean DEFAULT false NOT NULL,
    isupdated boolean DEFAULT false NOT NULL
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
    summary text NOT NULL,
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
    description text,
    "owner" integer NOT NULL,
    duplicateof integer,
    communityscore integer DEFAULT 0 NOT NULL,
    communitytimestamp timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    activityscore integer DEFAULT 0 NOT NULL,
    activitytimestamp timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    hits integer DEFAULT 0 NOT NULL,
    hitstimestamp timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    summary text,
    fti ts2.tsvector,
    private boolean DEFAULT false NOT NULL,
    CONSTRAINT notduplicateofself CHECK ((NOT (id = duplicateof))),
    CONSTRAINT valid_bug_name CHECK (valid_bug_name(name))
);



CREATE TABLE bugsubscription (
    id serial NOT NULL,
    person integer NOT NULL,
    bug integer NOT NULL,
    subscription integer NOT NULL
);



CREATE TABLE bugactivity (
    id serial NOT NULL,
    bug integer NOT NULL,
    datechanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    whatchanged text NOT NULL,
    oldvalue text,
    newvalue text,
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



CREATE TABLE bugtracker (
    id serial NOT NULL,
    bugtrackertype integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
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
    subject text,
    "owner" integer,
    parent integer,
    distribution integer,
    rfc822msgid text NOT NULL,
    fti ts2.tsvector,
    raw integer
);



CREATE TABLE bugattachment (
    id serial NOT NULL,
    message integer NOT NULL,
    name text,
    description text,
    libraryfile integer NOT NULL,
    datedeactivated timestamp without time zone,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE SEQUENCE projectbugtracker_id_seq
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
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE SEQUENCE binarypackagefile_id_seq
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
    major integer NOT NULL,
    minor integer NOT NULL,
    patch integer NOT NULL
);



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



CREATE TABLE cveref (
    id serial NOT NULL,
    bug integer NOT NULL,
    cveref text NOT NULL,
    title text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    "owner" integer NOT NULL,
    cvestate integer DEFAULT 1 NOT NULL,
    CONSTRAINT valid_cve CHECK (valid_cve(cveref))
);



CREATE TABLE karma (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    "action" integer NOT NULL
);



CREATE SEQUENCE spokenin_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE SEQUENCE sourcepackagerelationship_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE TABLE sshkey (
    id serial NOT NULL,
    person integer,
    keytype integer NOT NULL,
    keytext text NOT NULL,
    "comment" text NOT NULL
);



CREATE TABLE bugtask (
    id serial NOT NULL,
    bug integer NOT NULL,
    product integer,
    distribution integer,
    distrorelease integer,
    sourcepackagename integer,
    binarypackagename integer,
    status integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    assignee integer,
    dateassigned timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    "owner" integer NOT NULL,
    milestone integer,
    bugwatch integer,
    statusexplanation text,
    fti ts2.tsvector,
    CONSTRAINT bugtask_assignment_checks CHECK (CASE WHEN (product IS NOT NULL) THEN ((distribution IS NULL) AND (distrorelease IS NULL)) WHEN (distribution IS NOT NULL) THEN ((product IS NULL) AND (distrorelease IS NULL)) WHEN (distrorelease IS NOT NULL) THEN ((product IS NULL) AND (distribution IS NULL)) ELSE NULL::boolean END)
);



CREATE SEQUENCE branchlabel_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE SEQUENCE branchrelationship_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE SEQUENCE productreleasefile_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE TABLE logintoken (
    id serial NOT NULL,
    requester integer,
    requesteremail text,
    email text NOT NULL,
    created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    tokentype integer NOT NULL,
    token text,
    fingerprint text,
    CONSTRAINT valid_fingerprint CHECK (((fingerprint IS NULL) OR valid_fingerprint(fingerprint)))
);



CREATE TABLE milestone (
    id serial NOT NULL,
    product integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);



CREATE TABLE pushmirroraccess (
    id serial NOT NULL,
    name text NOT NULL,
    person integer
);



CREATE TABLE buildqueue (
    id serial NOT NULL,
    build integer NOT NULL,
    builder integer,
    logtail text,
    created timestamp without time zone NOT NULL,
    buildstart timestamp without time zone,
    lastscore integer
);



CREATE SEQUENCE packaging_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;



CREATE TABLE signedcodeofconduct (
    id serial NOT NULL,
    "owner" integer NOT NULL,
    signingkey integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    signedcode text,
    recipient integer,
    active boolean DEFAULT false NOT NULL,
    admincomment text
);



CREATE TABLE bountysubscription (
    id serial NOT NULL,
    bounty integer NOT NULL,
    person integer NOT NULL,
    subscription integer
);



CREATE TABLE productbounty (
    id serial NOT NULL,
    bounty integer NOT NULL,
    product integer NOT NULL
);



CREATE TABLE distrobounty (
    id serial NOT NULL,
    bounty integer NOT NULL,
    distribution integer NOT NULL
);



CREATE TABLE projectbounty (
    id serial NOT NULL,
    bounty integer NOT NULL,
    project integer NOT NULL
);



CREATE TABLE mirror (
    id serial NOT NULL,
    "owner" integer NOT NULL,
    baseurl text NOT NULL,
    country integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    freshness integer DEFAULT 99 NOT NULL,
    lastcheckeddate timestamp without time zone,
    approved boolean DEFAULT false NOT NULL
);



CREATE TABLE mirrorcontent (
    id serial NOT NULL,
    mirror integer NOT NULL,
    distroarchrelease integer NOT NULL,
    component integer NOT NULL
);



CREATE TABLE mirrorsourcecontent (
    id serial NOT NULL,
    mirror integer NOT NULL,
    distrorelease integer NOT NULL,
    component integer NOT NULL
);



CREATE TABLE potemplatename (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text,
    translationdomain text NOT NULL,
    CONSTRAINT potemplate_valid_name CHECK (valid_name(name))
);



CREATE TABLE maintainership (
    id serial NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    maintainer integer NOT NULL
);



CREATE TABLE messagechunk (
    id serial NOT NULL,
    message integer NOT NULL,
    "sequence" integer NOT NULL,
    content text,
    blob integer,
    fti ts2.tsvector,
    CONSTRAINT text_or_content CHECK ((((blob IS NULL) AND (content IS NULL)) OR ((blob IS NULL) <> (content IS NULL))))
);



CREATE TABLE sourcepackagepublishinghistory (
    id serial NOT NULL,
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
    embargolifted timestamp without time zone
);



CREATE TABLE packagepublishinghistory (
    id serial NOT NULL,
    binarypackage integer NOT NULL,
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
    embargolifted timestamp without time zone
);



CREATE TABLE translationgroup (
    id serial NOT NULL,
    name text NOT NULL,
    title text,
    summary text,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE translator (
    id serial NOT NULL,
    translationgroup integer NOT NULL,
    "language" integer NOT NULL,
    translator integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);



CREATE TABLE pocketchroot (
    id serial NOT NULL,
    distroarchrelease integer,
    pocket integer NOT NULL,
    chroot integer
);



CREATE TABLE posubmission (
    id serial NOT NULL,
    pomsgset integer NOT NULL,
    pluralform integer NOT NULL,
    potranslation integer NOT NULL,
    origin integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer,
    validationstatus integer DEFAULT 0 NOT NULL,
    CONSTRAINT posubmission_valid_pluralform CHECK ((pluralform >= 0))
);



CREATE TABLE poselection (
    id serial NOT NULL,
    pomsgset integer NOT NULL,
    pluralform integer NOT NULL,
    activesubmission integer,
    publishedsubmission integer,
    CONSTRAINT poselection_valid_pluralform CHECK ((pluralform >= 0))
);



CREATE TABLE poexportrequest (
    id serial NOT NULL,
    person integer NOT NULL,
    potemplate integer NOT NULL,
    pofile integer,
    format integer NOT NULL
);



CREATE TABLE karmaaction (
    id serial NOT NULL,
    name integer NOT NULL,
    category integer,
    points integer
);



CREATE TABLE karmacache (
    id serial NOT NULL,
    person integer NOT NULL,
    category integer NOT NULL,
    karmavalue integer NOT NULL
);



CREATE TABLE calendar (
    id serial NOT NULL,
    title text NOT NULL,
    revision integer NOT NULL
);



CREATE TABLE calendarsubscription (
    id serial NOT NULL,
    subject integer NOT NULL,
    object integer NOT NULL,
    colour text DEFAULT '#efefef'::text NOT NULL
);



CREATE TABLE calendarevent (
    id serial NOT NULL,
    uid character varying(255) NOT NULL,
    calendar integer NOT NULL,
    dtstart timestamp without time zone NOT NULL,
    duration interval NOT NULL,
    title text NOT NULL,
    description text,
    "location" text
);



CREATE TABLE distroreleaselanguage (
    id serial NOT NULL,
    distrorelease integer,
    "language" integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    contributorcount integer NOT NULL,
    dateupdated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);



CREATE INDEX idx_libraryfilecontent_sha1 ON libraryfilecontent USING btree (sha1);



CREATE UNIQUE INDEX idx_emailaddress_email ON emailaddress USING btree (lower(email));



CREATE INDEX pomsgidsighting_pomsgset_idx ON pomsgidsighting USING btree (potmsgset);



CREATE INDEX pomsgidsighting_pomsgid_idx ON pomsgidsighting USING btree (pomsgid);



CREATE INDEX pomsgidsighting_inlastrevision_idx ON pomsgidsighting USING btree (inlastrevision);



CREATE INDEX pomsgidsighting_pluralform_idx ON pomsgidsighting USING btree (pluralform);



CREATE UNIQUE INDEX person_name_key ON person USING btree (name);



CREATE UNIQUE INDEX schema_name_key ON "schema" USING btree (name);



CREATE UNIQUE INDEX bugtracker_name_key ON bugtracker USING btree (name);



CREATE INDEX distroreleasequeue_distrorelease_key ON distroreleasequeue USING btree (distrorelease);



CREATE INDEX product_project_idx ON product USING btree (project);



CREATE INDEX sshkey_person_key ON sshkey USING btree (person);



CREATE INDEX distroarchrelease_distrorelease_idx ON distroarchrelease USING btree (distrorelease);



CREATE INDEX distroarchrelease_processorfamily_idx ON distroarchrelease USING btree (processorfamily);



CREATE INDEX binarypackage_build_idx ON binarypackage USING btree (build);



CREATE INDEX bugtask_bug_idx ON bugtask USING btree (bug);



CREATE INDEX bugtask_product_idx ON bugtask USING btree (product);



CREATE INDEX bugtask_sourcepackagename_idx ON bugtask USING btree (sourcepackagename);



CREATE INDEX bugtask_distribution_idx ON bugtask USING btree (distribution);



CREATE INDEX bugtask_distrorelease_idx ON bugtask USING btree (distrorelease);



CREATE INDEX bugtask_binarypackagename_idx ON bugtask USING btree (binarypackagename);



CREATE INDEX bugtask_assignee_idx ON bugtask USING btree (assignee);



CREATE INDEX bugtask_owner_idx ON bugtask USING btree ("owner");



CREATE INDEX logintoken_requester_idx ON logintoken USING btree (requester);



CREATE INDEX bugtask_milestone_idx ON bugtask USING btree (milestone);



CREATE INDEX distroarchrelease_architecturetag_idx ON distroarchrelease USING btree (architecturetag);



CREATE INDEX build_sourcepackagerelease_idx ON build USING btree (sourcepackagerelease);



CREATE UNIQUE INDEX pomsgid_msgid_key ON pomsgid USING btree (sha1(msgid));



CREATE UNIQUE INDEX potranslation_translation_key ON potranslation USING btree (sha1(translation));



CREATE INDEX pushmirroraccess_person_idx ON pushmirroraccess USING btree (person);



CREATE INDEX libraryfilealias_content_idx ON libraryfilealias USING btree (content);



CREATE INDEX potemplate_potemplatename_idx ON potemplate USING btree (potemplatename);



CREATE INDEX pofile_potemplate_idx ON pofile USING btree (potemplate);



CREATE INDEX pofile_language_idx ON pofile USING btree ("language");



CREATE INDEX pofile_variant_idx ON pofile USING btree (variant);



CREATE INDEX potmsgset_sequence_idx ON potmsgset USING btree ("sequence");



CREATE INDEX pomsgset_sequence_idx ON pomsgset USING btree ("sequence");



CREATE INDEX potemplate_languagepack_idx ON potemplate USING btree (languagepack);



CREATE INDEX sourcepackagepublishinghistory_distrorelease_key ON sourcepackagepublishinghistory USING btree (distrorelease);



CREATE INDEX sourcepackagepublishinghistory_status_key ON sourcepackagepublishinghistory USING btree (status);



CREATE INDEX sourcepackagepublishinghistory_sourcepackagerelease_key ON sourcepackagepublishinghistory USING btree (sourcepackagerelease);



CREATE INDEX packagepublishinghistory_binarypackage_key ON packagepublishinghistory USING btree (binarypackage);



CREATE INDEX packagepublishinghistory_component_key ON packagepublishinghistory USING btree (component);



CREATE INDEX packagepublishinghistory_distroarchrelease_key ON packagepublishinghistory USING btree (distroarchrelease);



CREATE INDEX packagepublishinghistory_section_key ON packagepublishinghistory USING btree (section);



CREATE INDEX packagepublishinghistory_status_key ON packagepublishinghistory USING btree (status);



CREATE INDEX changeset_name_idx ON changeset USING btree (name);



CREATE INDEX archnamespace_archarchive_idx ON archnamespace USING btree (archarchive);



CREATE INDEX archnamespace_version_idx ON archnamespace USING btree ("version");



CREATE INDEX branch_archnamespace_idx ON branch USING btree (archnamespace);



CREATE INDEX archnamespace_category_idx ON archnamespace USING btree (category);



CREATE INDEX archnamespace_branch_idx ON archnamespace USING btree (branch);



CREATE INDEX packagepublishinghistory_pocket_idx ON packagepublishinghistory USING btree (pocket);



CREATE INDEX sourcepackagepublishinghistory_pocket_idx ON sourcepackagepublishinghistory USING btree (pocket);



CREATE UNIQUE INDEX emailaddress_person_key ON emailaddress USING btree (person, (NULLIF((status = 4), false)));



CREATE UNIQUE INDEX pofile_template_and_language_idx ON pofile USING btree (potemplate, "language", (COALESCE(variant, ''::text)));



CREATE INDEX poselection_pomsgset_and_pluralform_idx ON poselection USING btree (pomsgset, pluralform);



CREATE INDEX posubmission_pomsgset_and_pluralform_idx ON posubmission USING btree (pomsgset, pluralform);



CREATE INDEX posubmission_potranslation_idx ON posubmission USING btree (potranslation);



CREATE INDEX posubmission_person_idx ON posubmission USING btree (person);



CREATE INDEX pomsgset_pofile_and_sequence_idx ON pomsgset USING btree (pofile, "sequence");



CREATE INDEX poselection_activesubmission_idx ON poselection USING btree (activesubmission);



CREATE INDEX poselection_publishedsubmission_idx ON poselection USING btree (publishedsubmission);



CREATE INDEX poselection_activesubmission_pomsgset_plural_idx ON poselection USING btree (activesubmission, pomsgset, pluralform);



CREATE INDEX poselection_pubishedsubmission_pomsgset_plural_idx ON poselection USING btree (publishedsubmission, pomsgset, pluralform);



CREATE INDEX potmsgset_primemsgid_idx ON potmsgset USING btree (primemsgid);



CREATE INDEX potmsgset_potemplate_and_sequence_idx ON potmsgset USING btree (potemplate, "sequence");



CREATE INDEX person_datecreated_idx ON person USING btree (datecreated);



CREATE INDEX productseries_datecreated_idx ON productseries USING btree (datecreated);



CREATE INDEX productrelease_datecreated_idx ON productrelease USING btree (datecreated);



CREATE INDEX pofile_datecreated_idx ON pofile USING btree (datecreated);



CREATE INDEX archarchive_owner_idx ON archarchive USING btree ("owner");



CREATE INDEX person_teamowner_idx ON person USING btree (teamowner);



CREATE INDEX bug_duplicateof_idx ON bug USING btree (duplicateof);



CREATE INDEX bugactivity_datechanged_idx ON bugactivity USING btree (datechanged);



CREATE INDEX bugactivity_bug_datechanged_idx ON bugactivity USING btree (bug, datechanged);



CREATE INDEX bugactivity_person_datechanged_idx ON bugactivity USING btree (person, datechanged);



CREATE INDEX bugexternalref_bug_idx ON bugexternalref USING btree (bug);



CREATE INDEX bugexternalref_datecreated_idx ON bugexternalref USING btree (datecreated);



CREATE INDEX bugmessage_bug_idx ON bugmessage USING btree (bug);



CREATE INDEX bugmessage_message_idx ON bugmessage USING btree (message);



CREATE INDEX bugsubscription_bug_idx ON bugsubscription USING btree (bug);



CREATE INDEX bugsubscription_person_idx ON bugsubscription USING btree (person);



CREATE INDEX bugtask_distribution_and_sourcepackagename_idx ON bugtask USING btree (distribution, sourcepackagename);



CREATE INDEX bugtask_distrorelease_and_sourcepackagename_idx ON bugtask USING btree (distrorelease, sourcepackagename);



CREATE INDEX bugtask_datecreated_idx ON bugtask USING btree (datecreated);



CREATE INDEX bugtracker_owner_idx ON bugtracker USING btree ("owner");



CREATE INDEX bugwatch_bug_idx ON bugwatch USING btree (bug);



CREATE INDEX bugwatch_bugtracker_idx ON bugwatch USING btree (bugtracker);



CREATE INDEX bugwatch_owner_idx ON bugwatch USING btree ("owner");



CREATE INDEX bugwatch_datecreated_idx ON bugwatch USING btree (datecreated);



CREATE INDEX build_datecreated_idx ON build USING btree (datecreated);



CREATE INDEX build_datebuilt_idx ON build USING btree (datebuilt);



CREATE INDEX build_builder_and_buildstate_idx ON build USING btree (builder, buildstate);



CREATE INDEX build_distroarchrelease_and_datebuilt_idx ON build USING btree (distroarchrelease, datebuilt);



CREATE INDEX build_distroarchrelease_and_buildstate_idx ON build USING btree (distroarchrelease, buildstate);



CREATE INDEX build_buildstate_idx ON build USING btree (buildstate);



CREATE INDEX changeset_datecreated_idx ON changeset USING btree (datecreated);



CREATE INDEX changeset_branch_and_name_idx ON changeset USING btree (branch, name);



CREATE INDEX cveref_bug_idx ON cveref USING btree (bug);



CREATE INDEX cveref_datecreated_idx ON cveref USING btree (datecreated);



CREATE INDEX distribution_translationgroup_idx ON distribution USING btree (translationgroup);



CREATE INDEX product_translationgroup_idx ON product USING btree (translationgroup);



CREATE INDEX project_translationgroup_idx ON project USING btree (translationgroup);



CREATE INDEX distrobounty_distribution_idx ON distrobounty USING btree (distribution);



CREATE INDEX message_owner_idx ON message USING btree ("owner");



CREATE INDEX message_parent_idx ON message USING btree (parent);



CREATE INDEX packaging_sourcepackagename_idx ON packaging USING btree (sourcepackagename);



CREATE INDEX packaging_distrorelease_and_sourcepackagename_idx ON packaging USING btree (distrorelease, sourcepackagename);



CREATE INDEX binarypackagefile_libraryfile_idx ON binarypackagefile USING btree (libraryfile);



CREATE INDEX sourcepackagerelease_sourcepackagename_idx ON sourcepackagerelease USING btree (sourcepackagename);



CREATE INDEX binarypackagefile_binarypackage_idx ON binarypackagefile USING btree (binarypackage);



CREATE INDEX sourcepackagereleasefile_sourcepackagerelease_idx ON sourcepackagereleasefile USING btree (sourcepackagerelease);



CREATE INDEX sourcepackagereleasefile_libraryfile_idx ON sourcepackagereleasefile USING btree (libraryfile);



CREATE INDEX binarypackage_fti ON binarypackage USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX wikiname_person_idx ON wikiname USING btree (person);



CREATE INDEX karma_person_datecreated_idx ON karma USING btree (person, datecreated);



CREATE UNIQUE INDEX poexportrequest_duplicate_key ON poexportrequest USING btree (potemplate, person, format, (COALESCE(pofile, -1)));



CREATE INDEX message_rfc822msgid_idx ON message USING btree (rfc822msgid);



CREATE INDEX bug_fti ON bug USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX bugtask_fti ON bugtask USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX message_fti ON message USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX messagechunk_fti ON messagechunk USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX person_fti ON person USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX product_fti ON product USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX project_fti ON project USING gist (fti ts2.gist_tsvector_ops);



CREATE INDEX binarypackage_version_idx ON binarypackage USING btree ("version");



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



ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_pkey PRIMARY KEY (id);



ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_jabberid_key UNIQUE (jabberid);



ALTER TABLE ONLY ircid
    ADD CONSTRAINT ircid_pkey PRIMARY KEY (id);



ALTER TABLE ONLY teammembership
    ADD CONSTRAINT membership_pkey PRIMARY KEY (id);



ALTER TABLE ONLY teammembership
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



ALTER TABLE ONLY product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT productlabel_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT productlabel_product_key UNIQUE (product, label);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_key UNIQUE (product, name);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_pkey PRIMARY KEY (id);



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



ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection_pkey PRIMARY KEY (id);



ALTER TABLE ONLY osfile
    ADD CONSTRAINT osfile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY osfile
    ADD CONSTRAINT osfile_path_key UNIQUE ("path");



ALTER TABLE ONLY pomsgid
    ADD CONSTRAINT pomsgid_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potranslation
    ADD CONSTRAINT potranslation_pkey PRIMARY KEY (id);



ALTER TABLE ONLY "language"
    ADD CONSTRAINT language_pkey PRIMARY KEY (id);



ALTER TABLE ONLY "language"
    ADD CONSTRAINT language_code_key UNIQUE (code);



ALTER TABLE ONLY country
    ADD CONSTRAINT country_pkey PRIMARY KEY (id);



ALTER TABLE ONLY license
    ADD CONSTRAINT license_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_pkey PRIMARY KEY (id);



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



ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT bugactivity_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT bugexternalref_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT bugsystem_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_pkey PRIMARY KEY (id);



ALTER TABLE ONLY buglabel
    ADD CONSTRAINT buglabel_pkey PRIMARY KEY (bug, label);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_pkey PRIMARY KEY (id);



ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT projectbugsystem_pkey PRIMARY KEY (id);



ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT projectbugsystem_project_key UNIQUE (project, bugtracker);



ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_name_key UNIQUE (name);



ALTER TABLE ONLY componentselection
    ADD CONSTRAINT componentselection_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT sectionselection_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_name_key UNIQUE (name);



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



ALTER TABLE ONLY message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);



ALTER TABLE ONLY karma
    ADD CONSTRAINT karma_pkey PRIMARY KEY (id);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_name_key UNIQUE (name);



ALTER TABLE ONLY spokenin
    ADD CONSTRAINT spokenin_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sshkey
    ADD CONSTRAINT sshkey_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_pkey PRIMARY KEY (id);



ALTER TABLE ONLY manifest
    ADD CONSTRAINT manifest_uuid_uniq UNIQUE (uuid);



ALTER TABLE ONLY branchlabel
    ADD CONSTRAINT branchlabel_pkey PRIMARY KEY (id);



ALTER TABLE ONLY branchrelationship
    ADD CONSTRAINT branchrelationship_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT productreleasefile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY logintoken
    ADD CONSTRAINT logintoken_token_key UNIQUE (token);



ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_pkey PRIMARY KEY (id);



ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_key UNIQUE (product, name);



ALTER TABLE ONLY pushmirroraccess
    ADD CONSTRAINT pushmirroraccess_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pushmirroraccess
    ADD CONSTRAINT pushmirroraccess_name_key UNIQUE (name);



ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT buildqueue_pkey PRIMARY KEY (id);



ALTER TABLE ONLY launchpaddatabaserevision
    ADD CONSTRAINT launchpaddatabaserevision_pkey PRIMARY KEY (major, minor, patch);



ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_person_key UNIQUE (person, bounty);



ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_pkey PRIMARY KEY (id);



ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_bounty_key UNIQUE (bounty, product);



ALTER TABLE ONLY distrobounty
    ADD CONSTRAINT distrobounty_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distrobounty
    ADD CONSTRAINT distrobounty_bounty_key UNIQUE (bounty, distribution);



ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_pkey PRIMARY KEY (id);



ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_bounty_key UNIQUE (bounty, project);



ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_pkey PRIMARY KEY (id);



ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_name_key UNIQUE (name);



ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_pkey PRIMARY KEY (id);



ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potemplatename
    ADD CONSTRAINT potemplatename_pkey PRIMARY KEY (id);



ALTER TABLE ONLY potemplatename
    ADD CONSTRAINT potemplate_name_key UNIQUE (name);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_distrorelease_key UNIQUE (distrorelease, sourcepackagename, potemplatename);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_sourcepackagename_key UNIQUE (sourcepackagename, "path", filename, distrorelease);



ALTER TABLE ONLY potemplatename
    ADD CONSTRAINT potemplate_translationdomain_key UNIQUE (translationdomain);



ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_owner_key UNIQUE ("owner", id);



ALTER TABLE ONLY maintainership
    ADD CONSTRAINT maintainership_pkey PRIMARY KEY (id);



ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_pkey PRIMARY KEY (id);



ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_message_idx UNIQUE (message, "sequence");



ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_pkey PRIMARY KEY (id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_distribution_key UNIQUE (distribution, name);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_branch_key UNIQUE (branch);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_pkey PRIMARY KEY (id);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_uniqueness UNIQUE (distrorelease, sourcepackagename, productseries);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_cvsroot_key UNIQUE (cvsroot, cvsmodule, cvsbranch);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_targetarcharchive_key UNIQUE (targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_svnrepository_key UNIQUE (svnrepository);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_bkrepository_key UNIQUE (bkrepository);



ALTER TABLE ONLY packagepublishinghistory
    ADD CONSTRAINT packagepublishinghistory_pkey PRIMARY KEY (id);



ALTER TABLE ONLY changeset
    ADD CONSTRAINT changeset_branch_key UNIQUE (branch, id);



ALTER TABLE ONLY archarchive
    ADD CONSTRAINT archarchive_name_key UNIQUE (name);



ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_pkey PRIMARY KEY (id);



ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_name_key UNIQUE (name);



ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_pkey PRIMARY KEY (id);



ALTER TABLE ONLY translator
    ADD CONSTRAINT translation_translationgroup_key UNIQUE (translationgroup, "language");



ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_url_key UNIQUE (url);



ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot_distroarchrelease_key UNIQUE (distroarchrelease, pocket);



ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT pocketchroot_chroot_key UNIQUE (chroot);



ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission_pkey PRIMARY KEY (id);



ALTER TABLE ONLY poselection
    ADD CONSTRAINT poselection_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_potmsgset_key UNIQUE (potmsgset, pofile);



ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission_can_be_selected UNIQUE (pomsgset, pluralform, id);



ALTER TABLE ONLY poselection
    ADD CONSTRAINT poselection_uniqueness UNIQUE (pomsgset, pluralform);



ALTER TABLE ONLY country
    ADD CONSTRAINT country_name_uniq UNIQUE (name);



ALTER TABLE ONLY country
    ADD CONSTRAINT country_code2_uniq UNIQUE (iso3166code2);



ALTER TABLE ONLY country
    ADD CONSTRAINT country_code3_uniq UNIQUE (iso3166code3);



ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bugtask_target UNIQUE (id, bug);



ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_wikiname_key UNIQUE (wikiname, wiki);



ALTER TABLE ONLY karmaaction
    ADD CONSTRAINT karmaaction_pkey PRIMARY KEY (id);



ALTER TABLE ONLY karmaaction
    ADD CONSTRAINT karmaaction_name_key UNIQUE (name);



ALTER TABLE ONLY karmacache
    ADD CONSTRAINT karmacache_pkey PRIMARY KEY (id);



ALTER TABLE ONLY karmacache
    ADD CONSTRAINT category_person_key UNIQUE (category, person);



ALTER TABLE ONLY calendar
    ADD CONSTRAINT calendar_pkey PRIMARY KEY (id);



ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_pkey PRIMARY KEY (id);



ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_subject_key UNIQUE (subject, object);



ALTER TABLE ONLY calendarevent
    ADD CONSTRAINT calendarevent_pkey PRIMARY KEY (id);



ALTER TABLE ONLY calendarevent
    ADD CONSTRAINT calendarevent_uid_key UNIQUE (uid);



ALTER TABLE ONLY person
    ADD CONSTRAINT person_calendar_key UNIQUE (calendar);



ALTER TABLE ONLY project
    ADD CONSTRAINT project_calendar_key UNIQUE (calendar);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_calendar_key UNIQUE (calendar);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_productseries_ptname_uniq UNIQUE (productseries, potemplatename);



ALTER TABLE ONLY distroreleaselanguage
    ADD CONSTRAINT distroreleaselanguage_pkey PRIMARY KEY (id);



ALTER TABLE ONLY person
    ADD CONSTRAINT "$1" FOREIGN KEY (teamowner) REFERENCES person(id);



ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY wikiname
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY jabberid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY ircid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY teammembership
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY teammembership
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



ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES project(id);



ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES project(id);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productlabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY productcvsmodule
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productbkbranch
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);



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



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$3" FOREIGN KEY (manifest) REFERENCES manifest(id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$5" FOREIGN KEY (changeset) REFERENCES changeset(id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$7" FOREIGN KEY (manifest, patchon) REFERENCES manifestentry(manifest, "sequence");



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



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$2" FOREIGN KEY (creator) REFERENCES person(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$3" FOREIGN KEY (dscsigningkey) REFERENCES gpgkey(id);



ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



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



ALTER TABLE ONLY osfileinpackage
    ADD CONSTRAINT "$1" FOREIGN KEY (osfile) REFERENCES osfile(id);



ALTER TABLE ONLY osfileinpackage
    ADD CONSTRAINT "$2" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);



ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$1" FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$2" FOREIGN KEY (country) REFERENCES country(id);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);



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



ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



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



ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$2" FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$2" FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY build
    ADD CONSTRAINT "$6" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



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



ALTER TABLE ONLY person
    ADD CONSTRAINT person_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY cveref
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY cveref
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY message
    ADD CONSTRAINT message_parent_fk FOREIGN KEY (parent) REFERENCES message(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_message_fk FOREIGN KEY (message) REFERENCES message(id);



ALTER TABLE ONLY karma
    ADD CONSTRAINT karma_person_fk FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY project
    ADD CONSTRAINT project_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_project_fk FOREIGN KEY (project) REFERENCES project(id);



ALTER TABLE ONLY sshkey
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_product_fk FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_person_fk FOREIGN KEY (assignee) REFERENCES person(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_manifest_fk FOREIGN KEY (manifest) REFERENCES manifest(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_maintainer_fk FOREIGN KEY (maintainer) REFERENCES person(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);



ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_manifest_fk FOREIGN KEY (manifest) REFERENCES manifest(id);



ALTER TABLE ONLY logintoken
    ADD CONSTRAINT logintoken_requester_fk FOREIGN KEY (requester) REFERENCES person(id);



ALTER TABLE ONLY milestone
    ADD CONSTRAINT milestone_product_fk FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_milestone_fk FOREIGN KEY (milestone) REFERENCES milestone(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY pushmirroraccess
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT "$1" FOREIGN KEY (build) REFERENCES build(id);



ALTER TABLE ONLY buildqueue
    ADD CONSTRAINT "$2" FOREIGN KEY (builder) REFERENCES builder(id);



ALTER TABLE ONLY teammembership
    ADD CONSTRAINT reviewer_fk FOREIGN KEY (reviewer) REFERENCES person(id);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_message_fk FOREIGN KEY (message) REFERENCES message(id);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_libraryfile_fk FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);



ALTER TABLE ONLY bountysubscription
    ADD CONSTRAINT bountysubscription_person_fk FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);



ALTER TABLE ONLY productbounty
    ADD CONSTRAINT productbounty_product_fk FOREIGN KEY (product) REFERENCES product(id);



ALTER TABLE ONLY distrobounty
    ADD CONSTRAINT distrobounty_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);



ALTER TABLE ONLY distrobounty
    ADD CONSTRAINT distrobounty_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_bounty_fk FOREIGN KEY (bounty) REFERENCES bounty(id);



ALTER TABLE ONLY projectbounty
    ADD CONSTRAINT projectbounty_project_fk FOREIGN KEY (project) REFERENCES project(id);



ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY mirror
    ADD CONSTRAINT mirror_country_fk FOREIGN KEY (country) REFERENCES country(id);



ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_mirror_fk FOREIGN KEY (mirror) REFERENCES mirror(id);



ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_distroarchrelease_fk FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);



ALTER TABLE ONLY mirrorcontent
    ADD CONSTRAINT mirrorcontent_component_fk FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_mirror_fk FOREIGN KEY (mirror) REFERENCES mirror(id);



ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY mirrorsourcecontent
    ADD CONSTRAINT mirrorsourcecontent_component_fk FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY archarchive
    ADD CONSTRAINT archarchive_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY archarchivelocation
    ADD CONSTRAINT archarchivelocation_archive_fk FOREIGN KEY (archive) REFERENCES archarchive(id);



ALTER TABLE ONLY archarchivelocationsigner
    ADD CONSTRAINT archarchivelocationsigner_archarchivelocation_fk FOREIGN KEY (archarchivelocation) REFERENCES archarchivelocation(id);



ALTER TABLE ONLY archarchivelocationsigner
    ADD CONSTRAINT archarchivelocationsigner_gpgkey_fk FOREIGN KEY (gpgkey) REFERENCES gpgkey(id);



ALTER TABLE ONLY archconfig
    ADD CONSTRAINT archconfig_productrelease_fk FOREIGN KEY (productrelease) REFERENCES productrelease(id);



ALTER TABLE ONLY archconfig
    ADD CONSTRAINT archconfig_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT archconfigentry_archconfig_fk FOREIGN KEY (archconfig) REFERENCES archconfig(id);



ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT archconfigentry_branch_fk FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY archnamespace
    ADD CONSTRAINT archnamespace_archarchive_fk FOREIGN KEY (archarchive) REFERENCES archarchive(id);



ALTER TABLE ONLY archuserid
    ADD CONSTRAINT archuserid_person_fk FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_build_fk FOREIGN KEY (build) REFERENCES build(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_component_fk FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_section_fk FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_binarypackage_fk FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);



ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT binarypackagefile_libraryfile_fk FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_reviewer_fk FOREIGN KEY (reviewer) REFERENCES person(id);



ALTER TABLE ONLY bounty
    ADD CONSTRAINT bounty_claimant_fk FOREIGN KEY (claimant) REFERENCES person(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_potemplatename_fk FOREIGN KEY (potemplatename) REFERENCES potemplatename(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_license_fk FOREIGN KEY (license) REFERENCES license(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_rawimporter_fk FOREIGN KEY (rawimporter) REFERENCES person(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);



ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$2" FOREIGN KEY (members) REFERENCES person(id);



ALTER TABLE ONLY signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_lasttranslator_fk FOREIGN KEY (lasttranslator) REFERENCES person(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_license_fk FOREIGN KEY (license) REFERENCES license(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_rawimporter_fk FOREIGN KEY (rawimporter) REFERENCES person(id);



ALTER TABLE ONLY maintainership
    ADD CONSTRAINT maintainership_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY maintainership
    ADD CONSTRAINT maintainership_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);



ALTER TABLE ONLY maintainership
    ADD CONSTRAINT maintainership_maintainer_fk FOREIGN KEY (maintainer) REFERENCES person(id);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_uploaddistrorelease_fk FOREIGN KEY (uploaddistrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_signingkey_fk FOREIGN KEY ("owner", signingkey) REFERENCES gpgkey("owner", id) ON UPDATE CASCADE;



ALTER TABLE ONLY person
    ADD CONSTRAINT person_merged_fk FOREIGN KEY (merged) REFERENCES person(id);



ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_message_fk FOREIGN KEY (message) REFERENCES message(id);



ALTER TABLE ONLY messagechunk
    ADD CONSTRAINT messagechunk_blob_fk FOREIGN KEY (blob) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY message
    ADD CONSTRAINT message_raw_fk FOREIGN KEY (raw) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_sourcepackagerelease_fk FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_parentrelease_fk FOREIGN KEY (parentrelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_sections_fk FOREIGN KEY (sections) REFERENCES "schema"(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_components_fk FOREIGN KEY (components) REFERENCES "schema"(id);



ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_branch_fk FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_duplicateof_fk FOREIGN KEY (duplicateof) REFERENCES bug(id);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);



ALTER TABLE ONLY packagepublishinghistory
    ADD CONSTRAINT packagepublishinghistory_binarypackage_fk FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);



ALTER TABLE ONLY packagepublishinghistory
    ADD CONSTRAINT packagepublishinghistory_distroarchrelease_fk FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);



ALTER TABLE ONLY packagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES component(id);



ALTER TABLE ONLY packagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES section(id);



ALTER TABLE ONLY packagepublishinghistory
    ADD CONSTRAINT packagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES build(id);



ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT archconfigentry_changeset_fk FOREIGN KEY (branch, changeset) REFERENCES changeset(branch, id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$1" FOREIGN KEY (rawfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$1" FOREIGN KEY (rawfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$2" FOREIGN KEY (exportfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY translationgroup
    ADD CONSTRAINT translationgroup_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);



ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);



ALTER TABLE ONLY translator
    ADD CONSTRAINT translator_person_fk FOREIGN KEY (translator) REFERENCES person(id);



ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);



ALTER TABLE ONLY project
    ADD CONSTRAINT project_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES translationgroup(id);



ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT "$1" FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);



ALTER TABLE ONLY pocketchroot
    ADD CONSTRAINT "$2" FOREIGN KEY (chroot) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pofile_fk FOREIGN KEY (pofile) REFERENCES pofile(id);



ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission_pomsgset_fk FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);



ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission_potranslation_fk FOREIGN KEY (potranslation) REFERENCES potranslation(id);



ALTER TABLE ONLY posubmission
    ADD CONSTRAINT posubmission_person_fk FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY poselection
    ADD CONSTRAINT poselection_real_active_fk FOREIGN KEY (pomsgset, pluralform, activesubmission) REFERENCES posubmission(pomsgset, pluralform, id);



ALTER TABLE ONLY poselection
    ADD CONSTRAINT poselection_real_published_fk FOREIGN KEY (pomsgset, pluralform, publishedsubmission) REFERENCES posubmission(pomsgset, pluralform, id);



ALTER TABLE ONLY poselection
    ADD CONSTRAINT poselection_pomsgset_fk FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT manifestentry_changeset_fk FOREIGN KEY (branch, changeset) REFERENCES changeset(branch, id);



ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT manifestentry_branch_fk FOREIGN KEY (branch) REFERENCES branch(id);



ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_person_fk FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poeportrequest_potemplate_fk FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY poexportrequest
    ADD CONSTRAINT poexportrequest_pofile_fk FOREIGN KEY (pofile) REFERENCES pofile(id);



ALTER TABLE ONLY bugtask
    ADD CONSTRAINT bugtask_bugwatch_fk FOREIGN KEY (bugwatch, bug) REFERENCES bugwatch(id, bug);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bug_fk FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_bugtracker_fk FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY karmacache
    ADD CONSTRAINT person_fk FOREIGN KEY (person) REFERENCES person(id);



ALTER TABLE ONLY karma
    ADD CONSTRAINT action_fkey FOREIGN KEY ("action") REFERENCES karmaaction(id);



ALTER TABLE ONLY message
    ADD CONSTRAINT message_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY message
    ADD CONSTRAINT message_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT bugtracker_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY packaging
    ADD CONSTRAINT packaging_owner_fk FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_subject_fk FOREIGN KEY (subject) REFERENCES calendar(id);



ALTER TABLE ONLY calendarsubscription
    ADD CONSTRAINT calendarsubscription_object_fk FOREIGN KEY (object) REFERENCES calendar(id);



ALTER TABLE ONLY calendarevent
    ADD CONSTRAINT calendarevent_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);



ALTER TABLE ONLY person
    ADD CONSTRAINT person_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);



ALTER TABLE ONLY project
    ADD CONSTRAINT project_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);



ALTER TABLE ONLY product
    ADD CONSTRAINT product_calendar_fk FOREIGN KEY (calendar) REFERENCES calendar(id);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_productseries_fk FOREIGN KEY (productseries) REFERENCES productseries(id);



ALTER TABLE ONLY distroreleaselanguage
    ADD CONSTRAINT distroreleaselanguage_distrorelease_fk FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY distroreleaselanguage
    ADD CONSTRAINT distroreleaselanguage_language_fk FOREIGN KEY ("language") REFERENCES "language"(id);



CREATE TRIGGER you_are_your_own_member
    AFTER INSERT ON person
    FOR EACH ROW
    EXECUTE PROCEDURE you_are_your_own_member();



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON binarypackage
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.tsearch2('fti', 'summary', 'description');



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON bug
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON bugtask
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('statusexplanation', 'c');



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON message
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('subject', 'b');



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON messagechunk
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('content', 'c');



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON person
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'displayname', 'b', 'givenname', 'c', 'familyname', 'c');



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON product
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');



CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON project
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');



CREATE VIEW sourcepackagepublishing AS
    SELECT sourcepackagepublishinghistory.id, sourcepackagepublishinghistory.distrorelease, sourcepackagepublishinghistory.sourcepackagerelease, sourcepackagepublishinghistory.status, sourcepackagepublishinghistory.component, sourcepackagepublishinghistory.section, sourcepackagepublishinghistory.datepublished, sourcepackagepublishinghistory.scheduleddeletiondate, sourcepackagepublishinghistory.pocket FROM sourcepackagepublishinghistory WHERE ((sourcepackagepublishinghistory.status <> 7) AND (sourcepackagepublishinghistory.embargo = false));



CREATE VIEW packagepublishing AS
    SELECT packagepublishinghistory.id, packagepublishinghistory.distroarchrelease, packagepublishinghistory.binarypackage, packagepublishinghistory.status, packagepublishinghistory.component, packagepublishinghistory.section, packagepublishinghistory.priority, packagepublishinghistory.datepublished, packagepublishinghistory.scheduleddeletiondate, packagepublishinghistory.pocket FROM packagepublishinghistory WHERE ((packagepublishinghistory.status <> 7) AND (packagepublishinghistory.embargo = false));



CREATE VIEW publishedpackageview AS
    SELECT packagepublishing.id, distrorelease.distribution, distrorelease.id AS distrorelease, distrorelease.name AS distroreleasename, processorfamily.id AS processorfamily, processorfamily.name AS processorfamilyname, packagepublishing.status AS packagepublishingstatus, component.name AS component, section.name AS section, binarypackage.id AS binarypackage, binarypackagename.name AS binarypackagename, binarypackage.summary AS binarypackagesummary, binarypackage.description AS binarypackagedescription, binarypackage."version" AS binarypackageversion, build.id AS build, build.datebuilt, sourcepackagerelease.id AS sourcepackagerelease, sourcepackagerelease."version" AS sourcepackagereleaseversion, sourcepackagename.name AS sourcepackagename, binarypackage.fti AS binarypackagefti FROM ((((((((((packagepublishing JOIN distroarchrelease ON ((distroarchrelease.id = packagepublishing.distroarchrelease))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN processorfamily ON ((distroarchrelease.processorfamily = processorfamily.id))) JOIN component ON ((packagepublishing.component = component.id))) JOIN binarypackage ON ((packagepublishing.binarypackage = binarypackage.id))) JOIN section ON ((packagepublishing.section = section.id))) JOIN binarypackagename ON ((binarypackage.binarypackagename = binarypackagename.id))) JOIN build ON ((binarypackage.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));



CREATE VIEW binarypackagepublishingview AS
    SELECT packagepublishing.id, distrorelease.name AS distroreleasename, binarypackagename.name AS binarypackagename, component.name AS componentname, section.name AS sectionname, packagepublishing.priority, distrorelease.distribution, packagepublishing.status AS publishingstatus FROM packagepublishing, distrorelease, distroarchrelease, binarypackage, binarypackagename, component, section WHERE ((((((packagepublishing.distroarchrelease = distroarchrelease.id) AND (distroarchrelease.distrorelease = distrorelease.id)) AND (packagepublishing.binarypackage = binarypackage.id)) AND (binarypackage.binarypackagename = binarypackagename.id)) AND (packagepublishing.component = component.id)) AND (packagepublishing.section = section.id));



CREATE VIEW sourcepackagepublishingview AS
    SELECT sourcepackagepublishing.id, distrorelease.name AS distroreleasename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, section.name AS sectionname, distrorelease.distribution, sourcepackagepublishing.status AS publishingstatus FROM (((((sourcepackagepublishing JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN component ON ((sourcepackagepublishing.component = component.id))) JOIN section ON ((sourcepackagepublishing.section = section.id)));



CREATE VIEW vsourcepackagereleasepublishing AS
    SELECT DISTINCT sourcepackagerelease.id, sourcepackagename.name, maintainership.maintainer, sourcepackagepublishing.status AS publishingstatus, sourcepackagepublishing.datepublished, sourcepackagepublishing.distrorelease, component.name AS componentname, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.format, sourcepackagerelease.manifest, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, sourcepackagerelease.uploaddistrorelease, sourcepackagerelease.sourcepackagename FROM (((((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN component ON ((sourcepackagepublishing.component = component.id))) LEFT JOIN maintainership ON (((sourcepackagerelease.sourcepackagename = maintainership.sourcepackagename) AND (distrorelease.distribution = maintainership.distribution)))) ORDER BY sourcepackagerelease.id, sourcepackagename.name, maintainership.maintainer, sourcepackagepublishing.status, sourcepackagepublishing.datepublished, sourcepackagepublishing.distrorelease, component.name, sourcepackagerelease.architecturehintlist, sourcepackagerelease."version", sourcepackagerelease.creator, sourcepackagerelease.format, sourcepackagerelease.manifest, sourcepackagerelease.section, sourcepackagerelease.component, sourcepackagerelease.changelog, sourcepackagerelease.builddepends, sourcepackagerelease.builddependsindep, sourcepackagerelease.urgency, sourcepackagerelease.dateuploaded, sourcepackagerelease.dsc, sourcepackagerelease.dscsigningkey, sourcepackagerelease.uploaddistrorelease, sourcepackagerelease.sourcepackagename;



CREATE VIEW vsourcepackageindistro AS
    SELECT sourcepackagerelease.id, sourcepackagerelease.manifest, sourcepackagerelease.format, sourcepackagerelease.sourcepackagename, sourcepackagename.name, sourcepackagepublishing.distrorelease, distrorelease.distribution FROM (((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));



CREATE VIEW sourcepackagepublishingpublichistory AS
    SELECT sourcepackagepublishinghistory.id, sourcepackagepublishinghistory.sourcepackagerelease, sourcepackagepublishinghistory.distrorelease, sourcepackagepublishinghistory.status, sourcepackagepublishinghistory.component, sourcepackagepublishinghistory.section, sourcepackagepublishinghistory.datecreated, sourcepackagepublishinghistory.datepublished, sourcepackagepublishinghistory.datesuperseded, sourcepackagepublishinghistory.supersededby, sourcepackagepublishinghistory.datemadepending, sourcepackagepublishinghistory.scheduleddeletiondate, sourcepackagepublishinghistory.dateremoved, sourcepackagepublishinghistory.pocket, sourcepackagepublishinghistory.embargo, sourcepackagepublishinghistory.embargolifted FROM sourcepackagepublishinghistory WHERE (sourcepackagepublishinghistory.embargo = false);



CREATE VIEW packagepublishingpublichistory AS
    SELECT packagepublishinghistory.id, packagepublishinghistory.binarypackage, packagepublishinghistory.distroarchrelease, packagepublishinghistory.status, packagepublishinghistory.component, packagepublishinghistory.section, packagepublishinghistory.priority, packagepublishinghistory.datecreated, packagepublishinghistory.datepublished, packagepublishinghistory.datesuperseded, packagepublishinghistory.supersededby, packagepublishinghistory.datemadepending, packagepublishinghistory.scheduleddeletiondate, packagepublishinghistory.dateremoved, packagepublishinghistory.pocket, packagepublishinghistory.embargo, packagepublishinghistory.embargolifted FROM packagepublishinghistory WHERE (packagepublishinghistory.embargo = false);



CREATE VIEW binarypackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (packagepublishing.id)::text) AS id, distrorelease.distribution, packagepublishing.id AS packagepublishing, component.name AS componentname, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, binarypackagefile.libraryfile AS libraryfilealias, distrorelease.name AS distroreleasename, distroarchrelease.architecturetag, packagepublishing.status AS publishingstatus, packagepublishing.pocket FROM (((((((((packagepublishing JOIN binarypackage ON ((packagepublishing.binarypackage = binarypackage.id))) JOIN build ON ((binarypackage.build = build.id))) JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN binarypackagefile ON ((binarypackagefile.binarypackage = binarypackage.id))) JOIN libraryfilealias ON ((binarypackagefile.libraryfile = libraryfilealias.id))) JOIN distroarchrelease ON ((packagepublishing.distroarchrelease = distroarchrelease.id))) JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id))) JOIN component ON ((packagepublishing.component = component.id)));



CREATE VIEW sourcepackagefilepublishing AS
    SELECT (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishing.id)::text) AS id, distrorelease.distribution, sourcepackagepublishing.id AS sourcepackagepublishing, sourcepackagereleasefile.libraryfile AS libraryfilealias, libraryfilealias.filename AS libraryfilealiasfilename, sourcepackagename.name AS sourcepackagename, component.name AS componentname, distrorelease.name AS distroreleasename, sourcepackagepublishing.status AS publishingstatus, sourcepackagepublishing.pocket FROM ((((((sourcepackagepublishing JOIN sourcepackagerelease ON ((sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id))) JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id))) JOIN sourcepackagereleasefile ON ((sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id))) JOIN libraryfilealias ON ((libraryfilealias.id = sourcepackagereleasefile.libraryfile))) JOIN distrorelease ON ((sourcepackagepublishing.distrorelease = distrorelease.id))) JOIN component ON ((sourcepackagepublishing.component = component.id)));



CREATE VIEW poexport AS
    SELECT ((((((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) || COALESCE((pomsgset.id)::text, 'X'::text)) || '.'::text) || COALESCE((pomsgidsighting.id)::text, 'X'::text)) || '.'::text) || COALESCE((poselection.id)::text, 'X'::text)) AS id, potemplatename.name, potemplatename.translationdomain, potemplate.id AS potemplate, potemplate.productseries, potemplate.sourcepackagename, potemplate.distrorelease, potemplate.header AS potheader, potemplate.languagepack, pofile.id AS pofile, pofile."language", pofile.variant, pofile.topcomment AS potopcomment, pofile.header AS poheader, pofile.fuzzyheader AS pofuzzyheader, pofile.pluralforms AS popluralforms, potmsgset.id AS potmsgset, potmsgset."sequence" AS potsequence, potmsgset.commenttext AS potcommenttext, potmsgset.sourcecomment, potmsgset.flagscomment, potmsgset.filereferences, pomsgset.id AS pomsgset, pomsgset."sequence" AS posequence, pomsgset.iscomplete, pomsgset.obsolete, pomsgset.isfuzzy, pomsgset.commenttext AS pocommenttext, pomsgidsighting.pluralform AS msgidpluralform, poselection.pluralform AS translationpluralform, poselection.activesubmission, pomsgid.msgid, potranslation.translation FROM (((((((((pomsgid JOIN pomsgidsighting ON ((pomsgid.id = pomsgidsighting.pomsgid))) JOIN potmsgset ON ((potmsgset.id = pomsgidsighting.potmsgset))) JOIN potemplate ON ((potemplate.id = potmsgset.potemplate))) JOIN potemplatename ON ((potemplatename.id = potemplate.potemplatename))) JOIN pofile ON ((potemplate.id = pofile.potemplate))) LEFT JOIN pomsgset ON (((potmsgset.id = pomsgset.potmsgset) AND (pomsgset.pofile = pofile.id)))) LEFT JOIN poselection ON ((pomsgset.id = poselection.pomsgset))) LEFT JOIN posubmission ON ((posubmission.id = poselection.activesubmission))) LEFT JOIN potranslation ON ((potranslation.id = posubmission.potranslation)));


