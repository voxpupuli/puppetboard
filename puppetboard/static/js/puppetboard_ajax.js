function puppetboard_ajax_get_fact_names(start, end)
{
	if (lock_extend != true)
	{
		lock_extend = true;
		
		$.ajax({
	    url: 'facts/' + start + '/' + end,
	    success: function(return_content) {
			content = $(return_content).find('.fact_listing table');
			$('.fact_listing').append(content);
			
			// If no results are returned, interval timer and button will be disabled
			var test = $(content).find('li');
			if ($(content).find('li').length == 0)
			{
				$('#extend_button').remove();
				clearInterval(interval_check_list_extension);
			}
			
			var new_start_value = end + 1;
			var new_end_value	= new_start_value + 1000;
			
			jQuery('#extend_button').unbind('click');
			jQuery('#extend_button').click(function(){
			  puppetboard_ajax_get_fact_names(new_start_value, new_end_value);
			});
			lock_extend = false
	    }
	  });
	}
}

function puppetboard_ajax_search_fact_names (search_string, force)
{
	if (search_string == '')
	{
		window.location.replace("facts");
	}

	if (lock_search != true || force == true)
	{
		lock_search = true;
		$('#extend_button').remove();
		clearInterval(interval_check_list_extension);
		
		$.ajax({
		url: 'facts/search/' + search_string,
		success: function(return_content) {
			content = $(return_content).find('.fact_listing table');
			$('.fact_listing').html(content);
			
			var current_search_value = $('.filter-list').val();
			if (current_search_value != search_string)
			{
				puppetboard_ajax_search_fact_names (current_search_value, true);
			}
			lock_search = false;
		}
		});
	}
}