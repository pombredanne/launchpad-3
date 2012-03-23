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
        value: null;
    },

    branch_details_row_template: {
        value: null;
    },

    bug_details: {
        value: [];
    },

    branch_details: {
        value: [];
    }
};
Y.extend(SharingDetailsTable, Y.Widget, {

    initializer: function(config) {}

    _bug_details_row_template: function() {
        return [].join(' ');
    },

    _branch_details_row_template: function() {
        return [
        '<tr>',
        '    <td colspan="3">',
        '        <a class="sprite branch" href="{{ branch_link }}">
        '            {{ branch_name }}',
        '        </a>',
        '    </td>',
        '    <td>--</td>',
        '    <td class="actions" id="remove-button-{{ branch_id }}">',
        '        <a class="sprite remove" href="#"',
        '            title="Unshare this with the user"></a>',
        '    </td>',
        '</tr>'
        ].join(' ');
    },
});

SharingDetailsTable.NAME = 'SharingDetailsTable';
namespace.SharingDetailsTable = SharingDetailsTable;

}, "0.1", { "requires": [
    'node',
    'lp.mustache'
] });
