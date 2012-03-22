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

SharingDetailsTable.ATTRS = {};
Y.extend(SharingDetailsTable, Y.Widget, {

    initializer: function(config) {},

SharingDetailsTable.NAME = 'SharingDetailsTable';
namespace.SharingDetailsTable = SharingDetailsTable;

}, "0.1", { "requires": [
    'node',
    'lp.mustache'
] });
