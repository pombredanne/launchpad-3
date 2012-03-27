/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Sharee table widget.
 *
 * @module lp.registry.sharing.details
 */

YUI.add('lp.registry.sharing.details', function(Y) {

var namespace = Y.namespace('lp.registry.sharing.details');
/*
 * Sharing details table widget.
 * This widget displays the details of a specific person's shared artifacts.
 */
function SharingDetailsTable(config) {
    SharingDetailsTable.superclass.constructor.apply(this, arguments);
}

SharingDetailsTable.ATTRS = {

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
    }
};

Y.extend(SharingDetailsTable, Y.Widget, {

    initializer: function(config) {
        if (Y.Lang.isValue(config.branches)) {
            this.set('branches', config.branches);
        }

        this.set(
            'branch_details_row_template',
            this._branch_details_row_template());
    },

    renderUI: function() {
        var template = this.get('branch_details_row_template');
        var branch_data = this.get('branches');
        var html = Y.lp.mustache.to_html(template, {branches: branch_data});
        var table = Y.one('#sharing-table-body');
        table.set('innerHTML', html);
    },

    _bug_details_row_template: function() {
        return [].join(' ');
    },

    _branch_details_row_template: function() {
        return [
        '{{#branches}}',
        '<tr>',
        '    <td colspan="3">',
        '        <a class="sprite branch" href="{{ branch_link }}">',
        '            {{ branch_name }}',
        '        </a>',
        '    </td>',
        '    <td>&mdash;</td>',
        '    <td class="actions" id="remove-button-{{ branch_id }}">',
        '        <a class="sprite remove" href="#"',
        '            title="Unshare this with the user"></a>',
        '    </td>',
        '</tr>',
        '{{/branches}}'
        ].join(' ');
    }
});

SharingDetailsTable.NAME = 'sharingDetailsTable';

namespace.SharingDetailsTable = SharingDetailsTable;

}, "0.1", { "requires": [
    'node',
    'lp.mustache'
] });
