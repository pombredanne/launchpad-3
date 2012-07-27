/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Sharing details widget
 *
 * @module lp.registry.sharing.sharingdetails
 */

YUI.add('lp.registry.sharing.sharingdetails', function(Y) {

var namespace = Y.namespace('lp.registry.sharing.sharingdetails');

var
    NAME = "sharingDetailsTable",
    // Events
    REMOVE_GRANT = 'removeGrant';

/*
 * Sharing details table widget.
 * This widget displays the details of a specific person's shared artifacts.
 */
function SharingDetailsTable(config) {
    SharingDetailsTable.superclass.constructor.apply(this, arguments);
}

var clone_data = function(value) {
    if (!Y.Lang.isArray(value)) {
        return value;
    }
    return Y.JSON.parse(Y.JSON.stringify(value));
};

SharingDetailsTable.ATTRS = {
    // The duration for various animations eg row deletion.
    anim_duration: {
        value: 1
    },
    // The node holding the details table.
    details_table_body: {
        getter: function() {
            return Y.one('#sharing-table-body');
        }
    },
    table_body_template: {
        value: null
    },

    bug_details_row_template: {
        value: null
    },

    branch_details_row_template: {
        value: null
    },

    bugs: {
        value: [],
        // We clone the data passed in so external modifications do not
        // interfere.
        setter: clone_data
    },

    branches: {
        value: [],
        // We clone the data passed in so external modifications do not
        // interfere.
        setter: clone_data
    },

    write_enabled: {
        value: false
    },

    person_name: {
        value: null
    }
};

Y.extend(SharingDetailsTable, Y.Widget, {

    initializer: function(config) {
        this.set(
            'bug_details_row_template',
            this._bug_details_row_template());

        this.set(
            'branch_details_row_template',
            this._branch_details_row_template());

        this.set(
            'table_body_template',
            this._table_body_template());
        this.publish(REMOVE_GRANT);
    },

    renderUI: function() {
        var branch_data = this.get('branches');
        var bug_data = this.get('bugs');
        if (bug_data.length === 0 && branch_data.length === 0) {
            return;
        }
        var partials = {
            branch: this.get('branch_details_row_template'),
            bug: this.get('bug_details_row_template')
        };
        var template = this.get('table_body_template');
        var html = Y.lp.mustache.to_html(
            template,
            {branches: branch_data, bugs: bug_data,
            displayname: this.get('person_name')},
            partials);

        var details_table_body = this.get('details_table_body');
        var table_body_node = Y.Node.create(html);
        details_table_body.replace(table_body_node);
        this._update_editable_status();
    },

    _update_editable_status: function() {
        var details_table_body = this.get('details_table_body');
        if (!this.get('write_enabled')) {
            details_table_body.all('.sprite.remove').each(function(node) {
                node.addClass('hidden');
            });
        }
    },

     bindUI: function() {
        // Bind the delete links.
        if (!this.get('write_enabled')) {
            return;
        }
        var details_table_body = this.get('details_table_body');
        var self = this;
        details_table_body.delegate('click', function(e) {
            e.halt();
            var delete_link = e.currentTarget;
            var artifact_uri = delete_link.getAttribute('data-self_link');
            var artifact_name = delete_link.getAttribute('data-name');
            var artifact_type = delete_link.getAttribute('data-type');
            self.fire(
                REMOVE_GRANT, delete_link, artifact_uri, artifact_name,
                artifact_type);
        }, 'span[id^=remove-] a');
     },

    /**
     * If the artifact with id exists in the model, return it.
     * @param artifact_id
     * @param id_property
     * @param model
     * @return {*}
     * @private
     */
    _get_artifact_from_model: function(artifact_id, id_property, model) {
        var artifact = null;
        Y.Array.some(model, function(item) {
            if (item[id_property] === artifact_id) {
                artifact = item;
                return true;
            }
            return false;
        });
        return artifact;
    },

    branch_sort_key: function(cell, default_func) {
        // Generate the sort key for branches.
        return 'BRANCH:' + default_func(cell, true);
    },

    syncUI: function() {
        // Examine the widget's data model and delete any artifacts which have
        // been removed.
        var existing_bugs = this.get('bugs');
        var existing_branches = this.get('branches');
        var model_bugs = LP.cache.bugs;
        var model_branches = LP.cache.branches;
        var deleted_bugs = [];
        var deleted_branches = [];
        var self = this;
        Y.Array.each(existing_bugs, function(bug) {
            var model_bug =
                self._get_artifact_from_model(
                    bug.bug_id, 'bug_id', model_bugs);
            if (!Y.Lang.isValue(model_bug)) {
                deleted_bugs.push(bug);
            }
        });
        Y.Array.each(existing_branches, function(branch) {
            var model_branch =
                self._get_artifact_from_model(
                    branch.branch_id, 'branch_id', model_branches);
            if (!Y.Lang.isValue(model_branch)) {
                deleted_branches.push(branch);
            }
        });
        if (deleted_bugs.length > 0 || deleted_branches.length > 0) {
            this.delete_artifacts(
                deleted_bugs, deleted_branches,
                model_bugs.length === 0 && model_branches.length === 0);
        }
        this.set('bugs', model_bugs);
        this.set('branches', model_branches);
        Y.lp.app.sorttable.SortTable.registerSortKeyFunction(
            'branchsortkey', this.branch_sort_key);
        Y.lp.app.sorttable.SortTable.init(true);
    },

    // Delete the specified grantees from the table.
    delete_artifacts: function(bugs, branches, all_rows_deleted) {
        var deleted_row_selectors = [];
        var details_table_body = this.get('details_table_body');
        Y.Array.each(bugs, function(bug) {
            var selector = 'tr[id=shared-bug-' + bug.bug_id + ']';
            var table_row = details_table_body.one(selector);
            if (Y.Lang.isValue(table_row)) {
                deleted_row_selectors.push(selector);
            }
        });
        Y.Array.each(branches, function(branch) {
            var selector = 'tr[id=shared-branch-' + branch.branch_id + ']';
            var table_row = details_table_body.one(selector);
            if (Y.Lang.isValue(table_row)) {
                deleted_row_selectors.push(selector);
            }
        });
        if (deleted_row_selectors.length === 0) {
            return;
        }
        var rows_to_delete = details_table_body.all(
            deleted_row_selectors.join(','));
        var delete_rows = function() {
            rows_to_delete.remove(true);
            if (all_rows_deleted === true) {
                details_table_body
                    .appendChild('<tr></tr>')
                    .appendChild('<td colspan="3"></td>')
                    .setContent("There are no shared bugs or branches.");
            }
        };
        var anim_duration = this.get('anim_duration');
        if (anim_duration === 0 ) {
            delete_rows();
            return;
        }
        var anim = Y.lp.anim.green_flash(
            {node: rows_to_delete, duration:anim_duration});
        anim.on('end', function() {
            delete_rows();
        });
        anim.run();
    },

    // An error occurred performing an operation on an artifact.
    display_error: function(artifact_id, artifact_type, error_msg) {
        var details_table_body = this.get('details_table_body');
        var selector = Y.Lang.substitute(
            'tr[id=shared-{artifact_type}-{artifact_id}]', {
                artifact_type: artifact_type,
                artifact_id: artifact_id});
        var artifact_row = details_table_body.one(selector);
        Y.lp.app.errors.display_error(artifact_row, error_msg);
    },

    _table_body_template: function() {
        return [
        '<tbody id="sharing-table-body">',
        '{{#bugs}}',
        '{{> bug}}',
        '{{/bugs}}',
        '{{#branches}}',
        '{{> branch}}',
        '{{/branches}}',
        '</tbody>'
        ].join(' ');
    },

    _bug_details_row_template: function() {
        return [
        '<tr id="shared-bug-{{ bug_id }}">',
        '    <td>',
        '        <span class="sortkey">{{bug_id}}</span>',
        '        <span class="sprite bug-{{bug_importance}}">{{bug_id}}</span>',
        '        <a href="{{web_link}}">{{bug_summary}}</a>',
        '    </td>',
        '    <td class="action-icons nowrap">',
        '    <span id="remove-bug-{{ bug_id }}">',
        '    <a class="sprite remove action-icon" href="#"',
        '        title="Unshare bug {{bug_id}} with {{displayname}}"',
        '        data-self_link="{{self_link}}" data-name="Bug {{bug_id}}"',
        '        data-type="bug">Remove</a>',
        '    </span>',
        '    </td>',
        '   <td>',
        '   <span class="information_type">',
        '  {{information_type}}',
        '   </span>',
        '   </td>',
        '</tr>'
        ].join(' ');
    },

    _branch_details_row_template: function() {
        return [
        '<tr id="shared-branch-{{ branch_id }}">',
        '    <td>',
        '        <span class="sortkey">sorttable_branchsortkey</span>',
        '        <a class="sprite branch" href="{{web_link}}">',
        '            {{branch_name}}',
        '        </a>',
        '    </td>',
        '    <td class="action-icons nowrap">',
        '    <span id="remove-branch-{{branch_id}}">',
        '    <a class="sprite remove action-icon" href="#"',
        '        title="Unshare branch {{branch_name}} with {{displayname}}"',
        '        data-self_link="{{self_link}}" data-name="{{branch_name}}"',
        '        data-type="branch">Remove</a>',
        '    </span>',
        '    </td>',
        '   <td>',
        '   <span class="information_type">',
        '  {{information_type}}',
        '   </span>',
        '   </td>',
        '</tr>'
        ].join(' ');
    }
});

SharingDetailsTable.NAME = NAME;
SharingDetailsTable.REMOVE_GRANT = REMOVE_GRANT;

namespace.SharingDetailsTable = SharingDetailsTable;

}, "0.1", { "requires": [
    'node', 'event', 'json', 'lp.mustache', 'lp.anim',
    'lp.app.sorttable', 'lp.app.errors'
] });
