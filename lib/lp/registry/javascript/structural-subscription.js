/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Form overlay widgets and subscriber handling for structural subscriptions.
 *
 * @module registry
 * @submodule structural_subscription
 */

YUI.add('lp.registry.structural_subscription', function(Y) {

var namespace = Y.namespace('lp.registry.structural_subscription');

var EXPANDER_COLLAPSED = '/@@/treeCollapsed',
    EXPANDER_EXPANDED = '/@@/treeExpanded',
    INNER_HTML = 'innerHTML',
    VALUE = 'value',
    SRC = 'src';

var FILTER_COMMENTS = 'filter-comments',
    FILTER_WRAPPER = 'filter-wrapper',
    ACCORDION_WRAPPER = 'accordion-wrapper',
    ADDED_OR_CLOSED = 'added-or-closed',
    ADDED_OR_CHANGED = 'added-or-changed',
    ADVANCED_FILTER = 'advanced-filter',
    MATCH_ALL = 'match-all',
    MATCH_ANY = 'match-any',
    SS_COLLAPSIBLE = 'ss-collapsible'
    ;

namespace.is_ready = false;

var add_subscription_overlay;
namespace.lp_client = undefined;

/*
 * An object representing the global actions portlet.
 *
 */
var PortletTarget = function() {};
Y.augment(PortletTarget, Y.Event.Target);
namespace.portlet = new PortletTarget();

function subscription_success() {
    // TODO Should there be some success notification?
    add_subscription_overlay.hide();
}

function failure_handler(something, xhr) {
    // TODO Do something nicer.
    alert("it didn't work: " + xhr.responseText);
}

/**
 * Does the list contain the target?
 * information from the user request.
 *
 * @private
 * @method list_contains
 * @param {List} list The list to search.
 * @param {String} target The target of interest.
 */
function list_contains(list, target)
{
    return list.indexOf(target) != -1;
}
namespace.list_contains = list_contains;

/**
 * Given a minimally populated bug filter, patch it to add additional
 * information from the user request.
 *
 * @private
 * @method patch_bug_filter
 * @param {Object} bug_filter The incomplete bug filter.
 * @param {Object} form_data The data returned from the form submission.
 */

/**

{
x "recipient":["user"],
x "team":["https://launchpad.dev/api/devel/~guadamen"],
x "name":[""],
x "events":["added-or-changed"],
x "filters":["filter-out-comments","advanced-filter"],
x "tag_match":["match_all"],
x "tags":["ui"],
 "importances":["999","50","40","30","20","10","5"],
 "statuses":["10","15","16","17","18","19","20","21","22","25","30","999"]
 }

 */
function patch_bug_filter(bug_filter, form_data) {
    var config = {
        on: {
            success: subscription_success,
            failure: failure_handler
            }
        };

    var patch_data = {
        'description': form_data.name[0]
    };

    // Set the notification level.
    var added_or_closed = list_contains(form_data.events, ADDED_OR_CLOSED);
    var filter_comments = list_contains(form_data.filters, FILTER_COMMENTS);

    // Chattiness: Lifecycle < Details < Discussion.
    if (added_or_closed) {
        patch_data.bug_notification_level = 'Lifecycle';
    } else if (!filter_comments) {
        patch_data.bug_notification_level = 'Discussion';
    } else {
        patch_data.bug_notification_level = 'Details';
    }

    // Set the tags.
    var advanced_filter = list_contains(form_data.filters, ADVANCED_FILTER);
    if (advanced_filter) {
        // Tags are a list with one element being a space-separated string.
        var tags = form_data.tags[0];
        if (Y.Lang.isValue(tags) && tags != '') {
            var match_all = list_contains(form_data.tag_match, MATCH_ALL);
            if (match_all) {
                patch_data.find_all_tags = true;
            }
            patch_data.tags = tags.toLowerCase().split(' ');
        }
        if (form_data.importances.length > 0) {
            patch_data.importances = form_data.importances;
        }
        if (form_data.statuses.length > 0) {
            patch_data.statuses = form_data.statuses;
        }
    }
    namespace.lp_client.patch(bug_filter.lp_original_uri, patch_data, config);
}
namespace.patch_bug_filter = patch_bug_filter;

/**
 * Given a structural subscription, create a corresponding bug filter.
 *
 * @method add_bug_filter
 * @param {Object} subscription The newly created structural subscription.
 * @param {Object} form_data The data returned from the form submission.
 */
function add_bug_filter(subscription, form_data) {
    var config = {
        on: {
            success: function (bug_filter) {
                    patch_bug_filter(bug_filter, form_data);
                },
            failure: failure_handler
            }
        };

    var subscription_uri = subscription.lp_original_uri;
    namespace.lp_client.named_post(subscription_uri, 'newBugFilter', config);
}

/**
 * Create a structural subscription.  If successful, create a bug
 * filter for the new subscription.
 *
 * @method create_structural_subscription
 * @param {Object} who Link to the user or team to be subscribed.
 * @param {Object} form_data The data returned from the form submission.
 */
function create_structural_subscription(who, form_data) {
    var config = {
        on: {
            success: function (subscription) {
                add_bug_filter(subscription, form_data);
            },
            failure: failure_handler
            },
        parameters: {
            subscriber: who
            }
        };

    namespace.lp_client.named_post(LP.cache.context.self_link,
        'addBugSubscription', config);
}

/**
 * Given the form data from a user, save the subscription.
 *
 * @private
 * @method save_subscription
 * @param {Object} form_data The data generated by the form submission.
 */

function save_subscription(form_data) {
    var who;
    if (form_data.recipient[0] == 'user') {
        who = LP.links.me;
    } else {
        // There can be only one.
        who = form_data.team[0];
    }
    //Y.log(Y.JSON.stringify(form_data));
    create_structural_subscription(who, form_data);
}
namespace.save_subscription = save_subscription;

/*
 * Modify the DOM to insert a link or two into the global actions portlet.
 * If structural subscriptions already exist then a 'modify' link is
 * added.  Otherwise, just the 'add' link is put into the portlet.
 *
 * @method setup_subscription_links
 * @param {String} overlay_id Id of the overlay element.
 * @param {String} content_box_id Id of the element on the page where
 *     the overlay is anchored.
 */
function setup_subscription_links(content_box_id, overlay_id) {
    // Create a new link in the global actions portlet.
    var link = Y.Node.create('<a href="#">Subscribe to bug mail</a>');
    // Add a class denoting them as js-action links with add sprite.
    link.addClass('sprite add js-action');
    var portlet = Y.one('#global-actions');
    portlet.appendChild(link);
    // Intercept clicks on the new link.
    link.on('click', function(e) {
        // Only proceed if the form content is already available.
        if (add_subscription_overlay) {
            e.preventDefault();
            // If the overlay had been opened and closed, the
            // individual elements display must match the state of the selectors.
            events_state_handler();
            add_subscription_overlay.show();
        }
    });
    var form_submit_button = Y.Node.create(
        '<input type="submit" name="field.actions.create" ' +
        'value="Create Subscription"/>');

    // Create the overlay.
    add_subscription_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Add a mail subscription for ' +
            LP.cache.context.title + ' bugs</h2>',
        form_content: Y.one(overlay_id),
        centered: true,
        visible: false,
        form_submit_button: form_submit_button,
        form_submit_callback: save_subscription
    });
    add_subscription_overlay.render(content_box_id);
    // Prevent cruft from hanging around upon closing.
    function clean_up(e) {
        var filter_wrapper = Y.one('#' + FILTER_WRAPPER);
        filter_wrapper.hide();
        collapse_node(filter_wrapper);
    }
    add_subscription_overlay.get('form_cancel_button').on(
        'click', clean_up);
    add_subscription_overlay.get('form_submit_button').on(
        'click', clean_up);
}                               // setup_subscription_links


/**
 * Make a table cell.
 *
 * @private
 * @method make_cell
 * @param {Object} item Item to be placed in the cell.
 * @param {String} name Name of the control.
 */
function make_cell(item, name) {
    return '<td  style="padding-left:3px"><label><input type="checkbox" ' +
        'name="' + name +'" ' +
        'value="' + item.title + '" checked="checked">' +
        item.title + '</label><td>';
}
/**
 * Make a table.
 *
 * @private
 * @method make_table
 * @param {Object} list List of items to be put in the table.
 * @param {String} name Name of the control.
 * @param {Int} num_cols The number of columns for the table to use.
 */
function make_table(list, name, num_cols) {
    var html = '<table>';
    for (i in list) {
        i = parseInt(i); // JavaScript, you so crazy!
        if (i % num_cols == 0) {
            if (i != 0) {
                html += '</tr>';
            }
            html += '<tr>';
        }
        html += make_cell(list[i], name);
    }
    html += '</tr></table>';
    return html;
}


/*
 * Create the accordion.
 *
 * @method create_accordion
 * @param {String} overlay_id Id of the overlay element.
 * @return {Object} accordion The accordion just created.
 */
function create_accordion(overlay_id) {
    var accordion = new Y.Accordion({
          useAnimation: true,
          collapseOthersOnExpand: true,
          visible: false
    });

    accordion.render(overlay_id);

    var statuses_ai,
        importances_ai,
        tags_ai;

    // Build tags pane.
    tags_ai = new Y.AccordionItem( {
        label: "Tags",
        expanded: false,
        alwaysVisible: false,
        id: "tags_ai",
        contentHeight: {method: "auto"}
    } );

    tags_ai.set("bodyContent",
        '<div>\n' +
        '<div>\n' +
        '    <input type="radio" name="tag_match" value="' + MATCH_ALL + '" checked> Match all tags\n' +
        '    <input type="radio" name="tag_match" value="' + MATCH_ANY + '"> Match any tags\n' +
        '</div>\n' +
        '<div style="padding-bottom:10px;">\n' +
        '    <input type="text" name="tags" size="60"/>\n' +
        '    <a target="help" href="/+help/structural-subscription-tags.html" ' +
        '        class="sprite maybe">&nbsp;<span class="invisible-link">Structural subscription tags help</span></a>\n ' +
        '</div>\n' +
        '</div>\n');

    accordion.addItem(tags_ai);

    // Build importances pane.
    importances_ai = new Y.AccordionItem( {
        label: "Importances (Any)",
        expanded: false,
        alwaysVisible: false,
        id: "importances_ai",
        contentHeight: {method: "auto"}
    } );
    var importances = LP.cache['importances'];
    var importances_html = make_table(importances, 'importances', 4);
    importances_ai.set("bodyContent", importances_html);
    accordion.addItem(importances_ai);

    // Build statuses pane.
    statuses_ai = new Y.AccordionItem( {
        label: "Statuses (Any)",
        expanded: false,
        alwaysVisible: false,
        id: "statuses_ai",
        contentHeight: {method: "auto"}
    } );
    var statuses = LP.cache['statuses'];
    var status_html = make_table(statuses, 'statuses', 3);
    statuses_ai.set("bodyContent", status_html);
    accordion.addItem(statuses_ai);

    return accordion;
}

/**
 * Collapse the node and set its arrow to 'collapsed'
 * @param node The node to collapse.
 */
function collapse_node(node) {
    var anim = Y.lazr.effects.slide_in(node);
    // XXX: BradCrittenden 2011-03-03 bug=728457 : This fix for
    // resizing needs to be incorporated into lazr.effects.  When that
    // is done it should be removed from here.
    anim.on("start", function() {
        node.setStyles({
            visibility: 'visible'
        });
    });
    anim.on("end", function() {
        node.setStyles({
            height: 0,
            visibility: 'hidden'
        });
        node.set(SRC, EXPANDER_COLLAPSED);
    });
    anim.run();
}

/**
 * Expand the node and set its arrow to 'collapsed'
 * @param node The node to collapse.
 */
function expand_node(node) {
    // Set the node to 'hidden' so that the proper size can be found.
    node.setStyles({
        visibility: 'hidden'
    });
    var anim = Y.lazr.effects.slide_out(node);
    // XXX: BradCrittenden 2011-03-03 bug=728457 : This fix for
    // resizing needs to be incorporated into lazr.effects.  When that
    // is done it should be removed from here.
    anim.on("start", function() {
        // Set the node to 'visible' for the beginning of the animation.
        node.setStyles({
            visibility: 'visible'
        });
    });
    anim.on("end", function() {
        // Change the height to auto when the animation completes.
        node.setStyles({
            height: 'auto'
        });
        node.set(SRC, EXPANDER_EXPANDED);
    });
    anim.run();
}

/**
 * Modify the DOM to insert a link or two into the global actions portlet.
 * If structural subscriptions already exist then a 'modify' link is
 * added.  Otherwise, just the 'add' link is put into the portlet.
 *
 * @method setup_overlay
 * @param {String} content_box_id Id of the element on the page where
 *     the overlay is anchored.
 * @return {String} overlay_id Id of the constructed overlay element.
 */
function setup_overlay(content_box_id) {
    var content_node = Y.one(content_box_id);
    var container = Y.Node.create('<div id="overlay-container"></div>');
    var accordion_overlay_id = 'accordion-overlay';
    var control_code =
        '<dl>\n' +
        '    <dt>Bug mail recipient</dt>\n' +
        '    <dd>\n' +
        '      <input type="radio" name="recipient" value="user"\n' +
        '      checked> Yourself<br>\n' +
        '      <input type="radio" name="recipient" value="team"> One of the\n' +
        '      teams you administer<br>\n' +
        '      <dl style="margin-left:25px;">\n' +
        '        <dt></dt>\n' +
        '        <dd>\n' +
        '          <select name="team" id="structural-subscription-teams">\n' +
        '          </select>\n' +
        '        </dd>\n' +
        '      </dl>\n' +
        '    </dd>\n' +
        '  <dt>Subscription name</dt>\n' +
        '  <dd>\n' +
        '    <input type="text" name="name">\n' +
        '    <a target="help" href="/+help/structural-subscription-name.html" ' +
        '        class="sprite maybe">&nbsp;\n' +
        '        <span class="invisible-link">Structural subscription description help</span></a>\n ' +
        '  </dd>\n' +
        '  <dt>Receive mail for bugs affecting ' + LP.cache.context.title + ' that</dt>\n' +
        '  <dd>\n' +
        '    <div id="events">\n' +
        '    <input type="radio" name="events"\n' +
        '        value="' + ADDED_OR_CLOSED + '" id="' + ADDED_OR_CLOSED + '"\n' +
        '        checked> are added or closed<br>\n' +
        '    <input type="radio" name="events" value="' + ADDED_OR_CHANGED + '"\n' +
        '        id="' + ADDED_OR_CHANGED + '"> are added or changed in any way\n' +
        '    </div>\n' +
        '    <div id="' + FILTER_WRAPPER + '" class="ss-collapsible">\n' +
        '    <dl style="margin-left:25px;">\n' +
        '      <dt></dt>\n' +
        '      <dd>\n' +
        '        <input type="checkbox" name="filters"\n' +
        '            value="' + FILTER_COMMENTS + '" checked>\n' +
        '        filter out comments<br>\n' +
        '        <input type="checkbox" name="filters"\n' +
        '            value="' + ADVANCED_FILTER + '"\n' +
        '            id="' + ADVANCED_FILTER + '">\n' +
        '        bugs must match this filter<br>\n' +
        '        <div id="' + ACCORDION_WRAPPER + '" \n' +
        '            class="' + SS_COLLAPSIBLE + '">\n' +
        '            <dl>\n' +
        '                <dt></dt>\n' +
        '                <dd style="margin-left:25px;">\n' +
        '                    <div id="' + accordion_overlay_id + '"\n' +
        '                        style="position:relative; overflow:hidden;"></div>\n' +
        '                </dd>\n' +
        '            </dl>\n' +
        '        </div> \n' +
        '      </dd>\n' +
        '    </dl>\n' +
        '    </div> \n' +
        '  </dd>\n' +
        '  <dt></dt>\n' +
        '</dl>';

    content_node.appendChild(container);
    container.appendChild(Y.Node.create(control_code));

    var accordion = create_accordion('#' + accordion_overlay_id);

    Y.each(Y.all('div.ss-collapsible'), function(div) {
        collapse_node(div);
    });

    // Set up click handlers for the events radio buttons.
    var radio_group = Y.all('#events input');
    radio_group.on('change', events_state_handler);

    // And a listener for advanced filter selection.
    var advanced_filter = Y.one('#' + ADVANCED_FILTER);
    advanced_filter.on('change', function(e) {
        var div = Y.one('#' + ACCORDION_WRAPPER);
        var fw_div = Y.one('#' + FILTER_WRAPPER);
        var checked = e.currentTarget.get('checked');
        if (checked) {
            expand_node(div);
        }
        else
            collapse_node(div);
    });

    // Set the project name.
    // Populate the team drop down from LP.cache data.
    var teams = LP.cache['administratedTeams'];
    var select = Y.one('#structural-subscription-teams');
    for (i in teams) {
        team = teams[i];
        var option = Y.Node.create('<option></option>');
        option.set(INNER_HTML, team.title);
        option.set(VALUE, team.link);
        select.appendChild(option);
    }
    return '#' + container._node.id;
}                               // setup_overlay


function events_state_handler() {
    var ctl = Y.one('#' + ADDED_OR_CHANGED);
    var div = Y.one('#' + FILTER_WRAPPER);
    var checked = ctl.get('checked');
    if (checked)
        expand_node(div);
    else
        collapse_node(div);
}

/*
 * Create the LP client.
 *
 * @method setup_client
 */
function setup_client() {
    namespace.lp_client = new Y.lp.client.Launchpad();
}                               // setup_client

/*
 * External entry point for configuring the structual subscription.
 * @method setup
 * @param {Object} config Object literal of config name/value pairs.
 *     config.content_box is the name of an element on the page where
 *         the overlay will be anchored.
 */
namespace.setup = function(config) {
    if (! Y.Lang.isValue(config)) {
        throw new Error(
            'Missing config for structural_subscription.');
    }
    if (!Y.Lang.isValue(config.content_box)) {
            throw new Error(
                'Structural_subscription configuration has ' +
                'undefined properties.');
    }

    if (Y.UA.ie) {
        return;
    }

    // If the user is not logged in, then we need to defer to the
    // default behaviour.
    if (!Y.Lang.isValue(LP.links.me)) {
        return;
    }

    // Setup the Launchpad client.
    setup_client();

    // Create the overlay.
    var overlay_name = setup_overlay(config.content_box);
    // Create the subscription links on the page.
    setup_subscription_links(config.content_box, overlay_name);
    namespace.is_ready = true;
};               // setup

}, '0.1', {requires: [
        'dom', 'node', 'lazr.formoverlay', 'lazr.overlay', 'lazr.effects',
        'lp.client', 'gallery-accordion'
    ]});
