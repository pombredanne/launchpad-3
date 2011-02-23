/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Form overlay widgets and subscriber handling for structural subscriptions.
 *
 * @module registry
 * @submodule structural_subscription
 */

YUI.add('lp.registry.structural_subscription', function(Y) {

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

var namespace = Y.namespace('lp.registry.structural_subscription');

/*
 * An object representing the global actions portlet.
 *
 */
var PortletTarget = function() {};
Y.augment(PortletTarget, Y.Event.Target);
namespace.portlet = new PortletTarget();

function setup_handlers() {
    if (LP.client.links.me === undefined) {
        return;
    }

    namespace.portlet.subscribe('ss:portletloaded', function() {
        create_subscription_link();
    });
}                               //setup_handlers


/*
 * Modify the DOM to insert a link or two into the global actions portlet.
 * If structural subscriptions already exist then a 'modify' link is
 * added.  Otherwise, just the 'add' link is put into the portlet.
 *
 * @method setup_subscription_links
 * @param {String} content_box_id Id of the element on the page where
 *     the overlay is anchored.
 * @param {String} overlay_id Id of the overlay element.
 */
function setup_subscription_links(content_box_id, overlay_id) {
    // Create a new link in the global actions portlet.
    var link = Y.Node.create('<a href="#">Subscribe to bug mail</a>');
    // Add a class denoting them as js-action links with add sprite.
    link.addClass('sprite add js-action');
    var add_subscription_overlay;
    var portlet = Y.one('#global-actions');
    portlet.appendChild(link);
    // Intercept clicks on the new link.
    link.on('click', function(e) {
        // Only proceed if the form content is already available.
        if (add_subscription_overlay) {
            e.preventDefault();
            add_subscription_overlay.show();
            //Y.DOM.byId('field.something').focus();
        }
    });
    // Create the overlay.
    add_subscription_overlay = new Y.lazr.PrettyOverlay({
        headerContent: 'Add a mail subscription for $name bugs',
        bodyContent: Y.one(overlay_id),
        centered: true,
        visible: false
    });
    add_subscription_overlay.render(content_box_id);
}                               // setup_subscription_links

/*
 * Create the accordion.
 *
 * @method create_accordion
 * @param {String} overlay_id Id of the overlay element.
 * @return {Object} accordion The accordion just created.
 */
function create_accordion(overlay_id) {
    var accordion = new Y.Accordion({
          srcNode: overlay_id,
          useAnimation: true,
          collapseOthersOnExpand: true,
          visible: false
    });

    accordion.render();

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
        contentHeight: {
            method: "fixed",
            height: 80
        },
        closable: false
    } );

    recipient_ai.set("bodyContent",
        "Who will be the recipient of the bug subscription");

    accordion.addItem(recipient_ai);

    events_ai = new Y.AccordionItem( {
        label: "Events (Any)",
        expanded: false,
        id: "events_ai",
        contentHeight: {
            method: "fixed",
            height: 80
        }
    } );

    events_ai.set("bodyContent",
        "Bunch of event checkboxes.");

    accordion.addItem(events_ai);

    statuses_ai = new Y.AccordionItem( {
        label: "Statuses (Any)",
        expanded: false,
        alwaysVisible: false,
        id: "statuses_ai",
        contentHeight: {
            method: "fixed",
            height: 80
            //method: "auto"
        }
    } );

    statuses_ai.set("bodyContent",
        "Bunch of status checkboxes.");

    accordion.addItem(statuses_ai);

    importances_ai = new Y.AccordionItem( {
        label: "Importances (Any)",
        expanded: false,
        alwaysVisible: false,
        id: "importances_ai",
        contentHeight: {
            method: "fixed",
            height: 80
        }
    } );

    importances_ai.set("bodyContent",
        "Bunch of importance checkboxes.");

    accordion.addItem(importances_ai);

    tags_ai = new Y.AccordionItem( {
        label: "Tags (None)",
        expanded: false,
        alwaysVisible: false,
        id: "tags_ai",
        contentHeight: {
            method: "fixed",
            height: 80
        }
    } );

    tags_ai.set("bodyContent",
        "Bunch of status checkboxes.");

    accordion.addItem(tags_ai);

    subscription_name_ai = new Y.AccordionItem( {
        label: "Subscription Name",
        expanded: false,
        alwaysVisible: false,
        id: "subscription_name_ai",
        contentHeight: {
            method: "fixed",
            height: 80
        }
    } );

    subscription_name_ai.set("bodyContent",
        "Subscription name text entry.");

    accordion.addItem(subscription_name_ai);

    return accordion;
}

/**
 * Collapse the expander and set its arrow to 'collapsed'
 * @param expander The expander to collapse.
 */
function collapse_div(expander) {
    var anim = Y.lazr.effects.slide_in(expander);
    anim.run();
    expander.set(SRC, EXPANDER_COLLAPSED);
}

/**
 * Expand the expander and set its arrow to 'collapsed'
 * @param expander The expander to collapse.
 */
function expand_div(expander) {
    var anim = Y.lazr.effects.slide_out(expander);
    anim.run();
    expander.set(SRC, EXPANDER_EXPANDED);
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
        '<dl>' +
        '    <dt>Bug mail recipient</dt>' +
        '    <dd>' +
        '      <input type="radio" name="recipient" value="yourself"' +
        '      checked> Yourself<br>' +
        '      <input type="radio" name="recipient" value="team"> One of the' +
        '      teams you administer<br>' +
        '      <dl>' +
        '        <dt></dt>' +
        '        <dd>' +
        '          <select>' +
        '            <option>MOTU</option>' +
        '            <option>Launchpad Administrators</option>' +
        '            <option>Malone Alpha Testers</option>' +
        '          </select>' +
        '        </dd>' +
        '      </dl>' +
        '    </dd>' +
        '  <dt>Subscription name</dt>' +
        '  <dd>' +
        '    <input type="text" name="name"> <a href="#">why?</a>' +
        '  </dd>' +
        '  <dt>Receive mail for bugs affecting $name that</dt>' +
        '  <dd>' +
        '    <div id="events">' +
        '    <input type="radio" name="events" value="added-or-closed" id="events_add_or_close"' +
        '    checked> are added or closed<br>' +
        '    <input type="radio" name="events" value="added-or-changed" id="events_add_or_change">' +
        '    are added or changed in any way<br>' +
        '    </div>' +
        '    <div class="collapsible" id="filter_wrapper"  ' +
        '    <dl style="margin-left:25px;">' +
        '      <dt></dt>' +
        '      <dd>' +
        '        <input type="checkbox" name="filters"' +
        '               value="filter-out-comments" checked> filter out comments<br>' +
        '        <input type="checkbox" name="filters" value="advanced-filter" id="advanced-filter">' +
        '               bugs must match this filter<br>' +
        '            <div class="collapsible" id="accordion_wrapper"  ' +
        '            <dl>' +
        '                <dt></dt>' +
        '                <dd style="margin-left:25px;">' +
        '                    <div id="' + accordion_overlay_id + '"></div>' +
        '                </dd>' +
        '            </dl>' +
        '            </div> ' +
        '      </dd>' +
        '    </dl>' +
        '    </div> ' +
        '  </dd>' +
        '  <dt></dt>' +
        '  <dd>' +
        '      <input type="submit" value="Save subscription">' +
        '      <input type="submit" value="Cancel">' +
        '  </dd>' +
        '</dl>';

    content_node.appendChild(container);
    container.appendChild(Y.Node.create(control_code));

    var accordion = create_accordion('#' + accordion_overlay_id);

    Y.each(Y.all('div.collapsible'), function(div) {
        collapse_div(div);
    });

    // Set up click handlers for the events radio buttons.
    var radio_group = Y.all('#events input');
    radio_group.on('change', function(e) {
        var value = e.currentTarget.get('value');
        var div = Y.one('#filter_wrapper');
        if (value == 'added-or-changed')
            expand_div(div);
        else
            collapse_div(div);
    });

    // And a listener for advanced filter selection.
    var advanced_filter = Y.one('#advanced-filter');
    advanced_filter.on('change', function(e) {
        Y.log(e);
        var div = Y.one('#accordion_wrapper');
        var checked = e.currentTarget.get('checked');
        if (checked)
            expand_div(div);
        else
            collapse_div(div);
    });
    Y.log(advanced_filter);

    return '#' + container._node.id;
}                               // setup_overlay

/*
 * Create the LP client.
 *
 * @method setup_client
 */
function setup_client() {
    lp_client = new LP.client.Launchpad();
}                               // setup_client

/*
 * External entry point for configuring the structual subscription.
 * @method setup
 * @param {Object} config Object literal of config name/value pairs.
 *     config.content_box is the name of an element on the page where
 *         the overlay will be anchored.
 */
namespace.setup = function(config) {

    if (config === undefined) {
        throw new Error(
            "Missing config for structural_subscription.");
    }
    if (config.content_box === undefined) {
            throw new Error(
                "Structural_subscription configuration has " +
                "undefined properties.");
    }

    setup_handlers();

    Y.on('domready', function() {
        if (Y.UA.ie) {
            return;
        }
        // If the user is not logged in, then we need to defer to the
        // default behaviour.
        if (LP.client.links.me === undefined) {
            return;
        }
        // Setup the Launchpad client.
        setup_client();
        // Create the overlay.
        var overlay_name = setup_overlay(config.content_box);
        // Create the subscription links on the page.
        setup_subscription_links(config.content_box, overlay_name);
    }, window);};               // setup
}, '0.1', {requires: [
        'node', 'lazr.overlay', 'gallery-accordion'
    ]});
