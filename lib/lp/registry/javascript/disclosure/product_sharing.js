/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Disclosure infrastructure.
 *
 * @module lp.registry.disclosure
 */

YUI.add('lp.registry.disclosure.sharing', function(Y) {

var namespace = Y.namespace('lp.registry.disclosure.sharing');

var lp_client = null;
var disclosure_picker = null;

var save_sharing_selection = function(result) {
    Y.log(result.access_policy);
    Y.log(result.api_uri);
};

var setup_product_sharing = function(config) {

    lp_client = new Y.lp.client.Launchpad();
    if (disclosure_picker === null) {
        var vocab = 'ValidPillarOwner';
        var header = 'Grant access to project artifacts.';
        if (config !== undefined) {
            if (config.header !== undefined) {
                header = config.header;
            }
        } else {
            config = {};
        }
        var new_config = Y.merge(config, {
            align: {
                points: [Y.WidgetPositionAlign.CC,
                         Y.WidgetPositionAlign.CC]
            },
            progressbar: true,
            progress: 50,
            headerContent: Y.Node.create("<h2></h2>").set('text', header),
            zIndex: 1000,
            visible: false,
            access_policies: LP.cache.access_policies,
            save: save_sharing_selection
        });
        disclosure_picker =
            new Y.lp.registry.disclosure.DisclosurePicker(new_config);
        Y.lp.app.picker.setup_vocab_picker(
            disclosure_picker, vocab, new_config);
    }

    var share_link = Y.one('#add-observer-link');
    share_link.on('click', function(e) {
        e.preventDefault();
        disclosure_picker.show();
    });

    var access_policy_types = {};
    Y.Array.each(LP.cache.access_policies, function(policy) {
        access_policy_types[policy.value] = policy.title;
    });
    var sharing_permissions = LP.cache.sharing_permissions;
    var observer_data = LP.cache.observer_data;
    var otns = Y.lp.registry.disclosure.observertable;
    var observer_table = new otns.ObserverTableWidget({
        observers: observer_data,
        sharing_permissions: sharing_permissions,
        access_policy_types: access_policy_types
    });
    observer_table.subscribe(
        otns.ObserverTableWidget.REMOVE_OBSERVER, function(e) {
            namespace.performRemoveObserver(
                observer_table, e.details[0], e.details[1]);
    });
    observer_table.render();
};

/**
 * Show a spinner next to the delete icon.
 *
 * @method _showDeleteSpinner
 */
var _showDeleteSpinner = function(delete_link) {
    var spinner_node = Y.Node.create(
    '<img class="spinner" src="/@@/spinner" alt="Removing..." />');
    delete_link.insertBefore(spinner_node, delete_link);
    delete_link.addClass('unseen');
};

/**
 * Hide the delete spinner.
 *
 * @method _hideDeleteSpinner
 */
var _hideDeleteSpinner = function(delete_link) {
    delete_link.removeClass('unseen');
    var spinner = delete_link.get('parentNode').one('.spinner');
    if (spinner !== null) {
        spinner.remove();
    }
};

namespace.removeObserverSuccess = function(observer_table, person_uri) {
    var observer_data = LP.cache.observer_data;
    Y.Array.some(observer_data, function(observer, index) {
        if (observer.self_link === person_uri) {
            observer_data.splice(index, 1);
            observer_table.deleteObserver(observer);
            return true;
        }
    });
};

namespace.performRemoveObserver = function(
        observer_table, delete_link, person_uri) {
    var error_handler = new Y.lp.client.ErrorHandler();
    var product_uri = LP.cache.context.self_link;
    var y_config =  {
        on: {
            start: Y.bind(_showDeleteSpinner, delete_link),
            end: Y.bind(_hideDeleteSpinner, delete_link),
            success: function() {
                namespace.removeObserverSuccess(observer_table, person_uri);
            },
            failure: error_handler.getFailureHandler()
        },
        parameters: {
            product: product_uri,
            observer: person_uri
        }
    };
    lp_client.named_post(
        '/+services/accesspolicy', 'deleteProductObserver', y_config);
};

namespace.setup_product_sharing = setup_product_sharing;

}, "0.1", { "requires": [
    'node', 'lp.client', 'lp.mustache', 'lazr.picker', 'lp.app.picker',
    'lp.mustache', 'lp.registry.disclosure',
    'lp.registry.disclosure.observertable'] });

