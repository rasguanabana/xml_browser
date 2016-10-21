#!/bin/env python3

"""
xml_browser
"""

import os
import sys
from collections import deque
from xml.etree import ElementTree as etree

class Assembler():
    """
    Assemble XML file based on a directory structure.
    Class associated with ``xml_browser assemble`` command
    """
    pass

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
        def __init__(self, iterable=(), maxlen=None, ds_options=None): # py2 cannot into keyword only args
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
        self.xml_etree = etree.fromstring(self.xml_string)

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
    pass
