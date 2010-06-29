/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @module lp.translations.importqueueentry
 * @requires node, lazr.anim
 */

YUI.add('lp.translations.importqueueentry', function(Y) {

var namespace = Y.namespace('lp.translations.importqueueentry');

var fields = {'POT':
                    ['field.name', 'field.translation_domain',
                     'field.languagepack'],
              'PO':
                    ['field.potemplate', 'field.potemplate_name',
                     'field.language', 'field.variant'],
              'UNSPEC': []
             };
var nodes = {};
var last_file_type = 'UNSPEC';

function getElemById(elem_id) {
    // XXX 'elem_id' is a Zope form field, and triggers
    // YUI bug #2423101.  We'll work around it.
    return Y.one(Y.DOM.byId(elem_id));
}

function getEnclosingTR(fieldname) {
    var field = getElemById(fieldname);
    if (field === null) {
        return null;
    }
    return field.ancestor('tr');
}

function buildNodeLists() {
    for (var ftype in fields) {
        var the_class = ftype + '_row';
        Y.Array.each(fields[ftype], function(field) {
            var tr = getEnclosingTR(field);
            if (tr !== null) {
                tr.addClass(the_class);
                tr.addClass('dont_show_fields');
            }
        });
        nodes[ftype] = Y.all('.' + the_class);
    }
}

function updateCurrentFileType(file_type) {
    for (ftype in nodes) {
        // Logic has been inverted in the next line to avoid
        // breaking XHTML compliance of the template due to
        // ampersand usage.
        if (!(ftype == file_type || nodes[ftype] === null)) {
            nodes[ftype].addClass('dont_show_fields');
        }
    }
    if (nodes[file_type] !== null) {
        nodes[file_type].removeClass('dont_show_fields');
        nodes[file_type].each( function(node) {
            var anim = Y.lazr.anim.green_flash({ node: node });
            anim.run();
        });
    }
    last_file_type = file_type;
}

function initCurrentFileType(file_type) {
    // Same as updateCurrentFileType but without collapsing
    // everything and without the green flash.
    if (nodes[file_type] !== null) {
        nodes[file_type].removeClass('dont_show_fields');
    }
    last_file_type = file_type;
}

function handleFileTypeChange() {
    var file_type = this.get('value');
    if (file_type != last_file_type) {
        updateCurrentFileType(file_type);
    }
}

namespace.setup_page = function () {
    buildNodeLists();
    var file_type_field = getElemById('field.file_type');
    initCurrentFileType(file_type_field.get('value'));
    file_type_field.on('change', handleFileTypeChange);
};

}, "0.1", {"requires": ['node', 'lazr.anim']});
