$ = jQuery
$ ->
  $('.ui.dropdown.item').dropdown(
    onChange: (value, text) ->
      window.location.href = value
  )
