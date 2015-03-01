(function ($) {

$.fn.photoResize = function (options) {

var element	= $(this),
defaults = {
bottomSpacing: 10
};

$(element).load(function () {
updatePhotoHeight();

$(window).bind('resize', function () {
updatePhotoHeight();
});
});

options = $.extend(defaults, options);

function updatePhotoHeight() {
var o = options;
oldHeight = $(element).get(0).clientHeight;
oldWidth = $(element).get(0).clientWidth;

if(oldHeight > oldWidth) {
    var photoHeight = $(window).height();
    $(element).attr('height', photoHeight - o.bottomSpacing);
} else {
    var photoWidth = $(window).width();
    $(element).attr('width', photoWidth);
}
}
};

}(jQuery));
