SET client_min_messages=ERROR;

-- DistroRelease table -> DistroSeries
ALTER TABLE DistroRelease RENAME TO DistroSeries;

ALTER TABLE distrorelease_id_seq RENAME TO distroseries_id_seq;
ALTER TABLE DistroSeries ALTER COLUMN id
    SET DEFAULT nextval('distroseries_id_seq');

ALTER TABLE distrorelease_pkey RENAME TO distroseries_pkey;
ALTER TABLE distrorelease_distribution_key
    RENAME TO distroseries__distribution__name__key;

ALTER TABLE distrorelease_distro_release_unique
    RENAME TO distroseries__distribution__id__key;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__distribution__fk
    FOREIGN KEY (distribution) REFERENCES Distribution;
ALTER TABLE DistroSeries DROP CONSTRAINT distrorelease_distribution_fk;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__driver__fk
    FOREIGN KEY (driver) REFERENCES Person;
ALTER TABLE DistroSeries DROP CONSTRAINT distrorelease_driver_fk;
CREATE INDEX distroseries__driver__idx ON DistroSeries(driver)
    WHERE driver IS NOT NULL;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__nominatedarchindep__fk
    FOREIGN KEY (nominatedarchindep) REFERENCES DistroArchRelease;
ALTER TABLE DistroSeries DROP CONSTRAINT distrorelease_nominatedarchindep_fk;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__owner__fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER  TABLE DistroSeries DROP CONSTRAINT distrorelease_owner_fk;
CREATE INDEX distroseries__owner__idx ON DistroSeries(owner);

ALTER TABLE DistroSeries RENAME COLUMN parentrelease TO parent_series;
ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__parent_series__fk
    FOREIGN KEY (parent_series) REFERENCES DistroSeries;

-- DistroReleaseLanguage table -> DistroSeriesLanguage
ALTER TABLE DistroReleaseLanguage RENAME TO DistroSeriesLanguage;

ALTER TABLE distroreleaselanguage_id_seq RENAME TO distroserieslanguage_id_seq;
ALTER TABLE DistroSeriesLanguage ALTER COLUMN id
    SET DEFAULT nextval('distroserieslanguage_id_seq');

ALTER TABLE DistroSeriesLanguage RENAME COLUMN distrorelease TO distroseries;

ALTER TABLE distroreleaselanguage_pkey RENAME TO distroserieslanguage_pkey;
ALTER TABLE distroreleaselanguage_distrorelease_language_uniq
    RENAME TO distroserieslanguage__distroseries__language__key;
ALTER TABLE DistroSeriesLanguage
    ADD CONSTRAINT distroserieslanguage__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;
ALTER TABLE DistroSeriesLanguage
    DROP CONSTRAINT distroreleaselanguage_distrorelease_fk;
ALTER TABLE DistroSeriesLanguage
    ADD CONSTRAINT distroserieslanguage__language__fk
    FOREIGN KEY (language) REFERENCES Language;

-- DistroArchRelease -> DistroArchSeries
ALTER TABLE DistroArchRelease RENAME TO DistroArchSeries;

ALTER TABLE distroarchrelease_id_seq RENAME TO distroarchseries_id_seq;
ALTER TABLE DistroArchSeries ALTER COLUMN id
    SET DEFAULT nextval('distroarchseries_id_seq');

ALTER TABLE DistroArchSeries RENAME COLUMN distrorelease TO distroseries;

ALTER TABLE distroarchrelease_pkey RENAME TO distroarchseries_pkey;
ALTER TABLE DistroArchSeries
    ADD CONSTRAINT distroarchseries__architecturetag__distroseries__key
    UNIQUE (architecturetag, distroseries);
ALTER TABLE DistroArchSeries DROP CONSTRAINT
    distroarchrelease_distrorelease_architecturetag_unique;
DROP INDEX distroarchrelease_architecturetag_idx;
ALTER TABLE distroarchrelease_distrorelease_idx
    RENAME TO distroarchseries__distroseries__idx;
ALTER TABLE DistroArchSeries
    DROP CONSTRAINT distroarchrelease_distrorelease_processorfamily_unique;
ALTER TABLE DistroArchSeries
    ADD CONSTRAINT distroarchseries__processorfamily__distroseries__key
    UNIQUE (processorfamily, distroseries);
DROP INDEX distroarchrelease_processorfamily_idx;

ALTER TABLE DistroArchSeries ADD CONSTRAINT distroarchseries__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;
ALTER TABLE DistroArchSeries DROP CONSTRAINT "$1";
ALTER TABLE DistroArchSeries
    ADD CONSTRAINT distroarchseries__processorfamily__fk
    FOREIGN KEY (processorfamily) REFERENCES ProcessorFamily;
ALTER TABLE DistroArchSeries DROP CONSTRAINT "$2";
ALTER TABLE DistroArchSeries ADD CONSTRAINT distroarchseries__owner__fk
    FOREIGN KEY (owner) REFERENCES Person;
CREATE INDEX distroarchseries__owner__idx ON DistroArchSeries(owner);
ALTER TABLE DistroArchSeries DROP CONSTRAINT "$3";

-- DistroReleasePackageCache -> DistroSeriesPackageCache
ALTER TABLE DistroReleasePackageCache RENAME TO DistroSeriesPackageCache;
UPDATE fticache SET tablename='distroseriespackagecache'
    WHERE tablename='distroreleasepackagecache';

ALTER TABLE distroreleasepackagecache_id_seq
    RENAME TO distroseriespackagecache_id_seq;
ALTER TABLE DistroSeriesPackageCache ALTER COLUMN id
    SET DEFAULT nextval('distroseriespackagecache');

ALTER TABLE DistroSeriesPackageCache
    RENAME COLUMN distrorelease TO distroseries;

ALTER TABLE distroreleasepackagecache_pkey
    RENAME TO distroseriespackagecache_pkey;
ALTER TABLE distroreleasepackagecache_fti
    RENAME TO distroseriespackagecache_fti;

ALTER TABLE DistroSeriesPackageCache
    ADD CONSTRAINT
    distroseriespackagecache__binarypackagename_distroseries__key
    UNIQUE (binarypackagename, distroseries),

    DROP CONSTRAINT
    distroreleasepackagecache_distrorelease_binarypackagename_uniq,

    DROP CONSTRAINT distroreleasepackagecache_binarypackagename_fk,

    ADD CONSTRAINT distroseriespackagecache__binarypackagename__fk
    FOREIGN KEY (binarypackagename) REFERENCES BinaryPackageName,

    DROP CONSTRAINT distroreleasepackagecache_distrorelease_fk,

    ADD CONSTRAINT distroseriespackagecache__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;

CREATE INDEX distroseriespackagecache__distroseries__idx
    ON DistroSeriesPackageCache(distroseries);


-- BugNomination
ALTER TABLE BugNomination RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE BugNomination
    DROP CONSTRAINT bugnomination__distrorelease__fk,
    ADD CONSTRAINT bugnomination__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries;


-- BugTask
ALTER TABLE BugTask RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE bugtask_product_key RENAME TO bugtask__product__bug__key;
ALTER TABLE bugtask_assignee_idx RENAME TO bugtask__assignee__idx;
ALTER TABLE bugtask_bug_idx RENAME TO bugtask__bug__idx;
ALTER TABLE bugtask_datecreated_idx RENAME TO bugtask__datecreated__idx;
ALTER TABLE bugtask_distribution_and_sourcepackagename_idx
    RENAME TO bugtask__distribution__sourcepackagename__idx;
DROP INDEX bugtask_distribution_idx;
ALTER TABLE bugtask_distrorelease_and_sourcepackagename_idx
    RENAME TO bugtask__distroseries__sourcepackagename__idx;
DROP INDEX bugtask_distrorelease_idx;
ALTER TABLE bugtask_milestone_idx RENAME TO bugtask__milestone__idx;
ALTER TABLE bugtask_owner_idx RENAME TO bugtask__owner__idx;
DROP INDEX bugtask_sourcepackagename_idx;
CREATE INDEX bugtask__sourcepackagename__idx ON BugTask(sourcepackagename)
    WHERE sourcepackagename IS NOT NULL;
DROP INDEX bugtask_binarypackagename_idx;
CREATE INDEX bugtask__binarypackagename__idx ON BugTask(binarypackagename)
    WHERE binarypackagename IS NOT NULL;

ALTER TABLE BugTask
    DROP CONSTRAINT bugtask_binarypackagename_fk,
    ADD CONSTRAINT bugtask__binarypackagename__fk
        FOREIGN KEY (binarypackagename) REFERENCES BinaryPackageName,
    DROP CONSTRAINT bugtask_bug_fk,
    ADD CONSTRAINT bugtask__bug__fk
        FOREIGN KEY (bug) REFERENCES Bug,
    DROP CONSTRAINT bugtask_bugwatch_fk,
    ADD CONSTRAINT bugtask__bugwatch__fk
        FOREIGN KEY (bugwatch) REFERENCES BugWatch,
    DROP CONSTRAINT bugtask_distribution_fk,
    ADD CONSTRAINT bugtask__distribution__fk
        FOREIGN KEY (distribution) REFERENCES Distribution,
    DROP CONSTRAINT bugtask_distribution_milestone_fk,
    ADD CONSTRAINT bugtask__distribution__milestone__fk FOREIGN KEY (
        distribution, milestone) REFERENCES Milestone(distribution, id),
    DROP CONSTRAINT bugtask_distrorelease_fk,
    ADD CONSTRAINT bugtask__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries,
    DROP CONSTRAINT bugtask_owner_fk,
    ADD CONSTRAINT bugtask__owner__fk FOREIGN KEY (owner) REFERENCES Person,
    DROP CONSTRAINT bugtask_person_fk,
    ADD CONSTRAINT bugtask__assignee__fk
        FOREIGN KEY (assignee) REFERENCES Person,
    DROP CONSTRAINT bugtask_product_fk,
    ADD CONSTRAINT bugtask__product__fk
        FOREIGN KEY (product) REFERENCES Product,
    DROP CONSTRAINT bugtask_product_milestone_fk,
    ADD CONSTRAINT bugtask__product__milestone__fk
        FOREIGN KEY (product, milestone) REFERENCES Milestone(product, id),
    DROP CONSTRAINT bugtask_productseries_fk,
    ADD CONSTRAINT bugtask__productseries__fk
        FOREIGN KEY (productseries) REFERENCES ProductSeries,
    DROP CONSTRAINT bugtask_sourcepackagename_fk,
    ADD CONSTRAINT bugtask__sourcepackagename__fk
        FOREIGN KEY (sourcepackagename) REFERENCES SourcepackageName;


-- ComponentSelection
ALTER TABLE ComponentSelection RENAME COLUMN distrorelease TO distroseries;
DROP INDEX componentselection__distrorelease__component__uniq;
ALTER TABLE ComponentSelection
    ADD CONSTRAINT componentselection__distroseries__component__key
        UNIQUE (distroseries, component),
    DROP CONSTRAINT "$1",
    ADD CONSTRAINT componentselection__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries,
    DROP CONSTRAINT "$2",
    ADD CONSTRAINT componentselection__component__fk
        FOREIGN KEY (component) REFERENCES Component;


-- DistroReleaseRole
DROP SEQUENCE distroreleaserole_id_seq;


-- MirrorCdImageDistroRelease
ALTER TABLE MirrorCdImageDistroRelease RENAME TO MirrorCdImageDistroSeries;
ALTER TABLE MirrorCdImageDistroSeries
    RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE mirrorcdimagedistrorelease_pkey
    RENAME TO mirrorcdimagedistroseries_pkey;
ALTER TABLE mirrorcdimagedistrorelease_id_seq
    RENAME TO mirrorcdimagedistroseries_id_seq;
ALTER TABLE MirrorCdImageDistroSeries
    ALTER COLUMN id SET DEFAULT nextval('mirrorcdimagedistroseries_id_seq'),
    ADD CONSTRAINT mirrorcdimagedistroseries__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries,
    DROP CONSTRAINT mirrorcdimagedistrorelease_distrorelease_fkey,
    ADD CONSTRAINT mirrorcdimagedistroseries__distribution_mirror__fk
        FOREIGN KEY (distribution_mirror) REFERENCES DistributionMirror,
    DROP CONSTRAINT mirrorcdimagedistrorelease_distribution_mirror_fkey,
    ADD CONSTRAINT mirrorcdimagedistroseries__unq
        UNIQUE (distroseries, flavour, distribution_mirror),
    DROP CONSTRAINT mirrorcdimagedistrorelease__unq;


-- MirrorDistroReleaseSource
ALTER TABLE MirrorDistroReleaseSource RENAME TO MirrorDistroSeriesSource;
ALTER TABLE mirrordistroreleasesource_pkey
    RENAME TO mirrordistroseriessource_pkey;
ALTER TABLE MirrorDistroSeriesSource
    RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE mirrordistroreleasesource_id_seq
    RENAME TO mirrordistroseriessource_id_seq;
ALTER TABLE MirrorDistroSeriesSource
    ALTER COLUMN id SET DEFAULT nextval('mirrordistroseriessource_id_seq');
ALTER TABLE mirrordistroreleasesource_uniq
    RENAME TO mirrordistroseriessource_uniq;
ALTER TABLE MirrorDistroSeriesSource
    DROP CONSTRAINT mirrordistroreleasesource__component__fk,
    DROP CONSTRAINT mirrordistroreleasesource_distribution_mirror_fkey,
    DROP CONSTRAINT mirrordistroreleasesource_distro_release_fkey;
ALTER TABLE MirrorDistroSeriesSource
    ADD CONSTRAINT mirrordistroseriessource__component__fk
        FOREIGN KEY (component) REFERENCES Component,
    ADD CONSTRAINT mirrordistroseriessource__distribution_mirror__fk
        FOREIGN KEY (distribution_mirror) REFERENCES DistributionMirror,
    ADD CONSTRAINT mirrordistroseriessource__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries;


-- POTemplate
ALTER TABLE POTemplate RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE potemplate_distrorelease_key
    RENAME TO potemplate_distroseries_uniq;
ALTER TABLE POTemplate
    DROP CONSTRAINT potemplate_distrorelease_fk,
    DROP CONSTRAINT "$2";
ALTER TABLE POTemplate
    ADD CONSTRAINT potemplate__distrorelease__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries,
    ADD CONSTRAINT potemplate__from_sourcepackagename__fk
        FOREIGN KEY (from_sourcepackagename) REFERENCES SourcepackageName;


-- SecureSourcePackagePublishingHistory
ALTER TABLE SecureSourcePackagePublishingHistory
    RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE SecureSourcePackagePublishingHistory
    DROP CONSTRAINT securesourcepackagepublishinghistory_distrorelease_fk;
ALTER TABLE SecureSourcePackagePublishingHistory
    ADD CONSTRAINT securesourcepackagepublishinghistory__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries;
ALTER TABLE securesourcepackagepublishinghistory_distrorelease_idx
    RENAME TO securesourcepackagepublishinghistory__distroseries__idx;


-- PackageUploadBuild
ALTER TABLE distroreleasequeuebuild_pkey RENAME TO packageuploadbuild_pkey;
ALTER TABLE distroreleasequeuebuild__distroreleasequeue__build__unique
    RENAME TO packageuploadbuild__packageupload__build__key;


-- PackageUploadSource
ALTER TABLE distroreleasequeuesource_pkey RENAME TO packageuploadsource_pkey;
ALTER TABLE distroreleasequeuesource__distroreleasequeue__sourcepackagerele
    RENAME TO packageuploadsource__packageupload__sourcepackagerelease__key;


-- PackageUploadCustom
ALTER TABLE distroreleasequeuecustom_pkey RENAME TO packageuploadcustom_pkey;


-- PackageUpload
ALTER TABLE distroreleasequeue_pkey RENAME TO packageupload_pkey;
ALTER TABLE PackageUpload RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE PackageUpload DROP CONSTRAINT packageupload__distrorelease__fk;
ALTER TABLE PackageUpload ADD CONSTRAINT packageupload__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;
ALTER TABLE packageupload__distrorelease__key
    RENAME TO packageupload__distroseries__key;
ALTER TABLE packageupload__distrorelease__status__idx
    RENAME TO packageupload__distroseries__status__idx;


-- Packaging
ALTER TABLE Packaging RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE packaging_distrorelease_and_sourcepackagename_idx
    RENAME TO packaging__distroseries__sourcepackagename__idx;
ALTER TABLE Packaging DROP CONSTRAINT packaging_distrorelease_fk;
ALTER TABLE Packaging ADD CONSTRAINT packaging__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;


-- MirrorDistroArchRelease
ALTER TABLE MirrorDistroArchRelease RENAME TO MirrorDistroArchSeries;
ALTER TABLE mirrordistroarchrelease_pkey RENAME TO mirrordistroarchseries_pkey;
ALTER TABLE mirrordistroarchrelease_uniq RENAME TO mirrordistroarchseries_uniq;
ALTER TABLE mirrordistroarchrelease_id_seq
    RENAME TO mirrordistroarchseries_id_seq;
ALTER TABLE MirrorDistroArchSeries
    ALTER COLUMN id SET DEFAULT nextval('mirrordistroarchseries_id_seq');
ALTER TABLE MirrorDistroArchSeries
    RENAME COLUMN distro_arch_release TO distroarchseries;
ALTER TABLE MirrorDistroArchSeries
    DROP CONSTRAINT mirrordistroarchrelease__component__fk,
    DROP CONSTRAINT mirrordistroarchrelease_distribution_mirror_fkey,
    DROP CONSTRAINT mirrordistroarchrelease_distro_arch_release_fkey;
ALTER TABLE MirrorDistroArchSeries
    ADD CONSTRAINT mirrordistroarchseries__component__fk
        FOREIGN KEY (component) REFERENCES Component,
    ADD CONSTRAINT mirrordistroarchseries__distribution_mirror__fk
        FOREIGN KEY (distribution_mirror) REFERENCES DistributionMirror,
    ADD CONSTRAINT mirrordistroarchseries__distroarchseries__fk
        FOREIGN KEY (distroarchseries) REFERENCES DistroArchSeries;


-- PocketChroot
ALTER TABLE pocketchroot_distroarchrelease_key
    RENAME TO pocketchroot__distroarchseries__key;
ALTER TABLE PocketChroot RENAME COLUMN distroarchrelease TO distroarchseries;
ALTER TABLE PocketChroot DROP CONSTRAINT "$1", DROP CONSTRAINT "$2";
ALTER TABLE PocketChroot
    ADD CONSTRAINT pocketchroot__distroarchseries__fk
        FOREIGN KEY (distroarchseries) REFERENCES DistroArchSeries,
    ADD CONSTRAINT pocketchroot__libraryfilealias__fk
        FOREIGN KEY (chroot) REFERENCES LibraryFileAlias;


-- Build
ALTER TABLE Build RENAME COLUMN distroarchrelease TO distroarchseries;
ALTER TABLE build_distroarchrelease_and_datebuilt_idx
    RENAME TO build__distroarchseries__datebuilt__idx;
ALTER TABLE Build
    DROP CONSTRAINT "$1", DROP CONSTRAINT "$2",
    DROP CONSTRAINT "$3", DROP CONSTRAINT "$4", DROP CONSTRAINT "$6";
ALTER TABLE Build
    ADD CONSTRAINT build__processor__fk
        FOREIGN KEY (processor) REFERENCES Processor,
    ADD CONSTRAINT build__distroarchseries__fk
        FOREIGN KEY (distroarchseries) REFERENCES DistroArchSeries,
    ADD CONSTRAINT build__buildlog__fk
        FOREIGN KEY (buildlog) REFERENCES LibraryFileAlias,
    ADD CONSTRAINT build__builder__fk
        FOREIGN KEY (builder) REFERENCES Builder,
    ADD CONSTRAINT build__sourcepackagerelease__fk
        FOREIGN KEY (sourcepackagerelease) REFERENCES SourcePackageRelease;
ALTER TABLE build_distroarchrelease_and_buildstate_idx
    RENAME TO build__distroarchseries__buildstate__idx;


-- SecureBinaryPackagePublishingHistory
ALTER TABLE SecureBinaryPackagePublishingHistory
    RENAME COLUMN distroarchrelease TO distroarchseries;
ALTER TABLE securebinarypackagepublishinghistory_distroarchrelease_idx
    RENAME TO securebinarypackagepublishinghistory__distroarchseries__idx;
ALTER TABLE SecureBinaryPackagePublishingHistory
    DROP CONSTRAINT securebinarypackagepublishinghistory_distroarchrelease_fk;
ALTER TABLE SecureBinaryPackagePublishingHistory
    ADD CONSTRAINT securebinarypackagepublishinghistory__distroarchseries__fk
        FOREIGN KEY (distroarchseries) REFERENCES DistroArchSeries;


-- SourcepackagePublishingHistory
DROP VIEW SourcePackagePublishingHistory;
CREATE VIEW SourcePackagePublishingHistory AS
    SELECT
        securesourcepackagepublishinghistory.id,
        securesourcepackagepublishinghistory.sourcepackagerelease,
        securesourcepackagepublishinghistory.status,
        securesourcepackagepublishinghistory.component,
        securesourcepackagepublishinghistory.section,
        securesourcepackagepublishinghistory.distroseries AS distroseries,
        securesourcepackagepublishinghistory.pocket,
        securesourcepackagepublishinghistory.archive,
        securesourcepackagepublishinghistory.datecreated,
        securesourcepackagepublishinghistory.datepublished,
        securesourcepackagepublishinghistory.datesuperseded,
        securesourcepackagepublishinghistory.supersededby,
        securesourcepackagepublishinghistory.datemadepending,
        securesourcepackagepublishinghistory.scheduleddeletiondate,
        securesourcepackagepublishinghistory.dateremoved,
        securesourcepackagepublishinghistory.removed_by,
        securesourcepackagepublishinghistory.removal_comment,
        securesourcepackagepublishinghistory.embargo,
        securesourcepackagepublishinghistory.embargolifted
    FROM securesourcepackagepublishinghistory
    WHERE securesourcepackagepublishinghistory.embargo = false;


-- Milestone
ALTER TABLE Milestone RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE Milestone
    DROP CONSTRAINT milestone_distribution_release_fk,
    DROP CONSTRAINT milestone_distrorelease_fk;
ALTER TABLE Milestone
    ADD CONSTRAINT milestone__distroseries__distribution__fk
        FOREIGN KEY (distroseries, distribution)
        REFERENCES DistroSeries(id, distribution),
    ADD CONSTRAINT milestone__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries;


-- POExport
DROP VIEW POExport;
CREATE VIEW POExport AS
SELECT
    COALESCE(potmsgset.id::text, 'X') || '.' 
        || COALESCE(pomsgset.id::text, 'X') || '.'
        || COALESCE(pomsgidsighting.id::text, 'X') || '.'
        || COALESCE(posubmission.id::text, 'X') AS id,
    potemplatename.name, potemplatename.translationdomain,
    potemplate.id AS potemplate, potemplate.productseries,
    potemplate.sourcepackagename, potemplate.distroseries AS distroseries,
    potemplate."header" AS potheader, potemplate.languagepack,
    pofile.id AS pofile, pofile."language", pofile.variant,
    pofile.topcomment AS potopcomment, pofile."header" AS poheader,
    pofile.fuzzyheader AS pofuzzyheader, potmsgset.id AS potmsgset,
    potmsgset."sequence" AS potsequence,
    potmsgset.commenttext AS potcommenttext, potmsgset.sourcecomment,
    potmsgset.flagscomment, potmsgset.filereferences, pomsgset.id AS pomsgset,
    pomsgset."sequence" AS posequence, pomsgset.iscomplete, pomsgset.obsolete,
    pomsgset.isfuzzy, pomsgset.commenttext AS pocommenttext,
    pomsgidsighting.pluralform AS msgidpluralform,
    posubmission.pluralform AS translationpluralform,
    posubmission.id AS activesubmission, potmsgset.context, pomsgid.msgid,
    potranslation.translation
FROM pomsgid
   JOIN pomsgidsighting ON pomsgid.id = pomsgidsighting.pomsgid
   JOIN potmsgset ON potmsgset.id = pomsgidsighting.potmsgset
   JOIN potemplate ON potemplate.id = potmsgset.potemplate
   JOIN potemplatename ON potemplatename.id = potemplate.potemplatename
   JOIN pofile ON potemplate.id = pofile.potemplate
    LEFT JOIN pomsgset ON potmsgset.id = pomsgset.potmsgset
        AND pomsgset.pofile = pofile.id
   LEFT JOIN posubmission ON pomsgset.id = posubmission.pomsgset
        AND posubmission.active
   LEFT JOIN potranslation ON potranslation.id = posubmission.potranslation;


-- SourcepackageRelease
ALTER TABLE SourcepackageRelease
    RENAME COLUMN uploaddistrorelease TO upload_distroseries;
ALTER TABLE SourcepackageRelease
    DROP CONSTRAINT sourcepackagerelease_uploaddistrorelease_fk;
ALTER TABLE SourcepackageRelease
    ADD CONSTRAINT sourcepackagerelease__upload_distroseries__fk
        FOREIGN KEY (upload_distroseries) REFERENCES DistroSeries;


-- POTExport
DROP VIEW POTExport;
CREATE VIEW POTExport AS
SELECT 
    COALESCE(potmsgset.id::text, 'X') || '.'
        || COALESCE(pomsgidsighting.id::text, 'X') || '.' AS id,
    potemplatename.name, potemplatename.translationdomain,
    potemplate.id AS potemplate, potemplate.productseries,
    potemplate.sourcepackagename, potemplate.distroseries AS distroseries,
    potemplate."header", potemplate.languagepack, potmsgset.id AS potmsgset,
    potmsgset."sequence", potmsgset.commenttext, potmsgset.sourcecomment,
    potmsgset.flagscomment, potmsgset.filereferences,
    pomsgidsighting.pluralform, potmsgset.context, pomsgid.msgid
FROM pomsgid
   JOIN pomsgidsighting ON pomsgid.id = pomsgidsighting.pomsgid
   JOIN potmsgset ON potmsgset.id = pomsgidsighting.potmsgset
   JOIN potemplate ON potemplate.id = potmsgset.potemplate
   JOIN potemplatename ON potemplatename.id = potemplate.potemplatename;


-- Specification
ALTER TABLE Specification RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE Specification
    DROP CONSTRAINT distribution_and_distrorelease,
    DROP CONSTRAINT specification_distrorelease_valid;
ALTER TABLE Specification
    ADD CONSTRAINT distribution_and_distroseries
        CHECK (distroseries IS NULL OR distribution IS NOT NULL),
    ADD CONSTRAINT specification__distroseries__distribution__fk
        FOREIGN KEY (distroseries, distribution)
        REFERENCES DistroSeries(id, distribution);


-- RequestedCds
ALTER TABLE RequestedCds RENAME COLUMN distrorelease TO distroseries;


-- SectionSelection
ALTER TABLE SectionSelection RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE SectionSelection
    DROP CONSTRAINT "$1", DROP CONSTRAINT "$2";
ALTER TABLE SectionSelection
    ADD CONSTRAINT sectionselection__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries,
    ADD CONSTRAINT sectionselection__section__fk
        FOREIGN KEY (section) REFERENCES Section;


-- MirrorContent
ALTER TABLE MirrorContent RENAME COLUMN distroarchrelease TO distroarchseries;
ALTER TABLE MirrorContent DROP CONSTRAINT mirrorcontent_distroarchrelease_fk;
ALTER TABLE MirrorContent
    ADD CONSTRAINT mirrorcontent__distroarchseries__fk
        FOREIGN KEY (distroarchseries) REFERENCES DistroArchSeries;


-- PackageSelection (obsolete?)
ALTER TABLE PackageSelection RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE PackageSelection
    DROP CONSTRAINT "$1", DROP CONSTRAINT "$2", DROP CONSTRAINT "$3",
    DROP CONSTRAINT "$4", DROP CONSTRAINT "$5";
ALTER TABLE PackageSelection
    ADD CONSTRAINT packageselection__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries,
    ADD CONSTRAINT packageselection__sourcepackagename__fk
        FOREIGN KEY (sourcepackagename) REFERENCES SourcepackageName,
    ADD CONSTRAINT packageselection__binarypackagename__fk
        FOREIGN KEY (binarypackagename) REFERENCES BinarypackageName,
    ADD CONSTRAINT packageselection__component__fk
        FOREIGN KEY (component) REFERENCES Component,
    ADD CONSTRAINT packageselection__section__fk
        FOREIGN KEY (section) REFERENCES Section;


-- BinarypackagePublishingHistory
DROP VIEW BinarypackagePublishingHistory;
CREATE VIEW BinarypackagePublishingHistory AS
    SELECT
        securebinarypackagepublishinghistory.id,
        securebinarypackagepublishinghistory.binarypackagerelease,
        securebinarypackagepublishinghistory.status,
        securebinarypackagepublishinghistory.component,
        securebinarypackagepublishinghistory.section,
        securebinarypackagepublishinghistory.priority,
        securebinarypackagepublishinghistory.distroarchseries,
        securebinarypackagepublishinghistory.pocket,
        securebinarypackagepublishinghistory.archive,
        securebinarypackagepublishinghistory.datecreated,
        securebinarypackagepublishinghistory.datepublished,
        securebinarypackagepublishinghistory.datesuperseded,
        securebinarypackagepublishinghistory.supersededby,
        securebinarypackagepublishinghistory.datemadepending,
        securebinarypackagepublishinghistory.scheduleddeletiondate,
        securebinarypackagepublishinghistory.dateremoved,
        securebinarypackagepublishinghistory.removed_by,
        securebinarypackagepublishinghistory.removal_comment,
        securebinarypackagepublishinghistory.embargo,
        securebinarypackagepublishinghistory.embargolifted
   FROM securebinarypackagepublishinghistory
  WHERE securebinarypackagepublishinghistory.embargo = false;


-- SourcepackageFilePublishing
DROP VIEW SourcepackageFilePublishing;
CREATE VIEW SourcepackageFilePublishing AS
    SELECT
        libraryfilealias.id::text || '.'
            || securesourcepackagepublishinghistory.id::text AS id,
        distroseries.distribution,
        securesourcepackagepublishinghistory.id AS sourcepackagepublishing,
        sourcepackagereleasefile.libraryfile AS libraryfilealias,
        libraryfilealias.filename AS libraryfilealiasfilename,
        sourcepackagename.name AS sourcepackagename,
        component.name AS componentname,
        distroseries.name AS distroseriesname,
        securesourcepackagepublishinghistory.status AS publishingstatus,
        securesourcepackagepublishinghistory.pocket,
        securesourcepackagepublishinghistory.archive
    FROM securesourcepackagepublishinghistory
    JOIN sourcepackagerelease
        ON securesourcepackagepublishinghistory.sourcepackagerelease
            = sourcepackagerelease.id
    JOIN sourcepackagename
        ON sourcepackagerelease.sourcepackagename = sourcepackagename.id
    JOIN sourcepackagereleasefile
        ON sourcepackagereleasefile.sourcepackagerelease
            = sourcepackagerelease.id
    JOIN libraryfilealias
        ON libraryfilealias.id = sourcepackagereleasefile.libraryfile
    JOIN distroseries
        ON securesourcepackagepublishinghistory.distroseries
            = distroseries.id
    JOIN component
        ON securesourcepackagepublishinghistory.component = component.id
    WHERE securesourcepackagepublishinghistory.dateremoved IS NULL;


-- BinarypackageFilePublishing
DROP VIEW BinarypackageFilePublishing;
CREATE VIEW BinarypackageFilePublishing AS SELECT 
    libraryfilealias.id::text || '.'
        || securebinarypackagepublishinghistory.id::text AS id,
        distroseries.distribution,
        securebinarypackagepublishinghistory.id AS binarypackagepublishing,
        component.name AS componentname,
        libraryfilealias.filename AS libraryfilealiasfilename,
        sourcepackagename.name AS sourcepackagename,
        binarypackagefile.libraryfile AS libraryfilealias,
        distroseries.name AS distroseriesname,
        distroarchseries.architecturetag,
        securebinarypackagepublishinghistory.status AS publishingstatus,
        securebinarypackagepublishinghistory.pocket,
        securebinarypackagepublishinghistory.archive
    FROM securebinarypackagepublishinghistory
    JOIN binarypackagerelease
        ON securebinarypackagepublishinghistory.binarypackagerelease
            = binarypackagerelease.id
    JOIN build ON binarypackagerelease.build = build.id
    JOIN sourcepackagerelease
        ON build.sourcepackagerelease = sourcepackagerelease.id
    JOIN sourcepackagename
        ON sourcepackagerelease.sourcepackagename = sourcepackagename.id
    JOIN binarypackagefile
        ON binarypackagefile.binarypackagerelease = binarypackagerelease.id
    JOIN libraryfilealias
        ON binarypackagefile.libraryfile = libraryfilealias.id
    JOIN distroarchseries
        ON securebinarypackagepublishinghistory.distroarchseries
            = distroarchseries.id
    JOIN distroseries
        ON distroarchseries.distroseries = distroseries.id
    JOIN component
        ON securebinarypackagepublishinghistory.component = component.id
    WHERE securebinarypackagepublishinghistory.dateremoved IS NULL;


-- PublishedPackage
DROP VIEW PublishedPackage;
CREATE VIEW PublishedPackage AS SELECT
    securebinarypackagepublishinghistory.id,
    distroarchseries.id AS distroarchseries,
    distroseries.distribution, distroseries.id AS distroseries,
    distroseries.name AS distroseriesname,
    processorfamily.id AS processorfamily,
    processorfamily.name AS processorfamilyname,
    securebinarypackagepublishinghistory.status AS packagepublishingstatus,
    component.name AS component,
    section.name AS section,
    binarypackagerelease.id AS binarypackagerelease,
    binarypackagename.name AS binarypackagename,
    binarypackagerelease.summary AS binarypackagesummary,
    binarypackagerelease.description AS binarypackagedescription,
    binarypackagerelease.version AS binarypackageversion,
    build.id AS build,
    build.datebuilt,
    sourcepackagerelease.id AS sourcepackagerelease,
    sourcepackagerelease.version AS sourcepackagereleaseversion,
    sourcepackagename.name AS sourcepackagename,
    securebinarypackagepublishinghistory.pocket,
    securebinarypackagepublishinghistory.archive,
    binarypackagerelease.fti AS binarypackagefti
    FROM securebinarypackagepublishinghistory
    JOIN distroarchseries
        ON distroarchseries.id
            = securebinarypackagepublishinghistory.distroarchseries
    JOIN distroseries ON distroarchseries.distroseries = distroseries.id
    JOIN processorfamily
        ON distroarchseries.processorfamily = processorfamily.id
    JOIN component
        ON securebinarypackagepublishinghistory.component = component.id
    JOIN binarypackagerelease
        ON securebinarypackagepublishinghistory.binarypackagerelease
            = binarypackagerelease.id
    JOIN section ON securebinarypackagepublishinghistory.section = section.id
    JOIN binarypackagename
        ON binarypackagerelease.binarypackagename = binarypackagename.id
    JOIN build ON binarypackagerelease.build = build.id
    JOIN sourcepackagerelease ON build.sourcepackagerelease
        = sourcepackagerelease.id
    JOIN sourcepackagename
        ON sourcepackagerelease.sourcepackagename = sourcepackagename.id
    WHERE securebinarypackagepublishinghistory.dateremoved IS NULL;


-- MirrorSourceContent
ALTER TABLE MirrorSourceContent RENAME distrorelease TO distroseries;
ALTER TABLE MirrorSourceContent
    DROP CONSTRAINT mirrorsourcecontent_distrorelease_fk;
ALTER TABLE MirrorSourceContent
    ADD CONSTRAINT mirrorsourcecontent__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;


-- TranslationImportQueueEntry
ALTER TABLE TranslationImportQueueEntry
    RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE TranslationImportQueueEntry
    DROP CONSTRAINT "$1", DROP CONSTRAINT "$2", DROP CONSTRAINT "$3",
    DROP CONSTRAINT "$4", DROP CONSTRAINT "$5", DROP CONSTRAINT "$6",
    DROP CONSTRAINT "$7";
ALTER TABLE TranslationImportQueueEntry
    ADD CONSTRAINT translationimportqueueentry__content__fk
        FOREIGN KEY (content) REFERENCES LibraryFileAlias,
    ADD CONSTRAINT translationimportqueueentry__importer__fk
        FOREIGN KEY (importer) REFERENCES Person,
    ADD CONSTRAINT translationimportqueueentry__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES Distroseries,
    ADD CONSTRAINT translationimportqueueentry__sourcepackagename__fk
        FOREIGN KEY (sourcepackagename) REFERENCES SourcepackageName,
    ADD CONSTRAINT translationimportqueueentry__productseries__fk
        FOREIGN KEY (productseries) REFERENCES ProductSeries,
    ADD CONSTRAINT translationimportqueueentry__pofile__fk
        FOREIGN KEY (pofile) REFERENCES POFile,
    ADD CONSTRAINT translationimportqueueentry__potemplate__fk
        FOREIGN KEY (potemplate) REFERENCES POTemplate;


/*
-- Detect remaining tables
SELECT relname from pg_class
where  relname like '%distrorelease%'
    or relname like '%distroarchrelease%';

-- Remaining columns
SELECT relname, attname
FROM pg_attribute, pg_class
WHERE
    pg_attribute.attrelid = pg_class.oid
    and (attname like '%distrorelease%' or attname like '%distroarchrelease%');
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 16, 0);
