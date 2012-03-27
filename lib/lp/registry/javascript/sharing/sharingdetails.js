
/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Share details table widget.
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

    initializer: function(config) {},

    _bug_details_row_template: function() {
        return [
            '<tr id="bug-row-{{ bug-id }}">',
            '   <td width="20">',
            '       <img src="html_files/bug-high.png">&nbsp;',
            '   </td>',
            '   <td class="bugnr">{{ bug_number }}</td>',
            '   <td class="buglink">',
            '       <a href="#">{{ bug_summary }}</a>',
            '   </td>',
            '   <td>',
            '       <a class="sprite team" href="#">{{ via }}</a>',
            '   </td>',
            '   <td class="actions"> ',
            '       <a href="#">View shared items</a>',
            '   </td>',
            '</tr>'
        ].join(' ');
    },

    _branch_details_row_template: function() {
        return [].join(' ');
    }
});

SharingDetailsTable.NAME = 'SharingDetailsTable';
namespace.SharingDetailsTable = SharingDetailsTable;

}, "0.1", { "requires": [
    'node',
    'lp.mustache'
] });
