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
 */
function setup_subscription_links(config) {
    // Create a new link in the global actions portlet.
    var link = Y.Node.create('<a href="#">Subscribe to bug mail</a>');
    // Add a class denoting them as js-action links with add sprite.
    link.addClass('sprite add js-action');
    var add_subscription_overlay;
    portlet = Y.one('#global-actions');
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
        bodyContent: Y.one(config.content_box),
        centered: true,
        visible: false
    });
    add_subscription_overlay.render('#add-subscription-container');
}                               // setup_subscription_links


/*
 * Modify the DOM to insert a link or two into the global actions portlet.
 * If structural subscriptions already exist then a 'modify' link is
 * added.  Otherwise, just the 'add' link is put into the portlet.
 *
 * @method setup_overlay
 */
function setup_overlay(config) {
    // Create the accordion to go inside an overlay.
    var accordion = new Y.Accordion({
          srcNode: config.content_box,
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
    Y.log(accordion);
}                               // setup_overlay

/*
 * Create the LP client.
 *
 * @method setup_client
 */
function setup_client() {
    lp_client = new LP.client.Launchpad();
}                               // setup_client

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
        // Create the subscription links on the page.
        setup_subscription_links(config);
        // Create the overlay.
        setup_overlay(config);
    }, window);};               // setup
}, '0.1', {requires: [
        'node', 'lazr.overlay', 'gallery-accordion'
    ]});
