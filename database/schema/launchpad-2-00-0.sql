SET client_min_messages TO error;

DROP TABLE ProjectBugTracker CASCADE;
DROP TABLE BugTracker CASCADE;

--
-- PostgreSQL database dump
--

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET search_path = public, pg_catalog;

ALTER TABLE ONLY public.sourcepackagebugassignment DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.productbugassignment DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.sectionselection DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sectionselection DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.componentselection DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.componentselection DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.sourcepackage DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT "$6";
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugattachment DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugattachment DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugrelationship DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugrelationship DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.buglabel DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.buglabel DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.projectbugsystem DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.projectbugsystem DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugsystem DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugsystem DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugsystemtype DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugexternalref DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugexternalref DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugactivity DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productbugassignment DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.productbugassignment DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.sourcepackagebugassignment DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.sourcepackagebugassignment DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcepackagebugassignment DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.buginfestation DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.buginfestation DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.buginfestation DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.buginfestation DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.buginfestation DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugsubscription DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugsubscription DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bug DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.posubscription DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.posubscription DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.posubscription DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.translationeffortpotemplate DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.translationeffortpotemplate DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.translationeffortpotemplate DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.translationeffort DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.translationeffort DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.translationeffort DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.pocomment DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.pocomment DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.pocomment DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.pocomment DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.pocomment DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.potranslationsighting DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.potranslationsighting DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.potranslationsighting DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.potranslationsighting DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.pomsgidsighting DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.pomsgidsighting DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.pofile DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.pofile DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.pofile DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.pofile DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.pofile DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT "$6";
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.spokenin DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.spokenin DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.osfileinpackage DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.osfileinpackage DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.codereleaserelationship DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.codereleaserelationship DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.coderelease DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.coderelease DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.coderelease DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.packageselection DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.packageselection DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.packageselection DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.packageselection DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.packageselection DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.packagepublishing DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.packagepublishing DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.packagepublishing DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.packagepublishing DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.binarypackagefile DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.binarypackagefile DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.binarypackage DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.binarypackage DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.binarypackage DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.binarypackage DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.binarypackage DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.build DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.build DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.build DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.build DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.build DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.sourcepackageupload DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcepackageupload DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.sourcepackagereleasefile DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcepackagereleasefile DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.sourcepackagerelease DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.sourcepackagerelease DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.sourcepackagerelease DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcepackagerelease DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.packaging DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.packaging DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.sourcepackagelabel DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcepackagelabel DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.sourcepackagerelationship DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.sourcepackagerelationship DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcepackage DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.sourcepackage DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.sourcepackage DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productreleasefile DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.productreleasefile DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.libraryfilealias DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.distroarchrelease DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.distroarchrelease DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.distroarchrelease DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.distroreleaserole DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.distroreleaserole DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.distributionrole DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.distributionrole DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.distribution DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.builder DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.builder DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.processor DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.processor DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.processorfamily DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.archconfigentry DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.archconfigentry DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.archconfigentry DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.archconfigentry DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.archconfig DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.archconfig DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.manifestentry DROP CONSTRAINT "$7";
ALTER TABLE ONLY public.manifestentry DROP CONSTRAINT "$6";
ALTER TABLE ONLY public.manifestentry DROP CONSTRAINT "$5";
ALTER TABLE ONLY public.manifestentry DROP CONSTRAINT "$4";
ALTER TABLE ONLY public.manifestentry DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.manifest DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productbranchrelationship DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.productbranchrelationship DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.branchlabel DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.branchlabel DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.branchrelationship DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.branchrelationship DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.changesetfilehash DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.changesetfile DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.changesetfile DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.changeset DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.changeset DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.changeset DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.branch DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.branch DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.branch DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.archnamespace DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.archarchivelocationsigner DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.archarchivelocationsigner DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.archarchivelocation DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.archarchive DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productsvnmodule DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productbkbranch DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productcvsmodule DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productrelease DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.productrelease DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productseries DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productrole DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.productrole DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productlabel DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.productlabel DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.product DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.product DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.projectrole DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.projectrole DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.projectrelationship DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.projectrelationship DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.project DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.personlabel DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.personlabel DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.label DROP CONSTRAINT "$1";
ALTER TABLE ONLY public."schema" DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.teamparticipation DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.teamparticipation DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.membership DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.membership DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.ircid DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.jabberid DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.wikiname DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.archuserid DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.gpgkey DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.emailaddress DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.person DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT distrorelease_distribution_key;
ALTER TABLE ONLY public.distribution DROP CONSTRAINT distribution_name_key;
ALTER TABLE ONLY public.sectionselection DROP CONSTRAINT sectionselection_pkey;
ALTER TABLE ONLY public.componentselection DROP CONSTRAINT componentselection_pkey;
ALTER TABLE ONLY public.distroreleaserole DROP CONSTRAINT distroreleaserole_pkey;
ALTER TABLE ONLY public.distributionrole DROP CONSTRAINT distributionrole_pkey;
ALTER TABLE ONLY public.bug DROP CONSTRAINT bug_name_key;
ALTER TABLE ONLY public.potranslationsighting DROP CONSTRAINT potranslationsighting_pomsgset_key;
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT bugmessage_rfc822msgid_key;
ALTER TABLE ONLY public.projectbugsystem DROP CONSTRAINT projectbugsystem_project_key;
ALTER TABLE ONLY public.projectbugsystem DROP CONSTRAINT projectbugsystem_pkey;
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT sourcesource_branch_key;
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT sourcesource_pkey;
ALTER TABLE ONLY public.bugattachment DROP CONSTRAINT bugattachment_pkey;
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT bugmessage_pkey;
ALTER TABLE ONLY public.buglabel DROP CONSTRAINT buglabel_pkey;
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT bugwatch_pkey;
ALTER TABLE ONLY public.bugsystem DROP CONSTRAINT bugsystem_pkey;
ALTER TABLE ONLY public.bugsystemtype DROP CONSTRAINT bugsystemtype_name_key;
ALTER TABLE ONLY public.bugsystemtype DROP CONSTRAINT bugsystemtype_pkey;
ALTER TABLE ONLY public.bugexternalref DROP CONSTRAINT bugexternalref_pkey;
ALTER TABLE ONLY public.bugactivity DROP CONSTRAINT bugactivity_pkey;
ALTER TABLE ONLY public.productbugassignment DROP CONSTRAINT productbugassignment_bug_key;
ALTER TABLE ONLY public.productbugassignment DROP CONSTRAINT productbugassignment_pkey;
ALTER TABLE ONLY public.sourcepackagebugassignment DROP CONSTRAINT sourcepackagebugassignment_bug_key;
ALTER TABLE ONLY public.sourcepackagebugassignment DROP CONSTRAINT sourcepackagebugassignment_pkey;
ALTER TABLE ONLY public.buginfestation DROP CONSTRAINT buginfestation_pkey;
ALTER TABLE ONLY public.bugsubscription DROP CONSTRAINT bugsubscription_pkey;
ALTER TABLE ONLY public.bug DROP CONSTRAINT bug_pkey;
ALTER TABLE ONLY public.posubscription DROP CONSTRAINT posubscription_person_key;
ALTER TABLE ONLY public.posubscription DROP CONSTRAINT posubscription_pkey;
ALTER TABLE ONLY public.translationeffortpotemplate DROP CONSTRAINT translationeffortpotemplate_translationeffort_key;
ALTER TABLE ONLY public.translationeffort DROP CONSTRAINT translationeffort_name_key;
ALTER TABLE ONLY public.translationeffort DROP CONSTRAINT translationeffort_pkey;
ALTER TABLE ONLY public.pocomment DROP CONSTRAINT pocomment_pkey;
ALTER TABLE ONLY public.potranslationsighting DROP CONSTRAINT potranslationsighting_pkey;
ALTER TABLE ONLY public.pomsgidsighting DROP CONSTRAINT pomsgidsighting_pomsgset_key;
ALTER TABLE ONLY public.pomsgidsighting DROP CONSTRAINT pomsgidsighting_pkey;
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT pomsgset_potemplate_key;
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT pomsgset_pkey;
ALTER TABLE ONLY public.pofile DROP CONSTRAINT pofile_id_key;
ALTER TABLE ONLY public.pofile DROP CONSTRAINT pofile_pkey;
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT potemplate_product_key;
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT potemplate_name_key;
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT potemplate_pkey;
ALTER TABLE ONLY public.license DROP CONSTRAINT license_pkey;
ALTER TABLE ONLY public.spokenin DROP CONSTRAINT spokenin_pkey;
ALTER TABLE ONLY public.country DROP CONSTRAINT country_pkey;
ALTER TABLE ONLY public."language" DROP CONSTRAINT language_code_key;
ALTER TABLE ONLY public."language" DROP CONSTRAINT language_pkey;
ALTER TABLE ONLY public.potranslation DROP CONSTRAINT potranslation_translation_key;
ALTER TABLE ONLY public.potranslation DROP CONSTRAINT potranslation_pkey;
ALTER TABLE ONLY public.pomsgid DROP CONSTRAINT pomsgid_msgid_key;
ALTER TABLE ONLY public.pomsgid DROP CONSTRAINT pomsgid_pkey;
ALTER TABLE ONLY public.osfile DROP CONSTRAINT osfile_path_key;
ALTER TABLE ONLY public.osfile DROP CONSTRAINT osfile_pkey;
ALTER TABLE ONLY public.codereleaserelationship DROP CONSTRAINT codereleaserelationship_pkey;
ALTER TABLE ONLY public.coderelease DROP CONSTRAINT coderelease_pkey;
ALTER TABLE ONLY public.packageselection DROP CONSTRAINT packageselection_pkey;
ALTER TABLE ONLY public.packagepublishing DROP CONSTRAINT packagepublishing_pkey;
ALTER TABLE ONLY public.binarypackage DROP CONSTRAINT binarypackage_binarypackagename_key;
ALTER TABLE ONLY public.binarypackage DROP CONSTRAINT binarypackage_pkey;
ALTER TABLE ONLY public.binarypackagename DROP CONSTRAINT binarypackagename_name_key;
ALTER TABLE ONLY public.binarypackagename DROP CONSTRAINT binarypackagename_pkey;
ALTER TABLE ONLY public.build DROP CONSTRAINT build_pkey;
ALTER TABLE ONLY public.sourcepackageupload DROP CONSTRAINT sourcepackageupload_pkey;
ALTER TABLE ONLY public.sourcepackagerelease DROP CONSTRAINT sourcepackagerelease_pkey;
ALTER TABLE ONLY public.sourcepackagerelationship DROP CONSTRAINT sourcepackagerelationship_pkey;
ALTER TABLE ONLY public.sourcepackage DROP CONSTRAINT sourcepackage_pkey;
ALTER TABLE ONLY public.sourcepackagename DROP CONSTRAINT sourcepackagename_name_key;
ALTER TABLE ONLY public.sourcepackagename DROP CONSTRAINT sourcepackagename_pkey;
ALTER TABLE ONLY public.libraryfilealias DROP CONSTRAINT libraryfilealias_pkey;
ALTER TABLE ONLY public.libraryfilecontent DROP CONSTRAINT libraryfilecontent_pkey;
ALTER TABLE ONLY public.distroarchrelease DROP CONSTRAINT distroarchrelease_pkey;
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT distrorelease_pkey;
ALTER TABLE ONLY public.distribution DROP CONSTRAINT distribution_pkey;
ALTER TABLE ONLY public.section DROP CONSTRAINT section_name_key;
ALTER TABLE ONLY public.section DROP CONSTRAINT section_pkey;
ALTER TABLE ONLY public.component DROP CONSTRAINT component_name_key;
ALTER TABLE ONLY public.component DROP CONSTRAINT component_pkey;
ALTER TABLE ONLY public.builder DROP CONSTRAINT builder_fqdn_key;
ALTER TABLE ONLY public.builder DROP CONSTRAINT builder_pkey;
ALTER TABLE ONLY public.processor DROP CONSTRAINT processor_name_key;
ALTER TABLE ONLY public.processor DROP CONSTRAINT processor_pkey;
ALTER TABLE ONLY public.processorfamily DROP CONSTRAINT processorfamily_name_key;
ALTER TABLE ONLY public.processorfamily DROP CONSTRAINT processorfamily_pkey;
ALTER TABLE ONLY public.archconfig DROP CONSTRAINT archconfig_pkey;
ALTER TABLE ONLY public.manifestentry DROP CONSTRAINT manifestentry_manifest_key;
ALTER TABLE ONLY public.manifestentry DROP CONSTRAINT manifestentry_pkey;
ALTER TABLE ONLY public.manifest DROP CONSTRAINT manifest_pkey;
ALTER TABLE ONLY public.productbranchrelationship DROP CONSTRAINT productbranchrelationship_pkey;
ALTER TABLE ONLY public.branchrelationship DROP CONSTRAINT branchrelationship_pkey;
ALTER TABLE ONLY public.changesetfilehash DROP CONSTRAINT changesetfilehash_changesetfile_key;
ALTER TABLE ONLY public.changesetfilehash DROP CONSTRAINT changesetfilehash_pkey;
ALTER TABLE ONLY public.changesetfile DROP CONSTRAINT changesetfile_changeset_key;
ALTER TABLE ONLY public.changesetfile DROP CONSTRAINT changesetfile_pkey;
ALTER TABLE ONLY public.changesetfilename DROP CONSTRAINT changesetfilename_filename_key;
ALTER TABLE ONLY public.changesetfilename DROP CONSTRAINT changesetfilename_pkey;
ALTER TABLE ONLY public.changeset DROP CONSTRAINT changeset_id_key;
ALTER TABLE ONLY public.changeset DROP CONSTRAINT changeset_pkey;
ALTER TABLE ONLY public.branch DROP CONSTRAINT branch_pkey;
ALTER TABLE ONLY public.archnamespace DROP CONSTRAINT archnamespace_pkey;
ALTER TABLE ONLY public.archarchivelocation DROP CONSTRAINT archarchivelocation_pkey;
ALTER TABLE ONLY public.archarchive DROP CONSTRAINT archarchive_pkey;
ALTER TABLE ONLY public.productsvnmodule DROP CONSTRAINT productsvnmodule_pkey;
ALTER TABLE ONLY public.productbkbranch DROP CONSTRAINT productbkbranch_pkey;
ALTER TABLE ONLY public.productcvsmodule DROP CONSTRAINT productcvsmodule_pkey;
ALTER TABLE ONLY public.productrelease DROP CONSTRAINT productrelease_product_key;
ALTER TABLE ONLY public.productrelease DROP CONSTRAINT productrelease_pkey;
ALTER TABLE ONLY public.productseries DROP CONSTRAINT productseries_product_key;
ALTER TABLE ONLY public.productseries DROP CONSTRAINT productseries_pkey;
ALTER TABLE ONLY public.productrole DROP CONSTRAINT productrole_pkey;
ALTER TABLE ONLY public.productlabel DROP CONSTRAINT productlabel_product_key;
ALTER TABLE ONLY public.productlabel DROP CONSTRAINT productlabel_pkey;
ALTER TABLE ONLY public.product DROP CONSTRAINT product_id_key;
ALTER TABLE ONLY public.product DROP CONSTRAINT product_project_key;
ALTER TABLE ONLY public.product DROP CONSTRAINT product_pkey;
ALTER TABLE ONLY public.projectrole DROP CONSTRAINT projectrole_pkey;
ALTER TABLE ONLY public.projectrelationship DROP CONSTRAINT projectrelationship_pkey;
ALTER TABLE ONLY public.project DROP CONSTRAINT project_name_key;
ALTER TABLE ONLY public.project DROP CONSTRAINT project_pkey;
ALTER TABLE ONLY public.label DROP CONSTRAINT label_pkey;
ALTER TABLE ONLY public."schema" DROP CONSTRAINT schema_pkey;
ALTER TABLE ONLY public.teamparticipation DROP CONSTRAINT teamparticipation_team_key;
ALTER TABLE ONLY public.teamparticipation DROP CONSTRAINT teamparticipation_pkey;
ALTER TABLE ONLY public.membership DROP CONSTRAINT membership_person_key;
ALTER TABLE ONLY public.membership DROP CONSTRAINT membership_pkey;
ALTER TABLE ONLY public.ircid DROP CONSTRAINT ircid_pkey;
ALTER TABLE ONLY public.jabberid DROP CONSTRAINT jabberid_jabberid_key;
ALTER TABLE ONLY public.jabberid DROP CONSTRAINT jabberid_pkey;
ALTER TABLE ONLY public.wikiname DROP CONSTRAINT wikiname_wiki_key;
ALTER TABLE ONLY public.wikiname DROP CONSTRAINT wikiname_pkey;
ALTER TABLE ONLY public.archuserid DROP CONSTRAINT archuserid_archuserid_key;
ALTER TABLE ONLY public.archuserid DROP CONSTRAINT archuserid_pkey;
ALTER TABLE ONLY public.gpgkey DROP CONSTRAINT gpgkey_fingerprint_key;
ALTER TABLE ONLY public.gpgkey DROP CONSTRAINT gpgkey_keyid_key;
ALTER TABLE ONLY public.gpgkey DROP CONSTRAINT gpgkey_pkey;
ALTER TABLE ONLY public.emailaddress DROP CONSTRAINT emailaddress_pkey;
ALTER TABLE ONLY public.person DROP CONSTRAINT person_pkey;
DROP INDEX public.idx_emailaddress_email;
DROP INDEX public.idx_libraryfilecontent_sha1;
DROP TABLE public.sectionselection;
DROP TABLE public.componentselection;
DROP SEQUENCE public.distroreleaserole_id_seq;
DROP SEQUENCE public.distributionrole_id_seq;
DROP SEQUENCE public.projectbugsystem_id_seq;
DROP TABLE public.sourcesource;
DROP TABLE public.bugattachment;
DROP TABLE public.bugmessage;
DROP TABLE public.bugrelationship;
DROP TABLE public.buglabel;
DROP TABLE public.projectbugsystem;
DROP TABLE public.bugwatch;
DROP TABLE public.bugsystem;
DROP TABLE public.bugsystemtype;
DROP TABLE public.bugexternalref;
DROP TABLE public.bugactivity;
DROP TABLE public.productbugassignment;
DROP TABLE public.sourcepackagebugassignment;
DROP TABLE public.buginfestation;
DROP TABLE public.bugsubscription;
DROP TABLE public.bug;
DROP TABLE public.posubscription;
DROP TABLE public.translationeffortpotemplate;
DROP TABLE public.translationeffort;
DROP TABLE public.pocomment;
DROP TABLE public.potranslationsighting;
DROP TABLE public.pomsgidsighting;
DROP TABLE public.pomsgset;
DROP TABLE public.pofile;
DROP TABLE public.potemplate;
DROP TABLE public.license;
DROP TABLE public.spokenin;
DROP TABLE public.country;
DROP TABLE public."language";
DROP TABLE public.potranslation;
DROP TABLE public.pomsgid;
DROP TABLE public.osfileinpackage;
DROP TABLE public.osfile;
DROP TABLE public.codereleaserelationship;
DROP TABLE public.coderelease;
DROP TABLE public.packageselection;
DROP TABLE public.packagepublishing;
DROP TABLE public.binarypackagefile;
DROP TABLE public.binarypackage;
DROP TABLE public.binarypackagename;
DROP TABLE public.build;
DROP TABLE public.sourcepackageupload;
DROP TABLE public.sourcepackagereleasefile;
DROP TABLE public.sourcepackagerelease;
DROP TABLE public.packaging;
DROP TABLE public.sourcepackagelabel;
DROP TABLE public.sourcepackagerelationship;
DROP TABLE public.sourcepackage;
DROP TABLE public.sourcepackagename;
DROP TABLE public.productreleasefile;
DROP TABLE public.libraryfilealias;
DROP TABLE public.libraryfilecontent;
DROP TABLE public.distroarchrelease;
DROP TABLE public.distroreleaserole;
DROP TABLE public.distrorelease;
DROP TABLE public.distributionrole;
DROP TABLE public.distribution;
DROP TABLE public.section;
DROP TABLE public.component;
DROP TABLE public.builder;
DROP TABLE public.processor;
DROP TABLE public.processorfamily;
DROP TABLE public.archconfigentry;
DROP TABLE public.archconfig;
DROP TABLE public.manifestentry;
DROP TABLE public.manifest;
DROP TABLE public.productbranchrelationship;
DROP TABLE public.branchlabel;
DROP TABLE public.branchrelationship;
DROP TABLE public.changesetfilehash;
DROP TABLE public.changesetfile;
DROP TABLE public.changesetfilename;
DROP TABLE public.changeset;
DROP TABLE public.branch;
DROP TABLE public.archnamespace;
DROP TABLE public.archarchivelocationsigner;
DROP TABLE public.archarchivelocation;
DROP TABLE public.archarchive;
DROP TABLE public.productsvnmodule;
DROP TABLE public.productbkbranch;
DROP TABLE public.productcvsmodule;
DROP TABLE public.productrelease;
DROP TABLE public.productseries;
DROP TABLE public.productrole;
DROP TABLE public.productlabel;
DROP TABLE public.product;
DROP TABLE public.projectrole;
DROP TABLE public.projectrelationship;
DROP TABLE public.project;
DROP TABLE public.personlabel;
DROP TABLE public.label;
DROP TABLE public."schema";
DROP TABLE public.teamparticipation;
DROP TABLE public.membership;
DROP TABLE public.ircid;
DROP TABLE public.jabberid;
DROP TABLE public.wikiname;
DROP TABLE public.archuserid;
DROP TABLE public.gpgkey;
DROP TABLE public.emailaddress;
DROP TABLE public.person;

CREATE TABLE person (
    id serial NOT NULL,
    displayname text,
    givenname text,
    familyname text,
    "password" text,
    teamowner integer,
    teamdescription text,
    karma integer,
    karmatimestamp timestamp without time zone
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
    revoked boolean NOT NULL
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
    extensible boolean DEFAULT false NOT NULL
);



CREATE TABLE label (
    id serial NOT NULL,
    "schema" integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL
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
    CONSTRAINT "$2" CHECK ((name = lower(name)))
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
    CONSTRAINT "$3" CHECK ((name = lower(name)))
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
    displayname text NOT NULL
);



CREATE TABLE productrelease (
    id serial NOT NULL,
    product integer NOT NULL,
    datereleased timestamp without time zone NOT NULL,
    "version" text NOT NULL,
    title text,
    description text,
    changelog text,
    "owner" integer NOT NULL
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
    datecreated timestamp without time zone NOT NULL,
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
    name text NOT NULL
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
    CONSTRAINT "$2" CHECK ((name = lower(name)))
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
    CONSTRAINT "$6" CHECK ((name = lower(name)))
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
    CONSTRAINT lowercasename CHECK ((lower(name) = name))
);



CREATE TABLE sourcepackage (
    id serial NOT NULL,
    maintainer integer NOT NULL,
    shortdesc text NOT NULL,
    description text NOT NULL,
    manifest integer,
    distro integer,
    sourcepackagename integer NOT NULL
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
    srcpackageformat integer NOT NULL,
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
    dsc text
);



CREATE TABLE sourcepackagereleasefile (
    sourcepackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL
);



CREATE TABLE sourcepackageupload (
    distrorelease integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    uploadstatus integer NOT NULL
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
    changes text
);



CREATE TABLE binarypackagename (
    id serial NOT NULL,
    name text NOT NULL,
    CONSTRAINT "$1" CHECK ((name = lower(name)))
);



CREATE TABLE binarypackage (
    id serial NOT NULL,
    sourcepackagerelease integer NOT NULL,
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
    licence text
);



CREATE TABLE binarypackagefile (
    binarypackage integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL
);



CREATE TABLE packagepublishing (
    id serial NOT NULL,
    binarypackage integer NOT NULL,
    distroarchrelease integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer NOT NULL
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
    CONSTRAINT "$1" CHECK ((NOT ((productrelease IS NULL) AND (sourcepackagerelease IS NULL)))),
    CONSTRAINT "$2" CHECK ((NOT ((productrelease IS NOT NULL) AND (sourcepackagerelease IS NOT NULL))))
);



CREATE TABLE codereleaserelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL,
    CONSTRAINT "$1" CHECK ((subject <> object))
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
    "owner" integer
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
    filename text
);



CREATE TABLE pomsgset (
    id serial NOT NULL,
    primemsgid integer NOT NULL,
    "sequence" integer NOT NULL,
    potemplate integer NOT NULL,
    pofile integer,
    iscomplete boolean NOT NULL,
    obsolete boolean NOT NULL,
    fuzzy boolean NOT NULL,
    commenttext text,
    filereferences text,
    sourcecomment text,
    flagscomment text
);



CREATE TABLE pomsgidsighting (
    id serial NOT NULL,
    pomsgset integer NOT NULL,
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
    categories integer
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
    communityscore integer NOT NULL,
    communitytimestamp timestamp without time zone NOT NULL,
    activityscore integer NOT NULL,
    activitytimestamp timestamp without time zone NOT NULL,
    hits integer NOT NULL,
    hitstimestamp timestamp without time zone NOT NULL,
    shortdesc text NOT NULL,
    CONSTRAINT "$2" CHECK ((name = lower(name))),
    CONSTRAINT "$3" CHECK ((NOT (id = duplicateof))),
    CONSTRAINT notduplicateofself CHECK ((NOT (id = duplicateof)))
);



CREATE TABLE bugsubscription (
    id serial NOT NULL,
    person integer NOT NULL,
    bug integer NOT NULL,
    subscription integer NOT NULL
);



CREATE TABLE buginfestation (
    bug integer NOT NULL,
    coderelease integer NOT NULL,
    explicit boolean NOT NULL,
    infestation integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    creator integer NOT NULL,
    dateverified timestamp without time zone,
    verifiedby integer,
    lastmodified timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    lastmodifiedby integer NOT NULL
);



CREATE TABLE sourcepackagebugassignment (
    id serial NOT NULL,
    bug integer NOT NULL,
    sourcepackage integer NOT NULL,
    bugstatus integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    binarypackage integer,
    assignee integer NOT NULL
);



CREATE TABLE productbugassignment (
    id serial NOT NULL,
    bug integer NOT NULL,
    product integer NOT NULL,
    bugstatus integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    assignee integer NOT NULL
);



CREATE TABLE bugactivity (
    id serial NOT NULL,
    bug integer NOT NULL,
    datechanged timestamp without time zone NOT NULL,
    person integer NOT NULL,
    whatchanged text NOT NULL,
    oldvalue text NOT NULL,
    newvalue text NOT NULL,
    message text
);



CREATE TABLE bugexternalref (
    id serial NOT NULL,
    bug integer NOT NULL,
    bugreftype integer NOT NULL,
    data text NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE bugsystemtype (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    homepage text,
    "owner" integer NOT NULL
);



CREATE TABLE bugsystem (
    id serial NOT NULL,
    bugsystemtype integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    shortdesc text NOT NULL,
    baseurl text NOT NULL,
    "owner" integer NOT NULL,
    contactdetails text,
    CONSTRAINT "$3" CHECK ((name = lower(name)))
);



CREATE TABLE bugwatch (
    id serial NOT NULL,
    bug integer NOT NULL,
    bugsystem integer NOT NULL,
    remotebug text NOT NULL,
    remotestatus text NOT NULL,
    lastchanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    lastchecked timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);



CREATE TABLE projectbugsystem (
    project integer NOT NULL,
    bugsystem integer NOT NULL,
    id integer DEFAULT nextval('projectbugsystem_id_seq'::text) NOT NULL
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



CREATE TABLE bugmessage (
    id serial NOT NULL,
    bug integer NOT NULL,
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
    datedeactivated timestamp without time zone
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
    fileidreference text
);



CREATE SEQUENCE projectbugsystem_id_seq
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



CREATE INDEX idx_libraryfilecontent_sha1 ON libraryfilecontent USING btree (sha1);



CREATE UNIQUE INDEX idx_emailaddress_email ON emailaddress USING btree (lower(email));



ALTER TABLE ONLY person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);



ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress_pkey PRIMARY KEY (id);



ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_pkey PRIMARY KEY (id);



ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_keyid_key UNIQUE (keyid);



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



ALTER TABLE ONLY sourcepackageupload
    ADD CONSTRAINT sourcepackageupload_pkey PRIMARY KEY (distrorelease, sourcepackagerelease);



ALTER TABLE ONLY build
    ADD CONSTRAINT build_pkey PRIMARY KEY (id);



ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_pkey PRIMARY KEY (id);



ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_name_key UNIQUE (name);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_pkey PRIMARY KEY (id);



ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_binarypackagename_key UNIQUE (binarypackagename, "version");



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
    ADD CONSTRAINT potemplate_name_key UNIQUE (name);



ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_product_key UNIQUE (product, name);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_id_key UNIQUE (id, potemplate);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_potemplate_key UNIQUE (potemplate, pofile, primemsgid);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_pkey PRIMARY KEY (id);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_pomsgset_key UNIQUE (pomsgset, pomsgid);



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



ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT buginfestation_pkey PRIMARY KEY (bug, coderelease);



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



ALTER TABLE ONLY bugsystemtype
    ADD CONSTRAINT bugsystemtype_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugsystemtype
    ADD CONSTRAINT bugsystemtype_name_key UNIQUE (name);



ALTER TABLE ONLY bugsystem
    ADD CONSTRAINT bugsystem_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_pkey PRIMARY KEY (id);



ALTER TABLE ONLY buglabel
    ADD CONSTRAINT buglabel_pkey PRIMARY KEY (bug, label);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_pkey PRIMARY KEY (id);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT sourcesource_pkey PRIMARY KEY (id);



ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT sourcesource_branch_key UNIQUE (branch);



ALTER TABLE ONLY projectbugsystem
    ADD CONSTRAINT projectbugsystem_pkey PRIMARY KEY (id);



ALTER TABLE ONLY projectbugsystem
    ADD CONSTRAINT projectbugsystem_project_key UNIQUE (project, bugsystem);



ALTER TABLE ONLY bugmessage
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



ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$4" FOREIGN KEY (component) REFERENCES label(id);



ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);



ALTER TABLE ONLY sourcepackageupload
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);



ALTER TABLE ONLY sourcepackageupload
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
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);



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
    ADD CONSTRAINT "$1" FOREIGN KEY (primemsgid) REFERENCES pomsgid(id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$3" FOREIGN KEY (pofile) REFERENCES pofile(id);



ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$4" FOREIGN KEY (pofile, potemplate) REFERENCES pofile(id, potemplate);



ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT "$1" FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);



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



ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$2" FOREIGN KEY (coderelease) REFERENCES coderelease(id);



ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$3" FOREIGN KEY (creator) REFERENCES person(id);



ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$4" FOREIGN KEY (verifiedby) REFERENCES person(id);



ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$5" FOREIGN KEY (lastmodifiedby) REFERENCES person(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);



ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$3" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$2" FOREIGN KEY (product) REFERENCES sourcepackage(id);



ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugsystemtype
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugsystem
    ADD CONSTRAINT "$1" FOREIGN KEY (bugsystemtype) REFERENCES bugsystemtype(id);



ALTER TABLE ONLY bugsystem
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$2" FOREIGN KEY (bugsystem) REFERENCES bugsystem(id);



ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$3" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY projectbugsystem
    ADD CONSTRAINT "$1" FOREIGN KEY (project) REFERENCES project(id);



ALTER TABLE ONLY projectbugsystem
    ADD CONSTRAINT "$2" FOREIGN KEY (bugsystem) REFERENCES bugsystem(id);



ALTER TABLE ONLY buglabel
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY buglabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);



ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES bug(id);



ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES bug(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$3" FOREIGN KEY (parent) REFERENCES bugmessage(id);



ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$4" FOREIGN KEY (distribution) REFERENCES distribution(id);



ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT "$1" FOREIGN KEY (bugmessage) REFERENCES bugmessage(id);



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



COMMENT ON SCHEMA public IS 'Standard public schema';


