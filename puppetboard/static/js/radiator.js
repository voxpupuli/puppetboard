function resizeMe() {
  var preferredHeight = 944;
  var displayHeight = $(window).height();
  var percentageHeight = displayHeight / preferredHeight;

  var preferredWidth = 1100;
  var displayWidth = $(window).width();
  var percentageWidth = displayWidth / preferredWidth;

  var newFontSize;
  if (percentageHeight < percentageWidth) {
    newFontSize = Math.floor("960" * percentageHeight) - 30;
  } else {
    newFontSize = Math.floor("960" * percentageWidth) - 30;
  }
  $("body").css("font-size", newFontSize + "%")
}

$(document).ready(function() {
    $(window).on('resize', resizeMe).trigger('resize');
})
