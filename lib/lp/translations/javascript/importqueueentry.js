/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @module lp.translations.importqueueentry
 * @requires node, lazr.anim
 */

YUI.add('lp.translations.importqueueentry', function(Y) {

var namespace = Y.namespace('lp.translations.importqueueentry');


/**
 * Groups of form fields to be visible per file type.
 * @private
 */
var field_groups = {
    'POT': ['name', 'translation_domain', 'languagepack'],
    'PO': ['potemplate', 'potemplate_name', 'language', 'variant'],
    'UNSPEC': []
};


var last_file_type = 'UNSPEC';

var hidden_field_class = 'unseen';


/**
 * Find a page element by HTML id.
 *
 * Works around a YUI bug.
 *
 * @private
 * @method getElemById
 * @param elem_id The HTML id of an element on the current page.
 * @return The DOM Node with that id, or None.
 */
function getElemById(elem_id) {
    /* XXX HenningEggers 2009-03-24: 'elem_id' is a Zope form field, and
     * triggers YUI bug #2423101.  We'll work around it.
     */
    return Y.one(Y.DOM.byId(elem_id));
}


/**
 * Find the DOM input element for a given zope field.
 * @private
 * @method getFormField
 * @param field_name Name of a zope form field.
 * @return DOM input field corresponding to the zope form field.
 */
function getFormField(field_name) {
    return getElemById('field.' + field_name);
}


/**
 * Find the table row that contains the given form field.
 * @private
 * @method getFormEntry
 * @param field_name Name of a zope form field.
 * @return DOM entry containing the entire zope form field including
 *  markup.
 */
function getFormEntry(field_name) {
    /* We're interested in the tr tag surrounding the input element that
     * Zope generated for the field.  The input element's id consists of
     * the string "field" and the field's name, joined by a dot.
     */
    var field = getFormField(field_name);
    return (field === null) ? null : field.ancestor('tr');
}


/**
 * Apply function `alteration` to the form fields for a given file type.
 * @private
 * @method alterFields
 * @param file_type Apply to fields associated with this file type.
 * @param alteration Function to run for each field; takes the field's
 *  DOM element as an argument.
 */
function alterFields(file_type, alteration) {
    var field_names = field_groups[file_type];
    if (field_names !== null) {
        Y.Array.each(field_names, function (field_name) {
            var tr = getFormEntry(field_name);
            if (tr !== null) {
                alteration(tr);
            }
        });
    }
}


/**
 * Change selected file type.
 * @private
 * @param file_type The newly selected file type.
 * @param interactively Animate the appareance of previously hidden fields.
 */
function updateCurrentFileType(file_type, interactively) {
    // Hide irrelevant fields.
    var hideElement = function (element) {
        element.addClass(hidden_field_class);
    };
    for (var group in field_groups) {
        if (group !== file_type) {
            alterFields(group, hideElement);
        }
    }

    // Reveal relevant fields.
    var showElement = function (element) {
        element.removeClass(hidden_field_class);
    };
    alterFields(file_type, function (element) {
        element.removeClass(hidden_field_class);
    });

    if (interactively) {
        // Animate revealed fields.
        var animateElement = function (element) {
            Y.lazr.anim.green_flash({node: element}).run();
        };
        alterFields(file_type, animateElement);
    }

    last_file_type = file_type;
}


/**
 * Handle change event for current file type.
 * @private
 * @method handleFileTypeChange
 */
function handleFileTypeChange() {
    var file_type = this.get('value');
    if (file_type != last_file_type) {
        updateCurrentFileType(file_type, true);
    }
}


/**
 * Set up the import-queue-entry page.
 * @method setup_page
 */
namespace.setup_page = function () {
    var file_type_field = getFormField('file_type');
    var preselected_file_type = file_type_field.get('value');
    updateCurrentFileType(preselected_file_type, false);
    file_type_field.on('change', handleFileTypeChange);
};

}, "0.1", {"requires": ['node', 'lazr.anim']});
