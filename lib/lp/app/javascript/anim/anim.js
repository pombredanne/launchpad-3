/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI.add('lazr.anim', function(Y) {

Y.namespace('lazr.anim');

/**
 * @function flash_in
 * @description Create a flash-in animation object.  Dynamically checks
 * the 'to' property to see that the node's color isn't "transparent".
 * @param cfg Additional Y.Anim configuration.
 * @return Y.Anim instance
 */
Y.lazr.anim.flash_in = function(cfg) {
    var acfg = Y.merge(Y.lazr.anim.flash_in.defaults, cfg);
    var anim = new Y.lazr.anim.Anim(acfg);

    return anim;
};

Y.lazr.anim.flash_in.defaults = {
    duration: 1,
    easing: Y.Easing.easeIn,
    from: { backgroundColor: '#FFFF00' },
    to: { backgroundColor: '#FFFFFF' }
};



/**
 * @function green_flash
 * @description A green flash and fade, used to indicate new page data.
 * @param cfg Additional Y.Anim configuration.
 * @return Y.Anim instance
 */
Y.lazr.anim.green_flash = function(cfg) {
    return Y.lazr.anim.flash_in(
        Y.merge(Y.lazr.anim.green_flash.defaults, cfg));
};

Y.lazr.anim.green_flash.defaults = {
    from: { backgroundColor: '#90EE90' }
};


/**
 * @function red_flash
 * @description A red flash and fade, used to indicate errors.
 * @param cfg Additional Y.Anim configuration.
 * @return Y.Anim instance
 */
Y.lazr.anim.red_flash = function(cfg) {
    return Y.lazr.anim.flash_in(
        Y.merge(Y.lazr.anim.red_flash.defaults, cfg));
};

Y.lazr.anim.red_flash.defaults = {
    from: { backgroundColor: '#FF6666' }
};

var resolveNodeListFrom = function(protonode) {
    if (typeof protonode === 'string') {
        // selector
        return Y.all(protonode);
    } else if (protonode._node !== undefined) {
        // Node
        return new Y.NodeList([protonode]);
    } else if (protonode._nodes !== undefined) {
        // NodeList
        return protonode;
    }

    throw('Not a selector, Node, or NodeList');
};

/*
 * The Anim widget similar to Y.anim.Anim, but supports operating on a NodeList
 *
 * @class Anim
 */
Anim = function(cfg) {
   var nodelist = resolveNodeListFrom(cfg.node);
   this._anims = [];
   var self = this;
   var config = cfg;
   Y.each(nodelist,
          function(n) {
              var ncfg = Y.merge(config, {node: n});
              var anim = new Y.Anim(ncfg);
              // We need to validate the config
              // afterwards because some of the
              // properties may be dynamic.
              var to = ncfg.to;

              // Check the background color to make sure
              // it isn't 'transparent'.
              if (to && typeof to.backgroundColor === 'function') {
                  var bg = to.backgroundColor.call(
                      anim, anim.get('node'));
                  if (bg == 'transparent') {
                      Y.error("Can not animate to a 'transparent' background " +
                             "in '" + anim + "'");
                  }
              }

              // Reset the background color. This is
              // normally only necessary when the
              // original background color of the node
              // or its parent are not white, since we
              // normally fade to white.
              var original_bg = null;
              anim.on('start', function () {
                          original_bg = anim.get('node').getStyle('backgroundColor');
                      });
              anim.on('end', function () {
                          anim.get('node').setStyle('backgroundColor', original_bg);
                      });

              self._anims.push(anim);
          }
         );
};

Anim.prototype = {
    run: function() {
        // delegate all behavior back to our collection of Anims
        Y.each(this._anims,
               function(n) {
                   n.run();
               }
              );
    },

    on: function() {
        // delegate all behavior back to our collection of Anims
        var args = arguments;
        Y.each(this._anims,
               function(n) {
                   n.on.apply(n, args);
               }
              );
    }
};

Y.lazr.anim.Anim = Anim;
Y.lazr.anim.resolveNodeListFrom = resolveNodeListFrom;

}, "0.1", {"requires":["base", "node", "anim"]});
