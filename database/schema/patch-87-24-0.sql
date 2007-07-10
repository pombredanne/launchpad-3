SET client_min_messages=ERROR;

CREATE TABLE MailingList (
    id              serial PRIMARY KEY,
    team            integer NOT NULL REFERENCES Person,
    -- The id of the Person who requested this list be created.
    registrant      integer NOT NULL REFERENCES Person,
    -- Date the list was requested to be created
    date_registered timestamp without time zone DEFAULT timezone('UTC'::text,
                    ('now'::text)::timestamp(6) with time zone) NOT NULL,
    -- The id of the Person who reviewed the creation request, or NULL if not
    -- yet reviewed.
    reviewer        integer REFERENCES Person,
    -- The date the request was reviewed, or NULL if not yet reviewed.
    date_reviewed   timestamp without time zone DEFAULT timezone('UTC'::text,
                    ('now'::text)::timestamp(6) with time zone),
    -- The date the list was (last) activated.  If the list is not yet active,
    -- this field will be NULL.
    date_activated  timestamp without time zone DEFAULT timezone('UTC'::text,
                    ('now'::text)::timestamp(6) with time zone),
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
    welcome_message_text    text
    );

ALTER TABLE ONLY MailingList
    ADD CONSTRAINT MailingList_team_fk
    FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY MailingList
    ADD CONSTRAINT MailingList_registrant_fk
    FOREIGN KEY (registrant) REFERENCES person(id);

ALTER TABLE ONLY MailingList
    ADD CONSTRAINT MailingList_reviewer_fk
    FOREIGN KEY (reviewer) REFERENCES person(id);

CREATE INDEX mailinglist__team__status__idx ON MailingList(team, status);

CREATE INDEX mailinglist__registrant__idx ON MailingList(registrant)
    WHERE registrant IS NOT NULL;


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
ALTER TABLE person ADD COLUMN personal_standing integer DEFAULT 0 NOT NULL;

/* The reason a person's standing has changed.  This allows a Launchpad
   administrator to record the reason they might manually increase or decrease
   a person's standing.
*/
ALTER TABLE person ADD COLUMN personal_standing_reason_text text;

/* A NULL resumption date or a date in the past indicates that there is no
   vacation in effect.  Vacations are granular to the day, so a datetime is
   not necessary.
*/
ALTER TABLE person ADD COLUMN mail_resumption_date date DEFAULT NULL;

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
ALTER TABLE person ADD COLUMN
    mailing_list_auto_subscribe_policy integer DEFAULT 1 NOT NULL;

/* True means the user wants to receive list copies of messages on which they
   are explicitly named as a recipient.
*/
ALTER TABLE person ADD COLUMN
    mailing_list_receive_duplicates boolean DEFAULT true NOT NULL;


CREATE TABLE MailingListSubscription (
    id          serial NOT NULL,
    -- Person who is subscribed to the mailing list
    person      integer NOT NULL,
    -- Team whose mailing list this person is subscribed
    team        integer NOT NULL,
    -- The date this person subscribed to the mailing list
    date_joined timestamp without time zone DEFAULT
        timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
        NOT NULL,
    -- Foreign key to the EmailAddress table indicating which email address
    -- is subscribed to this list.  It may be NULL to indicate that the
    -- person's preferred address (which may change) is subscribed.
    email_address   integer
);

ALTER TABLE ONLY MailingListSubscription
    ADD CONSTRAINT MailingListSubscription_pkey PRIMARY KEY (id);

ALTER TABLE ONLY MailingListSubscription
    ADD CONSTRAINT MailingListSubscription_person_fk
    FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY MailingListSubscription
    ADD CONSTRAINT MailingListSubscription_team_fk
    FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY MailingListSubscription
    ADD CONSTRAINT MailingListSubscription_email_address_fk
    FOREIGN KEY (email_address) REFERENCES EmailAddress(id);

CREATE UNIQUE INDEX mailinglistsubscription__person__team__key
    ON MailingListSubscription(person, team);

CREATE INDEX mailinglistsubscription__team__idx
    ON MailingListSubscription(team);

CREATE INDEX mailinglistsubscription__email_address__idx
    ON MailingListSubscription(email_address) WHERE email_address IS NOT NULL;


CREATE TABLE MailingListBan (
    id          serial NOT NULL,
    -- The person who was banned
    person      integer NOT NULL,
    -- The administrator who imposed the ban
    banned_by   integer NOT NULL,
    -- When the ban was imposed
    date_banned timestamp without time zone DEFAULT
        timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
        NOT NULL,
    -- The reason for the ban
    reason_text text
);

ALTER TABLE ONLY MailingListBan
    ADD CONSTRAINT MailingListBan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY MailingListBan
    ADD CONSTRAINT MailingListBan_person_fk
    FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE ONLY MailingListBan
    ADD CONSTRAINT MailingListBan_banned_by_fk
    FOREIGN KEY (banned_by) REFERENCES person(id);

CREATE INDEX mailinglistban__person__idx
    ON MailingListBan(person);

CREATE INDEX mailinglistban__banned_by__idx
    ON MailingListBan(banned_by);


CREATE TABLE MessagesAwaitingApproval (
    id              serial NOT NULL,
    /* The Message-ID header of the held message. */
    message_id      text NOT NULL,
    /* The id of the Person who posted the message. */
    posted_by       integer NOT NULL,
    /* The team mailing list to which the message was posted. */
    team            integer NOT NULL,
    /* Foreign key to libraryfilealias table pointing to where the posted
       message's text lives.
    */
    posted_message  integer NOT NULL,
    /* The date the message was posted. */
    posted_date     timestamp without time zone DEFAULT
        timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
        NOT NULL,
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
    disposed_by     integer,
    /* The date on which this message was disposed, or NULL if no disposition
       has yet been made.
    */
    disposal_date   timestamp without time zone DEFAULT
        timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
);

ALTER TABLE ONLY MessagesAwaitingApproval
    ADD CONSTRAINT MessagesAwaitingApproval_pkey PRIMARY KEY (id);

ALTER TABLE ONLY MessagesAwaitingApproval
    ADD CONSTRAINT MessagesAwaitingApproval_posted_by_fk
    FOREIGN KEY (posted_by) REFERENCES person(id);

ALTER TABLE ONLY MessagesAwaitingApproval
    ADD CONSTRAINT MessagesAwaitingApproval_team_fk
    FOREIGN KEY (team) REFERENCES person(id);

ALTER TABLE ONLY MessagesAwaitingApproval
    ADD CONSTRAINT MessagesAwaitingApproval_disposed_by_fk
    FOREIGN KEY (disposed_by) REFERENCES person(id);

ALTER TABLE ONLY MessagesAwaitingApproval
    ADD CONSTRAINT MessagesAwaitingApproval_posted_message_fk
    FOREIGN KEY (posted_message) REFERENCES libraryfilealias(id);

ALTER TABLE MessagesAwaitingApproval ADD CONSTRAINT
    messagesawaitingapproval__message_id__key UNIQUE (message_id);


CREATE INDEX MessagesAwaitingApproval_message_id__idx
    ON MessagesAwaitingApproval USING btree (message_id);

CREATE INDEX messagesawaitingapproval__posted_by__idx
    ON MessagesAwaitingApproval(posted_by);

CREATE INDEX messagesawaitingapproval__team__status__posted_date__idx
    ON MessagesAwaitingApproval(team, status, posted_date);

CREATE INDEX messageawaitingapproval__posted_message__idx
    ON MessagesAwaitingApproval(posted_message);

CREATE INDEX messagesawaitingapproval__disposed_by__idx
    ON MessagesAwaitingApproval(disposed_by) WHERE disposed_by IS NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 24, 0);
