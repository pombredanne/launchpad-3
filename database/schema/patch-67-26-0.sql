SET client_min_messages=ERROR;

/* Add a load of date_created columns to various objects in the db.
   We create fake entries for existing rows - all timestamps before
   2006 are fake.
*/

-- Branch
ALTER TABLE Branch
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Branch
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM Branch)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Branch ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- BranchSubscription
ALTER TABLE BranchSubscription
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE BranchSubscription
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM BranchSubscription)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE BranchSubscription ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE BranchSubscription ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- BugCve
ALTER TABLE BugCve
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE BugCve
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM BugCve)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE BugCve ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE BugCve ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- BugSubscription
ALTER TABLE BugSubscription
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE BugSubscription
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM BugSubscription)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE BugSubscription ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE BugSubscription ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- BugTracker
ALTER TABLE BugTracker
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE BugTracker
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM BugTracker)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE BugTracker ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE BugTracker ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Builder
ALTER TABLE Builder
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Builder
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM Builder)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Builder ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Builder ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Calendar
ALTER TABLE Calendar
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Calendar
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM Calendar)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Calendar ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Calendar ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- CalendarEvent
ALTER TABLE CalendarEvent
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE CalendarEvent
    SET date_created='2006-01-01'::timestamp without time zone -
        (((SELECT max(id) FROM CalendarEvent)-id+1) || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE CalendarEvent ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE CalendarEvent ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- CalendarSubscription
ALTER TABLE CalendarSubscription
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE CalendarSubscription
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM CalendarSubscription)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE CalendarSubscription ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE CalendarSubscription ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- ComponentSelection
ALTER TABLE ComponentSelection
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE ComponentSelection
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM ComponentSelection)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE ComponentSelection ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE ComponentSelection ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- CveReference
ALTER TABLE CveReference
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE CveReference
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM CveReference)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE CveReference ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE CveReference ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Distribution
ALTER TABLE Distribution
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Distribution
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM Distribution)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Distribution ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Distribution ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- DistributionBounty
ALTER TABLE DistributionBounty
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistributionBounty
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistributionBounty)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistributionBounty ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistributionBounty ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- DistributionMirror
ALTER TABLE DistributionMirror
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistributionMirror
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistributionMirror)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistributionMirror ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistributionMirror ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
UPDATE DistributionMirror
SET date_created=min_date_created
FROM (
    SELECT MIN(date_created) AS min_date_created,distribution_mirror
    FROM MirrorProbeRecord
    GROUP BY distribution_mirror
    ) AS Probe
WHERE DistributionMirror.id = Probe.distribution_mirror
    AND date_created < '2006-01-01';

-- DistroArchRelease
ALTER TABLE DistroArchRelease
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistroArchRelease
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistroArchRelease)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistroArchRelease ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistroArchRelease ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- DistroComponentUploader
ALTER TABLE DistroComponentUploader
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistroComponentUploader
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistroComponentUploader)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistroComponentUploader ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistroComponentUploader ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Distrorelease
ALTER TABLE Distrorelease
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Distrorelease
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM Distrorelease)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Distrorelease ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Distrorelease ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- DistroreleaseQueue
ALTER TABLE DistroreleaseQueue
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistroreleaseQueue
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistroreleaseQueue)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistroreleaseQueue ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistroreleaseQueue ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- DistroreleaseQueueBuild
ALTER TABLE DistroreleaseQueueBuild
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistroreleaseQueueBuild
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistroreleaseQueueBuild)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistroreleaseQueueBuild ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistroreleaseQueueBuild ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- DistroreleaseQueueCustom
ALTER TABLE DistroreleaseQueueCustom
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistroreleaseQueueCustom
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistroreleaseQueueCustom)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistroreleaseQueueCustom ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistroreleaseQueueCustom ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- DistroreleaseQueueSource
ALTER TABLE DistroreleaseQueueSource
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE DistroreleaseQueueSource
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM DistroreleaseQueueSource)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE DistroreleaseQueueSource ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE DistroreleaseQueueSource ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- GpgKey
ALTER TABLE GpgKey
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE GpgKey
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM GpgKey)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE GpgKey ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE GpgKey ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- License
ALTER TABLE License
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE License
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM License)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE License ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE License ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Milestone
ALTER TABLE Milestone
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Milestone
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM Milestone)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Milestone ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Milestone ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Mirror
ALTER TABLE Mirror
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Mirror
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM Mirror)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Mirror ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Mirror ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- MirrorCdImageDistroRelease
ALTER TABLE MirrorCdImageDistroRelease
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE MirrorCdImageDistroRelease
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM MirrorCdImageDistroRelease)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE MirrorCdImageDistroRelease ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE MirrorCdImageDistroRelease ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- MirrorContent
ALTER TABLE MirrorContent
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE MirrorContent
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM MirrorContent)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE MirrorContent ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE MirrorContent ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- MirrorDistroArchRelease
ALTER TABLE MirrorDistroArchRelease
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE MirrorDistroArchRelease
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM MirrorDistroArchRelease)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE MirrorDistroArchRelease ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE MirrorDistroArchRelease ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- MirrorDistroReleaseSource
ALTER TABLE MirrorDistroReleaseSource
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE MirrorDistroReleaseSource
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM MirrorDistroReleaseSource)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE MirrorDistroReleaseSource ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE MirrorDistroReleaseSource ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- MirrorSourceContent
ALTER TABLE MirrorSourceContent
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE MirrorSourceContent
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM MirrorSourceContent)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE MirrorSourceContent ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE MirrorSourceContent ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PackageBugContact
ALTER TABLE PackageBugContact
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PackageBugContact
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PackageBugContact)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PackageBugContact ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PackageBugContact ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PackageSelection
ALTER TABLE PackageSelection
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PackageSelection
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PackageSelection)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PackageSelection ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PackageSelection ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Packaging
ALTER TABLE Packaging
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Packaging
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM Packaging)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Packaging ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Packaging ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- EmailAddress
ALTER TABLE EmailAddress
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE EmailAddress
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM EmailAddress)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE EmailAddress ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE EmailAddress ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PersonalPackageArchive
ALTER TABLE PersonalPackageArchive
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PersonalPackageArchive
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PersonalPackageArchive)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PersonalPackageArchive ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PersonalPackageArchive ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PersonalSourcePackagePublication
ALTER TABLE PersonalSourcePackagePublication
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PersonalSourcePackagePublication
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PersonalSourcePackagePublication)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PersonalSourcePackagePublication ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PersonalSourcePackagePublication ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PersonLanguage
ALTER TABLE PersonLanguage
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PersonLanguage
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PersonLanguage)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PersonLanguage ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PersonLanguage ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PocketChroot
ALTER TABLE PocketChroot
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PocketChroot
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PocketChroot)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PocketChroot ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PocketChroot ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- POExportRequest
ALTER TABLE POExportRequest
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE POExportRequest
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM POExportRequest)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE POExportRequest ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE POExportRequest ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Poll
ALTER TABLE Poll
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE Poll
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM Poll)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE Poll ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE Poll ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PollOption
ALTER TABLE PollOption
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PollOption
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PollOption)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PollOption ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PollOption ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- POSubscription
ALTER TABLE POSubscription
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE POSubscription
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM POSubscription)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE POSubscription ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE POSubscription ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- ProductBounty
ALTER TABLE ProductBounty
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE ProductBounty
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM ProductBounty)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE ProductBounty ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE ProductBounty ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- ProductBranchRelationship
ALTER TABLE ProductBranchRelationship
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE ProductBranchRelationship
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM ProductBranchRelationship)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE ProductBranchRelationship ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE ProductBranchRelationship ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- ProductCvsModule
ALTER TABLE ProductCvsModule
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE ProductCvsModule
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM ProductCvsModule)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE ProductCvsModule ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE ProductCvsModule ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- ProductSvnModule
ALTER TABLE ProductSvnModule
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE ProductSvnModule
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM ProductSvnModule)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE ProductSvnModule ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE ProductSvnModule ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- ProjectBounty
ALTER TABLE ProjectBounty
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE ProjectBounty
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM ProjectBounty)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE ProjectBounty ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE ProjectBounty ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- PushMirrorAccess
ALTER TABLE PushMirrorAccess
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE PushMirrorAccess
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM PushMirrorAccess)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE PushMirrorAccess ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE PushMirrorAccess ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- SectionSelection
ALTER TABLE SectionSelection
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE SectionSelection
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM SectionSelection)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE SectionSelection ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE SectionSelection ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- ShockAndAwe
ALTER TABLE ShockAndAwe
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE ShockAndAwe
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM ShockAndAwe)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE ShockAndAwe ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE ShockAndAwe ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- SpecificationDependency
ALTER TABLE SpecificationDependency
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE SpecificationDependency
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM SpecificationDependency)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE SpecificationDependency ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE SpecificationDependency ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- SpecificationFeedback
ALTER TABLE SpecificationFeedback
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE SpecificationFeedback
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM SpecificationFeedback)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE SpecificationFeedback ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE SpecificationFeedback ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- SpecificationSubscription
ALTER TABLE SpecificationSubscription
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE SpecificationSubscription
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM SpecificationSubscription)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE SpecificationSubscription ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE SpecificationSubscription ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- SprintAttendance
ALTER TABLE SprintAttendance
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE SprintAttendance
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM SprintAttendance)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE SprintAttendance ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE SprintAttendance ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- SshKey
ALTER TABLE SshKey
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE SshKey
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM SshKey)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE SshKey ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE SshKey ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- SupportContact
ALTER TABLE SupportContact
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE SupportContact
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM SupportContact)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE SupportContact ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE SupportContact ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- TicketBug
ALTER TABLE TicketBug
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE TicketBug
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM TicketBug)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE TicketBug ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE TicketBug ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- TicketSubscription
ALTER TABLE TicketSubscription
    ADD COLUMN date_created TIMESTAMP WITHOUT TIME ZONE;
UPDATE TicketSubscription
    SET date_created='2006-01-01'::timestamp without time zone
        - (((SELECT max(id) FROM TicketSubscription)-id+1)
            || ' seconds')::interval
    WHERE date_created IS NULL;
ALTER TABLE TicketSubscription ALTER COLUMN date_created
    SET NOT NULL;
ALTER TABLE TicketSubscription ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

/* Drop some unused and undocumented tables. We can always add them back if
needed, but for now they serve no purpose but to complicate things. */

DROP TABLE BranchLabel;
DROP TABLE BugLabel;
DROP TABLE PersonLabel;
DROP TABLE ProductLabel;
DROP TABLE TranslationEffortPOTemplate;
DROP TABLE TranslationEffort;
DROP TABLE Label;
DROP TABLE Schema;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 26, 0);
