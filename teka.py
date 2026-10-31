#!/usr/bin/env python3
"""T+ 0.9 — typed Python-like syntax with a native C++17 backend.

Commands: python3 teka.py run|build|check|emit-cpp FILE.teka
"""
from __future__ import annotations
import argparse
import difflib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from python_style import normalize_source, NormalizeError
from standard_modules import MODULES, known_modules
from project_tools import ProjectError, create_project, project_entry, doctor

VERSION = '0.9.0'
KEYWORDS = {'let', 'var', 'fn', 'return', 'if', 'else', 'while', 'for', 'in', 'true', 'false', 'and', 'or', 'not', 'break', 'continue', 'class', 'import', 'as'}
TYPE_NAMES = {'int', 'float', 'bool', 'string', 'void', 'list'}

# Native game APIs compile directly to raylib-backed C++; they do not execute Python.
GAME_FUNCTIONS = {'game_open': (['string', 'int', 'int'], 'void'), 'game_close': ([], 'void'), 'game_running': ([], 'bool'), 'game_begin': ([], 'void'), 'game_end': ([], 'void'), 'game_clear': (['int', 'int', 'int'], 'void'), 'game_rect': (['float', 'float', 'float', 'float', 'int', 'int', 'int'], 'void'), 'game_circle': (['float', 'float', 'float', 'int', 'int', 'int'], 'void'), 'game_line': (['float', 'float', 'float', 'float', 'float', 'int', 'int', 'int'], 'void'), 'game_triangle': (['float', 'float', 'float', 'float', 'float', 'float', 'int', 'int', 'int'], 'void'), 'game_text': (['string', 'float', 'float', 'int', 'int', 'int', 'int'], 'void'), 'game_key': (['string'], 'bool'), 'game_pressed': (['string'], 'bool'), 'game_dt': ([], 'float'), 'game_time': ([], 'float'), 'game_rand': (['int', 'int'], 'int'), 'game_fps': ([], 'int'), 'game_mouse_x': ([], 'int'), 'game_mouse_y': ([], 'int')}
GAME_NATIVE_CPP = r'''#include "raylib.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
inline unsigned char tk_channel(long long c) {
    return static_cast<unsigned char>(std::max(0LL, std::min(255LL, c)));
}
inline Color tk_rgb(long long r, long long g, long long b) {
    return Color{tk_channel(r), tk_channel(g), tk_channel(b), 255};
}
inline void tk_game_open(const std::string& title, long long w, long long h) {
    SetConfigFlags(FLAG_MSAA_4X_HINT | FLAG_VSYNC_HINT);
    InitWindow(static_cast<int>(w), static_cast<int>(h), title.c_str());
    SetTargetFPS(60);
}
inline void tk_game_close() { if (IsWindowReady()) CloseWindow(); }
inline bool tk_game_running() { return !WindowShouldClose(); }
inline void tk_game_begin() { BeginDrawing(); }
inline void tk_game_end() { EndDrawing(); }
inline void tk_game_clear(long long r, long long g, long long b) { ClearBackground(tk_rgb(r,g,b)); }
inline void tk_game_rect(double x, double y, double w, double h, long long r,long long g,long long b) {
    DrawRectangleRec(Rectangle{static_cast<float>(x),static_cast<float>(y),
        static_cast<float>(w),static_cast<float>(h)},tk_rgb(r,g,b));
}
inline void tk_game_circle(double x,double y,double radius,long long r,long long g,long long b) {
    DrawCircleV(Vector2{static_cast<float>(x),static_cast<float>(y)},
        static_cast<float>(radius),tk_rgb(r,g,b));
}
inline void tk_game_line(double x1,double y1,double x2,double y2,double width,
                         long long r,long long g,long long b) {
    DrawLineEx(Vector2{static_cast<float>(x1),static_cast<float>(y1)},
        Vector2{static_cast<float>(x2),static_cast<float>(y2)},
        static_cast<float>(width),tk_rgb(r,g,b));
}
inline void tk_game_triangle(double x1,double y1,double x2,double y2,double x3,double y3,
                             long long r,long long g,long long b) {
    DrawTriangle(Vector2{static_cast<float>(x1),static_cast<float>(y1)},
        Vector2{static_cast<float>(x2),static_cast<float>(y2)},
        Vector2{static_cast<float>(x3),static_cast<float>(y3)},tk_rgb(r,g,b));
}
inline void tk_game_text(const std::string& text,double x,double y,long long size,
                         long long r,long long g,long long b) {
    DrawText(text.c_str(),static_cast<int>(x),static_cast<int>(y),
        static_cast<int>(size),tk_rgb(r,g,b));
}
inline int tk_game_key_code(const std::string& name) {
    if (name == "W") return KEY_W;
    if (name == "A") return KEY_A;
    if (name == "S") return KEY_S;
    if (name == "D") return KEY_D;
    if (name == "UP") return KEY_UP;
    if (name == "DOWN") return KEY_DOWN;
    if (name == "LEFT") return KEY_LEFT;
    if (name == "RIGHT") return KEY_RIGHT;
    if (name == "SPACE") return KEY_SPACE;
    if (name == "ENTER") return KEY_ENTER;
    if (name == "ESC") return KEY_ESCAPE;
    if (name == "R") return KEY_R;
    if (name == "P") return KEY_P;
    if (name == "SHIFT") return KEY_LEFT_SHIFT;
    return KEY_NULL;
}
inline bool tk_game_key(const std::string& key) {
    int code = tk_game_key_code(key);
    return code != KEY_NULL && IsKeyDown(code);
}
inline bool tk_game_pressed(const std::string& key) {
    int code = tk_game_key_code(key);
    return code != KEY_NULL && IsKeyPressed(code);
}
inline double tk_game_dt() { return static_cast<double>(GetFrameTime()); }
inline double tk_game_time() { return GetTime(); }
inline long long tk_game_rand(long long a,long long b) {
    return static_cast<long long>(GetRandomValue(static_cast<int>(a),static_cast<int>(b)));
}
inline long long tk_game_fps() { return static_cast<long long>(GetFPS()); }
inline long long tk_game_mouse_x() { return static_cast<long long>(GetMouseX()); }
inline long long tk_game_mouse_y() { return static_cast<long long>(GetMouseY()); }
'''

def error_code(message: str) -> str:
    if message.startswith(('Unknown member', 'Unknown method', 'Unknown function')):
        return 'E102'
    if message.startswith('Unknown variable'):
        return 'E101'
    if message.startswith(('Unknown module', 'Module alias', 'Imports must')):
        return 'E201'
    if message.startswith(('Expected return type', 'Expected int', 'Expected float',
                           'Expected bool', 'Expected string', 'Cannot compare',
                           'Cannot order', 'Cannot store', 'Cannot infer')):
        return 'E301'
    if 'takes ' in message and 'arguments' in message:
        return 'E302'
    if message.startswith(('Reserved name', 'Class ', 'Function ')):
        return 'E202'
    return 'E001'


class TekaError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0, code: str = None):
        self.message, self.line, self.column = message, line, column
        self.code = code or error_code(message)
        super().__init__(message)

@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int

TOKEN_RE = re.compile(r'''(?P<SPACE>[ \t\r\n]+)|(?P<COMMENT>//[^\n]*|\#[^\n]*)|(?P<STRING>"(?:\\.|[^"\\])*")|(?P<FLOAT>\d+\.\d+(?!\.))|(?P<INT>\d+)|(?P<OP>==|!=|<=|>=|->|\.\.|&&|\|\||[+*/%\-<>=!,:;(){}\[\]\.])|(?P<ID>[A-Za-z_][A-Za-z0-9_]*)|(?P<ERROR>.)''')

def lex(source: str) -> list[Token]:
    result = []
    line, col = 1, 1
    for m in TOKEN_RE.finditer(source):
        kind, value = m.lastgroup, m.group()
        if kind == 'ERROR':
            raise TekaError(f"Unexpected character {value!r}", line, col)
        if kind == 'STRING':
            for esc in re.finditer(r'\\(.)', value):
                if esc.group(1) not in {'n', 'r', 't', '\\', '"', '0'}:
                    raise TekaError(f"Unsupported string escape \\{esc.group(1)}", line, col + esc.start())
        if kind not in {'SPACE', 'COMMENT'}:
            if kind == 'ID' and value in KEYWORDS:
                kind = value
            result.append(Token(kind if kind != 'OP' else value, value, line, col))
        parts = value.split('\n')
        if len(parts) > 1:
            line += len(parts) - 1
            col = len(parts[-1]) + 1
        else:
            col += len(value)
    result.append(Token('EOF', '', line, col))
    return result

@dataclass
class Node:
    kind: str
    tok: Token
    a: object = None
    b: object = None
    c: object = None
    d: object = None

class Parser:
    def __init__(self, tokens: list[Token]):
        self.ts, self.i = tokens, 0

    def cur(self): return self.ts[self.i]
    def is_(self, k): return self.cur().kind == k
    def take(self):
        t = self.cur()
        self.i += 1
        return t
    def match(self, k):
        if self.is_(k): return self.take()
        return None
    def need(self, k):
        t = self.match(k)
        if t is None:
            x = self.cur()
            raise TekaError(f"Expected {k!r}, got {x.value or x.kind!r}", x.line, x.column)
        return t
    def name(self):
        t = self.need('ID')
        if t.value in TYPE_NAMES or t.value in {'print', 'len', 'push', 'pop', 'str'} | GAME_FUNCTIONS.keys():
            raise TekaError(f"Reserved name '{t.value}'", t.line, t.column)
        return t

    def parse(self):
        out = []
        while not self.is_('EOF'):
            out.append(self.statement(top=True))
        return out

    def type_name(self, allow_void=False):
        tok = self.need('ID')
        if tok.value == 'list':
            self.need('<')
            inner = self.type_name()
            self.need('>')
            return f'list<{inner}>'
        if tok.value == 'void' and not allow_void:
            raise TekaError("'void' is only valid as a return type", tok.line, tok.column)
        # User-defined class types are resolved by the type checker after parsing.
        if tok.value not in TYPE_NAMES and not tok.value[0].isupper():
            raise TekaError(f"Unknown type '{tok.value}'", tok.line, tok.column)
        return tok.value

    def block(self, in_class=False):
        self.need('{')
        statements = []
        while not self.is_('}'):
            if self.is_('EOF'):
                tok = self.cur()
                raise TekaError('Unclosed block', tok.line, tok.column)
            statements.append(self.statement(top=in_class, in_class=in_class))
        self.need('}')
        return statements

    def statement(self, top=False, in_class=False):
        t = self.cur()
        if self.match('import'):
            if not top or in_class:
                raise TekaError('Imports must be at the top level', t.line, t.column)
            module = self.need('ID')
            namespaced = False
            if self.match('.'):
                if module.value != 'teka':
                    raise TekaError("Native imports use 'teka.module', e.g. import teka.math", t.line, t.column)
                module = self.need('ID')
                namespaced = True
            alias = Token('ID', 'teka', module.line, module.column) if namespaced else module
            if self.match('as'):
                alias = self.name()
                namespaced = False
            self.need(';')
            return Node('import', t, module, alias, None, 'namespace' if namespaced else None)
        if self.match('class'):
            if not top or in_class:
                raise TekaError('Classes must be at the top level', t.line, t.column)
            name = self.name()
            members = self.block(in_class=True)
            for member in members:
                if member.kind != 'fn':
                    raise TekaError('Class bodies currently support methods only', member.tok.line, member.tok.column)
            return Node('class', t, name, members)
        if self.match('fn'):
            if not top: raise TekaError('Functions must be at the top level', t.line, t.column)
            name = self.name()
            self.need('(')
            params = []
            if not self.is_(')'):
                while True:
                    p = self.name()
                    if in_class and p.value == 'self' and not self.is_(':'):
                        typ = 'SELF'
                    else:
                        self.need(':')
                        typ = self.type_name()
                    params.append((p, typ))
                    if not self.match(','): break
            self.need(')')
            ret = self.type_name(allow_void=True) if self.match('->') else 'void'
            body = self.block()
            return Node('fn', t, name, params, ret, body)
        if self.is_('let') or self.is_('var'):
            kw = self.take()
            name = self.name()
            typ = self.type_name() if self.match(':') else None
            self.need('=')
            expr = self.expr()
            self.need(';')
            return Node('decl', kw, name, typ, expr, kw.kind == 'var')
        if self.match('break'):
            self.need(';')
            return Node('break', t)
        if self.match('continue'):
            self.need(';')
            return Node('continue', t)
        if self.match('if'):
            cond = self.expr()
            yes = self.block()
            no = []
            if self.match('else'):
                if self.is_('if'):
                    no = [self.statement()]
                else: no = self.block()
            return Node('if', t, cond, yes, no)
        if self.match('while'):
            cond = self.expr()
            return Node('while', t, cond, self.block())
        if self.match('for'):
            var = self.name()
            self.need('in')
            start = self.expr(min_bp=1, stop_range=True)
            if self.match('..'):
                end = self.expr()
                return Node('for', t, var, start, end, self.block())
            return Node('foreach', t, var, start, self.block())
        if self.match('return'):
            expr = None if self.is_(';') else self.expr()
            self.need(';')
            return Node('return', t, expr)
        if self.is_('ID') and self.ts[self.i+1].kind in {'[', '.', '='}:
            checkpoint = self.i
            target = self.expr(min_bp=90)
            if self.match('='):
                value = self.expr()
                self.need(';')
                if target.kind == 'name':
                    return Node('set', t, target.tok, value)
                if target.kind == 'member':
                    return Node('setmember', t, target, value)
                if target.kind == 'index' and target.a.kind == 'name':
                    return Node('setindex', t, target.a.tok, target.b, value)
                raise TekaError('Assignment target is not a writable variable or field', t.line, t.column)
            self.i = checkpoint
        expr = self.expr()
        self.need(';')
        return Node('expr', t, expr)

    def expr(self, min_bp=0, stop_range=False):
        t = self.take()
        if t.kind in {'INT', 'FLOAT', 'STRING', 'true', 'false'}:
            left = Node('literal', t, t.value)
        elif t.kind == '[':
            items = []
            if not self.is_(']'):
                while True:
                    items.append(self.expr())
                    if not self.match(','): break
                    if self.is_(']'): break
            self.need(']')
            left = Node('list', t, items)
        elif t.kind == 'ID':
            left = Node('name', t, t.value)
        elif t.kind in {'-', '!', 'not'}:
            left = Node('unary', t, t.kind, self.expr(70))
        elif t.kind == '(':
            left = self.expr()
            self.need(')')
        else:
            raise TekaError(f"Expected expression, got {t.value or t.kind!r}", t.line, t.column)
        while True:
            op = self.cur()
            if op.kind == '.':
                if 90 < min_bp: break
                self.take()
                member = self.need('ID')
                left = Node('member', member, left, member.value)
                continue
            if op.kind == '[':
                if 90 < min_bp: break
                self.take()
                idx = self.expr()
                self.need(']')
                left = Node('index', op, left, idx)
                continue
            if op.kind == '(':
                if 90 < min_bp: break
                self.take()
                args = []
                if not self.is_(')'):
                    while True:
                        args.append(self.expr())
                        if not self.match(','): break
                self.need(')')
                left = Node('call', op, left, args)
                continue
            bp = {'or': 10, '||': 10, 'and': 20, '&&': 20, '==': 30, '!=': 30,
                  '<': 40, '<=': 40, '>': 40, '>=': 40, '+': 50, '-': 50,
                  '*': 60, '/': 60, '%': 60}.get(op.kind)
            if bp is None or bp < min_bp: break
            self.take()
            right = self.expr(bp + 1)
            left = Node('bin', op, op.kind, left, right)
        return left

@dataclass
class Binding:
    typ: str
    mutable: bool

class Checker:
    def __init__(self, tree):
        self.tree = tree
        self.funcs = {'print': (None, 'void'), **GAME_FUNCTIONS}
        self.classes = {}
        self.imports = {}
        self.uses_modules = set()
        self.namespaced_modules = set()
        self.current_class = None
        self.current_method = None
        self.uses_graphics = False
        self.scopes = [{}]
        self.ret = None
        self.in_function = False
        self.expr_types = {}
        self.decl_types = {}
        self.loop_depth = 0

    def err(self, node, msg):
        raise TekaError(msg, node.tok.line, node.tok.column)
    def push(self): self.scopes.append({})
    def pop(self): self.scopes.pop()
    def find(self, name):
        for scope in reversed(self.scopes):
            if name in scope: return scope[name]
        return None
    def add(self, tok, typ, mutable):
        if tok.value in self.scopes[-1]:
            raise TekaError(f"'{tok.value}' is already defined in this scope", tok.line, tok.column)
        self.scopes[-1][tok.value] = Binding(typ, mutable)
    def compatible(self, actual, expected):
        return (actual == expected or actual == 'int' and expected == 'float'
                or actual == 'list<?>' and expected.startswith('list<'))
    def expr(self, n):
        k = n.kind
        if k == 'literal':
            typ = {'INT':'int','FLOAT':'float','STRING':'string','true':'bool','false':'bool'}[n.tok.kind]
        elif k == 'list':
            types = [self.expr(item) for item in n.a]
            if not types:
                typ = 'list<?>'
            elif any(t == 'void' or t == 'list<?>' for t in types):
                self.err(n, 'List elements need known non-void types')
            elif set(types) <= {'int', 'float'}:
                typ = 'list<float>' if 'float' in types else 'list<int>'
            elif len(set(types)) == 1:
                typ = f'list<{types[0]}>'
            else:
                self.err(n, 'List elements must have compatible types')
        elif k == 'index':
            collection = self.expr(n.a)
            ix = self.expr(n.b)
            if ix != 'int': self.err(n.b, 'List index must be int')
            if not collection.startswith('list<') or collection == 'list<?>':
                self.err(n, 'Indexing requires a typed list')
            typ = collection[5:-1]
        elif k == 'name':
            b = self.find(n.a)
            if b is None:
                known = {name for scope in self.scopes for name in scope}
                guess = difflib.get_close_matches(n.a, known, n=1, cutoff=0.6)
                suffix = f". Did you mean '{guess[0]}'?" if guess else ". Declare it first, e.g. 'var " + n.a + " = 0'"
                self.err(n, f"Unknown variable '{n.a}'{suffix}")
            typ = b.typ
        elif k == 'member':
            owner = self.expr(n.a)
            if owner == 'module-root':
                if n.b not in self.namespaced_modules:
                    self.err(n, f"Unknown module 'teka.{n.b}'. Import it first with 'import teka.{n.b}'")
                typ = f'module:{n.b}'
            elif owner.startswith('module:'):
                module_name = owner[7:]
                module = MODULES[module_name]
                if n.b in module.constants:
                    typ = module.constants[n.b][0]
                    self.uses_modules.add(module_name)
                    if module.requires_graphics:
                        self.uses_graphics = True
                elif n.b in module.functions:
                    self.err(n, f"Module function '{module_name}.{n.b}' must be called")
                else:
                    names = list(module.functions) + list(module.constants)
                    guess = difflib.get_close_matches(n.b, names, n=1, cutoff=0.6)
                    hint = f". Did you mean '{guess[0]}'?" if guess else ''
                    self.err(n, f"Unknown member '{n.b}' in module '{module_name}'{hint}")
            elif owner in self.classes:
                info = self.classes[owner]
                if n.b in info['fields']:
                    typ = info['fields'][n.b]
                elif n.b in info['methods']:
                    self.err(n, f"Method '{owner}.{n.b}' must be called")
                else:
                    names = list(info['fields']) + list(info['methods'])
                    guess = difflib.get_close_matches(n.b, names, n=1, cutoff=0.6)
                    hint = f". Did you mean '{guess[0]}'?" if guess else ''
                    self.err(n, f"Unknown member '{n.b}' on {owner}{hint}")
            else:
                self.err(n, f"Type '{owner}' has no member '{n.b}'")
        elif k == 'unary':
            arg = self.expr(n.b)
            if n.a in {'!', 'not'}:
                if arg != 'bool': self.err(n, 'Logical not needs a bool')
                typ = 'bool'
            else:
                if arg not in {'int','float'}: self.err(n, 'Unary minus needs a number')
                typ = arg
        elif k == 'bin':
            a, b = self.expr(n.b), self.expr(n.c)
            op = n.a
            if op in {'and','or','&&','||'}:
                if a != 'bool' or b != 'bool': self.err(n, 'Logical operators need bool values')
                typ = 'bool'
            elif op in {'==','!='}:
                if a != b and not (a in {'int','float'} and b in {'int','float'}):
                    self.err(n, f"Cannot compare {a} with {b}")
                typ = 'bool'
            elif op in {'<','<=','>','>='}:
                if not (a in {'int','float'} and b in {'int','float'}) and not (a == b == 'string'):
                    self.err(n, f"Cannot order {a} and {b}")
                typ = 'bool'
            elif op == '+' and a == b == 'string':
                typ = 'string'
            elif op in {'+','-','*','/','%'}:
                if a not in {'int','float'} or b not in {'int','float'}:
                    self.err(n, f"Operator '{op}' needs numeric values")
                if op == '%' and (a != 'int' or b != 'int'):
                    self.err(n, 'Remainder requires int operands')
                typ = 'float' if 'float' in {a, b} else 'int'
            else: self.err(n, f"Unknown operator {op}")
        elif k == 'call':
            caller = n.a
            if caller.kind == 'name':
                name = caller.a
                if name in {'len', 'push', 'pop'}:
                    if len(n.b) != (2 if name == 'push' else 1):
                        self.err(n, f"'{name}' received the wrong number of arguments")
                    collection = self.expr(n.b[0])
                    if name == 'len':
                        if collection != 'string' and not collection.startswith('list<'):
                            self.err(n, 'len requires a string or list')
                        typ = 'int'
                    else:
                        if not collection.startswith('list<') or collection == 'list<?>':
                            self.err(n, f'{name} requires a typed list')
                        if n.b[0].kind != 'name':
                            self.err(n, f'{name} needs a variable as its first argument')
                        binding = self.find(n.b[0].a)
                        if not binding or not binding.mutable:
                            self.err(n, f'{name} requires a mutable var list')
                        if name == 'push':
                            val = self.expr(n.b[1])
                            if not self.compatible(val, collection[5:-1]):
                                self.err(n.b[1], f'Expected {collection[5:-1]}, got {val}')
                            typ = 'void'
                        else:
                            typ = collection[5:-1]
                elif name in {'str', 'int', 'float', 'bool'}:
                    if len(n.b) != 1:
                        self.err(n, f"'{name}' takes exactly one argument")
                    actual = self.expr(n.b[0])
                    if actual not in {'string', 'int', 'float', 'bool'}:
                        self.err(n, f"'{name}' cannot convert {actual}")
                    typ = 'string' if name == 'str' else name
                elif name == 'input':
                    if len(n.b) > 1:
                        self.err(n, "'input' expects zero or one prompt argument")
                    if n.b and self.expr(n.b[0]) != 'string':
                        self.err(n.b[0], 'input prompt must be a string')
                    typ = 'string'
                elif name == 'print':
                    for arg in n.b:
                        actual = self.expr(arg)
                        if actual == 'void' or actual.startswith(('list<', 'module:')) or actual in self.classes:
                            self.err(arg, f'Cannot directly print a value of type {actual}')
                    typ = 'void'
                elif name in self.classes:
                    info = self.classes[name]
                    init = info['methods'].get('__init__')
                    expected = init[0] if init else []
                    self.require_args(n, n.b, expected, name)
                    typ = name
                else:
                    if name not in self.funcs:
                        options = list(self.funcs) + list(self.classes) + ['str','int','float','bool','input']
                        guess = difflib.get_close_matches(name, options, n=1, cutoff=0.6)
                        hint = f". Did you mean '{guess[0]}'?" if guess else ''
                        self.err(n, f"Unknown function '{name}'{hint}")
                    expected, typ = self.funcs[name]
                    self.require_args(n, n.b, expected, name)
                    if name in GAME_FUNCTIONS:
                        self.uses_graphics = True
            elif caller.kind == 'member':
                receiver = self.expr(caller.a)
                member = caller.b
                if receiver.startswith('module:'):
                    module_name = receiver[7:]
                    module = MODULES[module_name]
                    if member not in module.functions:
                        names = list(module.functions)
                        guess = difflib.get_close_matches(member, names, n=1, cutoff=0.6)
                        hint = f". Did you mean '{guess[0]}'?" if guess else ''
                        self.err(caller, f"Unknown function '{module_name}.{member}'{hint}")
                    function = module.functions[member]
                    self.require_args(n, n.b, function.args, f'{module_name}.{member}')
                    typ = function.returns
                    self.uses_modules.add(module_name)
                    if MODULES[module_name].requires_graphics:
                        self.uses_graphics = True
                elif receiver in self.classes:
                    info = self.classes[receiver]
                    if member not in info['methods']:
                        names = list(info['methods'])
                        guess = difflib.get_close_matches(member, names, n=1, cutoff=0.6)
                        hint = f". Did you mean '{guess[0]}'?" if guess else ''
                        self.err(caller, f"Unknown method '{member}' on {receiver}{hint}")
                    if member == '__init__':
                        self.err(caller, 'Call the class constructor instead of calling __init__ directly')
                    expected, typ = info['methods'][member]
                    self.require_args(n, n.b, expected, f'{receiver}.{member}')
                else:
                    self.err(caller, f"Cannot call a member on type '{receiver}'")
            else:
                self.err(n, 'Only named functions and typed object methods can be called')
        else: self.err(n, f"Invalid expression '{k}'")
        self.expr_types[id(n)] = typ
        return typ

    def validate_type(self, node, typ):
        if typ.startswith('list<') and typ.endswith('>'):
            return self.validate_type(node, typ[5:-1])
        if typ not in {'int', 'float', 'bool', 'string', 'void'} and typ not in self.classes:
            self.err(node, f"Unknown type '{typ}'")

    def require_args(self, node, args, expected, label):
        if len(args) != len(expected):
            self.err(node, f"'{label}' takes {len(expected)} arguments, got {len(args)}")
        for arg, wanted in zip(args, expected):
            actual = self.expr(arg)
            if not self.compatible(actual, wanted):
                self.err(arg, f"Expected {wanted}, got {actual} in call to '{label}'")

    def block(self, nodes, new_scope=True):
        if new_scope: self.push()
        for n in nodes: self.statement(n)
        if new_scope: self.pop()

    def statement(self, n):
        k = n.kind
        if k in {'import','class','fn'}:
            return
        if k == 'setmember':
            target = n.a
            receiver = self.expr(target.a)
            if receiver not in self.classes:
                self.err(target, f"Cannot assign fields on type '{receiver}'")
            field = target.b
            info = self.classes[receiver]
            actual = self.expr(n.b)
            if field not in info['fields']:
                if (self.current_class != receiver or self.current_method != '__init__'
                        or target.a.kind != 'name' or target.a.a != 'self'):
                    self.err(target, f"Unknown field '{field}' on {receiver}; declare fields in __init__")
                if actual == 'void' or actual.startswith('module:') or actual == 'list<?>':
                    self.err(n, f"Cannot infer field '{field}' from {actual}")
                info['fields'][field] = actual
            elif not self.compatible(actual, info['fields'][field]):
                self.err(n.b, f"Expected {info['fields'][field]}, got {actual} for field '{field}'")
        elif k == 'decl':
            if n.b: self.validate_type(n, n.b)
            actual = self.expr(n.c)
            typ = n.b or actual
            if actual == 'void': self.err(n, 'Cannot store void')
            if not self.compatible(actual, typ): self.err(n, f"Expected {typ}, got {actual}")
            if actual == 'list<?>' and n.b:
                self.expr_types[id(n.c)] = typ
            if typ == 'list<?>':
                self.err(n, 'Empty lists need an explicit type, e.g. var xs: list<int> = []')
            self.add(n.a, typ, n.d)
            self.decl_types[id(n)] = typ
        elif k == 'set':
            binding = self.find(n.a.value)
            if binding is None: self.err(n, f"Unknown variable '{n.a.value}'")
            if not binding.mutable: self.err(n, f"'{n.a.value}' is immutable; use 'var' to change it")
            got = self.expr(n.b)
            if not self.compatible(got, binding.typ): self.err(n, f"Expected {binding.typ}, got {got}")
        elif k == 'setindex':
            binding = self.find(n.a.value)
            if binding is None or not binding.typ.startswith('list<'):
                self.err(n, 'Indexed assignment needs a list variable')
            if not binding.mutable:
                self.err(n, 'Cannot change an immutable let list')
            if self.expr(n.b) != 'int': self.err(n.b, 'List index must be int')
            got = self.expr(n.c)
            if not self.compatible(got, binding.typ[5:-1]):
                self.err(n.c, f'Expected {binding.typ[5:-1]}, got {got}')
        elif k == 'expr': self.expr(n.a)
        elif k == 'break' or k == 'continue':
            if self.loop_depth == 0: self.err(n, f'{k} must appear inside a loop')
        elif k == 'if':
            if self.expr(n.a) != 'bool': self.err(n, 'If condition must be bool')
            self.block(n.b)
            self.block(n.c)
        elif k == 'while':
            if self.expr(n.a) != 'bool': self.err(n, 'While condition must be bool')
            self.loop_depth += 1
            self.block(n.b)
            self.loop_depth -= 1
        elif k in {'for', 'foreach'}:
            if k == 'for':
                if self.expr(n.b) != 'int' or self.expr(n.c) != 'int':
                    self.err(n, 'Range bounds must be int')
                elem_type = 'int'
                body = n.d
            else:
                collection_type = self.expr(n.b)
                if not collection_type.startswith('list<') or collection_type == 'list<?>':
                    self.err(n, 'Collection loop requires a typed list')
                elem_type = collection_type[5:-1]
                body = n.c
            self.push()
            self.add(n.a, elem_type, False)
            self.loop_depth += 1
            self.block(body, new_scope=False)
            self.loop_depth -= 1
            self.pop()
        elif k == 'return':
            if not self.in_function: self.err(n, 'return can only be inside a function')
            got = 'void' if n.a is None else self.expr(n.a)
            if not self.compatible(got, self.ret): self.err(n, f"Expected return type {self.ret}, got {got}")
        else: self.err(n, f"Unexpected statement '{k}'")

    @staticmethod
    def guarantees_return(body):
        for n in body:
            if n.kind == 'return':
                return True
            if n.kind == 'if' and n.c and Checker.guarantees_return(n.b) and Checker.guarantees_return(n.c):
                return True
        return False

    def check(self):
        # Register native imports, types and function declarations before use.
        for n in self.tree:
            if n.kind == 'import':
                module_name = n.a.value
                if module_name not in MODULES:
                    guess = difflib.get_close_matches(module_name, MODULES, n=1)
                    hint = f" Did you mean '{guess[0]}'?" if guess else ''
                    self.err(n, f"Unknown module '{module_name}'. Supported modules: {known_modules()}.{hint}")
                alias = n.b
                if alias.value in self.funcs or alias.value in self.classes:
                    self.err(n, f"Module alias '{alias.value}' conflicts with another name")
                if n.d == 'namespace':
                    self.namespaced_modules.add(module_name)
                    if 'teka' not in self.imports:
                        self.add(alias, 'module-root', False)
                        self.imports['teka'] = 'namespace'
                else:
                    self.add(alias, f'module:{module_name}', False)
                    self.imports[alias.value] = module_name
            elif n.kind == 'class':
                name = n.a.value
                if name in self.classes or name in self.funcs or name in MODULES:
                    self.err(n, f"Class '{name}' is already defined or reserved")
                self.classes[name] = {'fields': {}, 'methods': {}, 'node': n}
            elif n.kind == 'fn':
                name = n.a.value
                if name in self.funcs:
                    self.err(n, f"Function '{name}' already exists")
                for token, typ in n.b: self.validate_type(n, typ)
                self.validate_type(n, n.c)
                self.funcs[name] = ([typ for _, typ in n.b], n.c)

        for n in self.tree:
            if n.kind == 'class':
                info = self.classes[n.a.value]
                for method in n.b:
                    name = method.a.value
                    if name in info['methods']:
                        self.err(method, f"Method '{name}' already exists in class '{n.a.value}'")
                    if not method.b or method.b[0][0].value != 'self' or method.b[0][1] != 'SELF':
                        self.err(method, f"Method '{name}' must declare 'self' as its first parameter")
                    params = [typ for _, typ in method.b[1:]]
                    for typ in params: self.validate_type(method, typ)
                    self.validate_type(method, method.c)
                    if name == '__init__' and method.c != 'void':
                        self.err(method, '__init__ must not return a value')
                    info['methods'][name] = (params, method.c)

        imported = {alias: self.scopes[0][alias] for alias in self.imports}
        # Initialize fields before validating methods that read them.
        for cls in self.classes.values():
            cls_name = cls['node'].a.value
            ordered = sorted(cls['node'].b, key=lambda method: method.a.value != '__init__')
            for method in ordered:
                self.scopes = [imported.copy(), {}]
                self.ret, self.in_function = method.c, True
                self.current_class, self.current_method = cls_name, method.a.value
                self.loop_depth = 0
                for index, (tok, typ) in enumerate(method.b):
                    if index == 0:
                        self.add(tok, cls_name, False)
                    else:
                        self.add(tok, typ, True)
                self.block(method.d, new_scope=False)
                if method.c != 'void' and not self.guarantees_return(method.d):
                    self.err(method, f"Method '{cls_name}.{method.a.value}' might exit without returning {method.c}")
        self.current_class = None
        self.current_method = None
        self.in_function = False
        self.ret = None
        self.scopes = [imported.copy()]
        # Check top-level only after constructor fields are inferred.
        for n in self.tree:
            if n.kind not in {'fn', 'class', 'import'}:
                self.statement(n)
        for n in self.tree:
            if n.kind == 'fn':
                self.scopes = [imported.copy(), {}]
                self.ret, self.in_function = n.c, True
                self.loop_depth = 0
                for tok, typ in n.b:
                    self.add(tok, typ, True)
                self.block(n.d, new_scope=False)
                if n.c != 'void' and not self.guarantees_return(n.d):
                    self.err(n, f"Function '{n.a.value}' might exit without returning {n.c}")
        self.in_function = False
        self.scopes = [imported]
        return self

class Emitter:
    TYPES = {'int':'long long','float':'double','bool':'bool','string':'std::string','void':'void'}
    def __init__(self, tree, checked):
        self.tree, self.ck = tree, checked
        self.level = 0
        self.lines = []
    def write(self, s): self.lines.append('    '*self.level+s)
    def cpp_type(self, t):
        if t.startswith('list<'):
            return 'std::vector<' + self.cpp_type(t[5:-1]) + '>'
        if t in self.ck.classes: return self.ident(t)
        return self.TYPES[t]
    @staticmethod
    def ident(s): return 'tk_' + s
    def condition(self, n):
        expr = self.expr(n)
        return expr if expr.startswith('(') and expr.endswith(')') else '(' + expr + ')'
    def expr(self, n):
        k = n.kind
        if k == 'literal':
            if n.tok.kind == 'STRING': return 'std::string(' + n.a + ')'
            if n.tok.kind == 'true': return 'true'
            if n.tok.kind == 'false': return 'false'
            return n.a
        if k == 'list':
            typ = self.ck.expr_types[id(n)]
            return self.cpp_type(typ) + '{' + ', '.join(self.expr(a) for a in n.a) + '}'
        if k == 'index':
            return f'{self.expr(n.a)}.at(static_cast<std::size_t>({self.expr(n.b)}))'
        if k == 'name': return 'this' if n.a == 'self' else self.ident(n.a)
        if k == 'member':
            receiver = self.ck.expr_types[id(n.a)]
            if receiver.startswith('module:'):
                return MODULES[receiver[7:]].constants[n.b][1]
            parent = self.expr(n.a)
            op = '->' if n.a.kind == 'name' and n.a.a == 'self' else '.'
            return f'{parent}{op}{self.ident(n.b)}'
        if k == 'unary': return '(' + ('!' if n.a == 'not' else n.a) + self.expr(n.b) + ')'
        if k == 'bin':
            op = {'and':'&&','or':'||'}.get(n.a, n.a)
            return f'({self.expr(n.b)} {op} {self.expr(n.c)})'
        if k == 'call':
            caller = n.a
            if caller.kind == 'member':
                owner = self.ck.expr_types[id(caller.a)]
                args = ', '.join(self.expr(a) for a in n.b)
                if owner.startswith('module:'):
                    return MODULES[owner[7:]].functions[caller.b].cpp + '(' + args + ')'
                parent = self.expr(caller.a)
                op = '->' if caller.a.kind == 'name' and caller.a.a == 'self' else '.'
                return f'{parent}{op}{self.ident(caller.b)}({args})'
            name = caller.a
            if name == 'input':
                args = self.expr(n.b[0]) if n.b else 'std::string()'
                return f'tk_input({args})'
            if name in {'int','float','bool','str'}:
                arg = self.expr(n.b[0])
                actual = self.ck.expr_types[id(n.b[0])]
                if name == 'str':
                    if actual == 'string': return arg
                    if actual == 'bool':
                        return '('+arg+' ? std::string("true") : std::string("false"))'
                    return 'std::to_string('+arg+')'
                if name == 'int':
                    return 'tk_parse_int('+arg+')' if actual == 'string' else f'static_cast<long long>({arg})'
                if name == 'float':
                    return 'tk_parse_float('+arg+')' if actual == 'string' else f'static_cast<double>({arg})'
                if name == 'bool':
                    if actual == 'string': return f'(!{arg}.empty())'
                    return f'static_cast<bool>({arg})'
            if name in self.ck.classes:
                return self.cpp_type(name)+'('+', '.join(map(self.expr,n.b))+')'
            if name in GAME_FUNCTIONS:
                return 'tk_'+name+'('+', '.join(self.expr(a) for a in n.b)+')'
            if name == 'len':
                return f'static_cast<long long>({self.expr(n.b[0])}.size())'
            if name == 'push':
                return f'{self.expr(n.b[0])}.push_back({self.expr(n.b[1])})'
            if name == 'pop':
                return f'tk_pop({self.expr(n.b[0])})'
            if name == 'print':
                parts = ['std::cout << std::boolalpha']
                for i, arg in enumerate(n.b):
                    if i: parts.append(' << " "')
                    parts.append(' << ' + self.expr(arg))
                parts.append(' << std::endl')
                return '([&](){ ' + ''.join(parts) + '; }())'
            return self.ident(name) + '(' + ', '.join(map(self.expr, n.b)) + ')'
        raise AssertionError(k)
    def block(self, body):
        self.write('{')
        self.level += 1
        for n in body: self.stmt(n)
        self.level -= 1
        self.write('}')
    def stmt(self, n):
        k = n.kind
        if k == 'decl':
            typ = self.cpp_type(self.ck.decl_types[id(n)])
            self.write(f'{"const " if not n.d else ""}{typ} {self.ident(n.a.value)} = {self.expr(n.c)};')
        elif k == 'set': self.write(f'{self.ident(n.a.value)} = {self.expr(n.b)};')
        elif k == 'setmember':
            self.write(f'{self.expr(n.a)} = {self.expr(n.b)};')
        elif k == 'setindex':
            self.write(f'{self.ident(n.a.value)}.at(static_cast<std::size_t>({self.expr(n.b)})) = {self.expr(n.c)};')
        elif k == 'expr': self.write(self.expr(n.a) + ';')
        elif k in {'break', 'continue'}: self.write(k + ';')
        elif k in {'import', 'class', 'fn'}: pass
        elif k == 'return': self.write('return' + (' '+self.expr(n.a) if n.a else '')+';')
        elif k == 'if':
            self.write('if '+self.condition(n.a))
            self.block(n.b)
            if n.c:
                self.write('else')
                self.block(n.c)
        elif k == 'while':
            self.write('while '+self.condition(n.a))
            self.block(n.b)
        elif k == 'foreach':
            self.write(f'for (const auto& {self.ident(n.a.value)} : {self.expr(n.b)})')
            self.block(n.c)
        elif k == 'for':
            var = self.ident(n.a.value)
            # bound evaluated once, like range(start, end) in Python
            lim = var + '_limit'
            self.write(f'for (long long {var} = {self.expr(n.b)}, {lim} = {self.expr(n.c)}; {var} < {lim}; ++{var})')
            self.block(n.d)
        else: raise AssertionError(k)
    def emit(self):
        self.write('// Generated by T+ 0.9; do not edit.')
        for header in ('<iostream>','<string>','<vector>','<stdexcept>',
                       '<cstddef>','<cmath>'):
            self.write('#include ' + header)
        self.write('')
        if self.ck.uses_graphics:
            self.write(GAME_NATIVE_CPP)
        for module_name in sorted(self.ck.uses_modules):
            module = MODULES[module_name]
            for header in module.includes:
                self.write('#include ' + header)
            self.write(module.helpers)
        self.write(r"""inline std::string tk_input(const std::string& prompt) {
    std::cout << prompt << std::flush;
    std::string value;
    if (!std::getline(std::cin, value))
        throw std::runtime_error("input: end of input reached");
    return value;
}
inline long long tk_parse_int(const std::string& value) {
    try {
        std::size_t position = 0;
        long long result = std::stoll(value, &position);
        if (position != value.size()) throw std::invalid_argument("trailing characters");
        return result;
    } catch (const std::exception&) {
        throw std::invalid_argument("int(): invalid integer '" + value + "'");
    }
}
inline double tk_parse_float(const std::string& value) {
    try {
        std::size_t position = 0;
        double result = std::stod(value, &position);
        if (position != value.size()) throw std::invalid_argument("trailing characters");
        return result;
    } catch (const std::exception&) {
        throw std::invalid_argument("float(): invalid number '" + value + "'");
    }
}""")
        self.write('template <class T> T tk_pop(std::vector<T>& xs) {')
        self.write('    if (xs.empty()) throw std::out_of_range("pop from empty list");')
        self.write('    T result = xs.back(); xs.pop_back(); return result;')
        self.write('}')
        self.write('')
        classes = [n for n in self.tree if n.kind == 'class']
        functions = [n for n in self.tree if n.kind == 'fn']

        # Class declarations come before their method implementations.
        for cls in classes:
            class_name = self.ident(cls.a.value)
            info = self.ck.classes[cls.a.value]
            self.write('class ' + class_name + ' {')
            self.write('public:')
            self.level += 1
            for field_name, field_type in info['fields'].items():
                self.write(f'{self.cpp_type(field_type)} {self.ident(field_name)};')
            has_ctor = False
            for method in cls.b:
                is_ctor = method.a.value == '__init__'
                if is_ctor: has_ctor = True
                params = ', '.join(self.cpp_type(t)+' '+self.ident(p.value)
                                   for p,t in method.b[1:])
                if is_ctor:
                    self.write(f'{class_name}({params});')
                else:
                    self.write(f'{self.cpp_type(method.c)} {self.ident(method.a.value)}({params});')
            if not has_ctor:
                self.write(f'{class_name}() = default;')
            self.level -= 1
            self.write('};')
            self.write('')

        # Global function declarations support recursion and calls across functions.
        for n in functions:
            signature = self.cpp_type(n.c) + ' ' + self.ident(n.a.value) + '(' + ', '.join(
                self.cpp_type(t)+' '+self.ident(p.value) for p,t in n.b) + ')'
            self.write(signature + ';')
        self.write('')

        for cls in classes:
            class_name = self.ident(cls.a.value)
            for method in cls.b:
                params = ', '.join(self.cpp_type(t)+' '+self.ident(p.value)
                                   for p,t in method.b[1:])
                if method.a.value == '__init__':
                    signature = f'{class_name}::{class_name}({params})'
                else:
                    signature = (f'{self.cpp_type(method.c)} {class_name}::'
                                 f'{self.ident(method.a.value)}({params})')
                self.write(signature)
                self.block(method.d)
                self.write('')

        for n in functions:
            signature = self.cpp_type(n.c) + ' ' + self.ident(n.a.value) + '(' + ', '.join(
                self.cpp_type(t)+' '+self.ident(p.value) for p,t in n.b) + ')'
            self.write(signature)
            self.block(n.d)
            self.write('')

        self.write('int main()')
        self.write('{')
        self.level += 1
        self.write('try')
        self.block([n for n in self.tree if n.kind not in {'fn','class','import'}])
        self.write('catch (const std::exception& err) {')
        self.level += 1
        self.write('std::cerr << "T+ runtime error: " << err.what() << std::endl;')
        self.write('return 1;')
        self.level -= 1
        self.write('}')
        self.level -= 1
        self.write('}')
        return '\n'.join(self.lines) + '\n'

def compile_source(source):
    try:
        normalized, prefixes = normalize_source(source)
    except NormalizeError as exc:
        raise TekaError(exc.message, exc.line, exc.column) from exc
    try:
        tree = Parser(lex(normalized)).parse()
        checker = Checker(tree).check()
        return Emitter(tree, checker).emit()
    except TekaError as exc:
        if exc.line in prefixes:
            exc.column = max(1, exc.column - prefixes[exc.line])
        raise
    except RecursionError as exc:
        raise TekaError('Expression or block nesting exceeds the compiler limit. Split it into smaller expressions or functions.', code='E401') from exc

def locate_cpp(requested=None):
    if requested: return requested
    return (shutil.which('g++') or shutil.which('clang++') or shutil.which('c++')) if sys.platform == 'win32' else (shutil.which('clang++') or shutil.which('g++') or shutil.which('c++'))

def render_error(path, source, error):
    location = f"{path}:{error.line}:{error.column}"
    lines = source.splitlines()
    if error.line < 1 or error.line > len(lines):
        return f"{location}: error: {error.message}"
    raw = lines[error.line - 1]
    col = max(1, error.column)
    snippet = raw.expandtabs(4)
    expanded_col = len(raw[:col-1].expandtabs(4)) + 1
    digits = len(str(error.line))
    return (
        f"{location}: error[{error.code}]: {error.message}\n"
        f" {error.line:>{digits}} | {snippet}\n"
        f" {' ' * digits} | {' ' * (expanded_col-1)}^"
    )

def main(argv=None):
    cli = argparse.ArgumentParser(prog='teka', description='T+ native compiler v'+VERSION)
    cli.add_argument('--version', action='version', version='T+ '+VERSION)
    subs = cli.add_subparsers(dest='command', required=True)
    new_cmd = subs.add_parser('new', help='Create a TekaLang project')
    new_cmd.add_argument('name', help='New project directory name')
    doctor_cmd = subs.add_parser('doctor', help='Check the compiler and native toolchain')
    doctor_cmd.add_argument('--json', action='store_true')
    subs.add_parser('docs', help='Show the local T+ Handbook path')
    lib_cmd = subs.add_parser('stdlib', help='List every built-in T+ native module and function')
    lib_cmd.add_argument('--json', action='store_true')
    for action in ['run','build','check','emit-cpp']:
        sub = subs.add_parser(action)
        sub.add_argument('file', nargs='?', help='A .teka source file, or - for stdin')
        sub.add_argument('--stdin', action='store_true', help='Read source from stdin (for editors)')
        sub.add_argument('--json', action='store_true', help='Machine-readable JSON diagnostics')
        if action == 'build':
            sub.add_argument('-o','--output', help='Output executable')
            sub.add_argument('--release', action='store_true', help='Optimize at -O3 instead of -O2')
        if action in {'run','build'}: sub.add_argument('--cxx', help='C++17 compiler path')
    args = cli.parse_args(argv)
    source = ''
    path = None
    filename = getattr(args, 'file', None) or '<stdin>'
    json_out = bool(getattr(args, 'json', False))
    try:
        if args.command == 'new':
            root = create_project(args.name)
            print('Created T+ project: ' + str(root))
            print('Open it in IntelliJ or run: cd ' + str(root) + ' && teka run')
            return 0
        if args.command == 'docs':
            doc = Path(__file__).resolve().parent / 'TPLUS_HANDBOOK.md'
            if not doc.is_file():
                raise TekaError('Handbook missing from this installation. See the T+ source distribution.')
            print(doc)
            return 0
        if args.command == 'stdlib':
            info = {name: {
                'functions': {key: {'args': list(value.args), 'returns': value.returns}
                              for key, value in sorted(module.functions.items())},
                'constants': {key: {'type': value[0]}
                              for key, value in sorted(module.constants.items())},
            } for name, module in sorted(MODULES.items())}
            if json_out:
                print(json.dumps(info, indent=2))
            else:
                for name, module in info.items():
                    print(f'teka.{name}')
                    for fn, definition in module['functions'].items():
                        print('  '+fn+'('+', '.join(definition['args'])+') -> '+definition['returns'])
                    for constant, definition in module['constants'].items():
                        print('  '+constant+': '+definition['type'])
            return 0
        if args.command == 'doctor':
            report = doctor(Path(__file__).resolve().parent)
            if json_out:
                print(json.dumps(report))
            else:
                for key, value in report.items():
                    print(f'{key}: {value}')
            return 0 if report['status'] == 'ready' else 1
        if args.stdin or args.file == '-':
            source = sys.stdin.read()
            filename = '<stdin>'
        else:
            if args.file:
                path = Path(args.file)
            else:
                path = project_entry(Path.cwd())
                if path is None:
                    raise TekaError('Provide a .teka file, or run from a folder with teka.toml')
            filename = str(path)
            if path.suffix != '.teka':
                raise TekaError('Expected a .teka file')
            source = path.read_text(encoding='utf-8')
        cpp = compile_source(source)
        if args.command == 'check':
            if json_out:
                print(json.dumps({'ok': True, 'errors': []}))
            else:
                print(f'OK: {filename} — syntax and types checked')
            return 0
        if args.command == 'emit-cpp':
            print(cpp, end='')
            return 0
        cxx = locate_cpp(args.cxx)
        if not cxx:
            raise TekaError('No C++ compiler found. Install Xcode Command Line Tools (macOS), g++ (Linux), or MinGW-w64 g++ (Windows).')
        if args.command == 'build':
            if path is None and not args.output:
                raise TekaError('Building stdin requires -o OUTPUT')
            output = Path(args.output or path.with_suffix('.exe' if sys.platform == 'win32' else '')).absolute()
            if output.suffix.lower() == '.teka':
                raise TekaError('Build output must not overwrite a .teka source file')
            if sys.platform == 'win32' and output.suffix.lower() != '.exe':
                output = output.with_name(output.name + '.exe')
            if output.is_symlink():
                raise TekaError('Build output must not be a symbolic link')
            if path is not None and output.exists() and output.samefile(path):
                raise TekaError('Build output must not overwrite the source file')
            output = output.resolve()
        # Stage beside the requested output so the final rename stays on the
        # same filesystem. A failed compiler/linker cannot truncate an old build.
        build_directory = output.parent if args.command == 'build' else None
        with tempfile.TemporaryDirectory(prefix='tekalang-', dir=build_directory) as tmp:
            executable = Path(tmp) / ('app.exe' if sys.platform == 'win32' else 'app')
            optimization = '-O3' if getattr(args, 'release', False) else '-O2'
            command = [cxx, '-std=c++17', optimization, '-x', 'c++', '-', '-o', str(executable)]
            if '#include "raylib.h"' in cpp:
                homebrew = Path('/opt/homebrew')
                if not (homebrew / 'include/raylib.h').is_file():
                    homebrew = Path('/usr/local')
                if not (homebrew / 'include/raylib.h').is_file():
                    raise TekaError('Native graphics need raylib. On macOS run: brew install raylib')
                command += ['-I' + str(homebrew / 'include'), '-L' + str(homebrew / 'lib'),
                            '-lraylib', '-Wl,-rpath,' + str(homebrew / 'lib')]
            compiled = subprocess.run(command, input=cpp, text=True, capture_output=True)
            if compiled.returncode != 0:
                summary = '\n'.join(compiled.stderr.splitlines()[:10])
                raise TekaError('Native C++ backend failed.\n' + summary)
            if args.command == 'build':
                os.replace(executable, output)
                print('Built ' + str(output))
                return 0
            return subprocess.run([str(executable)]).returncode
    except (TekaError, ProjectError, FileNotFoundError, UnicodeDecodeError, OSError) as exc:
        if isinstance(exc, TekaError):
            err = exc
        elif isinstance(exc, FileNotFoundError):
            err = TekaError(f"File not found: {exc.filename or filename}")
        elif isinstance(exc, UnicodeDecodeError):
            err = TekaError('Source must be UTF-8')
        else:
            err = TekaError(f"System error: {exc}")
        if json_out:
            print(json.dumps({'ok': False, 'errors': [{
                'line': max(1, err.line), 'column': max(1, err.column),
                'message': err.message, 'code': err.code, 'severity': 'error'
            }]}))
        else:
            print(render_error(filename, source, err), file=sys.stderr)
        return 1

if __name__ == '__main__': sys.exit(main())
