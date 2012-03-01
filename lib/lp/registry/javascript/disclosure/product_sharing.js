/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Disclosure infrastructure.
 *
 * @module lp.registry.disclosure
 */

YUI.add('lp.registry.disclosure.sharing', function(Y) {

var namespace = Y.namespace('lp.registry.disclosure.sharing');

function ProductSharingView(config) {
    ProductSharingView.superclass.constructor.apply(this, arguments);
}

ProductSharingView.ATTRS = {
    lp_client: {
        value: new Y.lp.client.Launchpad()
    },

    disclosure_picker: {
        value: null
    },

    observer_table: {
        value: null
    }
};

Y.extend(ProductSharingView, Y.Widget, {

    initializer: function(config) {
        var vocab = 'ValidPillarOwner';
        var header = 'Grant access to project artifacts.';
        if (Y.Lang.isValue(config)) {
            if (Y.Lang.isValue(config.header)) {
                header = config.header;
            }
            if (Y.Lang.isValue(config.vocabulary)) {
                vocab = config.vocabulary;
            }
        } else {
            config = {};
        }
        var self = this;
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
            save: function(result) {
                self.saveSharingSelection(result);
            }
        });
        var disclosure_picker =
            new Y.lp.registry.disclosure.DisclosurePicker(new_config);
        Y.lp.app.picker.setup_vocab_picker(
            disclosure_picker, vocab, new_config);
        this.set('disclosure_picker', disclosure_picker);
    },

    destructor: function() { },

    renderUI: function() {
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
        this.set('observer_table', observer_table);
        observer_table.render();
    },

    bindUI: function() {
        var self = this;
        var share_link = Y.one('#add-observer-link');
        share_link.on('click', function(e) {
            e.preventDefault();
            self.get('disclosure_picker').show();
        });
        var observer_table = this.get('observer_table');
        var otns = Y.lp.registry.disclosure.observertable;
        observer_table.subscribe(
            otns.ObserverTableWidget.REMOVE_OBSERVER, function(e) {
                self.performRemoveObserver(e.details[0], e.details[1]);
        });
    },

    syncUI: function() {
    },


    /**
     * Show a spinner next to the delete icon.
     *
     * @method _showDeleteSpinner
     */
    _showDeleteSpinner: function(delete_link) {
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Removing..." />');
        delete_link.insertBefore(spinner_node, delete_link);
        delete_link.addClass('unseen');
    },

    /**
     * Hide the delete spinner.
     *
     * @method _hideDeleteSpinner
     */
    _hideDeleteSpinner: function(delete_link) {
        delete_link.removeClass('unseen');
        var spinner = delete_link.get('parentNode').one('.spinner');
        if (Y.Lang.isValue(spinner)) {
            spinner.remove();
        }
    },

    /**
     * The server call to remove the specified observer has succeeded.
     * Update the model and view.
     * @method performRemoveObserver
     * @param person_uri
     */
    removeObserverSuccess: function(person_uri) {
        var observer_table = this.get('observer_table');
        var observer_data = LP.cache.observer_data;
        Y.Array.some(observer_data, function(observer, index) {
            if (observer.self_link === person_uri) {
                observer_data.splice(index, 1);
                observer_table.deleteObserver(observer);
                return true;
            }
        });
    },

    /**
     * Make a server call to remove the specified observer.
     * @method performRemoveObserver
     * @param delete_link
     * @param person_uri
     */
    performRemoveObserver: function(delete_link, person_uri) {
        var error_handler = new Y.lp.client.ErrorHandler();
        var product_uri = LP.cache.context.self_link;
        var self = this;
        var y_config =  {
            on: {
                start: Y.bind(self._showDeleteSpinner, namespace, delete_link),
                end: Y.bind(self._hideDeleteSpinner, namespace, delete_link),
                success: function() {
                    self.removeObserverSuccess(person_uri);
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                product: product_uri,
                observer: person_uri
            }
        };
        this.get('lp_client').named_post(
            '/+services/accesspolicy', 'deleteProductObserver', y_config);
    },

    /**
     * Show a spinner for a sharing update operation.
     *
     * @method _showSharingSpinner
     */
    _showSharingSpinner: function() {
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Saving..." />');
        var sharing_header = Y.one('#observer-table th:nth-child(2)');
        sharing_header.appendChild(spinner_node, sharing_header);
    },

    /**
     * Hide the sharing spinner.
     *
     * @method _hideSharingSpinner
     */
    _hideSharingSpinner: function() {
        var spinner = Y.one('#observer-table th .spinner');
        if (spinner !== null) {
            spinner.remove();
        }
    },

    /**
     * The server call to add the specified observer has succeeded.
     * Update the model and view.
     * @method saveSharingSelectionSuccess
     * @param observer
     */
    saveSharingSelectionSuccess: function(observer) {
        var observer_table = this.get('observer_table');
        var observer_data = LP.cache.observer_data;
        observer_data.splice(0, 0, observer);
        observer_table.addObserver(observer);
    },

    /**
     * Make a server call to add the specified observer and access policy.
     * @method performRemoveObserver
     * @param selection_result the disclosure picker
     */
    saveSharingSelection: function(selection_result) {
        var error_handler = new Y.lp.client.ErrorHandler();
        var product_uri = LP.cache.context.self_link;
        var person_uri = Y.lp.client.normalize_uri(selection_result.api_uri);
        person_uri = Y.lp.client.get_absolute_uri(person_uri);
        var self = this;
        var y_config =  {
            on: {
                start: Y.bind(self._showSharingSpinner, namespace),
                end: Y.bind(self._hideSharingSpinner, namespace),
                success: function(observer_entry) {
                    self.saveSharingSelectionSuccess(observer_entry.getAttrs());
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                product: product_uri,
                observer: person_uri,
                access_policy: selection_result.access_policy,
                sharing_permission: 'All'
            }
        };
        this.get('lp_client').named_post(
            '/+services/accesspolicy', 'addProductObserver', y_config);
    }
});

ProductSharingView.NAME = 'productSharingView';
namespace.ProductSharingView = ProductSharingView;

}, "0.1", { "requires": [
    'node', 'lp.client', 'lp.mustache', 'lazr.picker', 'lp.app.picker',
    'lp.mustache', 'lp.registry.disclosure',
    'lp.registry.disclosure.observertable'] });

