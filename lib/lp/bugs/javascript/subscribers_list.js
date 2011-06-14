/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Classes for managing the subscribers list.
 *
 * Two classes are provided:
 *
 *   - SubscribersList: deals with node construction/removal for the
 *     list of subscribers, including activity indication and animations.
 *
 *     Public methods to use:
 *       startActivity, stopActivity,
 *       addSubscriber, removeSubscriber, indicateSubscriberActivity,
 *       stopSubscriberActivity, addUnsubscribeAction
 *
 *   - BugSubscribersLoader: loads subscribers from LP, allows subscribing
 *     someone else and sets unsubscribe actions where appropriate.
 *     Depends on the SubscribersList to do the actual node construction.
 *
 *     No public methods are available: it all gets run from the constructor.
 *
 * @module bugs
 * @submodule subscribers_list
 */

YUI.add('lp.bugs.subscribers_list', function(Y) {

var namespace = Y.namespace('lp.bugs.subscribers_list');

/**
 * Reset the subscribers list if needed.
 *
 * Adds the "None" div to the subscribers list if
 * there aren't any subscribers left, and clears up
 * the duplicate subscribers list if empty.
 *
 * @method reset
 */
function reset() {
    var subscriber_list = Y.one('#subscribers-links');
    // Assume if subscriber_list has no child divs
    // then the list of subscribers is empty.
    if (!Y.Lang.isValue(subscriber_list.one('div')) &&
        !Y.Lang.isValue(Y.one('#none-subscribers'))) {
        var none_div = Y.Node.create(
            '<div id="none-subscribers">No subscribers.</div>');
        var subscribers = subscriber_list.get('parentNode');
        subscribers.appendChild(none_div);
    }

    // Clear the empty duplicate subscribers list if it exists.
    var dup_list = Y.one('#subscribers-from-duplicates');
    if (Y.Lang.isValue(dup_list) &&
        !Y.Lang.isValue(dup_list.one('div'))) {
        dup_list.remove();
    }
}
namespace._reset = reset;

/**
 * Remove the user's name from the subscribers list.
 * It uses the green-flash animation to indicate successful removal.
 *
 * @method remove_user_link
 * @param subscriber {Subscriber} Subscriber that you want to remove.
 * @param is_dupe {Boolean} Uses subscription link from the duplicates
 *     instead.
 */
function remove_user_link(subscriber, is_dupe) {
    var user_node_id;
    var user_name = subscriber.get('css_name');
    if (is_dupe === true) {
        user_node_id = '#dupe-' + user_name;
    } else {
        user_node_id = '#direct-' + user_name;
    }
    var user_node = Y.one(user_node_id);
    if (Y.Lang.isValue(user_node)) {
        // If there's an icon, we remove it prior to animation
        // so animation looks better.
        var unsub_icon = user_node.one('#unsubscribe-icon-' + user_name);
        if (Y.Lang.isValue(unsub_icon)) {
            unsub_icon.remove();
        }
        var anim = Y.lazr.anim.green_flash({ node: user_node });
        anim.on('end', function() {
            user_node.remove();
            reset();
        });
        anim.run();
    }
}
namespace.remove_user_link = remove_user_link;


var CSS_CLASSES = {
    section : 'subscribers-section',
    list: 'subscribers-list',
    subscriber: 'subscriber',
    no_subscribers: 'no-subscribers-indicator',
    activity: 'global-activity-indicator',
    activity_text: 'global-activity-text',
    subscriber_activity: 'subscriber-activity-indicator',
    actions: 'subscriber-actions',
    unsubscribe: 'unsubscribe-action'
};

/**
 * Possible subscriber levels with descriptive headers for
 * sections that will hold them.
 *
 * These match BugNotificationLevel enum options (as defined in
 * lib/lp/bugs/enum.py).
 */
var subscriber_levels = {
    'Discussion': 'Notified of all changes',
    'Details': 'Notified of all changes except comments',
    'Lifecycle': 'Notified when the bug is closed or reopened',
    'Maybe': 'Maybe notified'
};

/**
 * Order of subscribers sections.
 */
var subscriber_level_order = ['Discussion', 'Details', 'Lifecycle', 'Maybe'];


/**
 * Checks if the subscription level is one of the acceptable ones.
 * Throws an error if not, otherwise silently returns.
 */
function checkSubscriptionLevel(level) {
    if (!subscriber_levels.hasOwnProperty(level)) {
        Y.error(
            'Level "' + level + '" is not an acceptable subscription level.');
    }
}


/**
 * Load subscribers for a bug from Launchpad and put them in the web page.
 *
 * Uses SubscribersList class to manage actual node construction
 * and handling, and is mostly in charge of communication with Launchpad.
 *
 * Loading is triggered automatically on instance construction.
 *
 * @class BugSubscribersLoader
 * @param config {Object} Defines `container_box' CSS selector for the
 *     SubscribersList container box, `bug' holding bug metadata (at
 *     least with `web_link') and `subscribers_details_view' holding
 *     a relative URI to load subscribers' details from.
 */
function BugSubscribersLoader(config) {
    var sl = this.subscribers_list = new SubscribersList(config);

    if (!Y.Lang.isValue(config.bug) ||
        !Y.Lang.isString(config.bug.web_link)) {
        Y.error(
            "No bug specified in `config' or bug.web_link is invalid.");
    }
    this.bug = config.bug;

    // Get BugSubscribersWithDetails portlet link to load subscribers from.
    if (!Y.Lang.isString(config.subscribers_details_view)) {
        Y.error(
            "No config.subscribers_details_view specified to load " +
                "other bug subscribers from.");
    }
    this.subscribers_portlet_uri = (
        this.bug.web_link + config.subscribers_details_view);

    this.error_handler = new Y.lp.client.FormErrorHandler();
    this.error_handler.showError = function (error_msg) {
        sl.stopActivity("Problem loading subscribers. " + error_msg);
    };

    // Allow tests to override lp_client.
    if (Y.Lang.isValue(config.lp_client)) {
        this.lp_client = config.lp_client;
    } else {
        this.lp_client = new Y.lp.client.Launchpad();
    }

    this._loadSubscribers();

    // Check for CSS class for the link to subscribe someone else.
    if (Y.Lang.isString(config.subscribe_someone_else_link)) {
        this.subscribe_someone_else_link = config.subscribe_someone_else_link;
        this._setupSubscribeSomeoneElse();
    }
}
namespace.BugSubscribersLoader = BugSubscribersLoader;

/**
 * Adds a subscriber along with the unsubscribe callback if needed.
 *
 * @method _addSubscriber
 * @param subscriber {Object} A common subscriber object passed
 *     directly to SubscribersList.addSubscriber().
 *     If subscriber.can_edit === true, adds an unsubscribe callback
 *     as returned by this._getUnsubscribeCallback().
 * @param level {String} A bug subscription level (one of
 *     subscriber_levels values).  When level doesn't match any of the
 *     supported levels, 'Maybe' is used instead.
 */
BugSubscribersLoader.prototype._addSubscriber = function(subscriber, level) {
    if (!subscriber_levels.hasOwnProperty(level)) {
        // Default to 'subscribed at unknown level' for unrecognized
        // subscription levels.
        level = 'Maybe';
    }

    var unsubscribe_callback = this._getUnsubscribeCallback();

    if (subscriber.can_edit === true) {
        this.subscribers_list.addSubscriber(subscriber, level, {
            unsubscribe_callback: unsubscribe_callback});
    } else {
        this.subscribers_list.addSubscriber(subscriber, level);
    }
};

/**
 * Load bug subscribers from the list of subscribers and add subscriber rows
 * for them.
 *
 * @method _loadSubscribersFromList
 * @param details {List} List of subscribers with their subscription levels.
 */
BugSubscribersLoader.prototype._loadSubscribersFromList = function(
    details) {
    if (!Y.Lang.isArray(details)) {
        Y.error('Got non-array "'+ details +
                '" in _loadSubscribersFromList().');
    }
    var index, subscriber, level;
    for (index = 0; index < details.length; index++) {
        subscriber = details[index].subscriber;
        if (!Y.Lang.isObject(details[index])) {
            Y.error('Subscriber details at index ' + index + ' (' +
                    details[index] + ') are not an object.');
        }
        this._addSubscriber(subscriber,
                            details[index].subscription_level);
    }
};

/**
 * Load subscribers from the JSON portlet with details, adding them
 * to the actual subscribers list managed by this class.
 *
 * JSON string in the portlet should be of the following form:
 *
 *     [ { "subscriber": {
 *           "name": "foobar",
 *           "display_name": "Foo Bar",
 *           "can_edit": true/false,
 *           "is_team": false/false,
 *           "web_link": "https://launchpad.dev/~foobar"
 *           },
 *         "subscription_level": "Details"},
 *       { "subscriber": ... }
 *     ]
 * JSON itself is parsed by lp_client.get().
 *
 * Uses SubscribersList startActivity/stopActivity methods to indicate
 * progress and/or any errors it hits.
 *
 * @method _loadSubscribers
 */
BugSubscribersLoader.prototype._loadSubscribers = function() {
    var sl = this.subscribers_list;
    var loader = this;

    // Fetch the person and add a subscription.
    function on_success(subscribers) {
        loader._loadSubscribersFromList(subscribers);
        loader.subscribers_list.stopActivity();
    }

    var config = { on: {
        success: on_success,
        failure: this.error_handler.getFailureHandler()
    } };

    sl.startActivity("Loading subscribers...");
    this.lp_client.get(this.subscribers_portlet_uri, config);
};

/**
 * Return a function object that accepts SubscribersList and subscriber
 * objects as parameters.
 *
 * Constructed function tries to unsubscribe subscriber from the
 * this.bug, and indicates activity in the subscribers list.
 *
 * @method _getUnsubscribeCallback
 */
BugSubscribersLoader.prototype._getUnsubscribeCallback = function() {
    var loader = this;
    return function(subscribers_list, subscriber) {
        function on_success() {
            subscribers_list.stopSubscriberActivity(
                subscriber, true, function() {
                subscribers_list.removeSubscriber(subscriber);
            });
        }
        function on_failure() {
            subscribers_list.stopSubscriberActivity(subscriber, false);
        }

        var config = {
            on: { success: on_success,
                  failure: on_failure },
            parameters: { person: subscriber.self_link }
        };
        subscribers_list.indicateSubscriberActivity(subscriber);
        loader.lp_client.named_post(
            loader.bug.self_link, 'unsubscribe', config);
    };
};

/**
 * Set-up subscribe-someone-else link to pop-up a picker and subscribe
 * the selected person/team.
 *
 * On `save' from the picker, fetch the actual person object via API
 * and pass it into _subscribeSomeoneElse().
 *
 * @method _setupSubscribeSomeoneElse
 */
BugSubscribersLoader.prototype._setupSubscribeSomeoneElse = function() {
    var loader = this;
    var config = {
        header: 'Subscribe someone else',
        step_title: 'Search',
        picker_activator: this.subscribe_someone_else_link
    };
    config.save = function(result) {
        var person_uri = Y.lp.client.get_absolute_uri(result.api_uri);
        loader.lp_client.get(person_uri, {
            on: {
                success: function(person) {
                    loader._subscribeSomeoneElse(person);
                },
                failure: function() {
                    // Failed to get person/team details, thus
                    // they have not been subscribed.
                }
            } });
    };
    var picker = Y.lp.app.picker.create('ValidPersonOrTeam', config);
};

/**
 * Subscribe a person or a team to the bug.
 *
 * This is a callback for the subscribe someone else picker.
 *
 * @method _subscribeSomeoneElse
 * @param person {Object} Representation of a person returned by the API.
 */
BugSubscribersLoader.prototype._subscribeSomeoneElse = function(person) {
    var subscriber = person.getAttrs();
    this.subscribers_list.addSubscriber(subscriber, 'Discussion');
    this.subscribers_list.indicateSubscriberActivity(subscriber);

    var loader = this;

    function on_success() {
        loader.subscribers_list.stopSubscriberActivity(subscriber, true);
        loader._addUnsubscribeLinkIfTeamMember(subscriber);
    }
    function on_failure() {
        loader.subscribers_list.stopSubscriberActivity(
            subscriber, false, function() {
                loader.subscribers_list.removeSubscriber(subscriber);
            }
        );
    }
    var config = {
        on: { success: on_success,
              failure: on_failure },
        parameters: { person: subscriber.self_link } };
    this.lp_client.named_post(this.bug.self_link, 'subscribe', config);
};

/**
 * Add unsubscribe link for a team if the currently logged in user
 * is member of the team.
 *
 * @method _addUnsubscribeLinkIfTeamMember
 * @param team {Object} A person object as returned via API.
 */
BugSubscribersLoader.prototype
._addUnsubscribeLinkIfTeamMember = function(team) {
    var loader = this;
    function on_success(members) {
        var team_member = false;
        var i;
        for (i=0; i<members.entries.length; i++) {
            if (members.entries[i].get('member_link') ===
                Y.lp.client.get_absolute_uri(LP.links.me)) {
                team_member = true;
                break;
            }
        }
        if (team_member === true) {
            // Add unsubscribe action for the team member.
            loader.subscribers_list.addUnsubscribeAction(
                team, loader._getUnsubscribeCallback());
        }
    }

    if (Y.Lang.isString(LP.links.me) && team.is_team) {
        var config = {
            on: { success: on_success }
        };

        var members_link = team.members_details_collection_link;
        this.lp_client.get(members_link, config);
    }
};


/**
 * Manages entire subscribers' list for a single bug.
 *
 * If the passed in container_box is not present, or if there are multiple
 * nodes matching it, it throws an exception.
 *
 * @class SubscribersList
 * @param config {Object} Configuration object containing at least
 *   container_box value with the container div CSS selector
 *   where to add the subscribers list.
 */
function SubscribersList(config) {
    var container_nodes = Y.all(config.container_box);
    if (container_nodes.size() === 0) {
        Y.error('Container node must be specified in config.container_box.');
    } else if (container_nodes.size() > 1) {
        Y.error("Multiple container nodes for selector '" +
                config.container_box + "' present in the page. " +
                "You need to be more explicit.");
    } else {
        this.container_node = container_nodes.item(0);
    }
}
namespace.SubscribersList = SubscribersList;

/**
 * Reset the subscribers list:
 *  - If no sections with subscribers are left, it adds an indication
 *    of no subscribers.
 *  - If there are subscribers left, it ensures there is no indication
 *    of no subscribers.
 *
 * @method resetNoSubscribers
 * @param force_hide {Boolean} Whether to force hiding of the "no subscribers"
 *     indication.
 */
SubscribersList.prototype.resetNoSubscribers = function(force_hide) {
    var has_sections = (
        this.container_node.one('.' + CSS_CLASSES.section) !== null);
    var no_subs;
    if (has_sections || force_hide === true) {
        // Make sure the indicator for no subscribers is not there.
        no_subs = this.container_node.one('.' + CSS_CLASSES.no_subscribers);
        if (no_subs !== null) {
            no_subs.remove();
        }
    } else {
        no_subs = Y.Node.create('<div />')
            .addClass(CSS_CLASSES.no_subscribers)
            .set('text', 'No other subscribers.');
        this.container_node.appendChild(no_subs);
    }
};

/**
 * Returns or creates a node for progress indication for the subscribers list.
 *
 * If node is not present, it is created and added to the beginning of
 * subscribers list container node.
 *
 * @method _ensureActivityNode
 * @return {Y.Node} A node with the spinner img node and a span text node.
 */
SubscribersList.prototype._ensureActivityNode = function() {
    var activity_node = this.container_node.one('.' + CSS_CLASSES.activity);
    if (activity_node === null) {
        activity_node = Y.Node.create('<div />')
            .addClass(CSS_CLASSES.activity);
        progress_icon = Y.Node.create('<img />')
            .set('src', '/@@/spinner');
        activity_node.appendChild(progress_icon);
        activity_node.appendChild(
            Y.Node.create('<span />')
                .addClass(CSS_CLASSES.activity_text));
        this.container_node.prepend(activity_node);
    }
    return activity_node;
};

/**
 * Sets icon in the activity node to either 'error' or 'spinner' icon.
 *
 * @method _setActivityErrorIcon
 * @param node {Y.Node} An activity node as returned by _ensureActivityNode().
 * @param error {Boolean} Whether to show an error icon.
 *     Otherwise shows a spinner image.
 */
SubscribersList.prototype._setActivityErrorIcon = function(node, error) {
    var progress_icon = node.one('img');
    if (error === true) {
        progress_icon.set('src', '/@@/error');
    } else {
        progress_icon.set('src', '/@@/spinner');
    }
};

/**
 * Sets the activity text inside the activity node.
 *
 * @method _setActivityText
 * @param node {Y.Node} An activity node as returned by _ensureActivityNode().
 * @param text {String} Description of the activity currently in progress.
 */
SubscribersList.prototype._setActivityText = function(node, text) {
    var text_node = node.one('.' + CSS_CLASSES.activity_text);
    text_node.set('text', ' ' + text);
};

/**
 * Indicate some activity for the subscribers list with a progress spinner
 * and optionally some text.
 *
 * @method startActivity
 * @param text {String} Description of the action to indicate progress of.
 */
SubscribersList.prototype.startActivity = function(text) {
    // We don't ever want "No subscribers" to be shown when loading is in
    // progress.
    this.resetNoSubscribers(true);

    var activity_node = this._ensureActivityNode();
    // Ensure the icon is back to the spinner.
    this._setActivityErrorIcon(activity_node, false);
    this._setActivityText(activity_node, text);
};

/**
 * Stop any activity indication for the subscribers list and optionally
 * display an error message.
 *
 * @method stopActivity
 * @param error_text {String} Error message to display.  If not a string,
 *     it is considered that the operation was successful and no error
 *     indication is added to the subscribers list.
 */
SubscribersList.prototype.stopActivity = function(error_text) {
    var activity_node = this.container_node.one('.' + CSS_CLASSES.activity);
    if (Y.Lang.isString(error_text)) {
        // There is an error message, keep the node visible with
        // the error message in.
        activity_node = this._ensureActivityNode(true);
        this._setActivityErrorIcon(activity_node, true);
        this._setActivityText(activity_node, error_text);
        this.resetNoSubscribers(true);
    } else {
        // No errors, remove the activity node if present.
        if (activity_node !== null) {
            activity_node.remove();
        }
        // Restore "No subscribers" indication if needed.
        this.resetNoSubscribers();
    }
};

/**
 * Get a CSS class to use for the section of the subscribers' list
 * with subscriptions with the level `level`.
 *
 * @method _getSectionCSSClass
 * @param level {String} Level of the subscription.
 *     See `subscriber_levels` for a list of acceptable values.
 * @return {String} CSS class to use for the section for the `level`.
 */
SubscribersList.prototype._getSectionCSSClass = function(level) {
    return CSS_CLASSES.section + '-' + level.toLowerCase();
};

/**
 * Return the section node for a subscription level.
 *
 * @method _getSection
 * @param level {String} Level of the subscription.
 * @return {Object} Node containing the section or null.
 */
SubscribersList.prototype._getSection = function(level) {
    return this.container_node.one('.' + this._getSectionCSSClass(level));
};

/**
 * Create a subscribers section node depending on their level.
 *
 * @method _createSectionNode
 * @param level {String} Level of the subscription.
 *     See `subscriber_levels` for a list of acceptable values.
 * @return {Object} Node containing the entire section.
 */
SubscribersList.prototype._createSectionNode = function(level) {
    // Container node for the entire section.
    var node = Y.Node.create('<div />')
        .addClass(CSS_CLASSES.section)
        .addClass(this._getSectionCSSClass(level));
    // Header.
    node.appendChild(
        Y.Node.create('<h3 />')
            .set('text', subscriber_levels[level]));
    // Node listing the actual subscribers.
    node.appendChild(
        Y.Node.create('<div />')
            .addClass(CSS_CLASSES.list));
    return node;
};


/**
 * Inserts the section node in the appropriate place in the subscribers list.
 * Uses `subscriber_level_order` to figure out what position should a section
 * with subscribers on `level` hold.
 *
 * @method _insertSectionNode
 * @param level {String} Level of the subscription.
 * @param section_node {Object} Node to insert (containing
 *   the entire section).
 */
SubscribersList.prototype._insertSectionNode = function(level, section_node) {
    var index, existing_level;
    var existing_level_node = null;
    for (index=0; index < subscriber_level_order.length; index++) {
        existing_level = subscriber_level_order[index];
        if (existing_level === level) {
            // Insert either at the beginning of the list,
            // or after the last section which comes before this one.
            if (existing_level_node === null) {
                this.container_node.prepend(section_node);
            } else {
                existing_level_node.insert(section_node, 'after');
            }
            break;
        } else {
            var existing_node = this._getSection(existing_level);
            if (existing_node !== null) {
                existing_level_node = existing_node;
            }
        }
    }
};


/**
 * Create a subscribers section depending on their level and
 * add it to the other subscribers list.
 * If section is already there, returns the existing node for it.
 *
 * @method _getOrCreateSection
 * @param level {String} Level of the subscription.
 *     See `subscriber_levels` for a list of acceptable values.
 * @return {Object} Node containing the entire section.
 */
SubscribersList.prototype._getOrCreateSection = function(level) {
    var section_node = this._getSection(level);
    if (section_node === null) {
        section_node = this._createSectionNode(level);
        this._insertSectionNode(level, section_node);
    }
    // Remove the indication of no subscribers if it's present.
    this.resetNoSubscribers();
    return section_node;
};

/**
 * Return whether subscribers section has any subscribers or not.
 *
 * @method _sectionHasSubscribers
 * @param node {Y.Node} Node containing the subscribers section.
 * @return {Boolean} True if there are still subscribers in the section.
 */
SubscribersList.prototype._sectionNodeHasSubscribers = function(node) {
    var list = node.one('.' + CSS_CLASSES.list);
    if (list !== null) {
        var has_any = (list.one('.' + CSS_CLASSES.subscriber) !== null);
        return has_any;
    } else {
        Y.error(
            'No div.subscribers-list found inside the passed `node`.');
    }
};

/**
 * Removes a subscribers section node if there are no remaining subscribers.
 * Silently passes if nothing to remove.
 *
 * @method _removeSectionNodeIfEmpty
 * @param node {Object} Section node containing all the subscribers.
 */
SubscribersList.prototype._removeSectionNodeIfEmpty = function(node) {
    if (node !== null && !node.hasClass(CSS_CLASSES.section)) {
        Y.error('Node is not a section node.');
    }
    if (node !== null && !this._sectionNodeHasSubscribers(node)) {
        node.remove();
        // Add the indication of no subscribers if this was the last section.
        this.resetNoSubscribers();
    }
};

/**
 * Get a string value usable as the ID for the node based on
 * the subscriber name.
 */
SubscribersList.prototype._getNodeIdForSubscriberName = function(name) {
    return CSS_CLASSES.subscriber + '-' + Y.lp.names.launchpad_to_css(name);
};

/**
 * Validate and sanitize a subscriber object.
 * It must have at least a `name` attribute.
 * If `display_name` is not set, the value from `name` is used instead.
 *
 * @method _validateSubscriber
 * @param subscriber {Object} Object containing `name`, `display_name`,
 *    `web_link` and `is_team` indicator for the subscriber.
 *    If `display_name` is undefined, sets it to the same value as `name`.
 *    If `web_link` is not set, sets it to "/~name".
 * @return {Object} Modified `subscriber` object.
 */
SubscribersList.prototype._validateSubscriber = function(subscriber) {
    if (!Y.Lang.isString(subscriber.name)) {
        Y.error('No `name` passed in `subscriber`.');
    }
    if (!Y.Lang.isString(subscriber.display_name)) {
        // Default to `name` for display_name.
        subscriber.display_name = subscriber.name;
    }
    if (!Y.Lang.isString(subscriber.web_link)) {
        // Default to `/~name` for web_link.
        subscriber.web_link = '/~' + subscriber.name;
    }
    return subscriber;
};

/**
 * Creates and returns a node for the `subscriber`.
 *
 * It makes a link using subscriber.display_name as the link text,
 * and linking to /~`subscriber.name`.
 * Everything is wrapped in a div.subscriber node.
 *
 * @method _createSubscriberNode
 * @param subscriber {Object} Object containing `name`, `display_name`
 *    `web_link` and `is_team` attributes.
 * @return {Object} Node containing a subscriber link.
 */
SubscribersList.prototype._createSubscriberNode = function(subscriber) {
    var subscriber_node = Y.Node.create('<div />')
        .addClass(CSS_CLASSES.subscriber);

    var subscriber_link = Y.Node.create('<a />');
    subscriber_link.set('href', subscriber.web_link);

    var subscriber_text = Y.Node.create('<span />')
        .addClass('sprite')
        .set('text', subscriber.display_name);
    if (subscriber.is_team === true) {
        subscriber_text.addClass('team');
    } else {
        subscriber_text.addClass('person');
    }
    subscriber_link.appendChild(subscriber_text);

    subscriber_node.appendChild(subscriber_link);
    return subscriber_node;
};

/**
 * Add or change a subscriber in the subscribers list.
 *
 * If subscriber is already in the list and in a different subscription
 * level section, it is moved to the appropriate section indicated by
 * `level` parameter.  If subscriber is already in the list and subscribed
 * at the same level, nothing happens.
 *
 * @method addSubscriber
 * @param subscriber {Object} Object containing `name`, `display_name`
 *    `web_link` and `is_team` attributes describing the subscriber.
 * @param level {String} Level of the subscription.
 * @param config {Object} Object containing potential 'unsubscribe' callback
 *     in the `unsubscribe_callback` attribute.
 */
SubscribersList.prototype.addSubscriber = function(subscriber, level,
                                                   config) {
    checkSubscriptionLevel(level);
    subscriber = this._validateSubscriber(subscriber);

    var section_node = this._getOrCreateSection(level);
    var list_node = section_node.one('.' + CSS_CLASSES.list);

    var subscriber_id = this._getNodeIdForSubscriberName(subscriber.name);
    var subscriber_node = this.container_node.one('#' + subscriber_id);

    if (subscriber_node === null) {
        subscriber_node = this._createSubscriberNode(subscriber);
        subscriber_node.set('id', subscriber_id);
        // Insert the subscriber at the start of the list.
        list_node.prepend(subscriber_node);
        // Add the unsubscribe action if needed.
        if (Y.Lang.isValue(config) &&
            Y.Lang.isFunction(config.unsubscribe_callback)) {
            this.addUnsubscribeAction(
                subscriber, config.unsubscribe_callback);
        }
    } else {
        // Move the subscriber node from the existing section to the new one.
        var existing_section = subscriber_node.ancestor(
            '.' + CSS_CLASSES.section);
        if (existing_section === null) {
            Y.error("Matching subscriber node doesn't seem to be in any " +
                    "subscribers list sections.");
        }
        if (existing_section !== section_node) {
            // We do not destroy the node so we can insert it into
            // the appropriate position.
            subscriber_node.remove();
            this._removeSectionNodeIfEmpty(existing_section);
            // Insert the subscriber at the start of the list.
            list_node.prepend(subscriber_node);
        }
        // else:
        //   Subscriber is already there in the same section. A no-op.
    }

    return subscriber_node;
};

/**
 * Get a subscriber node for the passed in subscriber.
 *
 * If subscriber is not in the list already, it fails with an exception.
 *
 * @method _getSubscriberNode
 * @param subscriber {Object} Object containing at least `name`
 *     for the subscriber.
 */
SubscribersList.prototype._getSubscriberNode = function(subscriber) {
    subscriber = this._validateSubscriber(subscriber);

    var subscriber_id = this._getNodeIdForSubscriberName(subscriber.name);
    var subscriber_node = this.container_node.one('#' + subscriber_id);

    if (subscriber_node === null) {
        Y.error('Subscriber is not present in the subscribers list. ' +
                'Please call addSubscriber(subscriber) first.');
    }
    return subscriber_node;
};

/**
 * Create a subscriber actions node to hold actions like unsubscribe.
 * If the node already exists, returns it instead.
 *
 * @method _getOrCreateActionsNode
 * @param subscriber_node {Object} Node for a particular subscriber.
 * @return {Object} A node suitable for putting subscriber actions in.
 */
SubscribersList.prototype._getOrCreateActionsNode = function(subscriber_node)
{
    var actions_node = subscriber_node.one('.' + CSS_CLASSES.actions);
    if (actions_node === null) {
        // Create a node to hold all the actions.
        actions_node = Y.Node.create('<span />')
            .addClass(CSS_CLASSES.actions)
            .setStyle('float', 'right');
        subscriber_node.appendChild(actions_node);
    }
    return actions_node;
};

/**
 * Adds an unsubscribe action for the subscriber.
 *
 * It creates a separate actions node which will hold any actions
 * (including unsubscribe one), and creates a "remove" link with the
 * on.click action set to call `callback` function with subscriber
 * passed in as the parameter.
 *
 * If `subscriber` does not have at least the `name` attribute,
 * an exception is thrown.
 * If `callback` is not a function, it throws an exception.
 *
 * @method addUnsubscribeAction
 * @param subscriber {Object} Object containing `name`, `display_name`
 *    `web_link` and `is_team` attributes describing the subscriber.
 * @param callback {Function} Function to call on clicking the unsubscribe
 *     button.  It will be passed `this` (a SubscribersList) as the first,
 *     and `subscriber` as the second parameter.
 */
SubscribersList.prototype.addUnsubscribeAction = function(subscriber,
                                                          callback) {
    subscriber = this._validateSubscriber(subscriber);
    if (!Y.Lang.isFunction(callback)) {
        Y.error('Passed in callback for unsubscribe action ' +
                'is not a function.');
    }
    var subscriber_node = this._getSubscriberNode(subscriber);
    var actions_node = this._getOrCreateActionsNode(subscriber_node);
    var unsubscribe_node = actions_node.one('.' + CSS_CLASSES.unsubscribe);
    if (unsubscribe_node === null) {
        unsubscribe_node = Y.Node.create('<a />')
            .addClass(CSS_CLASSES.unsubscribe)
            .set('href', '+subscribe')
            .set('title', 'Unsubscribe ' + subscriber.display_name);
        unsubscribe_node.appendChild(
            Y.Node.create('<img />')
                .set('src', '/@@/remove')
                .set('alt', 'Remove'));
        var subscriber_list = this;
        unsubscribe_node.on('click', function(e) {
            e.halt();
            callback(subscriber_list, subscriber);
        });
        actions_node.appendChild(unsubscribe_node);
    }
};

/**
 * Remove a subscriber node for the `subscriber`.
 *
 * If subscriber is not in the list already, it fails with an exception.
 *
 * @method removeSubscriber
 * @param subscriber {Object} Object containing at least `name`
 *     for the subscriber.
 */
SubscribersList.prototype.removeSubscriber = function(subscriber) {
    subscriber = this._validateSubscriber(subscriber);
    var subscriber_node = this._getSubscriberNode(subscriber);
    var existing_section = subscriber_node.ancestor(
        '.' + CSS_CLASSES.section);
    subscriber_node.remove(true);
    if (existing_section === null) {
        Y.error("Matching subscriber node doesn't seem to be in any " +
                "subscribers list sections.");
    }
    this._removeSectionNodeIfEmpty(existing_section);
};

/**
 * Indicates some activity for a subscriber in the subscribers list.
 * Uses a regular Launchpad progress spinner UI.
 *
 * If subscriber is not in the list already, it fails with an exception.
 * If there are any actions available for the subscriber (such as unsubscribe
 * action), they are hidden.
 *
 * @method indicateSubscriberActivity
 * @param subscriber {Object} Object containing at least `name`
 *     for the subscriber.
 */
SubscribersList.prototype.indicateSubscriberActivity = function(subscriber) {
    var subscriber_node = this._getSubscriberNode(subscriber);
    var progress_node = subscriber_node.one(
        '.' + CSS_CLASSES.subscriber_activity);

    // No-op if there is already indication of progress,
    // and creates a new node with the spinner if there isn't.
    if (progress_node === null) {
        var actions_node = subscriber_node.one('.' + CSS_CLASSES.actions);
        if (actions_node !== null) {
            actions_node.setStyle('display', 'none');
        }
        var progress_icon = Y.Node.create('<img />')
            .set('src', '/@@/spinner');

        progress_node = Y.Node.create('<span />')
            .addClass(CSS_CLASSES.subscriber_activity)
            .setStyle('float', 'right');
        progress_node.appendChild(progress_icon);
        subscriber_node.appendChild(progress_node);
    }
};

/**
 * Stop any indication of activity for a subscriber in the subscribers list.
 *
 * If the spinner is present, it removes it.  If `success` parameter is
 * passed in, it determines if success or failure animation will be shown
 * as well.
 *
 * If subscriber is not in the list already, it fails with an exception.
 * If there are any actions available for the subscriber (such as unsubscribe
 * action), they are re-displayed if hidden.
 *
 * @method stopSubscriberActivity
 * @param subscriber {Object} Object containing at least `name`
 *     for the subscriber.
 * @param success {Boolean} Whether to indicate success (`success` == true,
 *     flash green) or failure (false, red).  Otherwise, perform no
 *     animation.
 * @param callback {Function} Function to call if and when success/failure
 *     animation completes.
 */
SubscribersList.prototype.stopSubscriberActivity = function(subscriber,
                                                            success,
                                                            callback) {
    var subscriber_node = this._getSubscriberNode(subscriber);
    var progress_node = subscriber_node.one(
        '.' + CSS_CLASSES.subscriber_activity);
    if (progress_node !== null) {
        // Remove and destroy the node if present.
        progress_node.remove(true);
    }
    // If actions node is present and hidden, show it.
    var actions_node = subscriber_node.one('.' + CSS_CLASSES.actions);
    if (actions_node !== null) {
        actions_node.setStyle('display', 'inline');
    }

    if (success === true || success === false) {
        var anim;
        if (success === true) {
            anim = Y.lazr.anim.green_flash({ node: subscriber_node });
        } else {
            anim = Y.lazr.anim.red_flash({ node: subscriber_node });
        }
        anim.on('end', callback);
        anim.run();
    }
};


}, "0.1", {"requires": ["node", "lazr.anim", "lp.app.picker", "lp.client",
                        "lp.names"]});
