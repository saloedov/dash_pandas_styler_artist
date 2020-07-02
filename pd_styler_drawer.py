import sys

import dash_bootstrap_components as dbc
import dash_html_components as html
import pandas as pd
from lxml import etree
from lxml.cssselect import CSSSelector
from cssselect.parser import parse
from pandas.io.formats.style import Styler


def str_to_class(str):
    return getattr(sys.modules['dash_html_components'], str)


def parse_val(**kwargs):
    tag = kwargs.get('type')
    tag = tag[0].upper() + tag[1:]

    value = kwargs.get('value')
    display_value = kwargs.get('display_value', str(value))
    className = kwargs.get('class')

    style = kwargs.get('style')

    attributes = kwargs.get('attributes')

    attr = {}

    if attributes:
        for attribute in attributes:
            name, val = attribute.split('=')
            name = name.replace('span', 'Span')
            attr[name] = val

    return str_to_class(tag)(className=className, children=display_value, style=style, **attr)


def parse_styles(styles_list):
    styles_map = {}

    for style in styles_list:
        selector = style.get('selector')
        if ':' in selector:
            # not supported
            continue

        not_used_props = ('height', 'width')

        props = {prop[0].strip(): prop[1].strip() for prop in style.get('props')}
        props = {prop: val for prop, val in props.items() if prop not in not_used_props}
        props = {prop: val.replace('linear-gradient(90deg,', '-webkit-linear-gradient(left, transparent,') for
                 prop, val in props.items()}

        if len(props) > 0:
            sel = CSSSelector(selector)
            styles_map[sel] = props

    return styles_map


def render_style(style: Styler, **kwargs):
    style._compute()
    d = style._translate()

    cell_styles = [x for x in d.pop('cellstyle') if any(any(y) for y in x["props"])]
    for cs in cell_styles:
        cs['selector'] = '.' + cs['selector'].replace('_', '.')
    cell_style_map = parse_styles(cell_styles)

    table_styles = d.pop('table_styles')
    table_style_map = parse_styles(table_styles)

    uuid = d.pop('uuid')

    """
    # will not be used (table component arguments could be used instead)
    table_attributes = d.pop('table_attributes') 
    # will not be used (small text after table could be done with bootstrap components)
    caption = d.pop('caption')
    # not used in template renderer at all
    precision = d.pop('precision')
    """

    def apply_styles(column):
        # style priority (high to low):
        # 0. original cell style
        # 1. styles from 'cellstyle'
        # 2. styles from 'table_styles'
        tag_name = column.get('type', '')
        classes_str = column.get('class', '')
        origin_style = column.get('style', {})
        tag = f'<{tag_name} class="{classes_str}"></{tag_name}>'
        element_tag = etree.fromstring(tag)

        styles_from_cell_style = [props for sel, props in cell_style_map.items() if sel(element_tag)]
        styles_from_table_style = [props for sel, props in table_style_map.items() if sel(element_tag)]

        res_styles = {}
        for style in styles_from_table_style:
            res_styles.update(style)
        for style in styles_from_cell_style:
            res_styles.update(style)
        for style in origin_style:
            if type(style) is dict:
                res_styles.update(style)

        column['style'] = res_styles

        return column

    head = []
    for row in d.pop('head'):
        row_content = []
        for column in filter(lambda c: c.get('is_visible', True), row):
            column = apply_styles(column)

            el = parse_val(**column)

            row_content.append(el)
        head.append(html.Tr(row_content))
    head = html.Thead(head)

    body = []
    for row in d.pop('body'):
        row_content = []
        for column in filter(lambda c: c.get('is_visible', False), row):
            column = apply_styles(column)

            el = parse_val(**column)

            row_content.append(el)
        body.append(html.Tr(row_content))
    body = html.Tbody(body)

    return dbc.Table([head, body],
                     id=kwargs.pop('id', uuid),
                     bordered=kwargs.pop('bordered', True),
                     striped=kwargs.pop('striped', False),
                     **kwargs)


if __name__ == '__main__':
    df = pd.DataFrame({
        'a': [1, 1, 1, 1, 1, 1, 1, 1, 1],
        'b': [1, 1, 1, 2, 2, 2, 3, 3, 3],
        'c': [1, 1, 1, 1, 1, 1, 1, 1, 1],
        'd': [1, 1, 1, 2, 2, 2, 3, 3, 3],
        'e': [1, 2, 3, 4, 5, 6, 7, 8, 9],
    })

    plt_df = df.pivot_table(index=['a', 'b'], columns=['c', 'd'], values='e', aggfunc='sum').fillna(999)

    style = plt_df.style

    style = style.format(lambda r: f'{r:,.0f}'.replace(',', ' '), subset=['c'])
    style = style.bar(subset=['d'])

    idx = plt_df.index.get_level_values(0)
    idx_unique = idx.unique().tolist()
    from seaborn import color_palette

    pal = color_palette('pastel', len(idx_unique)).as_hex()
    styles = [{'selector': f'th.row{i}', 'props': [('background-color', pal[idx_unique.index(x)])]} for i, x in
              enumerate(idx)]
    style.set_table_styles(styles)

    print(render_style(style))
