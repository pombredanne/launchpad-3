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

SharingDetailsTable.ATTRS = {
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
        value: []
    },

    branches: {
        value: []
    },

    write_enabled: {
        value: false
    },

    person_uri: {
        value: null
    },

    person_name: {
        value: null
    },

    pillar_uri: {
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
                node.addClass('unseen');
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
            var person_uri = self.get('person_uri');
            var person_name = self.get('person_name');
            var pillar_uri = self.get('pillar_uri');
            self.fire(
                REMOVE_GRANT, delete_link, person_uri, person_name, pillar_uri,
                artifact_uri, artifact_name);
        }, 'span[id^=remove-] a');
     },

    _table_body_template: function() {
        return [
        '<tbody id="sharing-table-body">',
        '{{#branches}}',
        '{{> branch}}',
        '{{/branches}}',
        '{{#bugs}}',
        '{{> bug}}',
        '{{/bugs}}',
        '</tbody>'
        ].join(' ');
    },

    _bug_details_row_template: function() {
        return [
        '<tr id="shared-bug-{{ bug_id }}">',
        '    <td class="icon right">',
        '        <span class="sprite bug-{{bug_importance}}"></span>',
        '    </td>',
        '    <td class="amount">{{bug_id}}</td>',
        '    <td>',
        '        <a href="{{web_link}}">{{bug_summary}}</a>',
        '    </td>',
        '    <td class="action-icons nowrap">',
        '    <span id="remove-bug-{{ bug_id }}">',
        '    <a class="sprite remove" href="#"',
        '        title="Unshare bug {{bug_id}} with {{displayname}}"',
        '        data-self_link="{{self_link}}" data-name="Bug {{bug_id}}">',
        '    &nbsp;</a>',
        '    </span>',
        '    </td>',
        '</tr>'
        ].join(' ');
    },

    _branch_details_row_template: function() {
        return [
        '<tr id="shared-branch-{{ branch_id }}">',
        '    <td colspan="3">',
        '        <a class="sprite branch" href="{{web_link}}">',
        '            {{branch_name}}',
        '        </a>',
        '    </td>',
        '    <td class="action-icons nowrap">',
        '    <span id="remove-branch-{{branch_id}}">',
        '    <a class="sprite remove" href="#"',
        '        title="Unshare branch {{branch_name}} with {{displayname}}"',
        '        data-self_link="{{self_link}}" data-name="{{branch_name}}">',
        '    &nbsp;</a>',
        '    </span>',
        '    </td>',
        '</tr>'
        ].join(' ');
    }
});

SharingDetailsTable.NAME = NAME;
SharingDetailsTable.REMOVE_GRANT = REMOVE_GRANT;

namespace.SharingDetailsTable = SharingDetailsTable;

}, "0.1", { "requires": [
    'node', 'event',
    'lp.mustache'
] });
