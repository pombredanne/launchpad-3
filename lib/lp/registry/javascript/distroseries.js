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

function nodeFactory(spec) {
    return function() {
        return Y.Node.create(spec);
    };
}

var CheckBoxListWidget = function() {
    CheckBoxListWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(CheckBoxListWidget, {

    NAME: 'checkBoxListWidget',

    ATTRS: {

        // Options.

        name: {
            setter: function(value, name) {
                this.get("fieldNode").all("input").set("name", value);
                return value;
            }
        },
        choices: {
            setter: function(value, name) {
                var ul = Y.Node.create("<ul />");
                Y.each(
                    value,
                    function(choice) {
                        var node = Y.Node.create(
                            "<li><input /> <label /></li>");
                        node.one("input")
                            .set("type", "checkbox")
                            .set("value", choice);
                        node.one("label")
                            .setAttribute(
                                "for", node.one("input").generateID())
                            .setStyle("font-weight", "normal")
                            .set("text", choice);
                        ul.append(node);
                    }
                );
                this.get("fieldNode").all().remove();
                this.get("fieldNode").appendChild(ul);
            }
        },
        label: {
            setter: function(value, name) {
                this.get("labelNode").set("text", value);
                return value;
            }
        },
        description: {
            setter: function(value, name) {
                this.get("descriptionNode").set("text", value);
                return value;
            }
        },

        // Nodes.

        labelNode: {
            valueFn: nodeFactory("<label />")
        },
        fieldNode: {
            valueFn: nodeFactory("<div></div>")
        },
        descriptionNode: {
            valueFn: nodeFactory('<p class="formHelp" />')
        }
    }

});

Y.extend(CheckBoxListWidget, Y.Widget, {

    BOUNDING_TEMPLATE: "<tr></tr>",

    CONTENT_TEMPLATE: '<td colspan="2"></td>',

    renderUI: function() {
        this.get("contentBox")
            .append(this.get("labelNode"))
            .append(this.get("fieldNode"))
            .append(this.get("descriptionNode"));
    }

});

namespace.CheckBoxListWidget = CheckBoxListWidget;

namespace.setup = function() {
    var form_table = Y.one(
        "[name=field.derived_from_series]").ancestor("tbody");
    var architecture_choice = new namespace.CheckBoxListWidget()
        .set("name", "field.architectures")
        .set("label", "Architectures")
        .set("choices", ["i386", "arm"])
        .set("description", (
                 "Choose the architectures you want to " +
                 "use from the parent series."))
        .render(form_table);
};

}, "0.1", {"requires": ["node", "dom", "io", "widget"]});
