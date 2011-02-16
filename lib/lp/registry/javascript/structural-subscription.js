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
        bodyContent: Y.one(overlay_id),
        centered: true,
        visible: false
    });
    add_subscription_overlay.render(content_box_id);
}                               // setup_subscription_links


/*
 * Modify the DOM to insert a link or two into the global actions portlet.
 * If structural subscriptions already exist then a 'modify' link is
 * added.  Otherwise, just the 'add' link is put into the portlet.
 *
 * @method setup_overlay
 * @param {String} content_box_id Id of the element on the page where
 *     the overlay is anchored.
 */
function setup_overlay(content_box_id) {
    // Create the accordion to go inside an overlay.
    var content_node = Y.one(content_box_id);
    var srcNode = Y.Node.create('<div id="accordion-overlay"></div>');
    var overlay_name = '#' + srcNode._node.id;
    content_node.appendChild(srcNode);
    var accordion = new Y.Accordion({
          srcNode: overlay_name,
          useAnimation: true,
          collapseOthersOnExpand: true
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

    // Dump the accordion to see what it looks like.
    return overlay_name;
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
