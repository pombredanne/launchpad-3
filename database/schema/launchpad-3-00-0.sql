SET client_min_messages TO fatal;

DROP TABLE SourcepackagePublishing CASCADE;
DROP SEQUENCE sourcepackagepublishing_id_seq;

--
-- PostgreSQL database dump
--

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET search_path = public, pg_catalog;

ALTER TABLE ONLY public.sourcepackagebugassignment DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.productbugassignment DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.build DROP CONSTRAINT "$6";
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
ALTER TABLE ONLY public.projectbugtracker DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.projectbugtracker DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT "$3";
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugtracker DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugtracker DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugtrackertype DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugexternalref DROP CONSTRAINT "$2";
ALTER TABLE ONLY public.bugexternalref DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.bugactivity DROP CONSTRAINT "$1";
ALTER TABLE ONLY public.productbugassignment DROP CONSTRAINT "$1";
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
ALTER TABLE ONLY public.gpgkey DROP CONSTRAINT gpg_fingerprint_key;
ALTER TABLE ONLY public.label DROP CONSTRAINT label_schema_key;
ALTER TABLE ONLY public.distrorelease DROP CONSTRAINT distrorelease_distribution_key;
ALTER TABLE ONLY public.distribution DROP CONSTRAINT distribution_name_key;
ALTER TABLE ONLY public.sectionselection DROP CONSTRAINT sectionselection_pkey;
ALTER TABLE ONLY public.componentselection DROP CONSTRAINT componentselection_pkey;
ALTER TABLE ONLY public.distroreleaserole DROP CONSTRAINT distroreleaserole_pkey;
ALTER TABLE ONLY public.distributionrole DROP CONSTRAINT distributionrole_pkey;
ALTER TABLE ONLY public.bug DROP CONSTRAINT bug_name_key;
ALTER TABLE ONLY public.potranslationsighting DROP CONSTRAINT potranslationsighting_pomsgset_key;
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT bugmessage_rfc822msgid_key;
ALTER TABLE ONLY public.projectbugtracker DROP CONSTRAINT projectbugsystem_project_key;
ALTER TABLE ONLY public.projectbugtracker DROP CONSTRAINT projectbugsystem_pkey;
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT sourcesource_branch_key;
ALTER TABLE ONLY public.sourcesource DROP CONSTRAINT sourcesource_pkey;
ALTER TABLE ONLY public.bugattachment DROP CONSTRAINT bugattachment_pkey;
ALTER TABLE ONLY public.bugmessage DROP CONSTRAINT bugmessage_pkey;
ALTER TABLE ONLY public.buglabel DROP CONSTRAINT buglabel_pkey;
ALTER TABLE ONLY public.bugwatch DROP CONSTRAINT bugwatch_pkey;
ALTER TABLE ONLY public.bugtracker DROP CONSTRAINT bugsystem_pkey;
ALTER TABLE ONLY public.bugtrackertype DROP CONSTRAINT bugsystemtype_name_key;
ALTER TABLE ONLY public.bugtrackertype DROP CONSTRAINT bugsystemtype_pkey;
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
ALTER TABLE ONLY public.pomsgidsighting DROP CONSTRAINT pomsgidsighting_pkey;
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT pomsgset_potemplate_key;
ALTER TABLE ONLY public.pomsgset DROP CONSTRAINT pomsgset_pkey;
ALTER TABLE ONLY public.pofile DROP CONSTRAINT pofile_id_key;
ALTER TABLE ONLY public.pofile DROP CONSTRAINT pofile_pkey;
ALTER TABLE ONLY public.potemplate DROP CONSTRAINT potemplate_product_key;
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
ALTER TABLE ONLY public.gpgkey DROP CONSTRAINT gpgkey_pkey;
ALTER TABLE ONLY public.emailaddress DROP CONSTRAINT emailaddress_pkey;
ALTER TABLE ONLY public.person DROP CONSTRAINT person_pkey;
DROP INDEX public.bugtracker_name_key;
DROP INDEX public.sourcepackage_sourcepackagename_key;
DROP INDEX public.sourcepackagerelease_sourcepackage_key;
DROP INDEX public.sourcepackageupload_sourcepackagerelease_key;
DROP INDEX public.binarypackage_binarypackagename_key2;
DROP INDEX public.packagepublishing_binarypackage_key;
DROP INDEX public.schema_name_key;
DROP INDEX public.person_name_key;
DROP INDEX public.pomsgset_index_primemsgid;
DROP INDEX public.pomsgset_index_pofile;
DROP INDEX public.pomsgset_index_potemplate;
DROP INDEX public.pomsgidsighting_pluralform_idx;
DROP INDEX public.pomsgidsighting_inlastrevision_idx;
DROP INDEX public.pomsgidsighting_pomsgid_idx;
DROP INDEX public.pomsgidsighting_pomsgset_idx;
DROP INDEX public.idx_emailaddress_email;
DROP INDEX public.idx_libraryfilecontent_sha1;
DROP TABLE public.sectionselection;
DROP TABLE public.componentselection;
DROP SEQUENCE public.distroreleaserole_id_seq;
DROP SEQUENCE public.distributionrole_id_seq;
DROP SEQUENCE public.projectbugtracker_id_seq;
DROP TABLE public.sourcesource;
DROP TABLE public.bugattachment;
DROP TABLE public.bugmessage;
DROP TABLE public.bugrelationship;
DROP TABLE public.buglabel;
DROP TABLE public.projectbugtracker;
DROP TABLE public.bugwatch;
DROP TABLE public.bugtracker;
DROP TABLE public.bugtrackertype;
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
--
-- TOC entry 8 (OID 26644)
-- Name: person; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE person (
    id serial NOT NULL,
    displayname text,
    givenname text,
    familyname text,
    "password" text,
    teamowner integer,
    teamdescription text,
    karma integer,
    karmatimestamp timestamp without time zone,
    name text NOT NULL,
    CONSTRAINT "$2" CHECK ((name = lower(name)))
);


--
-- TOC entry 9 (OID 26658)
-- Name: emailaddress; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE emailaddress (
    id serial NOT NULL,
    email text NOT NULL,
    person integer NOT NULL,
    status integer NOT NULL
);


--
-- TOC entry 10 (OID 26674)
-- Name: gpgkey; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 11 (OID 26692)
-- Name: archuserid; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE archuserid (
    id serial NOT NULL,
    person integer NOT NULL,
    archuserid text NOT NULL
);


--
-- TOC entry 12 (OID 26708)
-- Name: wikiname; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE wikiname (
    id serial NOT NULL,
    person integer NOT NULL,
    wiki text NOT NULL,
    wikiname text NOT NULL
);


--
-- TOC entry 13 (OID 26724)
-- Name: jabberid; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE jabberid (
    id serial NOT NULL,
    person integer NOT NULL,
    jabberid text NOT NULL
);


--
-- TOC entry 14 (OID 26740)
-- Name: ircid; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE ircid (
    id serial NOT NULL,
    person integer NOT NULL,
    network text NOT NULL,
    nickname text NOT NULL
);


--
-- TOC entry 15 (OID 26754)
-- Name: membership; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE membership (
    id serial NOT NULL,
    person integer NOT NULL,
    team integer NOT NULL,
    role integer NOT NULL,
    status integer NOT NULL
);


--
-- TOC entry 16 (OID 26771)
-- Name: teamparticipation; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE teamparticipation (
    id serial NOT NULL,
    team integer NOT NULL,
    person integer NOT NULL
);


--
-- TOC entry 17 (OID 26788)
-- Name: schema; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE "schema" (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL,
    extensible boolean DEFAULT false NOT NULL,
    CONSTRAINT "$2" CHECK ((name = lower(name)))
);


--
-- TOC entry 18 (OID 26803)
-- Name: label; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE label (
    id serial NOT NULL,
    "schema" integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL
);


--
-- TOC entry 19 (OID 26815)
-- Name: personlabel; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE personlabel (
    person integer NOT NULL,
    label integer NOT NULL
);


--
-- TOC entry 20 (OID 26827)
-- Name: project; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 21 (OID 26844)
-- Name: projectrelationship; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE projectrelationship (
    id serial NOT NULL,
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);


--
-- TOC entry 22 (OID 26859)
-- Name: projectrole; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE projectrole (
    id serial NOT NULL,
    person integer NOT NULL,
    role integer NOT NULL,
    project integer NOT NULL
);


--
-- TOC entry 23 (OID 26874)
-- Name: product; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 24 (OID 26897)
-- Name: productlabel; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productlabel (
    id serial NOT NULL,
    product integer NOT NULL,
    label integer NOT NULL
);


--
-- TOC entry 25 (OID 26914)
-- Name: productrole; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productrole (
    id serial NOT NULL,
    person integer NOT NULL,
    role integer NOT NULL,
    product integer NOT NULL
);


--
-- TOC entry 26 (OID 26929)
-- Name: productseries; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productseries (
    id serial NOT NULL,
    product integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL
);


--
-- TOC entry 27 (OID 26945)
-- Name: productrelease; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 28 (OID 26965)
-- Name: productcvsmodule; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productcvsmodule (
    id serial NOT NULL,
    product integer NOT NULL,
    anonroot text NOT NULL,
    module text NOT NULL,
    weburl text
);


--
-- TOC entry 29 (OID 26979)
-- Name: productbkbranch; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productbkbranch (
    id serial NOT NULL,
    product integer NOT NULL,
    locationurl text NOT NULL,
    weburl text
);


--
-- TOC entry 30 (OID 26993)
-- Name: productsvnmodule; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productsvnmodule (
    id serial NOT NULL,
    product integer NOT NULL,
    locationurl text NOT NULL,
    weburl text
);


--
-- TOC entry 31 (OID 27007)
-- Name: archarchive; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE archarchive (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    visible boolean NOT NULL,
    "owner" integer
);


--
-- TOC entry 32 (OID 27021)
-- Name: archarchivelocation; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE archarchivelocation (
    id serial NOT NULL,
    archive integer NOT NULL,
    archivetype integer NOT NULL,
    url text NOT NULL,
    gpgsigned boolean NOT NULL
);


--
-- TOC entry 33 (OID 27033)
-- Name: archarchivelocationsigner; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE archarchivelocationsigner (
    archarchivelocation integer NOT NULL,
    gpgkey integer NOT NULL
);


--
-- TOC entry 34 (OID 27045)
-- Name: archnamespace; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE archnamespace (
    id serial NOT NULL,
    archarchive integer NOT NULL,
    category text NOT NULL,
    branch text,
    "version" text,
    visible boolean NOT NULL
);


--
-- TOC entry 35 (OID 27059)
-- Name: branch; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE branch (
    id serial NOT NULL,
    archnamespace integer NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer,
    product integer
);


--
-- TOC entry 36 (OID 27081)
-- Name: changeset; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE changeset (
    id serial NOT NULL,
    branch integer NOT NULL,
    datecreated timestamp without time zone NOT NULL,
    name text NOT NULL,
    logmessage text NOT NULL,
    archid integer,
    gpgkey integer
);


--
-- TOC entry 37 (OID 27105)
-- Name: changesetfilename; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE changesetfilename (
    id serial NOT NULL,
    filename text NOT NULL
);


--
-- TOC entry 38 (OID 27117)
-- Name: changesetfile; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE changesetfile (
    id serial NOT NULL,
    changeset integer NOT NULL,
    changesetfilename integer NOT NULL,
    filecontents bytea NOT NULL,
    filesize integer NOT NULL
);


--
-- TOC entry 39 (OID 27137)
-- Name: changesetfilehash; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE changesetfilehash (
    id serial NOT NULL,
    changesetfile integer NOT NULL,
    hashalg integer NOT NULL,
    hash bytea NOT NULL
);


--
-- TOC entry 40 (OID 27151)
-- Name: branchrelationship; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE branchrelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);


--
-- TOC entry 41 (OID 27163)
-- Name: branchlabel; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE branchlabel (
    branch integer NOT NULL,
    label integer NOT NULL
);


--
-- TOC entry 42 (OID 27175)
-- Name: productbranchrelationship; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productbranchrelationship (
    id serial NOT NULL,
    product integer NOT NULL,
    branch integer NOT NULL,
    label integer NOT NULL
);


--
-- TOC entry 43 (OID 27190)
-- Name: manifest; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE manifest (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);


--
-- TOC entry 44 (OID 27202)
-- Name: manifestentry; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 45 (OID 27236)
-- Name: archconfig; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE archconfig (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    productrelease integer,
    "owner" integer
);


--
-- TOC entry 46 (OID 27252)
-- Name: archconfigentry; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE archconfigentry (
    archconfig integer NOT NULL,
    "path" text NOT NULL,
    branch integer NOT NULL,
    changeset integer
);


--
-- TOC entry 47 (OID 27275)
-- Name: processorfamily; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE processorfamily (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL
);


--
-- TOC entry 48 (OID 27291)
-- Name: processor; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE processor (
    id serial NOT NULL,
    family integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL
);


--
-- TOC entry 49 (OID 27311)
-- Name: builder; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE builder (
    id serial NOT NULL,
    processor integer NOT NULL,
    fqdn text NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    "owner" integer NOT NULL
);


--
-- TOC entry 50 (OID 27331)
-- Name: component; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE component (
    id serial NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 51 (OID 27343)
-- Name: section; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE section (
    id serial NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 52 (OID 27355)
-- Name: distribution; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE distribution (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    domainname text NOT NULL,
    "owner" integer NOT NULL,
    CONSTRAINT "$2" CHECK ((name = lower(name)))
);


--
-- TOC entry 53 (OID 27367)
-- Name: distributionrole; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE distributionrole (
    person integer NOT NULL,
    distribution integer NOT NULL,
    role integer NOT NULL,
    id integer DEFAULT nextval('DistributionRole_id_seq'::text) NOT NULL
);


--
-- TOC entry 54 (OID 27379)
-- Name: distrorelease; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 55 (OID 27407)
-- Name: distroreleaserole; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE distroreleaserole (
    person integer NOT NULL,
    distrorelease integer NOT NULL,
    role integer NOT NULL,
    id integer DEFAULT nextval('DistroreleaseRole_id_seq'::text) NOT NULL
);


--
-- TOC entry 56 (OID 27419)
-- Name: distroarchrelease; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE distroarchrelease (
    id serial NOT NULL,
    distrorelease integer NOT NULL,
    processorfamily integer NOT NULL,
    architecturetag text NOT NULL,
    "owner" integer NOT NULL
);


--
-- TOC entry 57 (OID 27441)
-- Name: libraryfilecontent; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE libraryfilecontent (
    id serial NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datemirrored timestamp without time zone,
    filesize integer NOT NULL,
    sha1 character(40) NOT NULL
);


--
-- TOC entry 58 (OID 27450)
-- Name: libraryfilealias; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE libraryfilealias (
    id serial NOT NULL,
    content integer NOT NULL,
    filename text NOT NULL,
    mimetype text NOT NULL
);


--
-- TOC entry 59 (OID 27462)
-- Name: productreleasefile; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productreleasefile (
    productrelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL
);


--
-- TOC entry 60 (OID 27474)
-- Name: sourcepackagename; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE sourcepackagename (
    id serial NOT NULL,
    name text NOT NULL,
    CONSTRAINT lowercasename CHECK ((lower(name) = name))
);


--
-- TOC entry 61 (OID 27486)
-- Name: sourcepackage; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE sourcepackage (
    id serial NOT NULL,
    maintainer integer NOT NULL,
    shortdesc text NOT NULL,
    description text NOT NULL,
    manifest integer,
    distro integer,
    sourcepackagename integer NOT NULL
);


--
-- TOC entry 62 (OID 27506)
-- Name: sourcepackagerelationship; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE sourcepackagerelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL,
    CONSTRAINT "$1" CHECK ((subject <> object))
);


--
-- TOC entry 63 (OID 27519)
-- Name: sourcepackagelabel; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE sourcepackagelabel (
    sourcepackage integer NOT NULL,
    label integer NOT NULL
);


--
-- TOC entry 64 (OID 27529)
-- Name: packaging; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE packaging (
    sourcepackage integer NOT NULL,
    packaging integer NOT NULL,
    product integer NOT NULL
);


--
-- TOC entry 65 (OID 27541)
-- Name: sourcepackagerelease; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 66 (OID 27566)
-- Name: sourcepackagereleasefile; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE sourcepackagereleasefile (
    sourcepackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL
);


--
-- TOC entry 67 (OID 27576)
-- Name: sourcepackageupload; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE sourcepackageupload (
    distrorelease integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    uploadstatus integer NOT NULL
);


--
-- TOC entry 68 (OID 27590)
-- Name: build; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 69 (OID 27621)
-- Name: binarypackagename; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE binarypackagename (
    id serial NOT NULL,
    name text NOT NULL,
    CONSTRAINT "$1" CHECK ((name = lower(name)))
);


--
-- TOC entry 70 (OID 27633)
-- Name: binarypackage; Type: TABLE; Schema: public; Owner: importd
--

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
    licence text
);


--
-- TOC entry 71 (OID 27663)
-- Name: binarypackagefile; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE binarypackagefile (
    binarypackage integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL
);


--
-- TOC entry 72 (OID 27675)
-- Name: packagepublishing; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE packagepublishing (
    id serial NOT NULL,
    binarypackage integer NOT NULL,
    distroarchrelease integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer NOT NULL
);


--
-- TOC entry 73 (OID 27698)
-- Name: packageselection; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 74 (OID 27725)
-- Name: coderelease; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE coderelease (
    id serial NOT NULL,
    productrelease integer,
    sourcepackagerelease integer,
    manifest integer,
    CONSTRAINT "$1" CHECK ((NOT ((productrelease IS NULL) AND (sourcepackagerelease IS NULL)))),
    CONSTRAINT "$2" CHECK ((NOT ((productrelease IS NOT NULL) AND (sourcepackagerelease IS NOT NULL))))
);


--
-- TOC entry 75 (OID 27744)
-- Name: codereleaserelationship; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE codereleaserelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL,
    CONSTRAINT "$1" CHECK ((subject <> object))
);


--
-- TOC entry 76 (OID 27759)
-- Name: osfile; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE osfile (
    id serial NOT NULL,
    "path" text NOT NULL
);


--
-- TOC entry 77 (OID 27769)
-- Name: osfileinpackage; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE osfileinpackage (
    osfile integer NOT NULL,
    binarypackage integer NOT NULL,
    unixperms integer NOT NULL,
    conffile boolean NOT NULL,
    createdoninstall boolean NOT NULL
);


--
-- TOC entry 78 (OID 27781)
-- Name: pomsgid; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE pomsgid (
    id serial NOT NULL,
    msgid text NOT NULL
);


--
-- TOC entry 79 (OID 27793)
-- Name: potranslation; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE potranslation (
    id serial NOT NULL,
    translation text NOT NULL
);


--
-- TOC entry 80 (OID 27805)
-- Name: language; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE "language" (
    id serial NOT NULL,
    code text NOT NULL,
    englishname text,
    nativename text,
    pluralforms integer,
    pluralexpression text,
    CONSTRAINT "$1" CHECK ((((pluralforms IS NOT NULL) AND (pluralexpression IS NOT NULL)) OR ((pluralforms IS NULL) AND (pluralexpression IS NULL))))
);


--
-- TOC entry 81 (OID 27818)
-- Name: country; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE country (
    id serial NOT NULL,
    iso3166code2 character(2) NOT NULL,
    iso3166code3 character(3) NOT NULL,
    name text NOT NULL,
    title text,
    description text
);


--
-- TOC entry 82 (OID 27826)
-- Name: spokenin; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE spokenin (
    "language" integer NOT NULL,
    country integer NOT NULL
);


--
-- TOC entry 83 (OID 27840)
-- Name: license; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE license (
    id serial NOT NULL,
    legalese text NOT NULL
);


--
-- TOC entry 84 (OID 27850)
-- Name: potemplate; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 85 (OID 27889)
-- Name: pofile; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 86 (OID 27921)
-- Name: pomsgset; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 87 (OID 27949)
-- Name: pomsgidsighting; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE pomsgidsighting (
    id serial NOT NULL,
    pomsgset integer NOT NULL,
    pomsgid integer NOT NULL,
    datefirstseen timestamp without time zone NOT NULL,
    datelastseen timestamp without time zone NOT NULL,
    inlastrevision boolean NOT NULL,
    pluralform integer NOT NULL
);


--
-- TOC entry 88 (OID 27966)
-- Name: potranslationsighting; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 89 (OID 27993)
-- Name: pocomment; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 90 (OID 28024)
-- Name: translationeffort; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 91 (OID 28046)
-- Name: translationeffortpotemplate; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE translationeffortpotemplate (
    translationeffort integer NOT NULL,
    potemplate integer NOT NULL,
    priority integer NOT NULL,
    category integer
);


--
-- TOC entry 92 (OID 28064)
-- Name: posubscription; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE posubscription (
    id serial NOT NULL,
    person integer NOT NULL,
    potemplate integer NOT NULL,
    "language" integer,
    notificationinterval interval,
    lastnotified timestamp without time zone
);


--
-- TOC entry 93 (OID 28085)
-- Name: bug; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 94 (OID 28102)
-- Name: bugsubscription; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE bugsubscription (
    id serial NOT NULL,
    person integer NOT NULL,
    bug integer NOT NULL,
    subscription integer NOT NULL
);


--
-- TOC entry 95 (OID 28115)
-- Name: buginfestation; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 96 (OID 28143)
-- Name: sourcepackagebugassignment; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE sourcepackagebugassignment (
    id serial NOT NULL,
    bug integer NOT NULL,
    sourcepackage integer NOT NULL,
    bugstatus integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    binarypackagename integer,
    assignee integer
);


--
-- TOC entry 97 (OID 28164)
-- Name: productbugassignment; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE productbugassignment (
    id serial NOT NULL,
    bug integer NOT NULL,
    product integer NOT NULL,
    bugstatus integer NOT NULL,
    priority integer NOT NULL,
    severity integer NOT NULL,
    assignee integer
);


--
-- TOC entry 98 (OID 28181)
-- Name: bugactivity; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 99 (OID 28195)
-- Name: bugexternalref; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE bugexternalref (
    id serial NOT NULL,
    bug integer NOT NULL,
    bugreftype integer NOT NULL,
    data text NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);


--
-- TOC entry 100 (OID 28214)
-- Name: bugtrackertype; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE bugtrackertype (
    id serial NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    homepage text,
    "owner" integer NOT NULL
);


--
-- TOC entry 101 (OID 28230)
-- Name: bugtracker; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE bugtracker (
    id serial NOT NULL,
    bugtrackertype integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    shortdesc text NOT NULL,
    baseurl text NOT NULL,
    "owner" integer NOT NULL,
    contactdetails text,
    CONSTRAINT "$3" CHECK ((name = lower(name))),
    CONSTRAINT "$4" CHECK ((name = lower(name)))
);


--
-- TOC entry 102 (OID 28248)
-- Name: bugwatch; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE bugwatch (
    id serial NOT NULL,
    bug integer NOT NULL,
    bugtracker integer NOT NULL,
    remotebug text NOT NULL,
    remotestatus text NOT NULL,
    lastchanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    lastchecked timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    "owner" integer NOT NULL
);


--
-- TOC entry 103 (OID 28271)
-- Name: projectbugtracker; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE projectbugtracker (
    project integer NOT NULL,
    bugtracker integer NOT NULL,
    id integer DEFAULT nextval('projectbugtracker_id_seq'::text) NOT NULL
);


--
-- TOC entry 104 (OID 28283)
-- Name: buglabel; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE buglabel (
    bug integer NOT NULL,
    label integer NOT NULL
);


--
-- TOC entry 105 (OID 28295)
-- Name: bugrelationship; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE bugrelationship (
    subject integer NOT NULL,
    label integer NOT NULL,
    object integer NOT NULL
);


--
-- TOC entry 106 (OID 28307)
-- Name: bugmessage; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 107 (OID 28334)
-- Name: bugattachment; Type: TABLE; Schema: public; Owner: importd
--

CREATE TABLE bugattachment (
    id serial NOT NULL,
    bugmessage integer NOT NULL,
    name text,
    description text,
    libraryfile integer NOT NULL,
    datedeactivated timestamp without time zone
);


--
-- TOC entry 108 (OID 28352)
-- Name: sourcesource; Type: TABLE; Schema: public; Owner: importd
--

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


--
-- TOC entry 5 (OID 46687)
-- Name: projectbugtracker_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE projectbugtracker_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


--
-- TOC entry 6 (OID 46715)
-- Name: distributionrole_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE distributionrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


--
-- TOC entry 7 (OID 46717)
-- Name: distroreleaserole_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE distroreleaserole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


--
-- TOC entry 109 (OID 46728)
-- Name: componentselection; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE componentselection (
    id serial NOT NULL,
    distrorelease integer NOT NULL,
    component integer NOT NULL
);


--
-- TOC entry 110 (OID 46743)
-- Name: sectionselection; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE sectionselection (
    id serial NOT NULL,
    distrorelease integer NOT NULL,
    section integer NOT NULL
);


--
-- TOC entry 185 (OID 27447)
-- Name: idx_libraryfilecontent_sha1; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX idx_libraryfilecontent_sha1 ON libraryfilecontent USING btree (sha1);


--
-- TOC entry 114 (OID 46708)
-- Name: idx_emailaddress_email; Type: INDEX; Schema: public; Owner: importd
--

CREATE UNIQUE INDEX idx_emailaddress_email ON emailaddress USING btree (lower(email));


--
-- TOC entry 232 (OID 212159)
-- Name: pomsgidsighting_pomsgset_idx; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX pomsgidsighting_pomsgset_idx ON pomsgidsighting USING btree (pomsgset);


--
-- TOC entry 231 (OID 212160)
-- Name: pomsgidsighting_pomsgid_idx; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX pomsgidsighting_pomsgid_idx ON pomsgidsighting USING btree (pomsgid);


--
-- TOC entry 228 (OID 212161)
-- Name: pomsgidsighting_inlastrevision_idx; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX pomsgidsighting_inlastrevision_idx ON pomsgidsighting USING btree (inlastrevision);


--
-- TOC entry 230 (OID 212162)
-- Name: pomsgidsighting_pluralform_idx; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX pomsgidsighting_pluralform_idx ON pomsgidsighting USING btree (pluralform);


--
-- TOC entry 224 (OID 212163)
-- Name: pomsgset_index_potemplate; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX pomsgset_index_potemplate ON pomsgset USING btree (potemplate);


--
-- TOC entry 223 (OID 212164)
-- Name: pomsgset_index_pofile; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX pomsgset_index_pofile ON pomsgset USING btree (pofile);


--
-- TOC entry 225 (OID 212165)
-- Name: pomsgset_index_primemsgid; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX pomsgset_index_primemsgid ON pomsgset USING btree (primemsgid);


--
-- TOC entry 111 (OID 212170)
-- Name: person_name_key; Type: INDEX; Schema: public; Owner: importd
--

CREATE UNIQUE INDEX person_name_key ON person USING btree (name);


--
-- TOC entry 129 (OID 212172)
-- Name: schema_name_key; Type: INDEX; Schema: public; Owner: importd
--

CREATE UNIQUE INDEX schema_name_key ON "schema" USING btree (name);


--
-- TOC entry 203 (OID 212184)
-- Name: packagepublishing_binarypackage_key; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX packagepublishing_binarypackage_key ON packagepublishing USING btree (binarypackage);


--
-- TOC entry 201 (OID 212185)
-- Name: binarypackage_binarypackagename_key2; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX binarypackage_binarypackagename_key2 ON binarypackage USING btree (binarypackagename);


--
-- TOC entry 196 (OID 212186)
-- Name: sourcepackageupload_sourcepackagerelease_key; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX sourcepackageupload_sourcepackagerelease_key ON sourcepackageupload USING btree (sourcepackagerelease);


--
-- TOC entry 194 (OID 212187)
-- Name: sourcepackagerelease_sourcepackage_key; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX sourcepackagerelease_sourcepackage_key ON sourcepackagerelease USING btree (sourcepackage);


--
-- TOC entry 191 (OID 212188)
-- Name: sourcepackage_sourcepackagename_key; Type: INDEX; Schema: public; Owner: importd
--

CREATE INDEX sourcepackage_sourcepackagename_key ON sourcepackage USING btree (sourcepackagename);


--
-- TOC entry 254 (OID 212199)
-- Name: bugtracker_name_key; Type: INDEX; Schema: public; Owner: importd
--

CREATE UNIQUE INDEX bugtracker_name_key ON bugtracker USING btree (name);


--
-- TOC entry 112 (OID 26650)
-- Name: person_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);


--
-- TOC entry 113 (OID 26664)
-- Name: emailaddress_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT emailaddress_pkey PRIMARY KEY (id);


--
-- TOC entry 117 (OID 26680)
-- Name: gpgkey_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_pkey PRIMARY KEY (id);


--
-- TOC entry 116 (OID 26684)
-- Name: gpgkey_fingerprint_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpgkey_fingerprint_key UNIQUE (fingerprint);


--
-- TOC entry 119 (OID 26698)
-- Name: archuserid_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archuserid
    ADD CONSTRAINT archuserid_pkey PRIMARY KEY (id);


--
-- TOC entry 118 (OID 26700)
-- Name: archuserid_archuserid_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archuserid
    ADD CONSTRAINT archuserid_archuserid_key UNIQUE (archuserid);


--
-- TOC entry 120 (OID 26714)
-- Name: wikiname_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_pkey PRIMARY KEY (id);


--
-- TOC entry 121 (OID 26716)
-- Name: wikiname_wiki_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT wikiname_wiki_key UNIQUE (wiki, wikiname);


--
-- TOC entry 123 (OID 26730)
-- Name: jabberid_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_pkey PRIMARY KEY (id);


--
-- TOC entry 122 (OID 26732)
-- Name: jabberid_jabberid_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT jabberid_jabberid_key UNIQUE (jabberid);


--
-- TOC entry 124 (OID 26746)
-- Name: ircid_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY ircid
    ADD CONSTRAINT ircid_pkey PRIMARY KEY (id);


--
-- TOC entry 126 (OID 26757)
-- Name: membership_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY membership
    ADD CONSTRAINT membership_pkey PRIMARY KEY (id);


--
-- TOC entry 125 (OID 26759)
-- Name: membership_person_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY membership
    ADD CONSTRAINT membership_person_key UNIQUE (person, team);


--
-- TOC entry 127 (OID 26774)
-- Name: teamparticipation_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_pkey PRIMARY KEY (id);


--
-- TOC entry 128 (OID 26776)
-- Name: teamparticipation_team_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT teamparticipation_team_key UNIQUE (team, person);


--
-- TOC entry 130 (OID 26795)
-- Name: schema_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY "schema"
    ADD CONSTRAINT schema_pkey PRIMARY KEY (id);


--
-- TOC entry 131 (OID 26809)
-- Name: label_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY label
    ADD CONSTRAINT label_pkey PRIMARY KEY (id);


--
-- TOC entry 134 (OID 26834)
-- Name: project_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);


--
-- TOC entry 133 (OID 26836)
-- Name: project_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY project
    ADD CONSTRAINT project_name_key UNIQUE (name);


--
-- TOC entry 135 (OID 26847)
-- Name: projectrelationship_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT projectrelationship_pkey PRIMARY KEY (id);


--
-- TOC entry 136 (OID 26862)
-- Name: projectrole_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectrole
    ADD CONSTRAINT projectrole_pkey PRIMARY KEY (id);


--
-- TOC entry 138 (OID 26881)
-- Name: product_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);


--
-- TOC entry 139 (OID 26883)
-- Name: product_project_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY product
    ADD CONSTRAINT product_project_key UNIQUE (project, name);


--
-- TOC entry 137 (OID 26885)
-- Name: product_id_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY product
    ADD CONSTRAINT product_id_key UNIQUE (id, project);


--
-- TOC entry 140 (OID 26900)
-- Name: productlabel_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productlabel
    ADD CONSTRAINT productlabel_pkey PRIMARY KEY (id);


--
-- TOC entry 141 (OID 26902)
-- Name: productlabel_product_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productlabel
    ADD CONSTRAINT productlabel_product_key UNIQUE (product, label);


--
-- TOC entry 142 (OID 26917)
-- Name: productrole_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productrole
    ADD CONSTRAINT productrole_pkey PRIMARY KEY (id);


--
-- TOC entry 143 (OID 26935)
-- Name: productseries_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_pkey PRIMARY KEY (id);


--
-- TOC entry 144 (OID 26937)
-- Name: productseries_product_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productseries
    ADD CONSTRAINT productseries_product_key UNIQUE (product, name);


--
-- TOC entry 145 (OID 26951)
-- Name: productrelease_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_pkey PRIMARY KEY (id);


--
-- TOC entry 146 (OID 26953)
-- Name: productrelease_product_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT productrelease_product_key UNIQUE (product, "version");


--
-- TOC entry 147 (OID 26971)
-- Name: productcvsmodule_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productcvsmodule
    ADD CONSTRAINT productcvsmodule_pkey PRIMARY KEY (id);


--
-- TOC entry 148 (OID 26985)
-- Name: productbkbranch_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbkbranch
    ADD CONSTRAINT productbkbranch_pkey PRIMARY KEY (id);


--
-- TOC entry 149 (OID 26999)
-- Name: productsvnmodule_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT productsvnmodule_pkey PRIMARY KEY (id);


--
-- TOC entry 150 (OID 27013)
-- Name: archarchive_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archarchive
    ADD CONSTRAINT archarchive_pkey PRIMARY KEY (id);


--
-- TOC entry 151 (OID 27027)
-- Name: archarchivelocation_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archarchivelocation
    ADD CONSTRAINT archarchivelocation_pkey PRIMARY KEY (id);


--
-- TOC entry 152 (OID 27051)
-- Name: archnamespace_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archnamespace
    ADD CONSTRAINT archnamespace_pkey PRIMARY KEY (id);


--
-- TOC entry 153 (OID 27065)
-- Name: branch_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branch
    ADD CONSTRAINT branch_pkey PRIMARY KEY (id);


--
-- TOC entry 155 (OID 27087)
-- Name: changeset_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changeset
    ADD CONSTRAINT changeset_pkey PRIMARY KEY (id);


--
-- TOC entry 154 (OID 27089)
-- Name: changeset_id_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changeset
    ADD CONSTRAINT changeset_id_key UNIQUE (id, branch);


--
-- TOC entry 157 (OID 27111)
-- Name: changesetfilename_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfilename
    ADD CONSTRAINT changesetfilename_pkey PRIMARY KEY (id);


--
-- TOC entry 156 (OID 27113)
-- Name: changesetfilename_filename_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfilename
    ADD CONSTRAINT changesetfilename_filename_key UNIQUE (filename);


--
-- TOC entry 159 (OID 27123)
-- Name: changesetfile_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT changesetfile_pkey PRIMARY KEY (id);


--
-- TOC entry 158 (OID 27125)
-- Name: changesetfile_changeset_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT changesetfile_changeset_key UNIQUE (changeset, changesetfilename);


--
-- TOC entry 161 (OID 27143)
-- Name: changesetfilehash_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfilehash
    ADD CONSTRAINT changesetfilehash_pkey PRIMARY KEY (id);


--
-- TOC entry 160 (OID 27145)
-- Name: changesetfilehash_changesetfile_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfilehash
    ADD CONSTRAINT changesetfilehash_changesetfile_key UNIQUE (changesetfile, hashalg);


--
-- TOC entry 162 (OID 27153)
-- Name: branchrelationship_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branchrelationship
    ADD CONSTRAINT branchrelationship_pkey PRIMARY KEY (subject, object);


--
-- TOC entry 163 (OID 27178)
-- Name: productbranchrelationship_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbranchrelationship
    ADD CONSTRAINT productbranchrelationship_pkey PRIMARY KEY (id);


--
-- TOC entry 164 (OID 27194)
-- Name: manifest_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifest
    ADD CONSTRAINT manifest_pkey PRIMARY KEY (id);


--
-- TOC entry 166 (OID 27210)
-- Name: manifestentry_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT manifestentry_pkey PRIMARY KEY (id);


--
-- TOC entry 165 (OID 27212)
-- Name: manifestentry_manifest_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT manifestentry_manifest_key UNIQUE (manifest, "sequence");


--
-- TOC entry 167 (OID 27242)
-- Name: archconfig_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archconfig
    ADD CONSTRAINT archconfig_pkey PRIMARY KEY (id);


--
-- TOC entry 169 (OID 27281)
-- Name: processorfamily_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_pkey PRIMARY KEY (id);


--
-- TOC entry 168 (OID 27283)
-- Name: processorfamily_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT processorfamily_name_key UNIQUE (name);


--
-- TOC entry 171 (OID 27297)
-- Name: processor_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_pkey PRIMARY KEY (id);


--
-- TOC entry 170 (OID 27299)
-- Name: processor_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY processor
    ADD CONSTRAINT processor_name_key UNIQUE (name);


--
-- TOC entry 173 (OID 27317)
-- Name: builder_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_pkey PRIMARY KEY (id);


--
-- TOC entry 172 (OID 27319)
-- Name: builder_fqdn_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY builder
    ADD CONSTRAINT builder_fqdn_key UNIQUE (fqdn, name);


--
-- TOC entry 175 (OID 27337)
-- Name: component_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY component
    ADD CONSTRAINT component_pkey PRIMARY KEY (id);


--
-- TOC entry 174 (OID 27339)
-- Name: component_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY component
    ADD CONSTRAINT component_name_key UNIQUE (name);


--
-- TOC entry 177 (OID 27349)
-- Name: section_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY section
    ADD CONSTRAINT section_pkey PRIMARY KEY (id);


--
-- TOC entry 176 (OID 27351)
-- Name: section_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY section
    ADD CONSTRAINT section_name_key UNIQUE (name);


--
-- TOC entry 179 (OID 27361)
-- Name: distribution_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_pkey PRIMARY KEY (id);


--
-- TOC entry 182 (OID 27385)
-- Name: distrorelease_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_pkey PRIMARY KEY (id);


--
-- TOC entry 184 (OID 27425)
-- Name: distroarchrelease_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT distroarchrelease_pkey PRIMARY KEY (id);


--
-- TOC entry 186 (OID 27445)
-- Name: libraryfilecontent_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY libraryfilecontent
    ADD CONSTRAINT libraryfilecontent_pkey PRIMARY KEY (id);


--
-- TOC entry 187 (OID 27456)
-- Name: libraryfilealias_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY libraryfilealias
    ADD CONSTRAINT libraryfilealias_pkey PRIMARY KEY (id);


--
-- TOC entry 189 (OID 27480)
-- Name: sourcepackagename_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_pkey PRIMARY KEY (id);


--
-- TOC entry 188 (OID 27482)
-- Name: sourcepackagename_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagename
    ADD CONSTRAINT sourcepackagename_name_key UNIQUE (name);


--
-- TOC entry 190 (OID 27492)
-- Name: sourcepackage_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT sourcepackage_pkey PRIMARY KEY (id);


--
-- TOC entry 192 (OID 27509)
-- Name: sourcepackagerelationship_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelationship
    ADD CONSTRAINT sourcepackagerelationship_pkey PRIMARY KEY (subject, object);


--
-- TOC entry 193 (OID 27548)
-- Name: sourcepackagerelease_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_pkey PRIMARY KEY (id);


--
-- TOC entry 195 (OID 27578)
-- Name: sourcepackageupload_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackageupload
    ADD CONSTRAINT sourcepackageupload_pkey PRIMARY KEY (distrorelease, sourcepackagerelease);


--
-- TOC entry 197 (OID 27597)
-- Name: build_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY build
    ADD CONSTRAINT build_pkey PRIMARY KEY (id);


--
-- TOC entry 199 (OID 27627)
-- Name: binarypackagename_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_pkey PRIMARY KEY (id);


--
-- TOC entry 198 (OID 27629)
-- Name: binarypackagename_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackagename
    ADD CONSTRAINT binarypackagename_name_key UNIQUE (name);


--
-- TOC entry 202 (OID 27639)
-- Name: binarypackage_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_pkey PRIMARY KEY (id);


--
-- TOC entry 200 (OID 27641)
-- Name: binarypackage_binarypackagename_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT binarypackage_binarypackagename_key UNIQUE (binarypackagename, "version");


--
-- TOC entry 204 (OID 27678)
-- Name: packagepublishing_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT packagepublishing_pkey PRIMARY KEY (id);


--
-- TOC entry 205 (OID 27701)
-- Name: packageselection_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT packageselection_pkey PRIMARY KEY (id);


--
-- TOC entry 206 (OID 27730)
-- Name: coderelease_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY coderelease
    ADD CONSTRAINT coderelease_pkey PRIMARY KEY (id);


--
-- TOC entry 207 (OID 27747)
-- Name: codereleaserelationship_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY codereleaserelationship
    ADD CONSTRAINT codereleaserelationship_pkey PRIMARY KEY (subject, object);


--
-- TOC entry 209 (OID 27765)
-- Name: osfile_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY osfile
    ADD CONSTRAINT osfile_pkey PRIMARY KEY (id);


--
-- TOC entry 208 (OID 27767)
-- Name: osfile_path_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY osfile
    ADD CONSTRAINT osfile_path_key UNIQUE ("path");


--
-- TOC entry 211 (OID 27787)
-- Name: pomsgid_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgid
    ADD CONSTRAINT pomsgid_pkey PRIMARY KEY (id);


--
-- TOC entry 210 (OID 27789)
-- Name: pomsgid_msgid_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgid
    ADD CONSTRAINT pomsgid_msgid_key UNIQUE (msgid);


--
-- TOC entry 212 (OID 27799)
-- Name: potranslation_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslation
    ADD CONSTRAINT potranslation_pkey PRIMARY KEY (id);


--
-- TOC entry 213 (OID 27801)
-- Name: potranslation_translation_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslation
    ADD CONSTRAINT potranslation_translation_key UNIQUE (translation);


--
-- TOC entry 215 (OID 27812)
-- Name: language_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY "language"
    ADD CONSTRAINT language_pkey PRIMARY KEY (id);


--
-- TOC entry 214 (OID 27814)
-- Name: language_code_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY "language"
    ADD CONSTRAINT language_code_key UNIQUE (code);


--
-- TOC entry 216 (OID 27824)
-- Name: country_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY country
    ADD CONSTRAINT country_pkey PRIMARY KEY (id);


--
-- TOC entry 217 (OID 27828)
-- Name: spokenin_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT spokenin_pkey PRIMARY KEY ("language", country);


--
-- TOC entry 218 (OID 27846)
-- Name: license_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY license
    ADD CONSTRAINT license_pkey PRIMARY KEY (id);


--
-- TOC entry 219 (OID 27857)
-- Name: potemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_pkey PRIMARY KEY (id);


--
-- TOC entry 220 (OID 27861)
-- Name: potemplate_product_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT potemplate_product_key UNIQUE (product, name);


--
-- TOC entry 222 (OID 27895)
-- Name: pofile_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_pkey PRIMARY KEY (id);


--
-- TOC entry 221 (OID 27897)
-- Name: pofile_id_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pofile
    ADD CONSTRAINT pofile_id_key UNIQUE (id, potemplate);


--
-- TOC entry 226 (OID 27927)
-- Name: pomsgset_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_pkey PRIMARY KEY (id);


--
-- TOC entry 227 (OID 27929)
-- Name: pomsgset_potemplate_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT pomsgset_potemplate_key UNIQUE (potemplate, pofile, primemsgid);


--
-- TOC entry 229 (OID 27952)
-- Name: pomsgidsighting_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT pomsgidsighting_pkey PRIMARY KEY (id);


--
-- TOC entry 233 (OID 27971)
-- Name: potranslationsighting_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT potranslationsighting_pkey PRIMARY KEY (id);


--
-- TOC entry 235 (OID 28000)
-- Name: pocomment_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT pocomment_pkey PRIMARY KEY (id);


--
-- TOC entry 237 (OID 28030)
-- Name: translationeffort_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT translationeffort_pkey PRIMARY KEY (id);


--
-- TOC entry 236 (OID 28032)
-- Name: translationeffort_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT translationeffort_name_key UNIQUE (name);


--
-- TOC entry 238 (OID 28048)
-- Name: translationeffortpotemplate_translationeffort_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT translationeffortpotemplate_translationeffort_key UNIQUE (translationeffort, potemplate);


--
-- TOC entry 240 (OID 28067)
-- Name: posubscription_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_pkey PRIMARY KEY (id);


--
-- TOC entry 239 (OID 28069)
-- Name: posubscription_person_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT posubscription_person_key UNIQUE (person, potemplate, "language");


--
-- TOC entry 242 (OID 28092)
-- Name: bug_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_pkey PRIMARY KEY (id);


--
-- TOC entry 243 (OID 28105)
-- Name: bugsubscription_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT bugsubscription_pkey PRIMARY KEY (id);


--
-- TOC entry 244 (OID 28119)
-- Name: buginfestation_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT buginfestation_pkey PRIMARY KEY (bug, coderelease);


--
-- TOC entry 246 (OID 28146)
-- Name: sourcepackagebugassignment_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT sourcepackagebugassignment_pkey PRIMARY KEY (id);


--
-- TOC entry 245 (OID 28148)
-- Name: sourcepackagebugassignment_bug_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT sourcepackagebugassignment_bug_key UNIQUE (bug, sourcepackage);


--
-- TOC entry 248 (OID 28167)
-- Name: productbugassignment_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT productbugassignment_pkey PRIMARY KEY (id);


--
-- TOC entry 247 (OID 28169)
-- Name: productbugassignment_bug_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT productbugassignment_bug_key UNIQUE (bug, product);


--
-- TOC entry 249 (OID 28187)
-- Name: bugactivity_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT bugactivity_pkey PRIMARY KEY (id);


--
-- TOC entry 250 (OID 28202)
-- Name: bugexternalref_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT bugexternalref_pkey PRIMARY KEY (id);


--
-- TOC entry 252 (OID 28220)
-- Name: bugsystemtype_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugtrackertype
    ADD CONSTRAINT bugsystemtype_pkey PRIMARY KEY (id);


--
-- TOC entry 251 (OID 28222)
-- Name: bugsystemtype_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugtrackertype
    ADD CONSTRAINT bugsystemtype_name_key UNIQUE (name);


--
-- TOC entry 253 (OID 28236)
-- Name: bugsystem_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT bugsystem_pkey PRIMARY KEY (id);


--
-- TOC entry 255 (OID 28257)
-- Name: bugwatch_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT bugwatch_pkey PRIMARY KEY (id);


--
-- TOC entry 258 (OID 28285)
-- Name: buglabel_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buglabel
    ADD CONSTRAINT buglabel_pkey PRIMARY KEY (bug, label);


--
-- TOC entry 259 (OID 28314)
-- Name: bugmessage_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_pkey PRIMARY KEY (id);


--
-- TOC entry 261 (OID 28340)
-- Name: bugattachment_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT bugattachment_pkey PRIMARY KEY (id);


--
-- TOC entry 263 (OID 28358)
-- Name: sourcesource_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT sourcesource_pkey PRIMARY KEY (id);


--
-- TOC entry 262 (OID 28360)
-- Name: sourcesource_branch_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT sourcesource_branch_key UNIQUE (branch);


--
-- TOC entry 256 (OID 46690)
-- Name: projectbugsystem_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT projectbugsystem_pkey PRIMARY KEY (id);


--
-- TOC entry 257 (OID 46692)
-- Name: projectbugsystem_project_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT projectbugsystem_project_key UNIQUE (project, bugtracker);


--
-- TOC entry 260 (OID 46694)
-- Name: bugmessage_rfc822msgid_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT bugmessage_rfc822msgid_key UNIQUE (rfc822msgid);


--
-- TOC entry 234 (OID 46697)
-- Name: potranslationsighting_pomsgset_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT potranslationsighting_pomsgset_key UNIQUE (pomsgset, potranslation, license, person, pluralform);


--
-- TOC entry 241 (OID 46704)
-- Name: bug_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bug
    ADD CONSTRAINT bug_name_key UNIQUE (name);


--
-- TOC entry 180 (OID 46719)
-- Name: distributionrole_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distributionrole
    ADD CONSTRAINT distributionrole_pkey PRIMARY KEY (id);


--
-- TOC entry 183 (OID 46721)
-- Name: distroreleaserole_pkey; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distroreleaserole
    ADD CONSTRAINT distroreleaserole_pkey PRIMARY KEY (id);


--
-- TOC entry 264 (OID 46731)
-- Name: componentselection_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT componentselection_pkey PRIMARY KEY (id);


--
-- TOC entry 265 (OID 46746)
-- Name: sectionselection_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT sectionselection_pkey PRIMARY KEY (id);


--
-- TOC entry 178 (OID 46765)
-- Name: distribution_name_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distribution
    ADD CONSTRAINT distribution_name_key UNIQUE (name);


--
-- TOC entry 181 (OID 46767)
-- Name: distrorelease_distribution_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT distrorelease_distribution_key UNIQUE (distribution, name);


--
-- TOC entry 132 (OID 212157)
-- Name: label_schema_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY label
    ADD CONSTRAINT label_schema_key UNIQUE ("schema", name);


--
-- TOC entry 115 (OID 212197)
-- Name: gpg_fingerprint_key; Type: CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT gpg_fingerprint_key UNIQUE (fingerprint);


--
-- TOC entry 266 (OID 26652)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY person
    ADD CONSTRAINT "$1" FOREIGN KEY (teamowner) REFERENCES person(id);


--
-- TOC entry 267 (OID 26668)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY emailaddress
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 268 (OID 26686)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY gpgkey
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 269 (OID 26702)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archuserid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 270 (OID 26718)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY wikiname
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 271 (OID 26734)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY jabberid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 272 (OID 26748)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY ircid
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 274 (OID 26761)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY membership
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 273 (OID 26765)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY membership
    ADD CONSTRAINT "$2" FOREIGN KEY (team) REFERENCES person(id);


--
-- TOC entry 276 (OID 26778)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT "$1" FOREIGN KEY (team) REFERENCES person(id);


--
-- TOC entry 275 (OID 26782)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY teamparticipation
    ADD CONSTRAINT "$2" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 277 (OID 26797)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY "schema"
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 278 (OID 26811)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY label
    ADD CONSTRAINT "$1" FOREIGN KEY ("schema") REFERENCES "schema"(id);


--
-- TOC entry 280 (OID 26817)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY personlabel
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 279 (OID 26821)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY personlabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);


--
-- TOC entry 281 (OID 26838)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY project
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 283 (OID 26849)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES project(id);


--
-- TOC entry 282 (OID 26853)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES project(id);


--
-- TOC entry 285 (OID 26864)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectrole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 284 (OID 26868)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectrole
    ADD CONSTRAINT "$2" FOREIGN KEY (project) REFERENCES project(id);


--
-- TOC entry 287 (OID 26887)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY product
    ADD CONSTRAINT "$1" FOREIGN KEY (project) REFERENCES project(id);


--
-- TOC entry 286 (OID 26891)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY product
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 289 (OID 26904)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productlabel
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 288 (OID 26908)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productlabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);


--
-- TOC entry 291 (OID 26919)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productrole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 290 (OID 26923)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productrole
    ADD CONSTRAINT "$2" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 292 (OID 26939)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productseries
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 294 (OID 26955)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 293 (OID 26959)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productrelease
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 295 (OID 26973)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productcvsmodule
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 296 (OID 26987)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbkbranch
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 297 (OID 27001)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productsvnmodule
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 298 (OID 27015)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archarchive
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 299 (OID 27029)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archarchivelocation
    ADD CONSTRAINT "$1" FOREIGN KEY (archive) REFERENCES archarchive(id);


--
-- TOC entry 301 (OID 27035)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archarchivelocationsigner
    ADD CONSTRAINT "$1" FOREIGN KEY (archarchivelocation) REFERENCES archarchivelocation(id);


--
-- TOC entry 300 (OID 27039)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archarchivelocationsigner
    ADD CONSTRAINT "$2" FOREIGN KEY (gpgkey) REFERENCES gpgkey(id);


--
-- TOC entry 302 (OID 27053)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archnamespace
    ADD CONSTRAINT "$1" FOREIGN KEY (archarchive) REFERENCES archarchive(id);


--
-- TOC entry 305 (OID 27067)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branch
    ADD CONSTRAINT "$1" FOREIGN KEY (archnamespace) REFERENCES archnamespace(id);


--
-- TOC entry 304 (OID 27071)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branch
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 303 (OID 27075)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branch
    ADD CONSTRAINT "$3" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 308 (OID 27091)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changeset
    ADD CONSTRAINT "$1" FOREIGN KEY (branch) REFERENCES branch(id);


--
-- TOC entry 307 (OID 27095)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changeset
    ADD CONSTRAINT "$2" FOREIGN KEY (archid) REFERENCES archuserid(id);


--
-- TOC entry 306 (OID 27099)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changeset
    ADD CONSTRAINT "$3" FOREIGN KEY (gpgkey) REFERENCES gpgkey(id);


--
-- TOC entry 310 (OID 27127)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT "$1" FOREIGN KEY (changeset) REFERENCES changeset(id);


--
-- TOC entry 309 (OID 27131)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfile
    ADD CONSTRAINT "$2" FOREIGN KEY (changesetfilename) REFERENCES changesetfilename(id);


--
-- TOC entry 311 (OID 27147)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY changesetfilehash
    ADD CONSTRAINT "$1" FOREIGN KEY (changesetfile) REFERENCES changesetfile(id);


--
-- TOC entry 313 (OID 27155)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branchrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES branch(id);


--
-- TOC entry 312 (OID 27159)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branchrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES branch(id);


--
-- TOC entry 315 (OID 27165)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branchlabel
    ADD CONSTRAINT "$1" FOREIGN KEY (branch) REFERENCES branch(id);


--
-- TOC entry 314 (OID 27169)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY branchlabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);


--
-- TOC entry 317 (OID 27180)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbranchrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 316 (OID 27184)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbranchrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (branch) REFERENCES branch(id);


--
-- TOC entry 318 (OID 27196)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifest
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 320 (OID 27214)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$3" FOREIGN KEY (manifest) REFERENCES manifest(id);


--
-- TOC entry 319 (OID 27218)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$4" FOREIGN KEY (branch) REFERENCES branch(id);


--
-- TOC entry 323 (OID 27222)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$5" FOREIGN KEY (changeset) REFERENCES changeset(id);


--
-- TOC entry 322 (OID 27226)
-- Name: $6; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$6" FOREIGN KEY (branch, changeset) REFERENCES changeset(branch, id);


--
-- TOC entry 321 (OID 27230)
-- Name: $7; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY manifestentry
    ADD CONSTRAINT "$7" FOREIGN KEY (manifest, patchon) REFERENCES manifestentry(manifest, "sequence");


--
-- TOC entry 325 (OID 27244)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archconfig
    ADD CONSTRAINT "$1" FOREIGN KEY (productrelease) REFERENCES productrelease(id);


--
-- TOC entry 324 (OID 27248)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archconfig
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 329 (OID 27257)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$1" FOREIGN KEY (archconfig) REFERENCES archconfig(id);


--
-- TOC entry 328 (OID 27261)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$2" FOREIGN KEY (branch) REFERENCES branch(id);


--
-- TOC entry 327 (OID 27265)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$3" FOREIGN KEY (changeset) REFERENCES changeset(id);


--
-- TOC entry 326 (OID 27269)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY archconfigentry
    ADD CONSTRAINT "$4" FOREIGN KEY (branch, changeset) REFERENCES changeset(branch, id);


--
-- TOC entry 330 (OID 27285)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY processorfamily
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 332 (OID 27301)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY processor
    ADD CONSTRAINT "$1" FOREIGN KEY (family) REFERENCES processorfamily(id);


--
-- TOC entry 331 (OID 27305)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY processor
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 334 (OID 27321)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY builder
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES processor(id);


--
-- TOC entry 333 (OID 27325)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY builder
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 335 (OID 27363)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distribution
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 337 (OID 27369)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distributionrole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 336 (OID 27373)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distributionrole
    ADD CONSTRAINT "$2" FOREIGN KEY (distribution) REFERENCES distribution(id);


--
-- TOC entry 342 (OID 27387)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$1" FOREIGN KEY (distribution) REFERENCES distribution(id);


--
-- TOC entry 341 (OID 27391)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$2" FOREIGN KEY (components) REFERENCES "schema"(id);


--
-- TOC entry 340 (OID 27395)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$3" FOREIGN KEY (sections) REFERENCES "schema"(id);


--
-- TOC entry 339 (OID 27399)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$4" FOREIGN KEY (parentrelease) REFERENCES distrorelease(id);


--
-- TOC entry 338 (OID 27403)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distrorelease
    ADD CONSTRAINT "$5" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 344 (OID 27409)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distroreleaserole
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 343 (OID 27413)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distroreleaserole
    ADD CONSTRAINT "$2" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);


--
-- TOC entry 347 (OID 27427)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);


--
-- TOC entry 346 (OID 27431)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$2" FOREIGN KEY (processorfamily) REFERENCES processorfamily(id);


--
-- TOC entry 345 (OID 27435)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY distroarchrelease
    ADD CONSTRAINT "$3" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 348 (OID 27458)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY libraryfilealias
    ADD CONSTRAINT "$1" FOREIGN KEY (content) REFERENCES libraryfilecontent(id);


--
-- TOC entry 350 (OID 27464)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (productrelease) REFERENCES productrelease(id);


--
-- TOC entry 349 (OID 27468)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productreleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);


--
-- TOC entry 353 (OID 27494)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$1" FOREIGN KEY (maintainer) REFERENCES person(id);


--
-- TOC entry 352 (OID 27498)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$2" FOREIGN KEY (manifest) REFERENCES manifest(id);


--
-- TOC entry 351 (OID 27502)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$3" FOREIGN KEY (distro) REFERENCES distribution(id);


--
-- TOC entry 356 (OID 27511)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (subject) REFERENCES sourcepackage(id);


--
-- TOC entry 355 (OID 27515)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelationship
    ADD CONSTRAINT "$3" FOREIGN KEY (object) REFERENCES sourcepackage(id);


--
-- TOC entry 358 (OID 27521)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagelabel
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);


--
-- TOC entry 357 (OID 27525)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagelabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);


--
-- TOC entry 360 (OID 27531)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packaging
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);


--
-- TOC entry 359 (OID 27535)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packaging
    ADD CONSTRAINT "$2" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 364 (OID 27550)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);


--
-- TOC entry 363 (OID 27554)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$2" FOREIGN KEY (creator) REFERENCES person(id);


--
-- TOC entry 362 (OID 27558)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$3" FOREIGN KEY (dscsigningkey) REFERENCES gpgkey(id);


--
-- TOC entry 361 (OID 27562)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagerelease
    ADD CONSTRAINT "$4" FOREIGN KEY (component) REFERENCES label(id);


--
-- TOC entry 366 (OID 27568)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);


--
-- TOC entry 365 (OID 27572)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagereleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);


--
-- TOC entry 368 (OID 27580)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackageupload
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);


--
-- TOC entry 367 (OID 27584)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackageupload
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);


--
-- TOC entry 374 (OID 27599)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY build
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES processor(id);


--
-- TOC entry 373 (OID 27603)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY build
    ADD CONSTRAINT "$2" FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);


--
-- TOC entry 372 (OID 27607)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY build
    ADD CONSTRAINT "$3" FOREIGN KEY (buildlog) REFERENCES libraryfilealias(id);


--
-- TOC entry 371 (OID 27611)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY build
    ADD CONSTRAINT "$4" FOREIGN KEY (builder) REFERENCES builder(id);


--
-- TOC entry 370 (OID 27615)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY build
    ADD CONSTRAINT "$5" FOREIGN KEY (gpgsigningkey) REFERENCES gpgkey(id);


--
-- TOC entry 378 (OID 27647)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$2" FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);


--
-- TOC entry 377 (OID 27651)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$3" FOREIGN KEY (build) REFERENCES build(id);


--
-- TOC entry 376 (OID 27655)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$4" FOREIGN KEY (component) REFERENCES component(id);


--
-- TOC entry 375 (OID 27659)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackage
    ADD CONSTRAINT "$5" FOREIGN KEY (section) REFERENCES section(id);


--
-- TOC entry 380 (OID 27665)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT "$1" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);


--
-- TOC entry 379 (OID 27669)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY binarypackagefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);


--
-- TOC entry 384 (OID 27680)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$1" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);


--
-- TOC entry 383 (OID 27684)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$2" FOREIGN KEY (distroarchrelease) REFERENCES distroarchrelease(id);


--
-- TOC entry 382 (OID 27688)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$3" FOREIGN KEY (component) REFERENCES component(id);


--
-- TOC entry 381 (OID 27692)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packagepublishing
    ADD CONSTRAINT "$4" FOREIGN KEY (section) REFERENCES section(id);


--
-- TOC entry 389 (OID 27703)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);


--
-- TOC entry 388 (OID 27707)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);


--
-- TOC entry 387 (OID 27711)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$3" FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);


--
-- TOC entry 386 (OID 27715)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$4" FOREIGN KEY (component) REFERENCES component(id);


--
-- TOC entry 385 (OID 27719)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY packageselection
    ADD CONSTRAINT "$5" FOREIGN KEY (section) REFERENCES section(id);


--
-- TOC entry 392 (OID 27732)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY coderelease
    ADD CONSTRAINT "$3" FOREIGN KEY (productrelease) REFERENCES productrelease(id);


--
-- TOC entry 391 (OID 27736)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY coderelease
    ADD CONSTRAINT "$4" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);


--
-- TOC entry 390 (OID 27740)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY coderelease
    ADD CONSTRAINT "$5" FOREIGN KEY (manifest) REFERENCES manifest(id);


--
-- TOC entry 394 (OID 27749)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY codereleaserelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (subject) REFERENCES coderelease(id);


--
-- TOC entry 393 (OID 27753)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY codereleaserelationship
    ADD CONSTRAINT "$3" FOREIGN KEY (object) REFERENCES coderelease(id);


--
-- TOC entry 396 (OID 27771)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY osfileinpackage
    ADD CONSTRAINT "$1" FOREIGN KEY (osfile) REFERENCES osfile(id);


--
-- TOC entry 395 (OID 27775)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY osfileinpackage
    ADD CONSTRAINT "$2" FOREIGN KEY (binarypackage) REFERENCES binarypackage(id);


--
-- TOC entry 398 (OID 27830)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$1" FOREIGN KEY ("language") REFERENCES "language"(id);


--
-- TOC entry 397 (OID 27834)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY spokenin
    ADD CONSTRAINT "$2" FOREIGN KEY (country) REFERENCES country(id);


--
-- TOC entry 402 (OID 27863)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 401 (OID 27867)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$2" FOREIGN KEY (branch) REFERENCES branch(id);


--
-- TOC entry 400 (OID 27871)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$3" FOREIGN KEY (changeset) REFERENCES changeset(id);


--
-- TOC entry 399 (OID 27875)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$4" FOREIGN KEY (license) REFERENCES license(id);


--
-- TOC entry 404 (OID 27879)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$5" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 403 (OID 27883)
-- Name: $6; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$6" FOREIGN KEY (changeset, branch) REFERENCES changeset(id, branch);


--
-- TOC entry 409 (OID 27899)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$1" FOREIGN KEY (potemplate) REFERENCES potemplate(id);


--
-- TOC entry 408 (OID 27903)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$2" FOREIGN KEY ("language") REFERENCES "language"(id);


--
-- TOC entry 407 (OID 27907)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$3" FOREIGN KEY (lasttranslator) REFERENCES person(id);


--
-- TOC entry 406 (OID 27911)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$4" FOREIGN KEY (license) REFERENCES license(id);


--
-- TOC entry 405 (OID 27915)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pofile
    ADD CONSTRAINT "$5" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 413 (OID 27931)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$1" FOREIGN KEY (primemsgid) REFERENCES pomsgid(id);


--
-- TOC entry 412 (OID 27935)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);


--
-- TOC entry 411 (OID 27939)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$3" FOREIGN KEY (pofile) REFERENCES pofile(id);


--
-- TOC entry 410 (OID 27943)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "$4" FOREIGN KEY (pofile, potemplate) REFERENCES pofile(id, potemplate);


--
-- TOC entry 415 (OID 27956)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT "$1" FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);


--
-- TOC entry 414 (OID 27960)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pomsgidsighting
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);


--
-- TOC entry 419 (OID 27975)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgset) REFERENCES pomsgset(id);


--
-- TOC entry 418 (OID 27979)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$3" FOREIGN KEY (potranslation) REFERENCES potranslation(id);


--
-- TOC entry 417 (OID 27983)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$4" FOREIGN KEY (license) REFERENCES license(id);


--
-- TOC entry 416 (OID 27987)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY potranslationsighting
    ADD CONSTRAINT "$5" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 424 (OID 28002)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$1" FOREIGN KEY (potemplate) REFERENCES potemplate(id);


--
-- TOC entry 423 (OID 28006)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$2" FOREIGN KEY (pomsgid) REFERENCES pomsgid(id);


--
-- TOC entry 422 (OID 28010)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$3" FOREIGN KEY ("language") REFERENCES "language"(id);


--
-- TOC entry 421 (OID 28014)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$4" FOREIGN KEY (potranslation) REFERENCES potranslation(id);


--
-- TOC entry 420 (OID 28018)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY pocomment
    ADD CONSTRAINT "$5" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 427 (OID 28034)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 426 (OID 28038)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT "$2" FOREIGN KEY (project) REFERENCES project(id);


--
-- TOC entry 425 (OID 28042)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffort
    ADD CONSTRAINT "$3" FOREIGN KEY (categories) REFERENCES "schema"(id);


--
-- TOC entry 430 (OID 28050)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT "$1" FOREIGN KEY (translationeffort) REFERENCES translationeffort(id) ON DELETE CASCADE;


--
-- TOC entry 429 (OID 28054)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);


--
-- TOC entry 428 (OID 28058)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY translationeffortpotemplate
    ADD CONSTRAINT "$3" FOREIGN KEY (category) REFERENCES label(id);


--
-- TOC entry 433 (OID 28071)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 432 (OID 28075)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (potemplate) REFERENCES potemplate(id);


--
-- TOC entry 431 (OID 28079)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY posubscription
    ADD CONSTRAINT "$3" FOREIGN KEY ("language") REFERENCES "language"(id);


--
-- TOC entry 434 (OID 28096)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bug
    ADD CONSTRAINT "$1" FOREIGN KEY (duplicateof) REFERENCES bug(id);


--
-- TOC entry 436 (OID 28107)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);


--
-- TOC entry 435 (OID 28111)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugsubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 441 (OID 28121)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 440 (OID 28125)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$2" FOREIGN KEY (coderelease) REFERENCES coderelease(id);


--
-- TOC entry 439 (OID 28129)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$3" FOREIGN KEY (creator) REFERENCES person(id);


--
-- TOC entry 438 (OID 28133)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$4" FOREIGN KEY (verifiedby) REFERENCES person(id);


--
-- TOC entry 437 (OID 28137)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buginfestation
    ADD CONSTRAINT "$5" FOREIGN KEY (lastmodifiedby) REFERENCES person(id);


--
-- TOC entry 444 (OID 28150)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 443 (OID 28154)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);


--
-- TOC entry 447 (OID 28171)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 449 (OID 28189)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugactivity
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 451 (OID 28204)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 450 (OID 28208)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugexternalref
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 452 (OID 28224)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugtrackertype
    ADD CONSTRAINT "$1" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 454 (OID 28238)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT "$1" FOREIGN KEY (bugtrackertype) REFERENCES bugtrackertype(id);


--
-- TOC entry 453 (OID 28242)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugtracker
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 457 (OID 28259)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 456 (OID 28263)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$2" FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);


--
-- TOC entry 455 (OID 28267)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugwatch
    ADD CONSTRAINT "$3" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 459 (OID 28275)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT "$1" FOREIGN KEY (project) REFERENCES project(id);


--
-- TOC entry 458 (OID 28279)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY projectbugtracker
    ADD CONSTRAINT "$2" FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);


--
-- TOC entry 461 (OID 28287)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buglabel
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 460 (OID 28291)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY buglabel
    ADD CONSTRAINT "$2" FOREIGN KEY (label) REFERENCES label(id);


--
-- TOC entry 463 (OID 28297)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$1" FOREIGN KEY (subject) REFERENCES bug(id);


--
-- TOC entry 462 (OID 28301)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugrelationship
    ADD CONSTRAINT "$2" FOREIGN KEY (object) REFERENCES bug(id);


--
-- TOC entry 466 (OID 28316)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);


--
-- TOC entry 465 (OID 28320)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$2" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 464 (OID 28324)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$3" FOREIGN KEY (parent) REFERENCES bugmessage(id);


--
-- TOC entry 467 (OID 28328)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugmessage
    ADD CONSTRAINT "$4" FOREIGN KEY (distribution) REFERENCES distribution(id);


--
-- TOC entry 469 (OID 28342)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT "$1" FOREIGN KEY (bugmessage) REFERENCES bugmessage(id);


--
-- TOC entry 468 (OID 28346)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY bugattachment
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES libraryfilealias(id);


--
-- TOC entry 475 (OID 28362)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 474 (OID 28366)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$2" FOREIGN KEY (cvstarfile) REFERENCES libraryfilealias(id);


--
-- TOC entry 473 (OID 28370)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$3" FOREIGN KEY (releaseparentbranch) REFERENCES branch(id);


--
-- TOC entry 472 (OID 28374)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$4" FOREIGN KEY (sourcepackage) REFERENCES sourcepackage(id);


--
-- TOC entry 471 (OID 28378)
-- Name: $5; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$5" FOREIGN KEY (branch) REFERENCES branch(id);


--
-- TOC entry 470 (OID 28382)
-- Name: $6; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcesource
    ADD CONSTRAINT "$6" FOREIGN KEY ("owner") REFERENCES person(id);


--
-- TOC entry 354 (OID 46711)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackage
    ADD CONSTRAINT "$4" FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);


--
-- TOC entry 477 (OID 46733)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);


--
-- TOC entry 476 (OID 46737)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY componentselection
    ADD CONSTRAINT "$2" FOREIGN KEY (component) REFERENCES component(id);


--
-- TOC entry 479 (OID 46748)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$1" FOREIGN KEY (distrorelease) REFERENCES distrorelease(id);


--
-- TOC entry 478 (OID 46752)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sectionselection
    ADD CONSTRAINT "$2" FOREIGN KEY (section) REFERENCES section(id);


--
-- TOC entry 448 (OID 46757)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$3" FOREIGN KEY (assignee) REFERENCES person(id);


--
-- TOC entry 445 (OID 46761)
-- Name: $4; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$4" FOREIGN KEY (assignee) REFERENCES person(id);


--
-- TOC entry 369 (OID 212166)
-- Name: $6; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY build
    ADD CONSTRAINT "$6" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);


--
-- TOC entry 446 (OID 212189)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY productbugassignment
    ADD CONSTRAINT "$2" FOREIGN KEY (product) REFERENCES product(id);


--
-- TOC entry 442 (OID 212193)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: importd
--

ALTER TABLE ONLY sourcepackagebugassignment
    ADD CONSTRAINT "$3" FOREIGN KEY (binarypackagename) REFERENCES binarypackagename(id);


--
-- TOC entry 3 (OID 2200)
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS 'Standard public schema';


