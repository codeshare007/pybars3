#
# Copyright (c) 2015 Will Bond, Mjumbe Wawatu Ukweli, 2012 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, version 3 only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# GNU Lesser General Public License version 3 (see the file LICENSE).

"""The compiler for pybars."""


__all__ = [
    'Compiler',
    'strlist',
    'Scope'
    ]

__metaclass__ = type

from functools import partial
import re

import pybars
from pymeta.grammar import OMeta
from pybars.frompymeta import moduleFromSource

# This allows the code to run on Python 2 and 3 by
# creating a consistent reference for the appropriate
# string class
try:
    str_class = unicode
except NameError:
    # Python 3 support
    str_class = str

import collections

# Flag for testing
debug = False

# preserve reference to the builtin compile.
_compile = compile

# Note that unless we presume handlebars is only generating valid html, we have
# to accept anything - so a broken template won't be all that visible - it will
# just render literally (because the anything rule matches it).

# this grammar generates a tokenised tree
handlebars_grammar = r"""

template ::= (<text> | <templatecommand>)*:body => ['template'] + body
text ::= <newline_text> | <whitespace_text> | <other_text>
newline_text ::= (~(<start>) ('\r'?'\n'):char) => ('newline', u'' + char)
whitespace_text ::= (~(<start>) (' '|'\t'))+:text => ('whitespace', u''.join(text))
other_text ::= (~(<start>) <anything>)+:text => ('literal', u''.join(text))
other ::= <anything>:char => ('literal', u'' + char)
templatecommand ::= <blockrule>
    | <comment>
    | <escapedexpression>
    | <expression>
    | <partial>
start ::= '{' '{'
finish ::= '}' '}'
comment ::= <start> '!' (~(<finish>) <anything>)* <finish> => ('comment', )
space ::= ' '|'\t'|'\r'|'\n'
arguments ::= (<space>+ (<kwliteral>|<literal>|<path>|<subexpression>))*:arguments => arguments
subexpression ::= '(' <spaces> <path>:p (<space>+ (<kwliteral>|<literal>|<path>|<subexpression>))*:arguments <spaces> ')' => ('subexpr', p, arguments)
expression_inner ::= <spaces> <path>:p <arguments>:arguments <spaces> <finish> => (p, arguments)
expression ::= <start> '{' <expression_inner>:e '}' => ('expand', ) + e
    | <start> '&' <expression_inner>:e => ('expand', ) + e
escapedexpression ::= <start> <expression_inner>:e => ('escapedexpand', ) + e
block_inner ::= <spaces> <symbol>:s <arguments>:args <spaces> <finish>
    => (u''.join(s), args)
partial_inner ::= <spaces> <partialname>:s <arguments>:args <spaces> <finish>
    => (u''.join(s), args)
alt_inner ::= <spaces> ('^' | 'e' 'l' 's' 'e') <spaces> <finish>
partial ::= <start> '>' <partial_inner>:i => ('partial',) + i
path ::= ~('/') <pathseg>+:segments => ('path', segments)
kwliteral ::= <safesymbol>:s '=' (<literal>|<path>|<subexpression>):v => ('kwparam', s, v)
literal ::= (<string>|<integer>|<boolean>|<null>|<undefined>):thing => ('literalparam', thing)
string ::= '"' <notdquote>*:ls '"' => u'"' + u''.join(ls) + u'"'
    | "'" <notsquote>*:ls "'" => u"'" + u''.join(ls) + u"'"
integer ::= '-'?:sign <digit>+:ds => int((sign if sign else '') + ''.join(ds))
boolean ::= <false>|<true>
false ::= 'f' 'a' 'l' 's' 'e' => False
true ::= 't' 'r' 'u' 'e' => True
null ::= ('n' 'u' 'l' 'l') => None
undefined ::= ('u' 'n' 'd' 'e' 'f' 'i' 'n' 'e' 'd') => None
notdquote ::= <escapedquote>
    | '\n' => '\\n'
    | '\r' => '\\r'
    | '\\' => '\\\\'
    | (~('"') <anything>)
notsquote ::= <escapedquote>
    | '\n' => '\\n'
    | '\r' => '\\r'
    | '\\' => '\\\\'
    | (~("'") <anything>)
escapedquote ::= '\\' '"' => '\\"'
    | "\\" "'" => "\\'"
notclosebracket ::= (~(']') <anything>)
safesymbol ::=  ~<alt_inner> '['? (<letter>|'_'):start (<letterOrDigit>|'_')+:symbol ']'? => start + u''.join(symbol)
symbol ::=  ~<alt_inner> '['? (<letterOrDigit>|'-'|'@')+:symbol ']'? => u''.join(symbol)
partialname ::= ~<alt_inner> ('['|'"')? (~(<space>|<finish>|']'|'"' ) <anything>)+:symbol (']'|'"')? => u''.join(symbol)
pathseg ::= '[' <notclosebracket>+:symbol ']' => u''.join(symbol)
    | ('@' '.' '.' '/') => u'@@_parent'
    | <symbol>
    | '/' => u''
    | ('.' '.' '/') => u'@_parent'
    | '.' => u''
pathfinish :expected ::= <start> '/' <path>:found ?(found == expected) <finish>
symbolfinish :expected ::= <start> '/' <symbol>:found ?(found == expected) <finish>
blockrule ::= <start> '#' <block_inner>:i
      <template>:t <alttemplate>:alt_t <symbolfinish i[0]> => ('block',) + i + (t, alt_t)
    | <start> '^' <block_inner>:i
      <template>:t <symbolfinish i[0]> => ('invertedblock',) + i + (t,)
alttemplate ::= (<start> <alt_inner> <template>)?:alt_t => alt_t or []
"""

# this grammar compiles the template to python
compile_grammar = """
compile ::= <prolog> <rule>* => builder.finish()
prolog ::= "template" => builder.start()
rule ::= <literal>
    | <expand>
    | <escapedexpand>
    | <comment>
    | <block>
    | <invertedblock>
    | <partial>
block ::= [ "block" <anything>:symbol [<arg>*:arguments] [<compile>:t] [<compile>?:alt_t] ] => builder.add_block(symbol, arguments, t, alt_t)
comment ::= [ "comment" ]
literal ::= [ ( "literal" | "newline" | "whitespace" ) :value ] => builder.add_literal(value)
expand ::= [ "expand" <path>:value [<arg>*:arguments]] => builder.add_expand(value, arguments)
escapedexpand ::= [ "escapedexpand" <path>:value [<arg>*:arguments]] => builder.add_escaped_expand(value, arguments)
invertedblock ::= [ "invertedblock" <anything>:symbol [<arg>*:arguments] [<compile>:t] ] => builder.add_invertedblock(symbol, arguments, t)
partial ::= ["partial" <anything>:symbol [<arg>*:arguments]] => builder.add_partial(symbol, arguments)
path ::= [ "path" [<pathseg>:segment]] => ("simple", segment)
 | [ "path" [<pathseg>+:segments] ] => ("complex", u'resolve(context, "'  + u'","'.join(segments) + u'")' )
complexarg ::= [ "path" [<pathseg>+:segments] ] => u'resolve(context, "'  + u'","'.join(segments) + u'")'
    | [ "subexpr" ["path" <pathseg>:name] [<arg>*:arguments] ] => u'resolve_subexpr(helpers, "' + name + '", context' + (u', ' + u', '.join(arguments) if arguments else u'') + u')'
    | [ "literalparam" <anything>:value ] => {str_class}(value)
arg ::= [ "kwparam" <anything>:symbol <complexarg>:a ] => {str_class}(symbol) + '=' + a
    | <complexarg>
pathseg ::= "/" => ''
    | "." => ''
    | "" => ''
    | "this" => ''
pathseg ::= <anything>:symbol => u''.join(symbol)
"""
compile_grammar = compile_grammar.format(str_class=str_class.__name__)


class PybarsError(Exception):

    pass


class strlist(list):

    """A quasi-list to let the template code avoid special casing."""

    def __str__(self):  # Python 3
        return ''.join(self)

    def __unicode__(self):  # Python 2
        return u''.join(self)

    def grow(self, thing):
        """Make the list longer, appending for unicode, extending otherwise."""
        if type(thing) == str_class:
            self.append(thing)

        # This will only ever match in Python 2 since str_class is str in
        # Python 3.
        elif type(thing) == str:
            self.append(unicode(thing))

        else:
            # Recursively expand to a flat list; may deserve a C accelerator at
            # some point.
            for element in thing:
                self.grow(element)


_map = {
    '&': '&amp;',
    '"': '&quot;',
    "'": '&#x27;',
    '`': '&#x60;',
    '<': '&lt;',
    '>': '&gt;',
    }


def substitute(match, _map=_map):
    return _map[match.group(0)]


_escape_re = re.compile(r"&|\"|'|`|<|>")


def escape(something, _escape_re=_escape_re, substitute=substitute):
    return _escape_re.sub(substitute, something)


def pick(context, name, default=None):
    if isinstance(name, str) and hasattr(context, name):
        return getattr(context, name)
    if hasattr(context, 'get'):
        return context.get(name)
    try:
        return context[name]
    except (KeyError, TypeError):
        return default


sentinel = object()


class Scope:

    def __init__(self, context, parent, root, overrides=None, index=None, key=None, first=None, last=None):
        self.context = context
        self.parent = parent
        self.root = root
        # Must be dict of keys and values
        self.overrides = overrides
        self.index = index
        self.key = key
        self.first = first
        self.last = last

    def get(self, name, default=None):
        if name == '@root':
            return self.root
        if name == '@_parent':
            return self.parent
        if name == '@index' and self.index is not None:
            return self.index
        if name == '@key' and self.key is not None:
            return self.key
        if name == '@first' and self.first is not None:
            return self.first
        if name == '@last' and self.last is not None:
            return self.last
        if name == 'this':
            return self.context
        if self.overrides and name in self.overrides:
            return self.overrides[name]
        return pick(self.context, name, default)
    __getitem__ = get

    def __len__(self):
        return len(self.context)

    # Added for Python 3
    def __str__(self):
        return str(self.context)

    # Only called in Python 2
    def __unicode__(self):
        return unicode(self.context)


def resolve(context, *segments):
    carryover_data = False

    # This makes sure that bare "this" paths don't return a Scope object
    if segments == ('',) and isinstance(context, Scope):
        return context.get('this')

    for segment in segments:

        # Handle @../index syntax by popping the extra @ along the segment path
        if carryover_data:
            carryover_data = False
            segment = u'@%s' % segment
        if len(segment) > 1 and segment[0:2] == '@@':
            segment = segment[1:]
            carryover_data = True

        if context is None:
            return None
        if segment in (None, ""):
            continue
        if type(context) in (list, tuple):
            offset = int(segment)
            context = context[offset]
        elif isinstance(context, Scope):
            context = context.get(segment)
        else:
            context = pick(context, segment)
    return context


def resolve_subexpr(helpers, name, context, *args, **kwargs):
    if name not in helpers:
        raise PybarsError(u"Could not find property %s" % (name,))
    return helpers[name](context, *args, **kwargs)


def _each(this, options, context):
    result = strlist()

    # All sequences in python have a length
    try:
        last_index = len(context) - 1

        # If there are no items, we want to trigger the else clause
        if last_index < 0:
            raise IndexError()

    except (TypeError, IndexError):
        return options['inverse'](this)

    # We use the presence of a keys method to determine if the
    # key attribute should be passed to the block handler
    has_keys = hasattr(context, 'keys')

    index = 0
    for value in context:
        kwargs = {
            'index': index,
            'first': index == 0,
            'last': index == last_index
        }

        if has_keys:
            kwargs['key'] = value
            value = context[value]

        scope = Scope(value, this, options['root'], **kwargs)
        result.grow(options['fn'](scope))

        index += 1

    return result


def _if(this, options, context):
    if isinstance(context, collections.Callable):
        context = context(this)
    if context:
        return options['fn'](this)
    else:
        return options['inverse'](this)


def _log(this, context):
    pybars.log(context)


def _unless(this, options, context):
    if not context:
        return options['fn'](this)


def _lookup(this, context, key):
    try:
        return context[key]
    except (KeyError, IndexError, TypeError):
        return


def _blockHelperMissing(this, options, context):
    if isinstance(context, collections.Callable):
        context = context(this)
    if context != u"" and not context:
        return options['inverse'](this)
    if type(context) in (list, strlist, tuple):
        return _each(this, options, context)
    if context is True:
        callwith = this
    else:
        callwith = context
    return options['fn'](callwith)


def _helperMissing(scope, name, *args):
    if not args:
        return None
    raise PybarsError(u"Could not find property %s" % (name,))


def _with(this, options, context):
    return options['fn'](context)


# scope for the compiled code to reuse globals
_pybars_ = {
    'helpers': {
        'blockHelperMissing': _blockHelperMissing,
        'each': _each,
        'if': _if,
        'helperMissing': _helperMissing,
        'log': _log,
        'unless': _unless,
        'with': _with,
        'lookup': _lookup,
    },
}


class CodeBuilder:

    """Builds code for a template."""

    def __init__(self):
        self.stack = []

    def start(self):
        self.stack.append((strlist(), {}))
        self._result, self._locals = self.stack[-1]
        # Context may be a user hash or a Scope (which injects '@_parent' to
        # implement .. lookups). The JS implementation uses a vector of scopes
        # and then interprets a linear walk-up, which is why there is a
        # disabled test showing arbitrary complex path manipulation: the scope
        # approach used here will probably DTRT but may be slower: reevaluate
        # when profiling.
        self._result.grow(u"def render(context, helpers=None, partials=None, root=None):\n")
        self._result.grow(u"    result = strlist()\n")
        self._result.grow(u"    _helpers = dict(pybars['helpers'])\n")
        self._result.grow(u"    if helpers is not None: _helpers.update(helpers)\n")
        self._result.grow(u"    helpers = _helpers\n")
        self._result.grow(u"    if partials is None: partials = {}\n")
        self._result.grow(u"    if root is None: root = context\n")
        # Expose used functions and helpers to the template.
        self._locals['strlist'] = strlist
        self._locals['escape'] = escape
        self._locals['Scope'] = Scope
        self._locals['PybarsError'] = PybarsError
        self._locals['partial'] = partial
        self._locals['pybars'] = _pybars_
        self._locals['resolve'] = resolve
        self._locals['resolve_subexpr'] = resolve_subexpr

    def finish(self):
        if debug:
            print('Locals')
            print('------')
            for key in self._locals:
                if key in ['strlist', 'escape', 'Scope', 'PybarsError', 'partial', 'pybars', 'resolve', 'resolve_subexpr']:
                    continue
                print("%s = %s" % (key, repr(self._locals[key])))
            print('')
        self._result.grow(u"    return result\n")
        lines, ns = self.stack.pop(-1)
        source = str_class(u"".join(lines))
        self._result = self.stack and self.stack[-1][0]
        self._locals = self.stack and self.stack[-1][1]
        fn = moduleFromSource(source, 'render', globalsDict=ns, registerModule=True)
        if debug:
            print('Compiled Python')
            print('---------------')
            print(source)
        return fn

    def allocate_value(self, value):
        name = 'constant_%d' % len(self._locals)
        self._locals[name] = value
        return name

    def _wrap_nested(self, name):
        return u"partial(%s, helpers=helpers, partials=partials, root=root)" % name

    def add_block(self, symbol, arguments, nested, alt_nested):
        name = self.allocate_value(nested)
        if alt_nested:
            alt_name = self.allocate_value(alt_nested)
        call = self.arguments_to_call(arguments)
        self._result.grow([
            u"    options = {'fn': %s}\n" % self._wrap_nested(name),
            u"    options['helpers'] = helpers\n"
            u"    options['partials'] = partials\n"
            u"    options['root'] = root\n"
            ])
        if alt_nested:
            self._result.grow([
                u"    options['inverse'] = ",
                self._wrap_nested(alt_name),
                u"\n"
                ])
        else:
            self._result.grow([
                u"    options['inverse'] = lambda this: None\n"
                ])
        self._result.grow([
            u"    value = helper = helpers.get('%s')\n" % symbol,
            u"    if value is None:\n"
            u"        value = context.get('%s')\n" % symbol,
            u"    if helper and callable(helper):\n"
            u"        this = context if isinstance(context, Scope) else Scope(context, context, root)\n"
            u"        value = value(this, options, %s\n" % call,
            u"    else:\n"
            u"        helper = helpers['blockHelperMissing']\n"
            u"        value = helper(context, options, value)\n"
            u"    if value is None: value = ''\n"
            u"    result.grow(value)\n"
            ])

    def add_literal(self, value):
        name = self.allocate_value(value)
        self._result.grow(u"    result.append(%s)\n" % name)

    def _lookup_arg(self, arg):
        if not arg:
            return u"context"
        return arg

    def arguments_to_call(self, arguments):
        params = list(map(self._lookup_arg, arguments))
        return u", ".join(params) + ")"

    def find_lookup(self, path, path_type, call):
        if path and path_type == "simple":  # simple names can reference helpers.
            # TODO: compile this whole expression in the grammar; for now,
            # fugly but only a compile time overhead.
            # XXX: just rm.
            realname = path.replace('.get("', '').replace('")', '')
            self._result.grow([
                u"    value = helpers.get('%s')\n" % realname,
                u"    if value is None:\n"
                u"        value = resolve(context, '%s')\n" % path,
                ])
        elif path_type == "simple":
            realname = None
            self._result.grow([
                u"    value = resolve(context, '%s')\n" % path,
                ])
        else:
            realname = None
            self._result.grow(u"    value = %s\n" % path)
        self._result.grow([
            u"    if callable(value):\n"
            u"        this = context if isinstance(context, Scope) else Scope(context, context, root)\n"
            u"        value = value(this, %s\n" % call,
            ])
        if realname:
            self._result.grow(
                u"    elif value is None:\n"
                u"        this = context if isinstance(context, Scope) else Scope(context, context, root)\n"
                u"        value = helpers.get('helperMissing')(this, '%s', %s\n"
                    % (realname, call)
                )
        self._result.grow(u"    if value is None: value = ''\n")

    def add_escaped_expand(self, path_type_path, arguments):
        (path_type, path) = path_type_path
        call = self.arguments_to_call(arguments)
        self.find_lookup(path, path_type, call)
        self._result.grow([
            u"    type_ = type(value)\n",
            u"    if type_ is not strlist:\n",
            u"        if type_ is bool:\n",
            u"            value = 'true' if value else 'false'\n",
            u"        else:\n",
            u"            value = escape(%s(value))\n" % str_class.__name__,
            u"    result.grow(value)\n"
            ])

    def add_expand(self, path_type_path, arguments):
        (path_type, path) = path_type_path
        call = self.arguments_to_call(arguments)
        self.find_lookup(path, path_type, call)
        self._result.grow([
            u"    type_ = type(value)\n",
            u"    if type_ is not strlist:\n",
            u"        if type_ is bool:\n",
            u"            value = 'true' if value else 'false'\n",
            u"        else:\n",
            u"            value = %s(value)\n" % str_class.__name__,
            u"    result.grow(value)\n"
            ])

    def _debug(self):
        self._result.grow(u"    import pdb;pdb.set_trace()\n")

    def add_invertedblock(self, symbol, arguments, nested):
        # This may need to be a blockHelperMissing clal as well.
        name = self.allocate_value(nested)
        self._result.grow([
            u"    value = context.get('%s')\n" % symbol,
            u"    if not value:\n"
            u"    "])
        self._invoke_template(name, "context")

    def _invoke_template(self, fn_name, this_name):
        self._result.grow([
            u"    result.grow(",
            fn_name,
            u"(",
            this_name,
            u", helpers=helpers, partials=partials, root=root))\n"
            ])

    def add_partial(self, symbol, arguments):
        arg = ""

        overrides = None
        positional_args = 0
        if arguments:
            for argument in arguments:
                kwmatch = re.match('(\w+)=(.+)$', argument)
                if kwmatch:
                    if not overrides:
                        overrides = {}
                    overrides[kwmatch.group(1)] = kwmatch.group(2)
                else:
                    if positional_args != 0:
                        raise PybarsError("An extra positional argument was passed to a partial")
                    positional_args += 1
                    arg = argument

        overrides_literal = 'None'
        if overrides:
            overrides_literal = u'{'
            for key in overrides:
                overrides_literal += u'"%s": %s, ' % (key, overrides[key])
            overrides_literal += u'}'
        self._result.grow([u"    overrides = %s\n" % overrides_literal])

        self._result.grow([
            u"    if '%s' not in partials:\n" % symbol,
            u"        raise PybarsError('Partial \"%s\" not defined')\n" % symbol,
            u"    inner = partials['%s']\n" % symbol,
            u"    scope = Scope(%s, context, root, overrides=overrides)\n" % self._lookup_arg(arg)])
        self._invoke_template("inner", "scope")


class Compiler:

    """A handlebars template compiler.

    The compiler is not threadsafe: you need one per thread because of the
    state in CodeBuilder.
    """

    _handlebars = OMeta.makeGrammar(handlebars_grammar, {}, 'handlebars')
    _builder = CodeBuilder()
    _compiler = OMeta.makeGrammar(compile_grammar, {'builder': _builder})

    def __init__(self):
        self._helpers = {}

    def compile(self, source):
        """Compile source to a ready to run template.

        :param source: The template to compile - should be a unicode string.
        :return: A template ready to run.
        """
        if not isinstance(source, str_class):
            raise PybarsError("Template source must be a unicode string")

        tree, error = self._handlebars(source).apply('template')

        self.clean_whitespace(tree)

        if debug:
            print('\nAST')
            print('---')
            print(tree)
            print('')

        if error[1]:
            line_num = source.count('\n') + 1
            beginning_of_line = source.rfind('\n', 0, error[0])
            if beginning_of_line == -1:
                char_num = error[0]
            else:
                char_num = error[0] - beginning_of_line
            if error[1][0][0] == 'message':
                message = error[1][0][1]
            elif error[1][0][0] == 'expected':
                message = 'expected "%s"' % error[1][0][2]
            else:
                message = repr(error[1][0])
            raise PybarsError("Error at character %s of line %s - %s" % (char_num, line_num, message))

        return self._compiler(tree).apply('compile')[0]

    def clean_whitespace(self, tree):
        """
        Cleans up whitespace around block open and close tags if they are the
        only thing on the line

        :param tree:
            The AST - will be modified in place
        """

        pointer = 0
        end = len(tree)

        while pointer < end:
            piece = tree[pointer]
            if piece[0] == 'block':
                child_tree = piece[3]

                # Look at open tag, if the only other thing on the line is whitespace
                # then delete it so we don't introduce extra newlines to the output
                open_pre_whitespace = False
                open_pre_content = True
                if pointer > 1 and tree[pointer - 1][0] == 'whitespace' and (tree[pointer - 2][0] == 'newline' or tree[pointer - 2] == 'template'):
                    open_pre_whitespace = True
                    open_pre_content = False
                elif pointer > 0 and (tree[pointer - 1][0] == 'newline' or tree[pointer - 1] == 'template'):
                    open_pre_content = False

                open_post_whitespace = False
                open_post_content = True
                child_len = len(child_tree)
                if child_len > 2 and child_tree[1][0] == 'whitespace' and child_tree[2][0] == 'newline':
                    open_post_whitespace = True
                    open_post_content = False
                elif child_len > 1 and child_tree[1][0] == 'newline':
                    open_post_content = False

                if not open_pre_content and not open_post_content:
                    if open_pre_whitespace:
                        tree.pop(pointer - 1)
                        pointer -= 1
                        end -= 1
                    if open_post_whitespace:
                        child_tree.pop(1)
                    child_tree.pop(1)  # trailing newline

                # Do the same thing, but for the close tag
                close_pre_whitespace = False
                close_pre_content = True
                child_len = len(child_tree)
                if child_len > 2 and child_tree[child_len - 1][0] == 'whitespace' and child_tree[child_len - 2][0] == 'newline':
                    close_pre_whitespace = True
                    close_pre_content = False
                elif child_len > 1 and child_tree[child_len - 1][0] == 'newline':
                    close_pre_content = False

                close_post_whitespace = False
                close_post_content = True
                tree_len = len(tree)
                if tree_len > pointer + 2 and tree[pointer + 1][0] == 'whitespace' and tree[pointer + 2][0] == 'newline':
                    close_post_whitespace = True
                    close_post_content = False
                elif tree_len == pointer + 2 and tree[pointer + 1][0] == 'whitespace':
                    close_post_whitespace = True
                    close_post_content = False
                elif tree_len > pointer + 1 and tree[pointer + 1][0] == 'newline':
                    close_post_content = False
                elif tree_len == pointer + 1:
                    close_post_content = False

                if not close_pre_content and not close_post_content:
                    if close_pre_whitespace:
                        child_tree.pop()
                    child_tree.pop()  # preceeding newline
                    if close_post_whitespace:
                        tree.pop(pointer + 1)
                        end -= 1

                self.clean_whitespace(child_tree)

            pointer += 1
