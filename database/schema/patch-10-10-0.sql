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


/* Bounty Tracker Enhancements

   This patch lays the foundations for being able to link a bounty to a
   product or to a distribution. It also allows people to subscribe to
   bounties. Subscribers will be notified when interesting things happen to
   the bounty.
*/

CREATE TABLE BountySubscription (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL REFERENCES Bounty,
    person         integer NOT NULL REFERENCES Person,
    subscription   integer, -- dbschema.BountySubscription
    UNIQUE ( person, bounty )
    );

CREATE TABLE ProductBounty (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL REFERENCES Bounty,
    product        integer NOT NULL REFERENCES Product,
    UNIQUE ( bounty, product )
    );

CREATE TABLE DistroBounty (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL REFERENCES Bounty,
    distribution   integer NOT NULL REFERENCES Distribution,
    UNIQUE ( bounty, distribution )
    );

CREATE TABLE ProjectBounty (
    id             serial PRIMARY KEY,
    bounty         integer NOT NULL REFERENCES Bounty,
    project   integer NOT NULL REFERENCES Distribution,
    UNIQUE ( bounty, project )
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (10,10,0);

