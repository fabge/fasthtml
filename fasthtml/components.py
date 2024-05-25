# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_components.ipynb.

# %% auto 0
__all__ = ['named', 'html_attrs', 'hx_attrs', 'show', 'xt_html', 'xt_hx', 'set_val', 'find_inps', 'fill_form', 'fill_dataclass',
           'find_elems', 'Html', 'Head', 'Title', 'Meta', 'Link', 'Style', 'Body', 'Pre', 'Code', 'Div', 'Span', 'P',
           'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'Strong', 'Em', 'B', 'I', 'U', 'S', 'Strike', 'Sub', 'Sup', 'Hr', 'Br',
           'Img', 'Nav', 'Ul', 'Ol', 'Li', 'Dl', 'Dt', 'Dd', 'Table', 'Thead', 'Tbody', 'Tfoot', 'Tr', 'Th', 'Td',
           'Caption', 'Col', 'Colgroup', 'Form', 'Input', 'Textarea', 'Button', 'Select', 'Option', 'Label', 'Fieldset',
           'Legend', 'Details', 'Dialog', 'Summary', 'Main', 'Header', 'Footer', 'Section', 'Article', 'Aside',
           'Figure', 'Figcaption', 'Mark', 'Small', 'Iframe', 'Object', 'Embed', 'Param', 'Video', 'Audio', 'Source',
           'Canvas', 'Svg', 'Math', 'Script', 'Noscript', 'Template', 'Slot']

# %% ../nbs/01_components.ipynb 2
from html.parser import HTMLParser
from dataclasses import dataclass, asdict

from fastcore.utils import *
from fastcore.xml import *
from fastcore.meta import use_kwargs, delegates

try: from IPython import display
except ImportError: display=None

# %% ../nbs/01_components.ipynb 4
def show(xt,*rest):
    if rest: xt = (xt,)+rest
    return display.HTML(to_xml(xt))

# %% ../nbs/01_components.ipynb 5
named = set('a button form frame iframe img input map meta object param select textarea'.split())
html_attrs = 'id cls title style accesskey contenteditable dir draggable enterkeyhint hidden inert inputmode lang popover spellcheck tabindex translate'.split()
hx_attrs = 'get post put delete patch trigger target swap include select indicator push_url confirm disable replace_url on'
hx_attrs = html_attrs + [f'hx_{o}' for o in hx_attrs.split()]

# %% ../nbs/01_components.ipynb 6
def xt_html(tag: str, *c, id=None, cls=None, title=None, style=None, **kwargs):
    kwargs['id'],kwargs['cls'],kwargs['title'],kwargs['style'] = id,cls,title,style
    tag,c,kw = xt(tag, *c, **kwargs)
    if tag in named and 'id' in kw and 'name' not in kw: kw['name'] = kw['id']
    return XT([tag,c,kw])

# %% ../nbs/01_components.ipynb 7
@use_kwargs(hx_attrs, keep=True)
def xt_hx(tag: str, *c, target_id=None, **kwargs):
    if target_id: kwargs['hx_target'] = '#'+target_id
    return xt_html(tag, *c, **kwargs)

# %% ../nbs/01_components.ipynb 8
_g = globals()
_all_ = ['Html', 'Head', 'Title', 'Meta', 'Link', 'Style', 'Body', 'Pre', 'Code',
    'Div', 'Span', 'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'Strong', 'Em', 'B',
    'I', 'U', 'S', 'Strike', 'Sub', 'Sup', 'Hr', 'Br', 'Img', 'Link', 'Nav',
    'Ul', 'Ol', 'Li', 'Dl', 'Dt', 'Dd', 'Table', 'Thead', 'Tbody', 'Tfoot', 'Tr',
    'Th', 'Td', 'Caption', 'Col', 'Colgroup', 'Form', 'Input', 'Textarea',
    'Button', 'Select', 'Option', 'Label', 'Fieldset', 'Legend', 'Details', 'Dialog',
    'Summary', 'Main', 'Header', 'Footer', 'Section', 'Article', 'Aside', 'Figure',
    'Figcaption', 'Mark', 'Small', 'Iframe', 'Object', 'Embed', 'Param', 'Video',
    'Audio', 'Source', 'Canvas', 'Svg', 'Math', 'Script', 'Noscript', 'Template', 'Slot']

for o in _all_: _g[o] = partial(xt_hx, o.lower())

# %% ../nbs/01_components.ipynb 12
def set_val(tag, attr, val):
    if attr.get('type', '') in ('checkbox','radio'):
        if val: attr['checked'] = '1'
        else: attr.pop('checked', '')
    else: attr['value'] = val

# %% ../nbs/01_components.ipynb 13
def find_inps(html):
    if not html: return []
    tag,cs,attrs = html
    if tag == 'input': return [html]
    res = []
    for c in cs:
        if isinstance(c, list): res.extend(find_inps(c))
    return res

# %% ../nbs/01_components.ipynb 14
def fill_form(form, obj):
    "Modifies form in-place and returns it"
    inps = find_inps(form)
    inps = {attrs['id']:(tag,attrs) for tag,c,attrs in inps if 'id' in attrs}
    for nm,val in asdict(obj).items():
        if nm in inps:
            tag,attr = inps[nm]
            set_val(tag, attr, val)
    return form

# %% ../nbs/01_components.ipynb 16
def fill_dataclass(src, dest):
    "Modifies dataclass in-place and returns it"
    for nm,val in asdict(src).items(): setattr(dest, nm, val)
    return dest

# %% ../nbs/01_components.ipynb 18
class _FindElems(HTMLParser):
    def __init__(self, tag=None, attr=None, **props):
        super().__init__()
        self.tag,self.attr,self.props = tag,attr,props
        self.res = []

    def handle_starttag(self, tag, attrs):
        if self.tag and tag!=self.tag: return
        d = dict(attrs)
        if [k for k,v in self.props.items() if d.get(k,None)==v]:
            self.res.append(d.get(self.attr, None) if self.attr else d)

# %% ../nbs/01_components.ipynb 19
def find_elems(s:XT|str, tag=None, attr=None, **props):
    "Find elements in `s` with `tag` (if supplied) and `props`, returning `attr`"
    o = _FindElems(tag, attr, **props)
    o.feed(to_xml(s))
    return o.res
