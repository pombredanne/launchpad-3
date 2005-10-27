
set client_min_messages=ERROR;

/* Infrastructure for the Support Tracker. This is a community and
 * commercial support tracker that will allow people to get help with
 * Ubuntu, or derivatives, or upstreams in Launchpad. */

/* create the support request table */

CREATE TABLE Ticket (
  id                 serial PRIMARY KEY,
  owner              integer NOT NULL CONSTRAINT ticket_owner_fk
                             REFERENCES Person,
  title              text NOT NULL,
  description        text NOT NULL,
  assignee           integer CONSTRAINT ticket_assignee_fk REFERENCES Person,
  answerer           integer CONSTRAINT ticket_answerer_fk REFERENCES Person,
  product            integer CONSTRAINT ticket_product_fk REFERENCES Product,
  distribution       integer CONSTRAINT ticket_distribution_fk
                             REFERENCES Distribution,
  sourcepackagename  integer CONSTRAINT ticket_sourcepackagename_fk
                             REFERENCES SourcePackagename,
  status             integer NOT NULL,
  priority           integer NOT NULL,
  datecreated        timestamp WITHOUT TIME ZONE NOT NULL
                               DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  datelastquery      timestamp WITHOUT TIME ZONE NOT NULL
                               DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  dateaccepted       timestamp WITHOUT TIME ZONE,
  datedue            timestamp WITHOUT TIME ZONE,
  datelastresponse   timestamp WITHOUT TIME ZONE,
  dateanswered       timestamp WITHOUT TIME ZONE,
  dateclosed         timestamp WITHOUT TIME ZONE,
  whiteboard         text,

  -- Currently must have either a product or a distribution
  CONSTRAINT product_or_distro CHECK (product IS NULL <> distribution IS NULL),
 
  -- sourcepackagename should only be set if we are linked to a distribution
  CONSTRAINT sourcepackagename_needs_distro
    CHECK (sourcepackagename IS NULL OR distribution IS NOT NULL)
);

/* Indexes on Ticket table */
CREATE INDEX ticket_owner_idx ON Ticket(assignee);
CREATE INDEX ticket_assignee_idx ON Ticket(assignee);
CREATE INDEX ticket_answerer_idx ON Ticket(answerer);
CREATE INDEX ticket_product_idx ON Ticket(product);
CREATE INDEX ticket_distribution_sourcepackagename_idx
    ON Ticket(distribution, sourcepackagename);
CREATE INDEX ticket_distro_datecreated_idx
    ON Ticket(distribution, datecreated);
CREATE INDEX ticket_product_datecreated_idx
    ON Ticket(product, datecreated);
-- Possibly want indexes on some of the timestamp columns too if we are
-- doing db side ordering or 'what issues have stagnated' type reports. 


 /* Link tickets and bugs */

CREATE TABLE TicketBug (
    id            serial PRIMARY KEY,
    ticket        integer NOT NULL,
    bug           integer NOT NULL
);

ALTER TABLE TicketBug ADD CONSTRAINT
    ticketbug_ticket_fk FOREIGN KEY (ticket) REFERENCES Ticket(id);

ALTER TABLE TicketBug ADD CONSTRAINT
    ticketbug_bug_fk FOREIGN KEY (bug) REFERENCES Bug(id);

ALTER TABLE TicketBug ADD CONSTRAINT
    ticketbug_bug_ticket_uniq UNIQUE (bug, ticket);

CREATE INDEX ticketbug_ticket_idx
    ON TicketBug(ticket);



/* Track the times we have re-opened a Ticket */

CREATE TABLE TicketReopening (
    id            serial PRIMARY KEY,
    ticket        integer NOT NULL CONSTRAINT ticketreopening_ticket_fk
                                   REFERENCES Ticket(id),
    datecreated   timestamp WITHOUT TIME ZONE NOT NULL
                            DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    reopener      integer NOT NULL CONSTRAINT ticketreopening_reopener_fk
                                   REFERENCES Person(id),
    answerer      integer CONSTRAINT ticketreopening_answerer_fk
                          REFERENCES Person(id),
    dateanswered  timestamp WITHOUT TIME ZONE,
    priorstate    integer NOT NULL
);

CREATE INDEX ticketreopening_ticket_idx ON TicketReopening(ticket);
CREATE INDEX ticketreopening_reopener_idx ON TicketReopening(reopener);
CREATE INDEX ticketreopening_answerer_idx ON TicketReopening(answerer);
CREATE INDEX ticketreopening_datecreated_idx ON TicketReopening(datecreated);


/* Allow for subscriptions to tickets */

CREATE TABLE TicketSubscription (
    id            serial PRIMARY KEY,
    ticket        integer NOT NULL,
    person        integer NOT NULL
);

ALTER TABLE TicketSubscription ADD CONSTRAINT
    ticketsubscription_ticket_fk FOREIGN KEY (ticket)
    REFERENCES Ticket(id);

ALTER TABLE TicketSubscription ADD CONSTRAINT
    ticketsubscription_person_fk FOREIGN KEY (person)
    REFERENCES Person(id);

ALTER TABLE TicketSubscription ADD CONSTRAINT
    ticketsubscription_ticket_person_uniq
    UNIQUE (ticket, person);

CREATE INDEX ticketsubscription_subscriber_idx
    ON TicketSubscription(person);


/* allow for comments on tickets */

CREATE TABLE TicketMessage (
    id                  serial PRIMARY KEY,
    ticket              integer NOT NULL CONSTRAINT ticketmessage_ticket_fk
                                REFERENCES Ticket(id),
    message             integer NOT NULL CONSTRAINT ticketmessage_message_fk
                                REFERENCES Message(id)
);

ALTER TABLE TicketMessage ADD CONSTRAINT ticketmessage_message_ticket_uniq
    UNIQUE (message, ticket);

CREATE INDEX ticketmessage_ticket_idx
    ON TicketMessage(ticket);


/* allow for comments on bounties */

CREATE TABLE BountyMessage (
    id                  serial PRIMARY KEY,
    bounty              integer NOT NULL CONSTRAINT bountymessage_bounty_fk
                                REFERENCES Bounty(id),
    message             integer NOT NULL CONSTRAINT bountymessage_message_fk
                                REFERENCES Message(id)
);

ALTER TABLE BountyMessage ADD CONSTRAINT bountymessage_message_bounty_uniq
    UNIQUE (message, bounty);

CREATE INDEX bountymessage_bounty_idx
    ON BountyMessage(bounty);


/* clean up bug subscription system */

DELETE FROM BugSubscription WHERE subscription=3;
ALTER TABLE BugSubscription DROP COLUMN subscription;

/* we should have done this last week */

CREATE INDEX specificationsubscription_specification_idx
    ON SpecificationSubscription(specification);

/* make sure we can identify the places where launchpad is being used as the
 * official bug tracker or translation engine for a product. */

ALTER TABLE Product ADD COLUMN official_rosetta BOOLEAN;
ALTER TABLE Product ADD COLUMN official_malone BOOLEAN;
-- Do one update, avoiding bloat (because rows need to be rewritten when
-- they grow new columns)
UPDATE Product SET official_rosetta = FALSE, official_malone=False;
ALTER TABLE Product ALTER COLUMN official_rosetta SET DEFAULT FALSE;
ALTER TABLE Product ALTER COLUMN official_rosetta SET NOT NULL;
ALTER TABLE Product ALTER COLUMN official_malone SET DEFAULT FALSE;
ALTER TABLE Product ALTER COLUMN official_malone SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,20,0);

