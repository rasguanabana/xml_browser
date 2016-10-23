#!/bin/env python3

"""
xml_browser
"""

import os
import sys
from collections import deque, defaultdict
from xml.etree import ElementTree as ET

class Assembler():
    """
    Assemble XML file based on a directory structure.
    Class associated with ``xml_browser assemble`` command
    """

    class InvalidName(Exception):
        "Raised when a directory has invalid name."
        pass

    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.root_element = None
        # lookup element for given path
        self.path_lookup_elem = dict()
        # keep element and set of its children, so we can sort them after processing all
        self.relations_dict = defaultdict(set)
        self.xml_string = None

    def assemble(self):
        """
        Traverse ``self.root_dir`` directory and assemble XML document.
        """
        # iterate over every directory in a structure.
        for walk_tuple in os.walk(self.root_dir):
            # normalize:
            element_path = os.path.normpath(walk_tuple[0])
            element_dirname = os.path.basename(element_path)
            try:
                tag, order = element_dirname.rsplit(',', 1)
            except ValueError:
                tag = element_dirname
                order = 0.
            else:
                try: # cast string to float
                    order = float(order)
                except ValueError:
                    raise Assembler.InvalidName("Non-numeric order in '%s'" % element_path)
            try:
                element = ET.Element(tag)
                # check if tag is valid
                ET.fromstring(ET.tostring(element))
            except ET.ParseError:
                raise Assembler.InvalidName("'%s' is not a valid directory name \
                    (full path: %s)." % (element_dirname, element_path))
            # save element in lookup dict
            self.path_lookup_elem[element_path] = element

            # try reading meta
            try:
                with open(os.path.join(element_path, '0-attributes'), mode='r') as attributes:
                    raw_attrib = attributes.read()
            except FileNotFoundError:
                pass
            else:
                for attribute in raw_attrib.strip().splitlines():
                    a_name, a_val = attribute.split('=', 1)
                    element.attrib[a_name.strip()] = a_val.strip()
            try:
                with open(os.path.join(element_path, '0-text'), mode='r') as text:
                    raw_text = text.read()
            except FileNotFoundError:
                pass
            else:
                element.text = raw_text.strip()
            try:
                with open(os.path.join(element_path, '0-tail'), mode='r') as tail:
                    raw_tail = tail.read()
            except FileNotFoundError:
                pass
            else:
                element.tail = raw_tail.strip()

            # establish relations
            if self.root_element is None:
                self.root_element = element
            else:
                parent_path = os.path.dirname(element_path)
                parent = self.path_lookup_elem[parent_path]
                self.relations_dict[parent].add((order, element))

        # order and attach elements
        for element, children in self.relations_dict.items():
            children_sort = sorted(children)
            # get rid of order
            element.extend(child[1] for child in children_sort)

    def write(self):
        """
        Write XML document to standard output.
        """
        self.xml_string = ET.tostring(self.root_element).decode(sys.getdefaultencoding())
        sys.stdout.write(self.xml_string)
        sys.stdout.write(os.linesep)

class Makedir():
    """
    Create a directory structure based on an XML file.
    Class associated with ``xml_browser makedir`` command
    """

    class Dirstack(deque):
        """
        Overrides deque's append method and allows setting options for directories and
        files creation.
        """
        def __init__(self, iterable=(), maxlen=None, ds_options=None):
            # py2 cannot into keyword-only args
            """
            Call deque's init and set options for Dirstack.
            """
            super(Makedir.Dirstack, self).__init__(iterable, maxlen)
            #opts TODO
            self.real_dirname = dict()

        def append(self, element):
            """
            Overriden append. With every new element pushed on stack, a new directory
            in tree is being created.
            """
            try:
                # if element has siblings, then we might need to be able to keep their order
                siblings = tuple(self[-1])
            except IndexError: # this will happen for root element
                siblings = (element,)

            assert element in siblings

            # add suffix to keep order of siblings
            if len(siblings) > 1:
                uniq_suffix = ',' + str(siblings.index(element))
            else:
                uniq_suffix = ''

            self.real_dirname[element] = element.tag + uniq_suffix

            super(Makedir.Dirstack, self).append(element)

            tag_chain = tuple(self.real_dirname[elem] for elem in self)
            element_path = os.path.join(*tag_chain)
            # directory creation
            os.mkdir(element_path)
            # meta files
            try:
                e_text = element.text.strip()
            except AttributeError:
                e_text = None
            if e_text:
                with open(os.path.join(element_path, '0-text'), mode='w+') as text:
                    text.write(e_text + os.linesep)
            try:
                e_tail = element.tail.strip()
            except AttributeError:
                e_tail = None
            if e_tail:
                with open(os.path.join(element_path, '0-tail'), mode='w+') as tail:
                    tail.write(e_tail + os.linesep)
            if element.attrib:
                e_attrib = os.linesep.join(k + '=' + v for k, v in element.attrib.items())
                with open(os.path.join(element_path, '0-attributes'), mode='w+') as attributes:
                    attributes.write(e_attrib + os.linesep)

    def __init__(self, **options):
        self.xml_string = None
        self.xml_etree = None

    def read(self):
        """
        Read XML document from standard input.
        """
        self.xml_string = sys.stdin.read()
        self.xml_etree = ET.fromstring(self.xml_string)

    def create_dirtree(self):
        """
        Iterate over nodes of ``self.xml_etree`` and create corresponding directories in
        a directory structure.
        """
        element_iterator = self.xml_etree.iter()
        stack = Makedir.Dirstack()
        root_element = next(element_iterator)
        stack.append(root_element)

        for element in element_iterator: # loop starts from 2nd element of iterator
            while element not in stack[-1]: # find parent on stack
                stack.pop()
            stack.append(element) # push current element on stack behind its parent

if __name__ == '__main__':
    #argument parsing
    # - assemble
    # - makedir
    #   --metadata
    #       none - do not create any special directories/files (attributes, content, namespace) - this creates only directories
    #       attributes - create 0-attributes for every node
    #       content - create 0-content for every node
    #       ...
    #       full - create each kind of special directories/files for every node
    #   --create-mode-attribute - specify the name of attribute used to tell Makedir what permissions should be set for a directory
    #   --regular-file-attribute - ... value of this attr will be file extension (can be none)
    if sys.argv[1] == 'assemble':
        directory = sys.argv[2]
        asm = Assembler(directory)
        asm.assemble()
        asm.write()
    elif sys.argv[1] == 'makedir':
        md = Makedir()
        md.read()
        md.create_dirtree()
    else:
        exit(1)
