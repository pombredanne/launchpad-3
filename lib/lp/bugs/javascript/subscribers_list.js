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
    no_subscribers: 'no-subscribers-indicator'
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
 * Removes a subscribers section for the appropriate level.
 * Silently passes if nothing to remove.
 *
 * @method removeSectionIfEmpty
 * @param level {String} Level of the subscription.
 */
SubscribersList.prototype.removeSectionIfEmpty = function(level) {
    var node = this._getSection(level);
    if (node !== null && !this._sectionNodeHasSubscribers(node)) {
        node.remove();
        // Add the indication of no subscribers if this was the last section.
        this.resetNoSubscribers();
    }
};

}, "0.1", {"requires": ["node", "lazr.anim", "lp.client"]});
