/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Distroseries related stuff.
 *
 * @module Y.lp.registry.distroseries
 * @requires node, DOM
 */
YUI.add('lp.registry.distroseries.initseries', function(Y) {

Y.log('loading lp.registry.distroseries.initseries');

var namespace = Y.namespace('lp.registry.distroseries.initseries');

var ArchitecturesChoice = function() {
    ArchitecturesChoice.superclass.constructor.apply(this, arguments);
};

Y.mix(ArchitecturesChoice, {

    NAME: 'architecturesChoice',

    ATTRS: {
        fieldName: {
            setter: function(value, name) {
                // XXX This is not updating "for" on the label!
                this.get("labelNode").set("for", value);
                this.get("fieldNode").all("input").set("name", value);
                return value;
            }
        },
        label: {
            setter: function(value, name) {
                this.get("labelNode").set("text", value);
                return value;
            }
        },
        labelNode: {
            valueFn: function() {
                return Y.Node.create("<label />")
                    .set("text", "Architectures");
            }
        },
        fieldNode: {
            valueFn: function() {
                return Y.Node.create("<div><input /></div>")
                    .append("i386")
                    .one("input")
                        .set("type", "checkbox")
                        .set("value", "i386")
                    .ancestor();
            }
        },
        description: {
            setter: function(value, name) {
                this.get("descriptionNode").set("text", value);
                return value;
            }
        },
        descriptionNode: {
            valueFn: function() {
                return Y.Node.create("<p />")
                    .set("class", "formHelp")
                    .set("text", "Select some stuff.");
            }
        }
    }

});

Y.extend(ArchitecturesChoice, Y.Widget, {

    BOUNDING_TEMPLATE: "<tr></tr>",

    CONTENT_TEMPLATE: '<td colspan="2"></td>',

    /**
     * Implementation of Widget.renderUI.
     *
     * This adds the widget row to the form table.
     *
     * @method renderUI
     */
    renderUI: function() {
        this.get("contentBox")
            .append(this.get("labelNode"))
            .append(this.get("fieldNode"))
            .append(this.get("descriptionNode"));
    }

});

namespace.ArchitecturesChoice = ArchitecturesChoice;

namespace.setup = function() {
    var form_table = Y.one(
        "[name=field.derived_from_series]").ancestor("tbody");
    var architecture_choice = new namespace.ArchitecturesChoice()
        .set("fieldName", "field.architectures")
        .set("description", "This is a custom description.")
        .render(form_table);
};

}, "0.1", {"requires": ["node", "dom", "io", "widget"]});
