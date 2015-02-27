jQuery(function($) {
  $(document).scroll(function() {
    if ( $(window).scrollTop() > 100 ) {
      $('#scroll-btn-top').addClass('show');
    } else {
      $('#scroll-btn-top').removeClass('show');
    }
  });

  $('#scroll-btn-top').click(function() {
    $('html, body').animate( { scrollTop: 0 }, 500 );
  });
});
