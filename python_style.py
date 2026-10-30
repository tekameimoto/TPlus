"""TekaLang's Python-like surface syntax, lowered to its typed core grammar.

One input line becomes one output line (plus EOF closing braces) to preserve
useful source locations for diagnostics. This is a syntax normalizer, not Python.
"""
from __future__ import annotations
import ast
import json
import re
from dataclasses import dataclass

@dataclass
class NormalizeError(Exception):
    message: str
    line: int
    column: int

def visual_indent(raw: str, line: int) -> int:
    whitespace = raw[:len(raw) - len(raw.lstrip(' \t'))]
    if '\t' in whitespace and ' ' in whitespace:
        raise NormalizeError("Do not mix tabs and spaces on the same indentation line", line, 1)
    return len(whitespace.expandtabs(4))

def split_code_comment(text: str, line: int) -> tuple[str, str]:
    """Respect quotes while finding #, // and single-quoted string literals."""
    out = []
    i = 0
    while i < len(text):
        if text.startswith('//', i) or text[i] == '#':
            return ''.join(out), text[i:]
        if text[i] in ('"', "'"):
            quote = text[i]
            begin = i
            i += 1
            escaped = False
            while i < len(text):
                ch = text[i]
                i += 1
                if ch == quote and not escaped:
                    break
                if ch == '\\' and not escaped:
                    escaped = True
                else:
                    escaped = False
            else:
                raise NormalizeError("Unclosed string. Add a matching quote.", line, begin + 1)
            literal = text[begin:i]
            if quote == "'":
                try:
                    value = ast.literal_eval(literal)
                    if not isinstance(value, str):
                        raise ValueError()
                    literal = json.dumps(value, ensure_ascii=False)
                except (ValueError, SyntaxError):
                    raise NormalizeError("Invalid quoted string", line, begin + 1)
            out.append(literal)
            continue
        j = i
        while i < len(text) and text[i] not in "\"'#":
            if text.startswith('//', i):
                break
            i += 1
        chunk = text[j:i]
        chunk = re.sub(r'\bTrue\b', 'true', chunk)
        chunk = re.sub(r'\bFalse\b', 'false', chunk)
        out.append(chunk)
    return ''.join(out), ''


def translate_english_expressions(statement: str) -> str:
    """Rewrite English comparisons only outside of quoted strings."""
    pieces = re.split(r'("(?:\\.|[^"\\])*")', statement)
    substitutions = (
        (r'\bis\s+not\s+equal\s+to\b', '!='),
        (r'\bis\s+equal\s+to\b', '=='),
        (r'\bis\s+at\s+least\b', '>='),
        (r'\bis\s+at\s+most\b', '<='),
        (r'\bis\s+below\b', '<'),
        (r'\bis\s+above\b', '>'),
    )
    for index in range(0, len(pieces), 2):
        for pattern, replacement in substitutions:
            pieces[index] = re.sub(pattern, replacement, pieces[index])
    return ''.join(pieces)


def translate_english_statement(statement: str, line: int) -> str:
    """Deterministic English/Python hybrid syntax; never interpret freeform prose."""
    statement = translate_english_expressions(statement)
    if statement.startswith('otherwise if '):
        return 'elif ' + statement[len('otherwise if '):]
    if statement == 'otherwise:':
        return 'else:'
    if statement.startswith('repeat ') and statement.endswith(' times:'):
        times = statement[len('repeat '):-len(' times:')].strip()
        if not times:
            raise NormalizeError('repeat needs a count, e.g. repeat 5 times:', line, 1)
        return f'for __teka_repeat_{line} in 0..({times}):'
    if statement == 'stop':
        return 'break'
    if statement == 'skip':
        return 'continue'
    if statement == 'say':
        return 'print()'
    if statement.startswith('say '):
        return 'print(' + statement[4:].strip() + ')'
    if statement.startswith('say('):
        return 'print' + statement[3:]
    if statement.startswith('ask('):
        return 'input' + statement[3:]
    if statement.startswith('ask '):
        return 'input(' + statement[4:].strip() + ')'
    # Inline input calls are rewritten only outside quoted strings.
    segments = re.split(r'("(?:\\.|[^"\\])*")', statement)
    for index in range(0, len(segments), 2):
        segments[index] = re.sub(r'(?<![A-Za-z0-9_])ask\s*\(', 'input(', segments[index])
    statement = ''.join(segments)
    rhs = re.match(r'^(.*?=\s*)ask\s+(.+)$', statement)
    if rhs:
        return rhs.group(1) + 'input(' + rhs.group(2).strip() + ')'
    return statement

def normalize_source(source: str) -> tuple[str, dict[int, int]]:
    """Return lower-level source and per-line inserted-prefix widths."""
    rows = source.splitlines()
    python_mode = any(
        re.match(r'^\s*(?:class|def|fn|if|elif|else|otherwise|repeat|while|for)\b', row)
        and split_code_comment(row.strip(), i)[0].rstrip().endswith(':')
        for i, row in enumerate(rows, 1)
    )
    out: list[str] = []
    prefixes: dict[int, int] = {}
    levels = [0]
    declarations = [set()]
    expecting = False
    header_line = 0
    header_vars: set[str] = set()
    last_code_line = 1

    for line, raw in enumerate(rows, 1):
        indent = visual_indent(raw, line)
        lead = raw[:len(raw) - len(raw.lstrip(' \t'))]
        body = raw[len(lead):]
        code, comment = split_code_comment(body, line)
        code = code.rstrip()
        if not code:
            out.append(raw)
            continue
        last_code_line = line
        prefix = ''
        if python_mode:
            if expecting:
                if indent <= levels[-1]:
                    raise NormalizeError(f"Expected an indented block after line {header_line}; press Tab on the next line", line, indent + 1)
                levels.append(indent)
                declarations.append(set(header_vars))
                expecting = False
                header_vars = set()
            else:
                if indent > levels[-1]:
                    raise NormalizeError("Unexpected indentation. Only lines after a ':' block may indent", line, indent + 1)
                while indent < levels[-1]:
                    levels.pop()
                    declarations.pop()
                    prefix += '} '
                if indent != levels[-1]:
                    raise NormalizeError("Inconsistent dedent: align with an earlier block", line, indent + 1)
        else:
            # Legacy curly-brace style retains its existing indentation and grammar.
            pass

        statement = translate_english_statement(code.strip(), line)
        head = re.match(r'^(class|def|fn|if|elif|else|while|for)\b', statement)
        colon = bool(head and statement.endswith(':'))
        if colon:
            statement = statement[:-1].rstrip()
            if statement.startswith('def '):
                statement = 'fn ' + statement[4:]
            elif statement.startswith('elif '):
                statement = 'else if ' + statement[5:]
            range_match = re.fullmatch(r'for\s+([A-Za-z_]\w*)\s+in\s+range\((.*)\)', statement)
            if range_match:
                var, argtext = range_match.groups()
                parts = [a.strip() for a in argtext.split(',')]
                if len(parts) == 1 and parts[0]:
                    statement = f'for {var} in 0..{parts[0]}'
                elif len(parts) == 2 and all(parts):
                    statement = f'for {var} in {parts[0]}..{parts[1]}'
                else:
                    raise NormalizeError("range() currently supports range(end) or range(start, end)", line, indent + 1)
            if re.match(r'^for\s+', statement):
                m = re.match(r'^for\s+([A-Za-z_]\w*)\s+in\b', statement)
                header_vars = {m.group(1)} if m else set()
            elif statement.startswith('fn '):
                params = re.search(r'\((.*?)\)', statement)
                header_vars = set(
                    part.strip().split(':')[0].strip()
                    for part in params.group(1).split(',')
                    if part.strip()
                ) if params else set()
            else:
                header_vars = set()
            statement += ' {'
            expecting = True
            header_line = line
        else:
            if statement == 'pass':
                statement = 'if true {}'  # a harmless no-op that produces no output
            # Python-style +=, -=, *= and /= lower to typed core assignments.
            augmented = re.fullmatch(
                r'([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*([+*/%-])=\s*(.+)',
                statement
            )
            if augmented:
                name, operator, right = augmented.groups()
                statement = f'{name} = {name} {operator} ({right})'
            # Python-like simple variable declarations: x = value, then x = later.
            assign = re.match(r'^([A-Za-z_]\w*)\s*=(?!=)', statement)
            if assign and not statement.startswith(('let ', 'var ')):
                name = assign.group(1)
                if not any(name in scope for scope in reversed(declarations)):
                    declarations[-1].add(name)
                    statement = 'var ' + statement
            declared = re.match(r'^(?:let|var)\s+([A-Za-z_]\w*)\b', statement)
            if declared:
                declarations[-1].add(declared.group(1))
            if statement and not statement.endswith((';', '{', '}')) and not statement.startswith('//'):
                statement += ';'
        insert_before = len(prefix)
        # Preserve the user's real TAB bytes in the original file.
        # The source compiler only needs the transformed copy in memory.
        out.append(lead + prefix + statement + ((' ' + comment) if comment else ''))
        prefixes[line] = insert_before
    if expecting:
        raise NormalizeError(f"Expected an indented block after line {header_line}", last_code_line + 1, 1)
    if python_mode and len(levels) > 1:
        out.append('}' * (len(levels) - 1))
    result = '\n'.join(out) + ('\n' if source.endswith('\n') else '')
    return result, prefixes