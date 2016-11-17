import os
import re

semantic_path = './puppetboard/static/Semantic-UI-2.1.8'


def test_semantic_patched():
    file = open(semantic_path + '/semantic.min.css', 'r')
    fc = file.read()
    m = re.search('url\(http', fc)
    assert m is None, 'found semantic.min.css references external http import'


def test_fonts_css():
    file = open(semantic_path + '/fonts.css', 'r')
    fc = file.read()
    m = re.search('url\(http', fc)
    assert m is None, 'found external font references'


def ensure_offline_fonts():
    fonts = ['bold', 'bolditalic', 'italic', 'regular']
    for font in fonts:
        font_path = semantic_path + '/fonts/lato-' + font + '.tff'
        font_path_exists = os.path.exists(font_path)
        assert font_path_exists, 'font file missing: ' + font_path
