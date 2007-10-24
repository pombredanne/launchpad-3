SET client_min_messages=ERROR;

CREATE TABLE MailingList (
    id              serial PRIMARY KEY,
    team            integer NOT NULL UNIQUE REFERENCES Person,
    -- The id of the Person who requested this list be created.
    registrant      integer NOT NULL REFERENCES Person,
    -- Date the list was requested to be created
    date_registered timestamp without time zone NOT NULL
                        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    -- The id of the Person who reviewed the creation request, or NULL if not
    -- yet reviewed.
    reviewer        integer REFERENCES Person,
    -- The date the request was reviewed, or NULL if not yet reviewed.
    date_reviewed   timestamp without time zone
                       DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), 
    -- The date the list was (last) activated.  If the list is not yet active,
    -- this field will be NULL.
    date_activated  timestamp without time zone
                       DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), 
    -- The status of the mailing list, as a DBschema value.
    -- MailingListStatus.REGISTERED (1)
    -- MailingListStatus.APPROVED (2)
    -- MailingListStatus.DECLINED (3)
    -- MailingListStatus.CONSTRUCTING (4)
    -- MailingListStatus.ACTIVE (5)
    -- MailingListStatus.FAILED (6)
    -- MailingListStatus.INACTIVE (7)
    status          integer DEFAULT 1 NOT NULL,
    -- Text sent to new members when they are subscribed to the team list.  If
    -- NULL, no welcome message is sent.
    welcome_message_text    text,
    CONSTRAINT is_team CHECK (is_team(team))
    );

-- Index for people merge and listing a teams mailinglists grouped by status
CREATE UNIQUE INDEX mailinglist__team__status__key ON MailingList(team, status);
CREATE INDEX mailinglist__registrant__idx ON MailingList(registrant);
CREATE INDEX mailinglist__reviewer__idx ON MailingList(reviewer);
-- Index For the review queue
CREATE INDEX mailinglist__date_registered__idx
    ON MailingList(status, date_registered);


/* The person's standing indicates (for now, just) whether the person can
   post to a mailing list without requiring first post moderation.  This
   field gets updated automatically by Launchpad, via cron script.

   It's values are a DBschema enum with the following values.  The number in
   parentheses is the integer equivalent.

   PersonalStanding.UNKNOWN (0)
        -- Nothing about this person's standing is known.
   PersonalStanding.POOR (100)
        -- This person has bad standing.  For now, the only way to get bad
           standing is for a Launchpad administrator to explicitly set it
           as such.
   PersonalStanding.GOOD (200)
        -- The person has good standing, meaning they reasonably understand
           netiquette and may post to mailing lists without having their
           first posts be moderated.
   PersonalStanding.EXCELLENT (300)
        -- The person has excellent standing.  Currently the only way to set
           is is by explicitly tweaking the database.  Nothing currently
           requires excellent standing, although a person with EXCELLENT
           standing can do everything a person with GOOD standing can do.
*/
/* Need to populate this post rollout and set NOT NULL next cycle
ALTER TABLE person ADD COLUMN personal_standing integer DEFAULT 0 NOT NULL;
*/
ALTER TABLE Person ADD COLUMN personal_standing integer;

/* The reason a person's standing has changed.  This allows a Launchpad
   administrator to record the reason they might manually increase or decrease
   a person's standing.
*/
ALTER TABLE person ADD COLUMN personal_standing_reason_text text;

/* A NULL resumption date or a date in the past indicates that there is no
   vacation in effect.  Vacations are granular to the day, so a datetime is
   not necessary.
*/
ALTER TABLE person ADD COLUMN mail_resumption_date date;

/* This DBschema enum defines the following values, used in this column.  The
   numbers in parentheses indicates the integer value equivalent.

   MailingListAutoSubscribePolicy.NEVER (0)
        -- The user must explicitly join a team mailing list for any team that
           she joins.
   MailingListAutoSubscribePolicy.ON_REGISTRATION (1)
        -- The user is automatically joined to any team mailing list that she
           joins herself.
   MailingListAutoSubscribePolicy.ALWAYS (2)
        -- The user is automatically joined to any team mailing list when she
           is added to the team, regardless of who joins her to the team.
*/
/* Needs to be populated post rollout, and a NOT NULL constraint added
next cycle
ALTER TABLE person ADD COLUMN
    mailing_list_auto_subscribe_policy integer DEFAULT 1 NOT NULL;
*/
ALTER TABLE Person ADD COLUMN mailing_list_auto_subscribe_policy integer;

/* True means the user wants to receive list copies of messages on which they
   are explicitly named as a recipient.
*/
/* Needs to be populated post rollout, and a NOT NULL constraint added next
cycle
ALTER TABLE person ADD COLUMN
    mailing_list_receive_duplicates boolean DEFAULT true NOT NULL;
*/
ALTER TABLE Person ADD COLUMN mailing_list_receive_duplicates boolean;


CREATE TABLE MailingListSubscription (
    id                  serial PRIMARY KEY,
    -- Person who is subscribed to the mailing list
    person              integer NOT NULL REFERENCES Person,
    -- Team whose mailing list this person is subscribed
    mailing_list        integer NOT NULL REFERENCES MailingList,
    -- The date this person subscribed to the mailing list
    date_joined         timestamp without time zone NOT NULL
                            DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'), 
    -- Foreign key to the EmailAddress table indicating which email address
    -- is subscribed to this list.  It may be NULL to indicate that the
    -- person's preferred address (which may change) is subscribed.
    email_address       integer
);

-- email_address should reference one of person's email addresses
ALTER TABLE EmailAddress ADD CONSTRAINT emailaddress__person__id__key
    UNIQUE (person, id);
ALTER TABLE ONLY MailingListSubscription
    ADD CONSTRAINT MailingListSubscription__person__email_address__fk
    FOREIGN KEY (person, email_address) REFERENCES EmailAddress(person, id)
    ON UPDATE CASCADE;

CREATE UNIQUE INDEX mailinglistsubscription__person__mailing_list__key
    ON MailingListSubscription(person, mailing_list);

CREATE INDEX mailinglistsubscription__mailing_list__idx
    ON MailingListSubscription(mailing_list);

CREATE INDEX mailinglistsubscription__email_address__idx
    ON MailingListSubscription(email_address) WHERE email_address IS NOT NULL;


CREATE TABLE MailingListBan (
    id          serial PRIMARY KEY,
    -- The person who was banned
    person      integer NOT NULL REFERENCES Person,
    -- The administrator who imposed the ban
    banned_by   integer NOT NULL REFERENCES Person,
    -- When the ban was imposed
    date_banned timestamp without time zone NOT NULL
                    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    -- The reason for the ban
    reason_text text NOT NULL
);

CREATE INDEX mailinglistban__person__idx
    ON MailingListBan(person);

CREATE INDEX mailinglistban__banned_by__idx
    ON MailingListBan(banned_by);


CREATE TABLE MessageApproval (
    id              serial PRIMARY KEY,
    /* The Message-ID header of the held message. */
    message_id      text UNIQUE NOT NULL,
    /* The id of the Person who posted the message. */
    posted_by       integer NOT NULL REFERENCES Person,
    /* The team mailing list to which the message was posted. */
    mailing_list    integer NOT NULL REFERENCES MailingList,
    /* Foreign key to libraryfilealias table pointing to where the posted
       message's text lives.
    */
    posted_message  integer NOT NULL REFERENCES LibraryFileAlias,
    /* The date the message was posted. */
    posted_date     timestamp without time zone NOT NULL
                        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    /* This DBschema enum defines the status of the posted message.  The
       numbers in parentheses indicates the integer value equivalent.

       PostedMessageStatus.NEW (0)
            -- The message has been posted but no disposition has yet been
               made.
       PostedMessageStatus.APPROVED (1)
            -- The message has been approved for delivery.
       PostedMessageStatus.REJECTED (2)
            -- The message has been rejected and will not be delivered.
    */
    status          integer DEFAULT 0 NOT NULL,
    /* Id of the Person who disposed of this message, or NULL if no
       disposition has yet been made (i.e. this message is in the
       PostedMessageStatus.NEW state.
    */
    disposed_by     integer REFERENCES Person,
    /* The date on which this message was disposed, or NULL if no disposition
       has yet been made.
    */
    disposal_date   timestamp without time zone
                        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);


-- Indexes needed by people merge
CREATE INDEX messageapproval__posted_by__idx
    ON MessageApproval(posted_by);
CREATE INDEX messageapproval__mailing_list__status__posted_date__idx
    ON MessageApproval(mailing_list, status, posted_date);
CREATE INDEX messageapproval__disposed_by__idx
    ON MessageApproval(disposed_by) WHERE disposed_by IS NOT NULL;

-- Index needed by Librarian garbage collection
CREATE INDEX messageapproval__posted_message__idx
    ON MessageApproval(posted_message);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 24, 0);
