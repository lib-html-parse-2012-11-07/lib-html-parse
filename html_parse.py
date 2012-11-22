# -*- mode: python; coding: utf-8 -*-
#
# Copyright 2012 Andrej A Antonov <polymorphm@gmail.com>.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

assert str is not bytes

import weakref
from html import parser
from html import entities

class HtmlNode:
    def __init__(self, parent=None):
        self.set_parent(parent)
    
    def get_parent(self):
        return self._parent_ref() \
                if self._parent_ref is not None else None
    
    def set_parent(self, parent):
        self._parent_ref = weakref.ref(parent) \
                if parent is not None else None

class DocHtmlNode(HtmlNode):
    def __init__(self):
        super().__init__(parent=None)
        self.decl = []
        self.childs = []

class TagHtmlNode(HtmlNode):
    def __init__(self, name, parent=None):
        super().__init__(parent=parent)
        self.name = name
        self.attrs = {}
        self.childs = []

class DataHtmlNode(HtmlNode):
    def __init__(self, data, parent=None):
        super().__init__(parent=parent)
        self.data = data

class HtmlParser:
    def __init__(self):
        self._doc_node = DocHtmlNode()
        self._curr_node = self._doc_node
        
        class ParserHandler(parser.HTMLParser):
            def handle_starttag(inner_self, tag, attrs):
                self._starttag_handle(tag, attrs)
            def handle_endtag(inner_self, tag):
                self._endtag_handle(tag)
            def handle_data(inner_self, data):
                self._data_handle(data)
            def handle_entityref(inner_self, name):
                self._entityref_handle(name)
            def handle_charref(inner_self, name):
                self._charref_handle(name)
            def handle_decl(inner_self, decl):
                self._decl_handle(decl)
        
        self._parser_handler = ParserHandler()
    
    def get_node(self):
        return self._doc_node
    
    def _starttag_handle(self, tag, attrs):
        parent_node = self._curr_node
        while not isinstance(parent_node, DocHtmlNode) and \
                not isinstance(parent_node, TagHtmlNode):
            parent_node = parent_node.get_parent()
        
        new_node = TagHtmlNode(tag, parent=parent_node)
        new_node.attrs.update(attrs)
        
        parent_node.childs.append(new_node)
        self._curr_node = new_node
    
    def _endtag_handle(self, tag):
        closing_node = self._curr_node
        
        while not isinstance(closing_node, DocHtmlNode):
            if isinstance(closing_node, TagHtmlNode) and \
                    closing_node.name == tag:
                self._curr_node = closing_node.get_parent()
                return
            
            closing_node = closing_node.get_parent()
    
    def _data_handle(self, data):
        if isinstance(self._curr_node, DataHtmlNode):
            self._curr_node.data += data
            return
        
        parent_node = self._curr_node
        while not isinstance(parent_node, DocHtmlNode) and \
                not isinstance(parent_node, TagHtmlNode):
            parent_node = parent_node.get_parent()
        
        new_node = DataHtmlNode(data, parent=parent_node)
        parent_node.childs.append(new_node)
        self._curr_node = new_node
    
    def _entityref_handle(self, name):
        try:
            code = entities.name2codepoint[name]
            data = chr(code)
        except (KeyError, ValueError, ArithmeticError):
            data = '&{};'.format(name)
        
        self._data_handle(data)
    
    def _charref_handle(self, name):
        try:
            code = int(name[1:], 16) if name.startswith('x') else int(name)
            data = chr(code)
        except (ValueError, ArithmeticError):
            data = '&#{};'.format(name)
        
        self._data_handle(data)
    
    def _decl_handle(self, decl):
        self._doc_node.decl.append(decl)
    
    def feed(self, data):
        self._parser_handler.feed(data)

def html_parse(data):
    parser = HtmlParser()
    parser.feed(data)
    return parser.get_node()

def print_node(node, level=None, print_func=None):
    if level is None:
        level = 0
    if print_func is None:
        print_func = print
    
    next_level = level + 1
    self_indent = level * 2
    attr_indent = self_indent + 4
    next_indent = self_indent + 1
    
    if level >= 100:
        print_func('{}Error: level too big'.format(' ' * self_indent))
        return
    
    if isinstance(node, DataHtmlNode):
        print_func('{}DataHtmlNode: {!r}'.format(' ' * self_indent, node.data))
        return
    
    if isinstance(node, DocHtmlNode):
        print_func('{}DocHtmlNode:'.format(' ' * self_indent))
        print_func('{}decl: {!r}'.format(' ' * attr_indent, node.decl))
        
        for child in node.childs:
            print_node(child, level=next_level, print_func=print_func)
        
        return
    
    if isinstance(node, TagHtmlNode):
        print_func('{}TagHtmlNode({!r}):'.format(' ' * self_indent, node.name))
        print_func('{}attrs: {!r}'.format(' ' * attr_indent, node.attrs))
        
        for child in node.childs:
            print_node(child, level=next_level, print_func=print_func)
        
        return
    
    print_func('{}Error: unknown type'.format(' ' * self_indent))

def get_all_nodes(node_list, direct_only=None):
    if direct_only is None:
        direct_only = False
    
    node_iter = iter(node_list)
    next_node_list = []
    
    while True:
        for node in node_iter:
            if not direct_only:
                yield node
            
            if isinstance(node, DocHtmlNode) or isinstance(node, TagHtmlNode):
                if not direct_only:
                    next_node_list += node.childs
                else:
                    for child_node in node.childs:
                        # TODO: in python 3.3 need replace this to
                        #           ``yield from node.childs``
                        yield child_node
        
        if not next_node_list:
            return
        
        node_iter = iter(next_node_list)
        next_node_list = []

def find_tags(node_list,
        name=None, attrs=None, in_attrs=None,
        direct_only=None):
    if attrs is None:
        attrs = {}
    if in_attrs is None:
        in_attrs = {}
    
    def check_filter(node):
        if not isinstance(node, TagHtmlNode):
            return False
        
        if name is not None and name != node.name:
            return False
        
        for attr_name in attrs:
            if attr_name not in node.attrs:
                return False
            
            attr_value = attrs[attr_name]
            
            if node.attrs[attr_name] != attr_value:
                return False
            
        for attr_name in in_attrs:
            if attr_name not in node.attrs:
                return False
            
            attr_value = in_attrs[attr_name]
            node_attr_values = node.attrs[attr_name].split(' ')
            
            if attr_value not in node_attr_values:
                return False
        
        return True
    
    return filter(check_filter, get_all_nodes(node_list, direct_only=direct_only))
