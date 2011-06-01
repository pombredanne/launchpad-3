/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Functions for managing the subscribers list.
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
    activity: 'activity-indicator'
};

/**
 * Possible subscriber levels with descriptive headers for
 * sections that will hold them.
 */
var subscriber_levels = {
    'Details': 'Notified of all changes',
    'Discussion': 'Notified of all changes except comments',
    'Lifecycle': 'Notified when the bug is closed or reopened',
    'Maybe': 'Maybe notified'
};

/**
 * Order of subscribers sections.
 */
var subscriber_level_order = ['Details', 'Discussion', 'Lifecycle', 'Maybe'];


/**
 * Checks if the subscription level is one of the acceptable ones.
 * Throws an error if not, otherwise returns true.
 */
function checkSubscriptionLevel(level) {
    if (!subscriber_levels.hasOwnProperty(level)) {
        Y.error(
            'Level "' + level + '" is not an acceptable subscription level.');
    }
    return true;
}



/**
 * Manages entire subscribers' list for a single bug.
 *
 * @class SubscribersList
 * @param config {Object} Configuration object containing at least
 *   container_box value with the container div ID where to add the
 *   subscribers list, and bug referencing the bug we need to
 *   list subscribers for.
 */
function SubscribersList(config) {
    this.container_node = Y.one(config.container_box);
    if (!Y.Lang.isValue(this.container_node)) {
        Y.error('Container div must be specified in config.container_box.');
    }
    if (!Y.Lang.isValue(config.bug)) {
        Y.error('No bug object provided.');
    }
    this.bug = config.bug;

    if (!Y.Lang.isValue(config.lp_client)) {
        this.lp_client = config.lp_client;
    } else {
        this.lp_client = new Y.lp.client.Launchpad();
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
 */
SubscribersList.prototype.resetNoSubscribers = function() {
    var has_sections = (
        this.container_node.one('.' + CSS_CLASSES.section) !== null);
    var no_subs;
    if (has_sections) {
        // Make sure the indicator for no subscribers is not there.
        no_subs = this.container_node.one('.' + CSS_CLASSES.no_subscribers);
        if (no_subs !== null) {
            no_subs.remove();
        }
    } else {
        no_subs = Y.Node.create('<div></div>')
            .addClass(CSS_CLASSES.no_subscribers)
            .set('text', 'No other subscribers.');
        this.container_node.appendChild(no_subs);
    }
};

/**
 * Get a CSS class to use for the section of the subscribers' list
 * with subscriptions with the level `level`.
 *
 * @method _getSectionCSSClass
 * @param level {String} Level of the subscription.
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
 * @return {Object} Node containing the entire section.
 */
SubscribersList.prototype._createSectionNode = function(level) {
    // Container node for the entire section.
    var node = Y.Node.create('<div></div>')
        .addClass(CSS_CLASSES.section)
        .addClass(this._getSectionCSSClass(level));
    // Header.
    node.appendChild(
        Y.Node.create('<h3></h3>')
            .set('text', subscriber_levels[level]));
    // Node listing the actual subscribers.
    node.appendChild(
        Y.Node.create('<div></div>')
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
        } else {
            existing_level_node = this._getSection(existing_level);
        }
    }
};


/**
 * Create a subscribers section depending on their level and
 * add it to the other subscribers list.
 * If section is already there, returns the existing node for it.
 *
 * @method getOrCreateSection
 * @param level {String} Level of the subscription.
 * @return {Object} Node containing the entire section.
 */
SubscribersList.prototype.getOrCreateSection = function(level) {
    var section_node = this._getSection(level);
    if (section_node === null) {
        section_node = this._createSectionNode(level);
        this.container_node.appendChild(section_node);
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
 * @method removeSectionIfEmpty
 * @param node {Object} Section node containing all the subscribers.
 */
SubscribersList.prototype._removeSectionNodeIfEmpty = function(node) {
    if (node !== null && !this._sectionNodeHasSubscribers(node)) {
        node.remove();
        // Add the indication of no subscribers if this was the last section.
        this.resetNoSubscribers();
    }
};

/**
 * Removes a subscribers section for the appropriate level.
 * Silently passes if nothing to remove.
 *
 * @method removeSectionIfEmpty
 * @param level {String} Level of the subscription.
 */
SubscribersList.prototype.removeSectionIfEmpty = function(level) {
    var node = this._getSection(level);
    this._removeSectionNodeIfEmpty(node);
};

/**
 * Get a string value usable as the ID for the node based on
 * the subscriber name.
 */
SubscribersList.prototype._getNodeIdForSubscriberName = function(name) {
    return CSS_CLASSES.subscriber + '-' + Y.lp.names.launchpad_to_css(name);
};

/**
 * Get a subscriber name by parsing the subscriber node ID.
 */
SubscribersList.prototype._getNameFromSubscriberNodeId = function(node) {
    var id = node.get('id');
    return id.substr(CSS_CLASSES.subscriber.length + 1);
};

/**
 * Validate and sanitize a subscriber object.
 * It must have at least a `name` attribute.
 * If `display_name` is not set, the value from `name` is used instead.
 *
 * @method _validateSubscriber
 * @param subscriber {Object} Object containing `name` and `display_name`
 *    for the subscriber.  If `display_name` is undefined, sets it to the
 *    same value as `name`.
 */
SubscribersList.prototype._validateSubscriber = function(subscriber) {
    if (!Y.Lang.isString(subscriber.name)) {
        Y.error('No `name` passed in `subscriber`.');
    }
    if (!Y.Lang.isString(subscriber.display_name)) {
        // Default to `name` for display_name.
        subscriber.display_name = subscriber.name;
    }
    return subscriber;
}

/**
 * Creates and returns a node for the `subscriber`.
 *
 * It makes a link using subscriber.display_name as the link text,
 * and linking to /~`subscriber.name`.
 * Everything is wrapped in a div.subscriber node.
 *
 * @method _createSubscriberNode
 * @param subscriber {Object} Object containing `name` and `display_name`
 *    attributes.
 * @return {Object} Node containing a subscriber link.
 */
SubscribersList.prototype._createSubscriberNode = function(subscriber) {
    var subscriber_node = Y.Node.create('<div></div>')
        .addClass(CSS_CLASSES.subscriber);

    var subscriber_link = Y.Node.create('<a></a>');
    subscriber_link.set('href', '/~' + subscriber.name);

    var subscriber_text = Y.Node.create('<span></span>')
        .addClass('sprite').addClass('person')
        .set('text', subscriber.display_name);
    subscriber_link.appendChild(subscriber_text);

    subscriber_node.appendChild(subscriber_link);
    return subscriber_node;
};

/**
 * Adds a subscriber to the subscribers list.
 *
 * If subscriber is already in the list and in a different subscription
 * level section, it is moved to the appropriate section indicated by
 * `level` parameter.  If subscriber is already in the list and subscribed
 * at the same level, nothing happens.
 *
 * @method addSubscriber
 * @param subscriber {Object} Object containing `name` and `display_name`
 *     for the subscriber.
 * @param level {String} Level of the subscription.
 * @param config {Object} Object containing potential 'unsubscribe' callback
 *     in the `unsubscribe_callback` property.
 */
SubscribersList.prototype.addSubscriber = function(subscriber, level,
                                                   config) {
    subscriber = this._validateSubscriber(subscriber);
    checkSubscriptionLevel(level);

    var section_node = this.getOrCreateSection(level);
    var list_node = section_node.one('.' + CSS_CLASSES.list);

    var subscriber_id = this._getNodeIdForSubscriberName(subscriber.name);
    var subscriber_node = this.container_node.one('#' + subscriber_id);

    if (subscriber_node === null) {
        var subscriber_node = this._createSubscriberNode(subscriber);
        subscriber_node.set('id', subscriber_id);
        // Insert the subscriber at the start of the list.
        list_node.prepend(subscriber_node);
    } else {
        // Remove the subscriber node from the existing section.
        var existing_section = subscriber_node.ancestor(
            '.' + CSS_CLASSES.section);
        if (existing_section === null) {
            Y.error("Matching subscriber node doesn't seem to be in any " +
                    "subscribers list sections.");
        }
        if (existing_section !== section_node) {
            subscriber_node.remove();
            this._removeSectionNodeIfEmpty(existing_section);
            // Insert the subscriber at the start of the list.
            list_node.prepend(subscriber_node);
        } else {
            // Subscriber is already there in the same section.
            // A no-op.
        }
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
 * Remove a subscriber node for the `subscriber`.
 *
 * If subscriber is not in the list already, it fails with an exception.
 *
 * @method removeSubscriber
 * @param subscriber {Object} Object containing at least `name`
 *     for the subscriber.
 */
SubscribersList.prototype.removeSubscriber = function(subscriber) {
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
 *
 * @method indicateSubscriberActivity
 * @param subscriber {Object} Object containing at least `name`
 *     for the subscriber.
 */
SubscribersList.prototype.indicateSubscriberActivity = function(subscriber) {
    var subscriber_node = this._getSubscriberNode(subscriber);
    var progress_node = subscriber_node.one('.' + CSS_CLASSES.activity);

    // No-op if there is already indication of progress,
    // and creates a new node with the spinner if there isn't.
    if (progress_node === null) {
        var progress_icon = Y.Node.create('<img></img>')
            .set('src', '/@@/spinner');

        progress_node = Y.Node.create('<span></span>')
            .addClass(CSS_CLASSES.activity);
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
    var progress_node = subscriber_node.one('.' + CSS_CLASSES.activity);
    if (progress_node !== null) {
        // Remove and destroy the node if present.
        progress_node.remove(true);
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


}, "0.1", {"requires": ["node", "lazr.anim", "lp.client", "lp.names"]});
