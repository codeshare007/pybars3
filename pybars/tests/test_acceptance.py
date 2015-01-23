# Copyright (C) 2011 by Yehuda Katz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""A port of the acceptance test for handlebars.js."""

from testtools import TestCase
from testtools.matchers import Equals

try:
    str_class = unicode
except NameError:
    # Python 3 support
    str_class = str

import sys

import pybars
from pybars import (
    Compiler,
    strlist,
    )
from pybars.tests.test__compiler import render


class RendersItself:

    def __str__(self):
        return "RendersItself()"

    def match(self, source):
        return Equals(source).match(render(source, {}))


class TestAcceptance(TestCase):

    def test_basic_context(self):
        self.assertEqual(
            "Goodbye\ncruel\nworld!",
            render(u"Goodbye\n{{cruel}}\n{{world}}!",
                {'cruel': "cruel", 'world': "world"}))

    def test_comments_ignored(self):
        self.assertEqual(
            "Goodbye\ncruel\nworld!",
            render(u"{{! Goodbye}}Goodbye\n{{cruel}}\n{{world}}!",
                {'cruel': "cruel", 'world': "world"}))

    def test_booleans(self):
        template = u"{{#goodbye}}GOODBYE {{/goodbye}}cruel {{world}}!"
        self.assertEqual(
            "GOODBYE cruel world!",
            render(template, {'goodbye': True, 'world': 'world'}))
        self.assertEqual(
            "cruel world!",
            render(template, {'goodbye': False, 'world': 'world'}))

    def test_zeros(self):
        self.assertEqual("num1: 42, num2: 0",
            render(u"num1: {{num1}}, num2: {{num2}}", {'num1': 42, 'num2': 0}))
        self.assertEqual("num: 0",
            render(u"num: {{.}}", 0))
        self.assertEqual("num: 0",
            render(u"num: {{num1/num2}}", {'num1': {'num2': 0}}))

    def test_negative_int_literal(self):
        self.assertEqual("str int int",
            render(u"{{type \"string\"}} {{type 1}} {{type -1}}", None,
            helpers={'type': lambda s, v: type(v).__name__}))
        self.assertEqual("string 1 -1",
            render(u"{{echo \"string\"}} {{echo 1}} {{echo -1}}", None,
            helpers={'echo': lambda s, v: str(v)}))

    def test_newlines(self):
        self.assertThat(u"Alan's\nTest", RendersItself())
        self.assertThat(u"Alan's\rTest", RendersItself())

    def test_escaping_text(self):
        self.assertThat(u"Awesome's", RendersItself())
        self.assertThat(u"Awesome\\", RendersItself())
        self.assertThat(u"Awesome\\\\ foo", RendersItself())
        self.assertEqual(u"Awesome \\",
            render(u"Awesome {{foo}}", {'foo': '\\'}))
        self.assertThat(u' " " ', RendersItself())

    def test_escaping_expressions(self):
        self.assertEqual('&\"\\<>',
            render(u"{{{awesome}}}", {'awesome': "&\"\\<>"}))
        self.assertEqual('&\"\\<>',
            render(u"{{&awesome}}", {'awesome': "&\"\\<>"}))
        self.assertEqual(u'&amp;&quot;&#x27;&#x60;\\&lt;&gt;',
            render(u"{{awesome}}", {'awesome': "&\"'`\\<>"}))

    def test_functions_returning_safestrings(self):
        # Note that we use liststr for our safestring implementation.
        text = '&\"\\<>'
        self.assertEqual(text,
            render(u'{{awesome}}', {'awesome': lambda this: strlist([text])}))

    def test_functions_called(self):
        text = 'Awesome'
        self.assertEqual(text,
            render(u'{{awesome}}', {'awesome': lambda this: text}))
        self.assertEqual(text,
            render(u'{{{awesome}}}', {'awesome': lambda this: text}))

    def test_functions_can_take_context_arguments(self):
        def awesome(this, context):
            return context
        self.assertEqual("Frank",
            render(u"{{awesome frank}}",
                {'awesome': awesome, 'frank': 'Frank'}))
        self.assertEqual("Frank",
            render(u"{{{awesome frank}}}",
                {'awesome': awesome, 'frank': 'Frank'}))

    def test_paths_can_contain_hyphens(self):
        self.assertEqual(u"baz", render(u"{{foo-bar}}", {"foo-bar": "baz"}))

    def test_nested_paths_access_nested_objects(self):
        self.assertEqual(u"Goodbye beautiful world!",
            render(u"Goodbye {{alan/expression}} world!",
                {'alan': {'expression': 'beautiful'}}))

    def test_nested_paths_to_empty_string_renders(self):
        self.assertEqual(u"Goodbye  world!",
            render(u"Goodbye {{alan/expression}} world!",
                {'alan': {'expression': ''}}))

    def test_literal_paths_can_be_used(self):
        self.assertEqual(u"Goodbye beautiful world!",
            render(u"Goodbye {{[@alan]/expression}} world!",
                {'@alan': {'expression': 'beautiful'}}))

    def skipped_upstream_not_ported_bad_idea_nested_paths(self):
        pass
#        test("--- TODO --- bad idea nested paths", function() {
#            return;
#            var hash     = {goodbyes: [{text: "goodbye"}, {text: "Goodbye"}, {text: "GOODBYE"}], world: "world"};
#            shouldThrow(function() {
#                CompilerContext.compile("{{#goodbyes}}{{../name/../name}}{{/goodbyes}}")(hash);
#                }, Handlebars.Exception,
#                "Cannot jump (..) into previous context after moving into a context.");
#            var string = "{{#goodbyes}}{{.././world}} {{/goodbyes}}";
#            shouldCompileTo(string, hash, "world world world ", "Same context (.) is ignored in paths");
#        });

    def test_current_context_does_not_invoke_helpers(self):
        self.assertEqual("test: ",
            render(u"test: {{.}}", None, helpers={'helper': "notcallable"}))

    def test_complex_but_empty_paths(self):
        self.assertEqual("",
            render(u"{{person/name}}", {'person': {'name': None}}))
        self.assertEqual("",
            render(u"{{person/name}}", {'person': {}}))

    def test_this_keyword_in_paths_simple(self):
        source = u"{{#goodbyes}}{{this}}{{/goodbyes}}"
        context = {'goodbyes': ["goodbye", "Goodbye", "GOODBYE"]}
        self.assertEqual("goodbyeGoodbyeGOODBYE", render(source, context))

    def test_this_keyword_in_paths_complex(self):
        source = u"{{#hellos}}{{this/text}}{{/hellos}}"
        context = {'hellos': [
            {'text': 'hello'}, {'text': 'Hello'}, {'text': "HELLO"}]}
        self.assertEqual("helloHelloHELLO", render(source, context))

    def test_inverted_sections(self):
        source = (
            u"{{#goodbyes}}{{this}}{{/goodbyes}}"
            u"{{^goodbyes}}Right On!{{/goodbyes}}")
        # Unset value
        self.assertEqual("Right On!", render(source, {}))
        # False value
        self.assertEqual("Right On!", render(source, {'goodbyes': False}))
        # Empty list
        self.assertEqual("Right On!", render(source, {'goodbyes': []}))

    def test_array_iteration(self):
        source = u"{{#goodbyes}}{{text}}! {{/goodbyes}}cruel {{world}}!"
        context = {
            'goodbyes': [
                {'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}],
            'world': "world"}
        self.assertEqual("goodbye! Goodbye! GOODBYE! cruel world!",
            render(source, context))
        self.assertEqual("cruel world!",
            render(source, {'goodbyes': [], 'world': "world"}))

    def test_empty_block(self):
        source = u"{{#goodbyes}}{{/goodbyes}}cruel {{world}}!"
        context = {
            'goodbyes': [
                {'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}],
            'world': "world"}
        self.assertEqual("cruel world!", render(source, context))
        self.assertEqual("cruel world!",
            render(source, {'goodbyes': [], 'world': "world"}))

    def test_nested_iteration(self):
        # Empty upstream
        pass

    def test_block_with_complex_lookup(self):
        source = u"{{#goodbyes}}{{text}} cruel {{../name}}! {{/goodbyes}}"
        context = {'name': "Alan", 'goodbyes': [
            {'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}]}
        self.assertEqual(
            "goodbye cruel Alan! Goodbye cruel Alan! GOODBYE cruel Alan! ",
            render(source, context))

    def test_parent_lookup(self):
        source = u"{{#goodbyes}}{{text}} cruel {{@_parent.name}}! {{/goodbyes}}"
        context = {'name': "Alan", 'goodbyes': [
            {'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}]}
        self.assertEqual(
            "goodbye cruel Alan! Goodbye cruel Alan! GOODBYE cruel Alan! ",
            render(source, context))

    def test_helper_with_complex_lookup(self):
        template = u"{{#goodbyes}}{{{link ../prefix}}}{{/goodbyes}}"
        context = {
            'prefix': "/root",
            'goodbyes': [{'text': "Goodbye", 'url': "goodbye"}]}
        def link(this, prefix):
            return (u"<a href='" + prefix + u"/" +
                this.get('url') + u"'>" +
                this.get('text') + u"</a>")
        helpers = {'link': link}
        self.assertEqual("<a href='/root/goodbye'>Goodbye</a>",
            render(template, context, helpers=helpers))

    def test_helper_block_with_complex_lookup(self):
        template = u"{{#goodbyes}}{{../name}}{{/goodbyes}}"
        context = {'name': "Alan"}
        def goodbyes(this, options):
            result = strlist()
            for bye in ["Goodbye", "goodbye", "GOODBYE"]:
                result.grow(bye)
                result.grow(' ')
                result.grow(options['fn'](this))
                result.grow("! ")
            return result
        helpers = {'goodbyes': goodbyes}
        self.assertEqual("Goodbye Alan! goodbye Alan! GOODBYE Alan! ",
            render(template, context, helpers=helpers))

    def test_helper_with_complex_lookup_and_nested_template(self):
        template = \
            u"{{#goodbyes}}{{#link ../prefix}}{{text}}{{/link}}{{/goodbyes}}"
        context = {
            'prefix': '/root', 'goodbyes': [{'text': "Goodbye", 'url': "goodbye"}]}
        def link(this, options, prefix):
            return u"<a href='" + str_class(prefix) + u"/" + this['url'] + u"'>" + str_class(options['fn'](this)) + u"</a>"
        self.assertEqual(u"<a href='/root/goodbye'>Goodbye</a>",
            render(template, context, helpers={'link': link}))

    def test_block_with_deep_nested_complex_lookup(self):
        template = u"{{#outer}}Goodbye "\
            u"{{#inner}}cruel {{../../omg}}{{/inner}}{{/outer}}"
        context = {'omg': "OMG!", 'outer': [{'inner': [{'text': "goodbye"}]}]}
        self.assertEqual(u"Goodbye cruel OMG!", render(template, context))

    def test_root_lookup(self):
        template = u"{{#outer}}Goodbye "\
            u"{{#inner}}cruel {{@root.top}}{{/inner}}{{/outer}}"
        context = {'top': "world", 'outer': [{'inner': [{'text': "goodbye"}]}]}
        self.assertEqual(u"Goodbye cruel world", render(template, context))

    def test_block_helper(self):
        template = u"{{#goodbyes}}{{text}}! {{/goodbyes}}cruel {{world}}!"
        self.assertEqual(
            u"GOODBYE! cruel world!",
            render(template, {'world': "world"}, helpers={'goodbyes':
                lambda this, options: options['fn']({'text': "GOODBYE"})}))

    def test_block_helper_staying_in_the_same_context(self):
        template = u"{{#form}}<p>{{name}}</p>{{/form}}"
        helpers = {'form': lambda this, options: strlist([u"<form>", options['fn'](this), u"</form>"])}
        self.assertEqual("<form><p>Yehuda</p></form>",
            render(template, {'name': "Yehuda"}, helpers=helpers))

    def test_block_helper_should_have_context_in_this(self):
        template = u"<ul>{{#people}}<li>"\
            u"{{#link}}{{name}}{{/link}}</li>{{/people}}</ul>"
        def link(this, options):
            return strlist(('<a href="/people/', str_class(this['id']), '">', options['fn'](this), '</a>'))
        context = {"people": [
            {"name": "Alan", "id": 1},
            {"name": "Yehuda", "id": 2}
            ]}
        result = "<ul><li><a href=\"/people/1\">Alan</a></li>"\
            "<li><a href=\"/people/2\">Yehuda</a></li></ul>"
        self.assertEqual(
            result, render(template, context, helpers={'link': link}))

    def test_block_helper_for_undefined_value(self):
        self.assertEqual(
            "", render(u"{{#empty}}shouldn't render{{/empty}}", {}))

    def test_block_helper_passing_a_new_context(self):
        template = u"{{#form yehuda}}<p>{{name}}</p>{{/form}}"
        context = {'yehuda': {'name': "Yehuda"}}
        expected = u"<form><p>Yehuda</p></form>"
        def form(this, options, context):
            return "<form>" + str_class(options['fn'](context)) + '</form>'
        helpers = {'form': form}
        self.assertEqual(expected, render(template, context, helpers=helpers))

    def test_block_helper_passing_a_complex_path_context(self):
        source = u"{{#form yehuda/cat}}<p>{{name}}</p>{{/form}}"
        def form(this, options, context):
            return u"<form>" + str_class(options['fn'](context)) + u"</form>"
        context = {'yehuda': {'name': "Yehuda", 'cat': {'name': "Harold"}}}
        self.assertEqual("<form><p>Harold</p></form>",
            render(source, context, helpers={'form': form}))

    def test_subexpression(self):
        source = u"{{#para (fold 'foo' val)}}{{foo}}{{/para}}"
        def para(this, options, values_dict):
            return strlist(u'<p>') + options['fn'](values_dict) + strlist(u'</p>')
        def fold(this, key, val):
            return {key: val}
        context = {'val': 'bar'}
        self.assertEqual("<p>bar</p>",
            render(source, context, helpers={'para': para, 'fold': fold}))

    def test_subexpression_containing_keyword(self):
        source = u"{{#para (fold2 'foo' value=val)}}{{foo}}{{/para}}"
        def para(this, options, values_dict):
            return strlist(u'<p>') + options['fn'](values_dict) + strlist(u'</p>')
        def fold2(this, key, value=None):
            return {key: value}
        context = {'val': 'bar'}
        self.assertEqual("<p>bar</p>",
            render(source, context, helpers={'para': para, 'fold2': fold2}))

    def test_subexpression_as_keyword(self):
        source = u"{{#para2 values_dict=(fold2 'foo' value=val)}}{{foo}}{{/para2}}"
        def para2(this, options, blah=None, values_dict=None):
            return strlist(u'<p>') + options['fn'](values_dict) + strlist(u'</p>')
        def fold2(this, key, value=None):
            return {key: value}
        context = {'val': 'bar'}
        self.assertEqual("<p>bar</p>",
            render(source, context, helpers={'para2': para2, 'fold2': fold2}))

    def test_nested_block_helpers(self):
        source = \
            u"{{#form yehuda}}<p>{{name}}</p>{{#link}}Hello{{/link}}{{/form}}"
        def link(this, options):
            return (
                "<a href='" + this['name'] + "'>" +
                str_class(options['fn'](this)) + "</a>")
        def form(this, options, context):
            return "<form>" + str_class(options['fn'](context)) + "</form>"
        self.assertEqual(
            "<form><p>Yehuda</p><a href='Yehuda'>Hello</a></form>",
            render(source, {'yehuda': {'name': "Yehuda"}}, helpers={
                'link': link, 'form': form}))

    def test_block_inverted_sections(self):
        self.assertEqual("No people",
            render(u"{{#people}}{{name}}{{^}}{{none}}{{/people}}",
                {'none': "No people"}))

    def test_block_inverted_sections_with_empty_arrays(self):
        self.assertEqual("No people",
            render(u"{{#people}}{{name}}{{^}}{{none}}{{/people}}",
                {'none': "No people", 'people': []}))

    def test_block_helper_inverted_sections(self):
        def list(this, options, context):
            if len(context):
                out = "<ul>"
                for thing in context:
                    out += "<li>"
                    out += str_class(options['fn'](thing))
                    out += "</li>"
                out += "</ul>"
                return out
            else:
                return "<p>" + str_class(options['inverse'](this)) + "</p>"
        context = {'people': [{'name': "Alan"}, {'name': "Yehuda"}]}
        empty = {'people': []}
        rootMessage = {'people': [], 'message': "Nobody's here"}
        src1 = u"{{#list people}}{{name}}{{^}}<em>Nobody's here</em>{{/list}}"
        src2 = u"{{#list people}}Hello{{^}}{{message}}{{/list}}"
        src3 = u"{{#list people}}{{name}}{{else}}<em>Nobody's here</em>{{/list}}"
        helpers = {'list': list}
        # inverse not executed by helper:
        self.assertEqual("<ul><li>Alan</li><li>Yehuda</li></ul>",
            render(src1, context, helpers))
        # inverse can be called by a helper
        self.assertEqual("<p><em>Nobody's here</em></p>",
            render(src1, empty, helpers))
        # the expected context of the inverse is the this parameter to block
        # helpers.
        self.assertEqual("<p>Nobody&#x27;s here</p>",
            render(src2, rootMessage, helpers=helpers))
        # inverse can also be denoted by 'else':
        self.assertEqual("<ul><li>Alan</li><li>Yehuda</li></ul>",
            render(src3, context, helpers))
        self.assertEqual("<p><em>Nobody's here</em></p>",
            render(src3, empty, helpers))

    def test_providing_a_helpers_hash(self):
        self.assertEqual("Goodbye cruel world!",
            render(u"Goodbye {{cruel}} {{world}}!", {'cruel': "cruel"},
                helpers={'world': "world"}))
        self.assertEqual("Goodbye cruel world!",
            render(u"Goodbye {{#iter}}{{cruel}} {{world}}{{/iter}}!",
                {'iter': [{'cruel': "cruel"}]},
                helpers={'world': "world"}))

    def test_in_cases_of_conflict_helpers_before_context(self):
        self.assertEqual("helpers",
            render(u"{{lookup}}", {'lookup': 'Explicit'},
                helpers={'lookup': 'helpers'}))
        self.assertEqual("helpers",
            render(u"{{{lookup}}}", {'lookup': 'Explicit'},
                helpers={'lookup': 'helpers'}))
        self.assertEqual("Explicit",
            render(u"{{#lookup}}Explicit{{/lookup}}", {'lookup': []},
                helpers={'lookup': [{}]}))

    def test_the_helpers_hash_is_available_is_nested_contexts(self):
        self.assertEqual("helper",
            render(u"{{#outer}}{{#inner}}{{helper}}{{/inner}}{{/outer}}",
                {'outer': {'inner': {'unused': []}}},
                helpers={'helper': 'helper'}))

    def test_basic_partials(self):
        source = u"Dudes: {{#dudes}}{{> dude}}{{/dudes}}"
        partial = u"{{name}} ({{url}}) "
        context = {
            'dudes': [
                {'name': "Yehuda", 'url': "http://yehuda"},
                {'name': "Alan", 'url': "http://alan"}
                ]}
        self.assertEqual("Dudes: Yehuda (http://yehuda) Alan (http://alan) ",
            render(source, context, partials={'dude': partial}))

    def test_partials_with_context(self):
        source = u"Dudes: {{>dude dudes}}"
        partial = u"{{#this}}{{name}} ({{url}}) {{/this}}"
        context = {
            'dudes': [
                {'name': "Yehuda", 'url': "http://yehuda"},
                {'name': "Alan", 'url': "http://alan"}
                ]}
        self.assertEqual("Dudes: Yehuda (http://yehuda) Alan (http://alan) ",
            render(source, context, partials={'dude': partial}))

    def test_partials_too_many_args(self):
        source = u'Dudes: {{>dude dudes "extra"}}'
        partial = u"{{#this}}{{name}} ({{url}}) {{/this}}"
        context = {
            'dudes': [
                {'name': "Yehuda", 'url': "http://yehuda"},
                {'name': "Alan", 'url': "http://alan"}
                ]}
        self.assertRaises(Exception, render, source, context,
            partials={'dude': partial})

    def test_partials_kwargs(self):
        source = u'Dudes: {{#dudes}}{{>dude url="http://example"}}{{/dudes}}'
        partial = u"{{name}} ({{url}}) "
        context = {
            'dudes': [
                {'name': "Yehuda", 'url': "http://yehuda"},
                {'name': "Alan", 'url': "http://alan"}
                ]}
        self.assertEqual("Dudes: Yehuda (http://example) Alan (http://example) ",
            render(source, context, partials={'dude': partial}))

    def test_partial_in_a_partial(self):
        source = u"Dudes: {{#dudes}}{{>dude}}{{/dudes}}"
        dude_src = u"{{name}} {{> url}} "
        url_src = u"<a href='{{url}}'>{{url}}</a>"
        partials = {'dude': dude_src, 'url': url_src}
        context = {
            'dudes': [
                {'name': "Yehuda", 'url': "http://yehuda"},
                {'name': "Alan", 'url': "http://alan"}
                ]}
        self.assertEqual(
            "Dudes: Yehuda <a href='http://yehuda'>http://yehuda</a>"
            " Alan <a href='http://alan'>http://alan</a> ",
            render(source, context, partials=partials))

    def test_rendering_undefined_partial_throws_an_exception(self):
        self.assertRaises(Exception, render, u"{{> whatever}}", {})

    def test_root_nested_partial(self):
        source = u"Dudes: {{#dudes}}{{>dude}}{{/dudes}}"
        dude_src = u"{{name}} {{> url}} "
        url_src = u"<a href='{{url}}' target='{{@root.target}}'>{{url}}</a>"
        partials = {'dude': dude_src, 'url': url_src}
        context = {
            'target': '_blank',
            'dudes': [
                {'name': "Yehuda", 'url': "http://yehuda"},
                {'name': "Alan", 'url': "http://alan"}
                ]}
        self.assertEqual(
            "Dudes: Yehuda <a href='http://yehuda' target='_blank'>http://yehuda</a>"
            " Alan <a href='http://alan' target='_blank'>http://alan</a> ",
            render(source, context, partials=partials))

    def test_GH_14_a_partial_preceding_a_selector(self):
        source = u"Dudes: {{>dude}} {{another_dude}}"
        dude_src = u"{{name}}"
        context = {'name': "Jeepers", 'another_dude': "Creepers"}
        self.assertEqual("Dudes: Jeepers Creepers",
            render(source, context, partials=dict(dude=dude_src)))

    def test_partials_with_literal_paths(self):
        source = u"Dudes: {{> [dude]}}"
        dude_src = u"{{name}}"
        context = {'name': "Jeepers", 'another_dude': "Creepers"}
        self.assertEqual("Dudes: Jeepers",
            render(source, context, partials=dict(dude=dude_src)))

    def test_partials_with_string(self):
        source = u'Dudes: {{> "+404/asdf?.bar"}}';
        dude_src = u"{{name}}"
        context = {'name': "Jeepers", 'another_dude': "Creepers"}
        self.assertEqual("Dudes: Jeepers",
            render(source, context, partials={'+404/asdf?.bar':dude_src}))

    def test_simple_literals_work(self):
        source = u'Message: {{hello "world" 12 true false}}'
        def hello(this, param, times, bool1, bool2):
            self.assertEqual(True, bool1)
            self.assertEqual(False, bool2)
            self.assertEqual(12, times)
            return ("Hello " + param + " " + str_class(times) + " times: " +
                str_class(bool1) + " " + str_class(bool2))
        helpers = dict(hello=hello)
        self.assertEqual("Message: Hello world 12 times: True False",
            render(source, {}, helpers=helpers))

    def test_true(self):
        source = u"{{var}}"
        self.assertEqual("true",
            render(source, {'var': True}))

    def test_true_unescaped(self):
        source = u"{{{var}}}"
        self.assertEqual("true",
            render(source, {'var': True}))

    def test_false(self):
        source = u"{{var}}"
        self.assertEqual("false",
            render(source, {'var': False}))

    def test_false_unescaped(self):
        source = u"{{{var}}}"
        self.assertEqual("false",
            render(source, {'var': False}))

    def test_none(self):
        source = u"{{var}}"
        self.assertEqual("",
            render(source, {'var': None}))

    def test_none_unescaped(self):
        source = u"{{{var}}}"
        self.assertEqual("",
            render(source, {'var': None}))

    def test_null(self):
        source = u"Message: {{{hello null}}}"
        def hello(this, param):
            return "Hello " + ('' if param is None else param)
        self.assertEqual("Message: Hello ",
            render(source, {}, helpers=dict(hello=hello)))

    def test_undefined(self):
        source = u"Message: {{{hello undefined}}}"
        def hello(this, param):
            return "Hello " + ('' if param is None else param)
        self.assertEqual("Message: Hello ",
            render(source, {}, helpers=dict(hello=hello)))

    def test_using_a_quote_in_the_middle_of_a_parameter_raises_an_error(self):
        self.skipTest("<end> causes the grammar to fail weirdly!")
        compiler = Compiler()
        self.assertRaises(Exception,
            compiler.compile, u'Message: {{hello wo"rld"}}')

    def test_escaping_a_String_is_possible(self):
        source = u'Message: {{{hello "\\"world\\""}}}'
        def hello(this, param):
            return "Hello " + param
        self.assertEqual("Message: Hello \"world\"",
            render(source, {}, helpers=dict(hello=hello)))

    def test_it_works_with_single_quote_marks(self):
        source = u"Message: {{{hello 'Alan\\\'s world'}}}"
        def hello(this, param):
            return "Hello " + param
        self.assertEqual("Message: Hello Alan's world",
            render(source, {}, helpers=dict(hello=hello)))

    def test_simple_multi_params_work(self):
        source = u'Message: {{goodbye cruel world}}'
        context = {'cruel': "cruel", 'world': "world"}
        def goodbye(this, cruel, world):
            return "Goodbye " + cruel + " " + world
        self.assertEqual("Message: Goodbye cruel world",
            render(source, context, helpers=dict(goodbye=goodbye)))

    def test_block_multi_params_work(self):
        source = u'Message: {{#goodbye cruel world}}'\
            u'{{greeting}} {{adj}} {{noun}}{{/goodbye}}'
        context = {'cruel': "cruel", 'world': "world"}
        def goodbye(this, options, cruel, world):
            return options['fn'](
                {'greeting': "Goodbye", 'adj': cruel, 'noun': world})
        self.assertEqual("Message: Goodbye cruel world",
            render(source, context, helpers=dict(goodbye=goodbye)))

    def test_constructing_a_safestring_from_a_string_and_checking_its_type(self):
        reference = "testing 1, 2, 3"
        instance = strlist([reference])
        self.assertIsInstance(instance, strlist)
        self.assertEqual(str_class(reference), str_class(instance))

    def test_if_a_context_is_not_found_helperMissing_is_used(self):
        def link_to(this, helpername, context):
            if helpername == 'link_to':
                return strlist(("<a>", context, "</a>"))
        source = u"{{hello}} {{link_to world}}"
        context = {'hello': "Hello", 'world': "world"}
        self.assertEqual("Hello <a>world</a>",
            render(source, context, helpers=dict(helperMissing=link_to)))

    def test_Known_helper_should_render_helper(self):
        source = u"{{hello}}"
        self.assertEqual("foo",
            render(source, {}, helpers=dict(hello=lambda this: "foo"),
            knownHelpers=set(['hello'])))

    def test_Unknown_helper_in_knownHelpers_only_mode_should_be_passed_as_undefined(self):
        source = u"{{{typeof hello}}}"
        self.assertEqual("<type 'NoneType'>" if sys.version_info < (3,) else "<class 'NoneType'>",
            render(source, {}, helpers=dict(
                typeof=lambda this, arg: str_class(type(arg)), hello=lambda this: "foo"),
            knownHelpers=set(['typeof']), knownHelpersOnly=True))

    def test_Builtin_helpers_available_in_knownHelpers_only_mode(self):
        source = u"{{#unless foo}}bar{{/unless}}"
        self.assertEqual("bar",
            render(source, {}, knownHelpersOnly=True))

    def test_Field_lookup_works_in_knownHelpers_only_mode(self):
        source = u"{{foo}}"
        self.assertEqual("bar",
            render(source, {'foo': 'bar'}, knownHelpersOnly=True))

    def test_Conditional_blocks_work_in_knownHelpers_only_mode(self):
        source = u"{{#foo}}bar{{/foo}}"
        self.assertEqual("bar",
            render(source, {'foo': 'baz'}, knownHelpersOnly=True))

    def test_Invert_blocks_work_in_knownHelpers_only_mode(self):
        source = u"{{^foo}}bar{{/foo}}"
        self.assertEqual("bar",
            render(source, {'foo': False}, knownHelpersOnly=True))

    def test_lambdas_are_resolved_by_blockHelperMissing_not_handlebars_proper(self):
        # Probably should be called 'lambdas in the context are called as
        # though for a simple block' - it wants to check moustache
        # compatibility which allows all block stuff to be overridden via
        # blockHelperMissing
        source = u"{{#truthy}}yep{{/truthy}}"
        self.assertEqual("yep", render(source, {'truthy': lambda this: True}))

    def test_default_helperMissing_no_params(self):
        source = u"a{{missing}}b"
        self.assertEqual("ab", render(source, {}))

    def test_default_helperMissing_with_param(self):
        source = u"a{{missing something}}b"
        self.assertRaises(Exception, render, source, {})

    def test_with(self):
        source = u"{{#with person}}{{first}} {{last}}{{/with}}"
        self.assertEqual("Alan Johnson",
            render(source, {'person': {'first': "Alan", 'last': "Johnson"}}))

    def test_if(self):
        source = u"{{#if goodbye}}GOODBYE {{/if}}cruel {{world}}!"
        self.assertEqual(u"GOODBYE cruel world!",
            render(source, {'goodbye': True, 'world': "world"}))
        self.assertEqual(u"GOODBYE cruel world!",
            render(source, {'goodbye': 'dummy', 'world': "world"}))
        self.assertEqual(u"cruel world!",
            render(source, {'goodbye': False, 'world': "world"}))
        self.assertEqual(u"cruel world!",
            render(source, {'world': "world"}))
        self.assertEqual(u"GOODBYE cruel world!",
            render(source, {'goodbye': ['foo'], 'world': "world"}))
        self.assertEqual(u"cruel world!",
            render(source, {'goodbye': [], 'world': "world"}))

    def test_if_else(self):
        source = u"{{#if goodbye}}GOODBYE{{else}}Hello{{/if}} cruel {{world}}!"
        self.assertEqual(u"Hello cruel world!",
            render(source, {'goodbye': False, 'world': "world"}))

    def test_if_with_function_argument(self):
        source = u"{{#if goodbye}}GOODBYE {{/if}}cruel {{world}}!"
        self.assertEqual(u"GOODBYE cruel world!",
            render(source, {'goodbye': lambda this: True, 'world': "world"}))
        self.assertEqual(u"GOODBYE cruel world!",
            render(source,
                {'goodbye': lambda this: this['world'], 'world': "world"}))
        self.assertEqual(u"cruel world!",
            render(source, {'goodbye': lambda this: False, 'world': "world"}))
        self.assertEqual(u"cruel world!",
            render(source, {'goodbye': lambda this: None, 'world': "world"}))

    def test_resolve_with_attrs(self):
        class TestAttr():
            @property
            def text(self):
                return 'Hello'

        class TestGet():
            def get(self, name):
                return {'text': 'Hi'}.get(name)

        source = u"{{#each .}}{{test.text}}! {{/each}}"
        context = [
            {'test': TestAttr()},
            {'test': TestGet()},
            {'test': {'text': 'Goodbye'}}
        ]
        self.assertEqual("Hello! Hi! Goodbye! ",
            render(source, context))

    def test_list_context(self):
        source = u"{{#each .}}{{#each .}}{{text}}! {{/each}}cruel world!{{/each}}"
        context = [[{'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}]]
        self.assertEqual("goodbye! Goodbye! GOODBYE! cruel world!",
            render(source, context))

    def test_context_with_attrs(self):
        class TestContext():
            @property
            def text(self):
                return 'Goodbye'

        source = u"{{#each .}}{{text}}! {{/each}}cruel world!"
        context = [TestContext()]
        self.assertEqual("Goodbye! cruel world!",
            render(source, context))

    def test_each(self):
        source = u"{{#each goodbyes}}{{text}}! {{/each}}cruel {{world}}!"
        context = {'goodbyes':
            [{'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}],
            'world': "world"}
        self.assertEqual("goodbye! Goodbye! GOODBYE! cruel world!",
            render(source, context))
        self.assertEqual("cruel world!",
            render(source, {'goodbyes': [], 'world': "world"}))

    def test_each_this(self):
        source = u"{{#each name}}{{capitalize this}} {{/each}}"
        helpers = {'capitalize': lambda this, value: value.upper()}
        context = {
            'name': ['John', 'James']
        }
        self.assertEqual("JOHN JAMES ",
            render(source, context, helpers=helpers))

    def test_each_of_None(self):
        self.assertEqual(u"Goodbye cruel world!",
            render(u"Goodbye {{^each things}}cruel{{/each}} world!",
                {'things': None}))

    def test_each_of_empty_list(self):
        self.assertEqual(u"Goodbye cruel world!",
            render(u"Goodbye {{#each things}}happy {{^}}cruel {{/each}}world!",
                {'things': []}))

    def test_each_of_truthy_non_iterable_object(self):
        self.assertEqual(u"Goodbye cruel world!",
            render(u"Goodbye {{#each things}}happy {{^}}cruel {{/each}}world!",
                {'things': True}))

    def test_each_with_object_and_key(self):
        source = u"{{#each goodbyes}}{{@key}}. {{text}}! {{/each}}cruel {{world}}!"
        context = {
            'goodbyes': {
                "<b>#1</b>": {'text': "goodbye"},
                2: {'text': "GOODBYE"}
            }, 'world': "world"};
        self.assertIn(
            render(source, context),

            # Depending on iteration order, one will come before the other.
            (
                "&lt;b&gt;#1&lt;/b&gt;. goodbye! 2. GOODBYE! cruel world!",
                "2. GOODBYE! &lt;b&gt;#1&lt;/b&gt;. goodbye! cruel world!"
            )
        )

    def test_each_with_index(self):
        source = u"{{#each goodbyes}}{{@index}}. {{text}}! {{/each}}cruel {{world}}!"
        context = {
            'goodbyes': [{'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}],
            'world': "world"}
        self.assertEqual(
            "0. goodbye! 1. Goodbye! 2. GOODBYE! cruel world!",
            render(source, context))

    def test_each_with_nested_index(self):
        source = u"{{#each goodbyes}}{{@index}}. {{text}}! {{#each ../goodbyes}}{{@index}} {{/each}}After {{@index}} {{/each}}{{@index}}cruel {{world}}!"
        context = {
            'goodbyes': [{'text': "goodbye"}, {'text': "Goodbye"}, {'text': "GOODBYE"}],
            'world': "world"}
        self.assertEqual(
            "0. goodbye! 0 1 2 After 0 1. Goodbye! 0 1 2 After 1 2. GOODBYE! 0 1 2 After 2 cruel world!",
            render(source, context))

    def test_each_with_parent_index(self):
        source = u"{{#each people}}{{#each foods}}{{../name}}({{@../index}}) likes {{name}}({{@index}}), {{/each}}{{/each}}"
        context = {
            'people': [
                {
                    'name': 'John',
                    'foods': [{'name': 'apples'}, {'name': 'pears'}]
                },
                {
                    'name': 'Jane',
                    'foods': [{'name': 'grapes'}, {'name': 'pineapple'}]
                }
            ],
        }
        self.assertEqual(
            "John(0) likes apples(0), John(0) likes pears(1), Jane(1) likes grapes(0), Jane(1) likes pineapple(1), ",
            render(source, context))

    def test_log(self):
        source = u"{{log blah}}"
        context = {'blah': "whee"}
        log = []
        self.patch(pybars, 'log', log.append)
        self.assertEqual("", render(source, context))
        self.assertEqual(["whee"], log)

    def test_overriding_property_lookup(self):
        pass
        # Empty upstream

    # ... in data ... skipped

    def test_helpers_take_precedence_over_same_named_context_properties(self):
        source = u"{{goodbye}} {{cruel world}}"
        helpers = {'goodbye': lambda this: this['goodbye'].upper()}
        context = {'cruel': lambda this, world: "cruel " + world.upper(),
            'goodbye': "goodbye",
            'world': "world",
            }
        self.assertEqual("GOODBYE cruel WORLD",
            render(source, context, helpers=helpers))

    def test_block_helpers_take_precedence_over_same_named_context_properties(self):
        source = u"{{#goodbye}} {{cruel world}}{{/goodbye}}"
        def goodbye(this, options):
            return strlist([this['goodbye'].upper()]) + options['fn'](this)
        helpers = {'goodbye': goodbye}
        context = {'cruel': lambda this, world: "cruel " + world.upper(),
            'goodbye': "goodbye",
            'world': "world",
            }
        self.assertEqual("GOODBYE cruel WORLD",
            render(source, context, helpers=helpers))

    def test_Scoped_names_take_precedence_over_helpers(self):
        source = u"{{this.goodbye}} {{cruel world}} {{cruel this.goodbye}}"
        helpers = {'goodbye': lambda this: this['goodbye'].upper()}
        context = {'cruel': lambda this, world: "cruel " + world.upper(),
            'goodbye': "goodbye",
            'world': "world",
            }
        self.assertEqual(u"goodbye cruel WORLD cruel GOODBYE",
            render(source, context, helpers=helpers))

    def test_Scoped_names_take_precedence_over_block_helpers(self):
        source = u"{{#goodbye}} {{cruel world}}{{/goodbye}} {{this.goodbye}}"
        def goodbye(this, options):
            return strlist([this['goodbye'].upper()]) + options['fn'](this)
        helpers = {'goodbye': goodbye}
        context = {'cruel': lambda this, world: "cruel " + world.upper(),
            'goodbye': "goodbye",
            'world': "world",
            }
        self.assertEqual("GOODBYE cruel WORLD goodbye",
            render(source, context, helpers=helpers))

    def test_helpers_can_take_an_optional_hash(self):
        source = u'{{goodbye cruel="CRUEL" world="WORLD" times=12}}'
        # Note: the order is a rotation on the template order to avoid *args
        # processing generating a false pass
        def goodbye(this, times, cruel, world):
            return "GOODBYE " + cruel + " " + world + " " + str(times) + " TIMES"
        helpers = {'goodbye': goodbye}
        self.assertEquals(u"GOODBYE CRUEL WORLD 12 TIMES",
            render(source, {}, helpers=helpers))

    def test_helpers_can_take_an_optional_hash_with_booleans(self):
        def goodbye(this, cruel, world, _print):
            if _print is True:
                return "GOODBYE " + cruel + " " + world
            elif _print is False:
                return "NOT PRINTING"
            else:
                return "THIS SHOULD NOT HAPPEN"
        helpers = {'goodbye': goodbye}
        self.assertEqual("GOODBYE CRUEL WORLD",
            render(u'{{goodbye cruel="CRUEL" world="WORLD" _print=true}}',
                {}, helpers=helpers))
        self.assertEqual("NOT PRINTING",
            render(u'{{goodbye cruel="CRUEL" world="WORLD" _print=false}}',
                {}, helpers=helpers))

    def test_block_helpers_can_take_an_optional_hash(self):
        source = u'{{#goodbye cruel="CRUEL" times=12}}world{{/goodbye}}'
        def goodbye(this, options, times, cruel):
            return "GOODBYE " + cruel + " " + str_class(options['fn'](this)) + " " + str(times) + " TIMES"
        helpers = {'goodbye': goodbye}
        self.assertEqual("GOODBYE CRUEL world 12 TIMES",
            render(source, {}, helpers=helpers))

    def test_block_helpers_can_take_an_optional_hash_with_booleans(self):
        def goodbye(this, options, cruel, _print):
            if _print is True:
                return "GOODBYE " + cruel + " " + str_class(options['fn'](this))
            elif _print is False:
                return "NOT PRINTING"
            else:
                return "THIS SHOULD NOT HAPPEN"
        helpers = {'goodbye': goodbye}
        self.assertEqual("GOODBYE CRUEL world",
            render(u'{{#goodbye cruel="CRUEL" _print=true}}world{{/goodbye}}',
                {}, helpers=helpers))
        self.assertEqual("NOT PRINTING",
            render(u'{{#goodbye cruel="CRUEL" _print=false}}world{{/goodbye}}',
                {}, helpers=helpers))

    def test_should_lookup_arbitrary_content(self):
        string  = u'{{#each goodbyes}}{{lookup ../data .}}{{/each}}'
        context = {'goodbyes': [0, 1], 'data': ['foo', 'bar']}

        template = Compiler().compile(string)
        result   = template(context)

        self.assertEqual(str_class(result), 'foobar')

    def test_should_not_fail_on_undefined_value(self):
        string  = u'{{#each goodbyes}}{{lookup ../bar .}}{{/each}}'
        context = {'goodbyes': [0, 1], 'data': ['foo', 'bar']}

        template = Compiler().compile(string)
        result = template(context)

        self.assertEqual(str_class(result), '')

    def test_should_not_fail_on_unavailable_value(self):
        string  = u'{{lookup thelist 3}}.{{lookup theobject "qux"}}.{{lookup thenumber 0}}'
        context = {'thelist': ['foo', 'bar'], 'theobject': {'foo': 'bar'}, 'thenumber': 7}

        template = Compiler().compile(string)
        result = template(context)

        self.assertEqual(str_class(result), '..')

    def test_should_lookup_content_by_special_variables(self):
        string  = u'{{#each goodbyes}}{{lookup ../data @index}}{{/each}}'
        context = {'goodbyes': [0, 1], 'data': ['foo', 'bar']}

        template = Compiler().compile(string)
        result   = template(context)

        self.assertEqual(str_class(result), 'foobar')

    def test_GH_94_Cannot_read_property_of_undefined(self):
        context = {"books": [
            {"title": "The origin of species",
             "author": {"name": "Charles Darwin"}},
            {"title": "Lazarillo de Tormes"}]}
        source = u"{{#books}}{{title}}{{author.name}}{{/books}}"
        self.assertEqual(
            "The origin of speciesCharles DarwinLazarillo de Tormes",
            render(source, context))

    def test_GH_150__Inverted_sections_print_when_they_shouldnt(self):
        source = u"{{^set}}not set{{/set}} :: {{#set}}set{{/set}}"
        self.assertEqual("not set :: ", render(source, {}))
        self.assertEqual("not set :: ", render(source, {'set': None}))
        self.assertEqual("not set :: ", render(source, {'set': False}))
        self.assertEqual(" :: set", render(source, {'set': True}))

    def test_Mustache_man_page(self):
        source = (u"Hello {{name}}. You have just won ${{value}}!"
            u"{{#in_ca}} Well, ${{taxed_value}}, after taxes.{{/in_ca}}")
        context = {
            "name": "Chris",
            "value": 10000,
            # Note that the int here is not needed in JS because JS doesn't
            # have ints and floats.
            "taxed_value": int(10000 - (10000 * 0.4)),
            "in_ca": True
            }
        self.assertEqual(
            "Hello Chris. You have just won $10000! Well, $6000, after taxes.",
            render(source, context))

    def test_GH_158__Using_array_index_twice_breaks_the_template(self):
        source = u"{{arr.[0]}}, {{arr.[1]}}"
        context = {"arr": [1, 2]}
        self.assertEqual("1, 2", render(source, context))

    def test_bug_reported_by__fat_where_lambdas_weren_t_being_properly_resolved(self):
        source = u"<strong>This is a slightly more complicated {{thing}}.</strong>.\n{{! Just ignore this business. }}\nCheck this out:\n{{#hasThings}}\n<ul>\n{{#things}}\n<li class={{className}}>{{word}}</li>\n{{/things}}</ul>.\n{{/hasThings}}\n{{^hasThings}}\n\n<small>Nothing to check out...</small>\n{{/hasThings}}"
        context = {
            'thing': lambda this: "blah",
            'things': [
                {'className': "one", 'word': "@fat"},
                {'className': "two", 'word': "@dhg"},
                {'className': "three", 'word':"@sayrer"}
                ],
            'hasThings': lambda this: True,
            }
        expected = "<strong>This is a slightly more complicated blah.</strong>.\n\nCheck this out:\n\n<ul>\n\n<li class=one>@fat</li>\n\n<li class=two>@dhg</li>\n\n<li class=three>@sayrer</li>\n</ul>.\n\n"
        self.assertEqual(expected, render(source, context))

    def test_invalid_python_identifiers_cannot_be_used_as_keyword_arguments(self):
        source = u'{{foo 0x="bar"}}'
        self.assertEqual('', render(source, {}))

    def test_backslash_does_not_normally_escape_text(self):
        source = u'{{echo "\\x"}}'
        self.assertEqual('\\x', render(source, {}, helpers={'echo': (lambda this, arg: arg)}))

    def test_backslash_only_escapes_quote(self):
        # Notice that the following is a raw string. It is a helper, 'echo',
        # with a string argument equal to a backslash and an escaped quote.
        source = u'{{echo "\\\\""}}'
        # If the parser does not know to escape the backslash but does know to
        # escape the quote, it will end up with something like the following
        # in our generated rendering code:
        #
        #     value = value(child_scope, "\\"")
        #
        # Which will raise a SyntaxError.
        self.assertEqual('\\&quot;', render(source, {}, helpers={'echo': (lambda this, arg: arg)}))

    def test_newlines_in_string_litereals(self):
        source = u'{{echo "Hello,\nWorld!"}}'
        self.assertEqual('Hello,\nWorld!', render(source, {}, helpers={'echo': (lambda this, arg: arg)}))

    def test_code_injection(self):
        # If esape sequences are not dealt with properly, we are able to run
        # arbitrary Python code. Thanks to @thomasst for pointing this out:
        # https://github.com/elasticsales/pybars/commit/3a262b8cd7902889cde5c786f76bb0c30f8894e6#commitcomment-4687173
        source = u'{{echo "\\\\")\n\n        raise AssertionError(\'Code Injected!\')\n#"}}'
        self.assertEqual('\\&quot;)\n\n        raise AssertionError(&#x27;Code Injected!&#x27;)\n#', render(source, {}, helpers={'echo': (lambda this, arg: arg)}))
