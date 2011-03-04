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

var BLOCK = 'block',
    DISPLAY = 'display',
    EXPANDER_COLLAPSED = '/@@/treeCollapsed',
    EXPANDER_EXPANDED = '/@@/treeExpanded',
    INLINE = 'inline',
    INNER_HTML = 'innerHTML',
    LAZR_CLOSED = 'lazr-closed',
    NONE = 'none',
    SRC = 'src',
    UNSEEN = 'unseen';

var add_subscription_overlay;

var super_sized = false;

/*
 * An object representing the global actions portlet.
 *
 */
var PortletTarget = function() {};
Y.augment(PortletTarget, Y.Event.Target);
namespace.portlet = new PortletTarget();

function setup_handlers() {
    if (LP.links.me === undefined) {
        return;
    }

    namespace.portlet.subscribe('ss:portletloaded', function() {
        create_subscription_link();
    });
}                               //setup_handlers

function subscription_success() {
    // TODO Should there be some success notification?
    add_subscription_overlay.hide();
}

function failure_handler(something, xhr) {
    // TODO Do something nicer.
    alert("it didn't work: " + xhr.responseText);
}

function bug_filter_added(bug_filter, form_data) {
    var config = {
        on: {
            success: subscription_success,
            failure: failure_handler
            }
        };

    // TODO Extract more data and complete the patch request.
    var patch_data = {
        'description': form_data.name[0]
    };

    // Figure out what notification level to set.
    include_comments = form_data.filters.indexOf('filter-out-comments') == -1;
    open_close_only = form_data.events.indexOf('added-or-closed') != -1;

    if (open_close_only) {
        patch_data.bug_notification_level = 'Lifecycle';
    } else if (include_comments) {
        patch_data.bug_notification_level = 'Discussion';
    } else {
        patch_data.bug_notification_level = 'Details';
    }

    patch_data.statuses = form_data.statuses;
    patch_data.importances = form_data.importances;

    lp_client.patch(bug_filter.lp_original_uri, patch_data, config)
}

function add_bug_filter(subscription, form_data) {
    var config = {
        on: {
            success: function (bug_filter) {
                    bug_filter_added(bug_filter, form_data);
                },
            failure: failure_handler
            }
        };

    var subscription_uri = subscription.lp_original_uri;
    lp_client.named_post(subscription_uri, 'newBugFilter', config);
}

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

    lp_client.named_post(LP.cache.context.self_link,
      'addBugSubscription', config);
}

function save_subscription(form_data) {
    if (form_data.recipient == 'yourself') {
        who = LP.links.me;
    } else {
        // There can be only one.
        who = form_data.team[0];
    }
    // TODO Remove this comment and the next two.
    // If you want to see what the form data looks like, you can do this:
    create_structural_subscription(who, form_data);
}

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
            add_subscription_overlay.show();
        }
    });
    var form_submit_button = Y.Node.create(
        '<input type="submit" name="field.actions.create" ' +
        'value="Create Subscription"/>');

    // Create the overlay.
    add_subscription_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Add a mail subscription for $name bugs</h2>',
        form_content: Y.one(overlay_id),
        centered: true,
        visible: false,
        form_submit_button: form_submit_button,
        form_submit_callback: save_subscription
    });
    add_subscription_overlay.render(content_box_id);
}                               // setup_subscription_links

function make_status_cell(s) {
    return '<td><label><input type="checkbox" name="statuses" '+
        'value="'+s+'" checked="checked">'+s+'</label><td>';
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

    var recipient_ai,
        events_ai,
        statuses_ai,
        importances_ai,
        tags_ai,
        subscription_name_ai;

    recipient_ai = new Y.AccordionItem( {
        label: "Bug subscription recipient",
        expanded: true,
        id: "recipients_ai",
        // XXX: BradCrittenden 2011-02-10: contentHeight methods
        // "auto" and "stretch" do not currently work.
        contentHeight: {method: "auto"},
        closable: false
    } );

    recipient_ai.set("bodyContent",
        "<div>Who will be the recipient of the bug subscription</div>");

    accordion.addItem(recipient_ai);

    events_ai = new Y.AccordionItem( {
        label: "Events (Any)",
        expanded: false,
        id: "events_ai",
        contentHeight: {method: "auto"}
    } );

    events_ai.set("bodyContent",
        "<div>Bunch of event checkboxes.</div>");

    accordion.addItem(events_ai);

    // Build statuses pane.
    statuses_ai = new Y.AccordionItem( {
        label: "Statuses (Any)",
        expanded: false,
        alwaysVisible: false,
        id: "statuses_ai",
        contentHeight: {method: "auto"}
    } );
    var statuses = LP.cache['statuses'];
    var status_html = '<table>';
    for (i in statuses) {
        i = parseInt(i); // JavaScript, you so crazy!
        if (i % 2)
            continue;
        status_html += '<tr>'+make_status_cell(statuses[i]);
        if (i+1 < statuses.length) {
            status_html += make_status_cell(statuses[i+1]);
        }
        status_html += '</tr>';
    }
    status_html += '</table>';
    statuses_ai.set("bodyContent", status_html);
    accordion.addItem(statuses_ai);

    // Build importances pane.
    importances_ai = new Y.AccordionItem( {
        label: "Importances (Any)",
        expanded: false,
        alwaysVisible: false,
        id: "importances_ai",
        contentHeight: {method: "auto"}
    } );
    var importances = LP.cache['importances'];
    var importance_html = '<ul>';
    for (i in importances) {
        var importance = importances[i];
        importance_html += '<li><label><input type="checkbox" '+
            'name="importances" value="'+importance+'" '+
            'checked="checked">'+
            importance+'</label>';
    }
    importance_html += '</ul>';
    importances_ai.set("bodyContent", importance_html);
    accordion.addItem(importances_ai);

    // Build tags pane.
    tags_ai = new Y.AccordionItem( {
        label: "Tags (None)",
        expanded: false,
        alwaysVisible: false,
        id: "tags_ai",
        contentHeight: {method: "auto"}
    } );

    tags_ai.set("bodyContent",
        "<div>Tags!  Tags!  Tags!</div>");

    accordion.addItem(tags_ai);

    subscription_name_ai = new Y.AccordionItem( {
        label: "Subscription Name",
        expanded: false,
        alwaysVisible: false,
        id: "subscription_name_ai",
        contentHeight: {method: "auto"}
    } );

    subscription_name_ai.set("bodyContent",
        "<div>Subscription name text entry.</div>");

    accordion.addItem(subscription_name_ai);

    return accordion;
}

/**
 * Collapse the node and set its arrow to 'collapsed'
 * @param node The node to collapse.
 */
function collapse_node(node) {
    var anim = Y.lazr.effects.slide_in(node);
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
        '      <input type="radio" name="recipient" value="yourself"\n' +
        '      checked> Yourself<br>\n' +
        '      <input type="radio" name="recipient" value="team"> One of the\n' +
        '      teams you administer<br>\n' +
        '      <dl>\n' +
        '        <dt></dt>\n' +
        '        <dd>\n' +
        '          <select name="team" id="structural-subscription-teams">\n' +
        '          </select>\n' +
        '        </dd>\n' +
        '      </dl>\n' +
        '    </dd>\n' +
        '  <dt>Subscription name</dt>\n' +
        '  <dd>\n' +
        '    <input type="text" name="name"> <a href="#">why?</a>\n' +
        '  </dd>\n' +
        '  <dt>Receive mail for bugs affecting $name that</dt>\n' +
        '  <dd>\n' +
        '    <div id="events">\n' +
        '    <input type="radio" name="events" value="added-or-closed" id="events_add_or_close"\n' +
        '    checked> are added or closed<br>\n' +
        '    <input type="radio" name="events" value="added-or-changed" id="events_add_or_change">\n' +
        '    are added or changed in any way<br>\n' +
        '    </div>\n' +
        '    <div id="filter-wrapper" class="ss-collapsible">\n' +
        '    <dl style="margin-left:25px;">\n' +
        '      <dt></dt>\n' +
        '      <dd>\n' +
        '        <input type="checkbox" name="filters"\n' +
        '               value="filter-out-comments" checked> filter out comments<br>\n' +
        '        <input type="checkbox" name="filters" value="advanced-filter" id="advanced-filter">\n' +
        '               bugs must match this filter<br>\n' +
        '            <div id="accordion-wrapper" class="ss-collapsible">\n' +
        '            <dl>\n' +
        '                <dt></dt>\n' +
        '                <dd style="margin-left:25px;">\n' +
        '                    <div id="' + accordion_overlay_id + '" style="position:relative; overflow:hidden;"></div>\n' +
        '                </dd>\n' +
        '            </dl>\n' +
        '            </div> \n' +
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
    radio_group.on('change', function(e) {
        var value = e.currentTarget.get('value');
        var div = Y.one('#filter-wrapper');
        if (value == 'added-or-changed')
            expand_node(div);
        else
            collapse_node(div);
        // Notify the overlay that content has changed.
        container.fire('contentUpdate');
    });

    // And a listener for advanced filter selection.
    var advanced_filter = Y.one('#advanced-filter');
    advanced_filter.on('change', function(e) {
        Y.log(e);
        var div = Y.one('#accordion-wrapper');
        var fw_div = Y.one('#filter-wrapper');
        var checked = e.currentTarget.get('checked');
        if (checked) {
            expand_node(div);
        }
        else
            collapse_node(div);
        // Notify the overlay that content has changed.
        container.fire('contentUpdate');
    });

    var teams = LP.cache['administratedTeams'];
    var select = Y.one('#structural-subscription-teams');
    for (i in teams) {
        team = teams[i];
        var option = Y.Node.create('<option></option>')
        option.set('innerHTML', team.title);
        option.set('value', team.link);
        select.appendChild(option);
    }
    return '#' + container._node.id;
}                               // setup_overlay

/*
 * Create the LP client.
 *
 * @method setup_client
 */
function setup_client() {
    lp_client = new Y.lp.client.Launchpad();
}                               // setup_client

namespace.render_bug_subscriptions = function() {
    Y.on('domready', function() {
        if (Y.UA.ie) {
            return;
        }

        fill_in_bug_subscriptions();
    }, window);
};

function fill_in_bug_subscriptions() {
    var listing = Y.one('#subscription-listing');
    var subscription_info = LP.cache['subscription_info'];
    var html = '<div class="yui-g"><div id="structural-subscriptions">';

    for (i in subscription_info) {
        var sub = subscription_info[i];
        html +=
            '<div style="margin-top: 2em; padding: 0 1em 1em 1em; '+
            '      border: 1px solid #ddd;">'+
            '  <span style="float: left; margin-top: -0.6em; padding: 0 1ex;'+
            '      background-color: #fff;">Subscriptions via'+
            '    <a href="'+sub.target_url+'">'+sub.target_title+'</a>'+
            '  </span>'+
            '  <div style="margin: 1em 0em 0em 1em">';

        for (j in sub.filters) {
            var filter = sub.filters[j].filter;

            if (filter.description) {
                var description = '"'+filter.description+'"';
            } else {
                var description = '(unnamed)';
            }

            html += '<div style="margin-top: 1em"><strong>'
            if (sub.filters[j].subscriber_is_team) {
                html += sub.filters[j].subscriber_title +
                    " subscription: " + description
            } else {
                html += 'Your subscription: ' + description
            }

            html += '</strong><span style="float: right">'+
                '<a href="#" class="sprite modify edit js-action">'+
                '    Edit this subscription</a><br>'+
                '<a href="#" class="sprite modify remove js-action">'+
                '    Unsubscribe</a></span></div>'+
                '<div style="padding-left: 1em">';

            var filter_items = '';
            // Format status conditions.
            if (filter.statuses.length != 0) {
                filter_items += '<li> have status ' +
                    filter.statuses.join(', ');
            }

            // Format importance conditions.
            if (filter.importances.length != 0) {
                filter_items += '<li> are of importance ' +
                    filter.importances.join(', ');
            }

            // Format tag conditions.
            if (filter.tags.length != 0) {
                filter_items += '<li> is tagged with ';
                if (filter.find_all_tags) {
                    filter_items += '<strong>all</strong>';
                } else {
                    filter_items += '<strong>any</strong>';
                }
                filter_items += ' of these tags: ' +
                    filter.tags.join(', ');
            }

            // If there were any conditions to list, stich them in with an
            // intro.
            if (filter_items != '') {
                html += 'You are subscribed to bugs which:'+
                    '<ul class="bulleted">'+filter_items+'</ul>';
            }

            // Format event details.
            if (filter.bug_notification_level == 'Discussion') {
                html += 'Notifications emails will be sent when any change '+
                    'is made or a comment is added.'
            } else if (filter.bug_notification_level == 'Details') {
                html += 'Notifications emails will be sent when any changes '+
                    'are made to the bug.  Bug comments will not be sent.'
            } else if (filter.bug_notification_level == 'Lifecycle') {
                html += 'Notifications emails will be sent when bugs are '+
                    'opened or closed.'
            }

            html += '</div>';
        }

        // We can remove this once we enforce at least one filter per
        // subscription.
        if (subscription_info[i].filters.length == 0) {
            html += '<strong>All messages</strong>';
        }
        html += '</div></div>';
    }
    html += '</div></div>';
    listing.appendChild(Y.Node.create(html));
}

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
            "Missing config for structural_subscription.")
    }
    if (!Y.Lang.isValue(config.content_box)) {
            throw new Error(
                "Structural_subscription configuration has " +
                "undefined properties.");
    }


    Y.on('domready', function() {
        if (Y.UA.ie) {
            return;
        }

        setup_handlers();

        // If the user is not logged in, then we need to defer to the
        // default behaviour.
        if (LP.links.me === undefined) {
            return;
        }
        // Setup the Launchpad client.
        setup_client();
        // Create the overlay.
        var overlay_name = setup_overlay(config.content_box);
        // Create the subscription links on the page.
        setup_subscription_links(config.content_box, overlay_name);
    }, window);
};               // setup

}, '0.1', {requires: [
        'dom', 'node', 'lazr.formoverlay', 'lazr.overlay', 'gallery-accordion',
        'lp.client', 'lp'
    ]});
