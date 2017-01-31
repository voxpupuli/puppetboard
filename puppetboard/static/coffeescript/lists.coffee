$ = jQuery
filter_list = (val) ->
  rex = new RegExp(val, "i")
  $(".searchable li").hide()
  $(".searchable li").parent().parent('.list_hide_segment').hide()
  $(".searchable li").filter( ->
    rex.test $(this).text()
  ).show()
  $(".searchable li").filter( ->
    rex.test $(this).text()
  ).parent().parent().show()
$("input.filter-list").on "keyup", (e) ->
  # If key is escape, reset value
  if e.keyCode is 27
    $(e.currentTarget).val ""
    ev = $.Event("keyup")
    ev.keyCode = 13
    $(e.currentTarget).trigger(ev)
    e.currentTarget.blur()
  else
    filter_list($(this).val())
$("input.filter-list").ready ->
  elem = $("input.filter-list")
  elem.focus()
  val = elem.val()
  filter_list(val)
  # Force cursor at the end
  elem.val('').val(val)
