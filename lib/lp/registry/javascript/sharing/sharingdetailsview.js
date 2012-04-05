/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Disclosure infrastructure.
 *
 * @module lp.registry.sharing
 */

YUI.add('lp.registry.sharing.sharingdetailsview', function(Y) {

var namespace = Y.namespace('lp.registry.sharing.sharingdetailsview');

function SharingDetailsView(config) {
    SharingDetailsView.superclass.constructor.apply(this, arguments);
}

SharingDetailsView.ATTRS = {
    lp_client: {
        value: new Y.lp.client.Launchpad()
    },

    write_enabled: {
        value: false
    },

    sharing_details_table: {
        value: null
    }
};

Y.extend(SharingDetailsView, Y.Widget, {

    initializer: function(config) {
        if (LP.cache.sharing_write_enabled !== true) {
            return;
        }
        this.set('write_enabled', true);
    },

    renderUI: function() {
        var ns = Y.lp.registry.sharing.sharingdetails;
        var details_table = new ns.SharingDetailsTable({
            bugs: LP.cache.bugs,
            branches: LP.cache.branches,
            person_name: LP.cache.sharee.displayname,
            write_enabled: this.get('write_enabled')
        });
        this.set('sharing_details_table', details_table);
        details_table.render();
    },

    bindUI: function() {
        if (!this.get('write_enabled')) {
            return;
        }
        var self = this;
        var sharing_details_table = this.get('sharing_details_table');
        var ns = Y.lp.registry.sharing.sharingdetails;
        sharing_details_table.subscribe(
            ns.SharingDetailsTable.REMOVE_GRANT, function(e) {
                self.confirm_grant_removal(
                    e.details[0], e.details[1], e.details[2], e.details[3]);
        });
    },

    syncUI: function() {
        var sharing_details_table = this.get('sharing_details_table');
        sharing_details_table.syncUI();
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
        delete_link.addClass('unseen');
    },

    /**
     * Hide the delete spinner.
     *
     * @method _hide_delete_spinner
     */
    _hide_delete_spinner: function(delete_link) {
        delete_link.removeClass('unseen');
        var spinner = delete_link.get('parentNode').one('.spinner');
        if (Y.Lang.isValue(spinner)) {
            spinner.remove();
        }
    },

    /**
     * Prompt the user to confirm the removal of access to the selected
     * artifact.
     *
     * @method confirm_grant_removal
     * @param delete_link
     * @param artifact_uri
     * @param artifact_name
     * @param artifact_type
     */
    confirm_grant_removal: function(delete_link, artifact_uri,
                                    artifact_name, artifact_type) {
        var confirm_text_template = [
            '<p class="large-warning" style="padding:2px 2px 15px 36px;">',
            '    Do you really want to stop sharing',
            '    "{artifact}" with {person_name}?',
            '</p>'
            ].join('');
        var person_name = LP.cache.sharee.displayname;
        var confirm_text = Y.Lang.sub(confirm_text_template,
                {artifact: artifact_name,
                 person_name: person_name});
        var self = this;
        var co = new Y.lp.app.confirmationoverlay.ConfirmationOverlay({
            submit_fn: function() {
                self.perform_remove_grant(
                    delete_link, artifact_uri, artifact_type);
            },
            form_content: confirm_text,
            headerContent: '<h2>Stop sharing</h2>'
        });
        co.show();
    },

    /**
     * The server call to remove the specified sharee has succeeded.
     * Update the model and view.
     * @method remove_grant_success
     * @param artifact_uri
     */
    remove_grant_success: function(artifact_uri) {
        var bugs_data = LP.cache.bugs;
        var self = this;
        Y.Array.some(bugs_data, function(bug, index) {
            if (bug.self_link === artifact_uri) {
                bugs_data.splice(index, 1);
                self.syncUI();
                return true;
            }
        });
        var branch_data = LP.cache.branches;
        Y.Array.some(branch_data, function(branch, index) {
            if (branch.self_link === artifact_uri) {
                branch_data.splice(index, 1);
                self.syncUI();
                return true;
            }
        });
    },

    /**
     * Make a server call to remove access to the specified artifact.
     * @method perform_remove_sharee
     * @param delete_link
     * @param artifact_uri
     * @param artifact_type
     */
    perform_remove_grant: function(delete_link, artifact_uri, artifact_type) {
        var error_handler = new Y.lp.client.ErrorHandler();
        var bugs = [];
        var branches = [];
        if (artifact_type === 'bug') {
            bugs = [artifact_uri];
        } else {
            branches = [artifact_uri];
        }
        var self = this;
        var y_config =  {
            on: {
                start: Y.bind(
                    self._show_delete_spinner, namespace, delete_link),
                end: Y.bind(self._hide_delete_spinner, namespace, delete_link),
                success: function() {
                    self.remove_grant_success(artifact_uri);
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                pillar: LP.cache.pillar.self_link,
                sharee: LP.cache.sharee.self_link,
                bugs: bugs,
                branches: branches
            }
        };
        this.get('lp_client').named_post(
            '/+services/sharing', 'revokeAccessGrants', y_config);
    }
});

SharingDetailsView.NAME = 'sharingDetailsView';
namespace.SharingDetailsView = SharingDetailsView;

}, "0.1", { "requires": [
    'node', 'selector-css3', 'lp.client', 'lp.mustache',
    'lp.registry.sharing.sharingdetails', 'lp.app.confirmationoverlay'
    ]});

