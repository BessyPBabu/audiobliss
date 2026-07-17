(function ($) {
    'use strict';

    // NOTE: This file previously handled the old product-detail gallery
    // (Slick slider + elevateZoom) and cart quantity buttons. Both were
    // replaced by our own custom JS in product_details.html and cart.html
    // respectively — that code has been removed from here to avoid
    // duplicate/conflicting event bindings on the same elements.
    //
    // Only WOW.js scroll-animation init remains, since `wow fadeIn animated`
    // classes are still used across many templates (base.html, baseuser.html,
    // index.html, about.html, contact.html, user_register.html, etc.).

    new WOW().init();

})(jQuery);