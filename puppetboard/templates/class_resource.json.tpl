{%- import '_macros.html' as macros -%}
{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {% for report_hash, node in nodes_data.items() -%}
      {%- if not loop.first %},{%- endif -%}
      [
        {% filter jsonprint %}<a href="{{ url_for('node', env=current_env, node_name=node.node_name) }}">{{ node.node_name }}</a>{% endfilter %},
        {% filter jsonprint %}<a class="ui {{ node.node_status }} label status" href="{{url_for('report', env=current_env, node_name=node.node_name, report_id=node.report_hash)}}">{{ node.node_status|upper }}</a>{% endfilter %},
        {% filter jsonprint %}<a class="ui {{ node.class_status }} label status" href="{{url_for('report', env=current_env, node_name=node.node_name, report_id=node.report_hash)}}#events">{{ node.class_status|upper }}</a>{% endfilter %}
      ]
    {% endfor -%}
  ]
}
