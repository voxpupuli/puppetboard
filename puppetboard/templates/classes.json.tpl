{%- import '_macros.html' as macros -%}
{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {% for class in classes_data -%}
      {%- if not loop.first %},{%- endif -%}
      [
        {% filter jsonprint %}<a href="{{ url_for('class_resource', env=current_env, class_name=class) }}">{{ class }}</a>{% endfilter %},
        {% filter jsonprint %}<span class="ui small count label nodes total">{{ classes_data[class]['nb_nodes'] }}</span>{% endfilter %},
        {%- for column in columns -%}
          {%- if not loop.first %},{%- endif -%}
          {%- if column in classes_data[class]['nb_nodes_per_class_status'] -%}
            {{ macros.event_status_counts(status=column, count=classes_data[class]['nb_nodes_per_class_status'][column]) | jsonprint }}
          {%- else -%}
            ""
          {%- endif -%}
        {%- endfor -%}
      ]
    {% endfor -%}
  ]
}
