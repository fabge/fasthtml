# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['empty', 'htmx_hdrs', 'is_namedtuple', 'date', 'snake2hyphens', 'HtmxHeaders', 'RouteX', 'RouterX', 'FastHTML',
           'reg_re_param']

# %% ../nbs/00_core.ipynb 2
import json, dateutil

from fastcore.utils import *
from fastcore.xml import *

from types import UnionType, SimpleNamespace as ns
from typing import Optional, get_type_hints, get_args, get_origin, Union, Mapping
from datetime import datetime
from dataclasses import dataclass,fields,is_dataclass,MISSING,asdict
from collections import namedtuple
from inspect import isfunction,ismethod,signature,Parameter
from functools import wraps, partialmethod

from starlette.applications import Starlette
from starlette.routing import Route, Mount, Router
from starlette.responses import Response, HTMLResponse, FileResponse, JSONResponse
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette._utils import is_async_callable
from starlette.convertors import Convertor, StringConvertor, register_url_convertor, CONVERTOR_TYPES

# %% ../nbs/00_core.ipynb 4
empty = Parameter.empty

# %% ../nbs/00_core.ipynb 5
def is_namedtuple(cls):
    return issubclass(cls, tuple) and hasattr(cls, '_fields')

# %% ../nbs/00_core.ipynb 6
def date(s): return dateutil.parser.parse(s)

# %% ../nbs/00_core.ipynb 7
def snake2hyphens(s):
    s = snake2camel(s)
    return camel2words(s, '-')

# %% ../nbs/00_core.ipynb 8
htmx_hdrs = dict(
    boosted="HX-Boosted",
    current_url="HX-Current-URL",
    history_restore_request="HX-History-Restore-Request",
    prompt="HX-Prompt",
    request="HX-Request",
    target="HX-Target",
    trigger_name="HX-Trigger-Name",
    trigger="HX-Trigger")

@dataclass
class HtmxHeaders:
    boosted:str|None=None; current_url:str|None=None; history_restore_request:str|None=None; prompt:str|None=None
    request:str|None=None; target:str|None=None; trigger_name:str|None=None; trigger:str|None=None
    def __bool__(self): return any(hasattr(self,o) for o in htmx_hdrs)

def _get_htmx(req):
    res = {k:req.headers.get(v.lower(), None) for k,v in htmx_hdrs.items()}
    return HtmxHeaders(**res)

# %% ../nbs/00_core.ipynb 9
def _fix_anno(t):
    origin = get_origin(t)
    if origin is Union or origin is UnionType:
        t = first(o for o in get_args(t) if o!=type(None))
    if t==bool: return str2bool
    return t

# %% ../nbs/00_core.ipynb 10
def _form_arg(k, v, d):
    if v is None: return
    anno = d[k]
    anno = _fix_anno(anno)
    return anno(v)

# %% ../nbs/00_core.ipynb 11
def _is_body(anno):
    return issubclass(anno, (dict,ns)) or is_dataclass(anno) or is_namedtuple(anno)

def _anno2flds(anno):
    if is_dataclass(anno): return {o.name:o.type for o in fields(anno)}
    if is_namedtuple(anno): return {o:str for o in anno._fields}
    return {o.name:str for o in dict(anno)}

async def _from_body(req, arg, p):
    body = await req.form()
    anno = p.annotation
    d = _anno2flds(anno)
    cargs = {k:_form_arg(k, v, d) for k,v in body.items()}
    return anno(**cargs)

# %% ../nbs/00_core.ipynb 12
async def _find_p(req, arg:str, p):
    anno = p.annotation
    if isinstance(anno, type):
        if issubclass(anno, Request): return req
        if issubclass(anno, HtmxHeaders): return _get_htmx(req)
        if issubclass(anno, Starlette): return req.scope['app']
        if _is_body(anno): return await _from_body(req, arg, p)
    if anno is empty:
        if 'request'.startswith(arg.lower()): return req
        if arg.lower()=='htmx': return _get_htmx(req)
        if arg.lower()=='app': return req.scope['app']
        return None
    res = req.path_params.get(arg, None)
    if not res: res = req.query_params.get(arg, None)
    if not res: res = req.cookies.get(arg, None)
    if not res: res = req.headers.get(snake2hyphens(arg), None)
    if not res: res = p.default
    if res is empty: return None
    anno = _fix_anno(anno)
    if res is not None and anno is not empty: res = anno(res)
    return res

# %% ../nbs/00_core.ipynb 13
async def _wrap_req(req, params):
    return [await _find_p(req, arg, p) for arg,p in params.items()]

# %% ../nbs/00_core.ipynb 14
def _xt_resp(req, resp, hdrs, **bodykw):
    if resp and 'hx-request' not in req.headers and isinstance(resp,tuple) and resp[0][0] not in ('!doctype','html'):
        title,bdy = resp
        if isinstance(title,str): title=Title(title)
        resp = Html(Header(title, *hdrs), Body(bdy, **bodykw))
    return HTMLResponse(to_xml(resp))

# %% ../nbs/00_core.ipynb 15
def _wrap_resp(req, resp, cls, hdrs, **bodykw):
    if isinstance(resp, Response): return resp
    if cls is not empty: return cls(resp)
    if isinstance(resp, (list,tuple)): return _xt_resp(req, resp, hdrs, **bodykw)
    if isinstance(resp, str): cls = HTMLResponse 
    elif isinstance(resp, Mapping): cls = JSONResponse 
    else:
        resp = str(resp)
        cls = HTMLResponse
    return cls(resp)

# %% ../nbs/00_core.ipynb 16
def _wrap_ep(f, hdrs, **bodykw):
    if not (isfunction(f) or ismethod(f)): return f
    sig = signature(f)
    params = sig.parameters
    cls = sig.return_annotation

    async def _f(req):
        wreq = await _wrap_req(req, params)
        resp = f(*wreq)
        if is_async_callable(f): resp = await resp
        return _wrap_resp(req, resp, cls, hdrs, **bodykw)
    return _f

# %% ../nbs/00_core.ipynb 17
class RouteX(Route):
    def __init__(self, path:str, endpoint, *, methods=None, name=None, include_in_schema=True, middleware=None,
                hdrs=None, **bodykw):
        super().__init__(path, _wrap_ep(endpoint, hdrs, **bodykw), methods=methods, name=name,
                         include_in_schema=include_in_schema, middleware=middleware)

# %% ../nbs/00_core.ipynb 18
class RouterX(Router):
    def __init__(self, routes=None, redirect_slashes=True, default=None, on_startup=None, on_shutdown=None,
                 lifespan=None, *, middleware=None, hdrs=None, **bodykw):
        super().__init__(routes, redirect_slashes, default, on_startup, on_shutdown,
                 lifespan=lifespan, middleware=middleware)
        self.hdrs,self.bodykw = hdrs or (),bodykw

    def add_route( self, path: str, endpoint: callable, methods=None, name=None, include_in_schema=True):
        route = RouteX(path, endpoint=endpoint, methods=methods, name=name, include_in_schema=include_in_schema,
                      hdrs=self.hdrs, **self.bodykw)
        self.routes.append(route)

# %% ../nbs/00_core.ipynb 19
class FastHTML(Starlette):
    def __init__(self, debug=False, routes=None, middleware=None, exception_handlers=None,
                 on_startup=None, on_shutdown=None, lifespan=None, hdrs=None, **bodykw):
        super().__init__(debug, routes, middleware, exception_handlers, on_startup, on_shutdown, lifespan=lifespan)
        self.router = RouterX(routes, on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan, hdrs=hdrs, **bodykw)

    def route(self, path:str, methods=None, name=None, include_in_schema=True):
        if isinstance(methods,str): methods=[methods]
        def f(func):
            self.router.add_route(path, func, methods=methods, name=name, include_in_schema=include_in_schema)
            return func
        return f

for o in 'get post put delete patch head trace options'.split():
    setattr(FastHTML, o, partialmethod(FastHTML.route, methods=o.capitalize()))

# %% ../nbs/00_core.ipynb 20
def reg_re_param(m, s):
    cls = get_class(f'{m}Conv', sup=StringConvertor, regex=s)
    register_url_convertor(m, cls())

# Starlette doesn't have the '?', so it chomps the whole remaining URL
reg_re_param("path", ".*?")
