SET client_min_messages=ERROR;

/*
  This fixes the name of a field in the bugattachment table. Ages ago when
  we renamed bugmessage to message and then created a new bugmessage linking
  table between bug and message I should have spotted this fieldname and
  renamed it. Stub, this one is good to go.

  Note that the bugattachment system will be entirely reviewed once we have
  figured out emails-in-the-database properly, with the email-sig.
*/

ALTER TABLE bugattachment RENAME COLUMN bugmessage TO message;
ALTER TABLE bugattachment DROP CONSTRAINT bugattachment_bugmessage_fk;
ALTER TABLE bugattachment ADD CONSTRAINT bugattachment_message_fk
    FOREIGN KEY (message) REFERENCES Message;
ALTER TABLE bugattachment DROP CONSTRAINT "$2";
ALTER TABLE bugattachment ADD CONSTRAINT bugattachment_libraryfile_fk
    FOREIGN KEY (libraryfile) REFERENCES LibraryFileAlias;


/* Bounty Tracker Enhancements

   This patch lays the foundations for being able to link a bounty to a
   product or to a distribution. It also allows people to subscribe to
   bounties. Subscribers will be notified when interesting things happen to
   the bounty.
*/

CREATE TABLE BountySubscription (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL CONSTRAINT bountysubscription_bounty_fk
                    REFERENCES Bounty,
    person         integer NOT NULL CONSTRAINT bountysubscription_person_fk
                    REFERENCES Person,
    subscription   integer, -- dbschema.BountySubscription
    UNIQUE ( person, bounty )
    );

CREATE TABLE ProductBounty (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL CONSTRAINT productbounty_bounty_fk
                    REFERENCES Bounty,
    product        integer NOT NULL CONSTRAINT productbounty_product_fk
                    REFERENCES Product,
    UNIQUE ( bounty, product )
    );

CREATE TABLE DistroBounty (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL CONSTRAINT distrobounty_bounty_fk
                    REFERENCES Bounty,
    distribution   integer NOT NULL CONSTRAINT distrobounty_distribution_fk
                    REFERENCES Distribution,
    UNIQUE ( bounty, distribution )
    );

CREATE TABLE ProjectBounty (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL CONSTRAINT projectbounty_bounty_fk
                    REFERENCES Bounty,
    project        integer NOT NULL CONSTRAINT projectbounty_project_fk
                    REFERENCES Project,
    UNIQUE ( bounty, project )
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (11,1,0);

