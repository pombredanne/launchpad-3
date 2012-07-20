/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Disclosure infrastructure.
 *
 * @module lp.registry.sharing
 */

YUI.add('lp.registry.sharing.pillarsharingview', function(Y) {

var namespace = Y.namespace('lp.registry.sharing.pillarsharingview');

function PillarSharingView(config) {
    PillarSharingView.superclass.constructor.apply(this, arguments);
}

PillarSharingView.ATTRS = {
    lp_client: {
        value: new Y.lp.client.Launchpad()
    },

    write_enabled: {
        value: false
    },

    grantee_picker: {
        value: null
    },

    grantee_table: {
        value: null
    },

    information_types_by_value: {
        value: null
    },

    sharing_permissions_by_value: {
        value: null
    }
};

Y.extend(PillarSharingView, Y.Widget, {

    initializer: function(config) {
        var information_types_by_value = {};
        Y.Array.each(LP.cache.information_types, function(info_type) {
            information_types_by_value[info_type.value] = info_type.title;
        });
        this.set(
            'information_types_by_value', information_types_by_value);
        var sharing_permissions_by_value = {};
        Y.Array.each(LP.cache.sharing_permissions, function(permission) {
            sharing_permissions_by_value[permission.value] = permission.title;
        });
        this.set(
            'sharing_permissions_by_value', sharing_permissions_by_value);

        // No need to do anything else if we are read only.
        if (LP.cache.sharing_write_enabled !== true) {
            return;
        }
        this.set('write_enabled', true);

        var vocab;
        var header;
        var steptitle;
        if (Y.Lang.isValue(config)) {
            if (Y.Lang.isValue(config.header)) {
                header = config.header;
            } else {
                throw new Error(
                    "Missing header config value for grantee picker");
            }
            if (Y.Lang.isValue(config.steptitle)) {
                steptitle = config.steptitle;
            } else {
                throw new Error(
                    "Missing steptitle config value for grantee picker");
            }
            if (Y.Lang.isValue(config.vocabulary)) {
                vocab = config.vocabulary;
            } else {
                throw new Error(
                    "Missing vocab config value for grantee picker");
            }
        } else {
            throw new Error("Missing config for grantee picker");
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
            steptitle: steptitle,
            zIndex: 1000,
            visible: false,
            information_types: LP.cache.information_types,
            sharing_permissions: LP.cache.sharing_permissions,
            save: function(result) {
                self.save_sharing_selection(
                    result.api_uri, result.selected_permissions);
            }
        });
        var ns = Y.lp.registry.sharing.granteepicker;
        var picker = new ns.GranteePicker(new_config);
        Y.lp.app.picker.setup_vocab_picker(picker, vocab, new_config);
        this.set('grantee_picker', picker);
    },

    renderUI: function() {
        var grantee_data = LP.cache.grantee_data;
        var otns = Y.lp.registry.sharing.granteetable;
        var grantee_table = new otns.GranteeTableWidget({
            grantees: grantee_data,
            sharing_permissions:
                this.get('sharing_permissions_by_value'),
            information_types: this.get('information_types_by_value'),
            write_enabled: this.get('write_enabled')
        });
        this.set('grantee_table', grantee_table);
        grantee_table.render();
        if (!this.get('write_enabled')) {
            Y.one('#add-grantee-link').addClass('hidden');
        }
    },

    bindUI: function() {
        if (!this.get('write_enabled')) {
            return;
        }
        var self = this;
        var share_link = Y.one('#add-grantee-link');
        share_link.on('click', function(e) {
            e.preventDefault();
            self.get('grantee_picker').show();
        });
        var grantee_table = this.get('grantee_table');
        var otns = Y.lp.registry.sharing.granteetable;
        grantee_table.subscribe(
            otns.GranteeTableWidget.REMOVE_SHAREE, function(e) {
                self.confirm_grantee_removal(
                    e.details[0], e.details[1], e.details[2]);
        });
        grantee_table.subscribe(
            otns.GranteeTableWidget.UPDATE_SHAREE, function(e) {
                self.update_grantee_interaction(
                    e.details[0], e.details[1], e.details[2]);
        });
        grantee_table.subscribe(
            otns.GranteeTableWidget.UPDATE_PERMISSION, function(e) {
                var permissions = {};
                permissions[e.details[1]] = e.details[2];
                self.save_sharing_selection(e.details[0], permissions);
        });
    },

    syncUI: function() {
        var grantee_table = this.get('grantee_table');
        grantee_table.syncUI();
    },

    // A common error handler for XHR operations.
    _error_handler: function(person_uri) {
        var grantee_data = LP.cache.grantee_data;
        var error_handler = new Y.lp.client.ErrorHandler();
        var grantee_name = null;
        Y.Array.some(grantee_data, function(grantee) {
            if (grantee.self_link === person_uri) {
                grantee_name = grantee.name;
                return true;
            }
        });
        var self = this;
        error_handler.showError = function(error_msg) {
            self.get('grantee_table').display_error(grantee_name, error_msg);
        };
        return error_handler;
    },

    /**
     * Show a spinner next to the delete icon.
     *
     * @method _show_delete_spinner
     */
    _show_delete_spinner: function(delete_link) {
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Removing..." />');
        delete_link.insertBefore(spinner_node, delete_link);
        delete_link.addClass('hidden');
    },

    /**
     * Hide the delete spinner.
     *
     * @method _hide_delete_spinner
     */
    _hide_delete_spinner: function(delete_link) {
        delete_link.removeClass('hidden');
        var spinner = delete_link.get('parentNode').one('.spinner');
        if (Y.Lang.isValue(spinner)) {
            spinner.remove();
        }
    },

    /**
     * Prompt the user to confirm the removal of the selected grantee.
     *
     * @method confirm_grantee_removal
     */
    confirm_grantee_removal: function(delete_link, person_uri, person_name) {
        var confirm_text_template = [
            '<p class="large-warning" style="padding:2px 2px 15px 36px;">',
            '    Do you really want to stop sharing',
            '    "{pillar}" with {person_name}?',
            '</p>'
            ].join('');
        var confirm_text = Y.Lang.sub(confirm_text_template,
                {pillar: LP.cache.context.display_name,
                 person_name: person_name});
        var self = this;
        var co = new Y.lp.app.confirmationoverlay.ConfirmationOverlay({
            submit_fn: function() {
                self.perform_remove_grantee(delete_link, person_uri);
            },
            form_content: confirm_text,
            headerContent: '<h2>Stop sharing</h2>'
        });
        co.show();
    },

    /**
     * The server call to remove the specified grantee has succeeded.
     * Update the model and view.
     * @method remove_grantee_success
     * @param person_uri
     */
    remove_grantee_success: function(person_uri) {
        var grantee_data = LP.cache.grantee_data;
        var self = this;
        Y.Array.some(grantee_data, function(grantee, index) {
            if (grantee.self_link === person_uri) {
                grantee_data.splice(index, 1);
                self.syncUI();
                return true;
            }
        });
    },

    /**
     * Make a server call to remove the specified grantee.
     * @method perform_remove_grantee
     * @param delete_link
     * @param person_uri
     */
    perform_remove_grantee: function(delete_link, person_uri) {
        var error_handler = this._error_handler(person_uri);
        var pillar_uri = LP.cache.context.self_link;
        var self = this;
        var y_config =  {
            on: {
                start: Y.bind(
                    self._show_delete_spinner, namespace, delete_link),
                end: Y.bind(self._hide_delete_spinner, namespace, delete_link),
                success: function() {
                    self.remove_grantee_success(person_uri);
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                pillar: pillar_uri,
                grantee: person_uri
            }
        };
        this.get('lp_client').named_post(
            '/+services/sharing', 'deletePillarGrantee', y_config);
    },

    /**
     * Show a spinner for a sharing update operation.
     *
     * @method _show_sharing_spinner
     */
    _show_sharing_spinner: function() {
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Saving..." />');
        var sharing_header = Y.one('#grantee-table th:nth-child(2)');
        sharing_header.appendChild(spinner_node, sharing_header);
    },

    /**
     * Hide the sharing spinner.
     *
     * @method _hide_hiding_spinner
     */
    _hide_hiding_spinner: function() {
        var spinner = Y.one('#grantee-table th .spinner');
        if (spinner !== null) {
            spinner.remove();
        }
    },

    /**
     * The server call to add the specified grantee has succeeded.
     * Update the model and view.
     * @method save_sharing_selection_success
     * @param updated_grantee
     */
    save_sharing_selection_success: function(updated_grantee) {
        var grantee_data = LP.cache.grantee_data;
        var grantee_replaced = false;
        Y.Array.some(grantee_data, function(grantee, index) {
            if (updated_grantee.name === grantee.name) {
                grantee_replaced = true;
                grantee_data.splice(index, 1, updated_grantee);
                return true;
            }
            return false;
        });
        if (!grantee_replaced) {
            grantee_data.splice(0, 0, updated_grantee);
        }
        this.syncUI();
    },

    /**
     * Make a server call to add the specified grantee and access policy.
     * @method save_sharing_selection
     * @param person_uri
     * @param permissions
     */
    save_sharing_selection: function(person_uri, permissions) {
        var error_handler = this._error_handler(person_uri);
        var pillar_uri = LP.cache.context.self_link;
        person_uri = Y.lp.client.normalize_uri(person_uri);
        person_uri = Y.lp.client.get_absolute_uri(person_uri);
        var information_types_by_value =
            this.get('information_types_by_value');
        var sharing_permissions_by_value =
            this.get('sharing_permissions_by_value');
        var permission_params = [];
        Y.each(permissions, function(permission, info_type) {
            permission_params.push(
                [information_types_by_value[info_type],
                sharing_permissions_by_value[permission]]);
        });
        var self = this;
        var y_config =  {
            on: {
                start: Y.bind(self._show_sharing_spinner, namespace),
                end: Y.bind(self._hide_hiding_spinner, namespace),
                success: function(grantee_entry) {
                    if (!Y.Lang.isValue(grantee_entry)) {
                        self.remove_grantee_success(person_uri);
                    } else {
                        self.save_sharing_selection_success(grantee_entry);
                    }
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                pillar: pillar_uri,
                grantee: person_uri,
                permissions: permission_params
            }
        };
        this.get('lp_client').named_post(
            '/+services/sharing', 'sharePillarInformation', y_config);
    },

    /**
     * The user has clicked the (+) icon for a grantee. We display the sharing
     * picker to allow the sharing permissions to be updated.
     * @param update_link
     * @param person_uri
     * @param person_name
     */
    update_grantee_interaction: function(update_link, person_uri, person_name) {
        var grantee_data = LP.cache.grantee_data;
        var grantee_permissions = {};
        var disabled_some_types = [];
        Y.Array.some(grantee_data, function(grantee) {
            var full_person_uri = Y.lp.client.normalize_uri(person_uri);
            full_person_uri = Y.lp.client.get_absolute_uri(full_person_uri);
            if (grantee.self_link !== full_person_uri) {
                return false;
            }
            grantee_permissions = grantee.permissions;
            // Do not allow the user to choose 'Some' unless there are shared
            // artifacts of that type.
            Y.Array.each(LP.cache.information_types, function(info_type) {
                if (Y.Array.indexOf(
                    grantee.shared_artifact_types, info_type.value) < 0) {
                    disabled_some_types.push(info_type.value);
                }
            });
            return true;
        });
        var allowed_permissions = [];
        Y.Array.each(LP.cache.sharing_permissions, function(permission) {
            allowed_permissions.push(permission.value);
        });
        this.get('grantee_picker').show({
            first_step: 2,
            grantee: {
                person_uri: person_uri,
                person_name: person_name
            },
            grantee_permissions: grantee_permissions,
            allowed_permissions: allowed_permissions,
            disabled_some_types: disabled_some_types
        });
    }
});

PillarSharingView.NAME = 'pillarSharingView';
namespace.PillarSharingView = PillarSharingView;

}, "0.1", { "requires": [
    'node', 'selector-css3', 'lp.client', 'lp.mustache', 'lazr.picker',
    'lp.app.picker', 'lp.mustache', 'lp.registry.sharing.granteepicker',
    'lp.registry.sharing.granteetable', 'lp.app.confirmationoverlay'
    ]});

