#!/bin/env python3

"""
xml_browser
"""

import os
import sys
import re
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
            # get tag and extract ordering information
            try:
                tag, order_s = element_dirname.split(',', 1)
            except ValueError:
                tag = element_dirname
                order = (0.,)
            else:
                if not order_s:
                    order_s = '0'
                try: # convert string to tuple of floats
                    order = tuple(float(o) for o in order_s.split(','))
                except ValueError:
                    raise Assembler.InvalidName(
                        "Non-numeric order component in '%s'" % element_path
                    )
            # create element. For now it is unattached to anything
            try:
                element = ET.Element(tag)
                # check if tag is valid
                ET.fromstring(ET.tostring(element))
            except ET.ParseError:
                raise Assembler.InvalidName(
                    "'%s' is not a valid directory name" % element_path
                )
            # save element in lookup dict under its path in dir structure
            self.path_lookup_elem[element_path] = element

            # try reading meta
            try:
                with open(os.path.join(element_path, '0-attributes'), mode='r') as attributes:
                    raw_attrib = attributes.read()
            except IOError:
                pass
            else:
                for attribute in raw_attrib.splitlines():
                    try:
                        a_name, a_val = attribute.split('=', 1)
                    except ValueError:
                        # FIXME? this will just ignore misformatted lines in attrib file
                        # with no warning, but sth like this is needed for empty lines
                        pass
                    else:
                        a_name = a_name.strip()
                        if re.match(r'\S*\s+\S*', a_name):
                            raise Assembler.InvalidName("Attribute name '%s' contains a whitespace"
                                                        % a_name)
                        element.attrib[a_name] = a_val
            for meta in ('text', 'tail'):
                try:
                    # reading whitespaces. For easier editing, text/tail is saved to 2 files.
                    # .text.ws/.tail.ws file contains whitespaces and a 'x' mark, where
                    # 0-text/0-tail file contents should be substituted.
                    with open(os.path.join(element_path, '.%s.ws' % meta), mode='r') as file_:
                        raw_meta_ws = file_.read()
                except IOError:
                    raw_meta_ws = ''
                try:
                    # reading text/tail
                    with open(os.path.join(element_path, '0-' + meta), mode='r') as file_:
                        raw_meta = file_.read()
                except IOError:
                    raw_meta = ''

                if raw_meta_ws:
                    # discard whitespaces in main file if .ws file is not empty
                    raw_meta = raw_meta.strip()

                # if ws file has no substitution mark and yet there is some text
                # to insert, then we need to guess where 'x' should be put
                if raw_meta and not raw_meta_ws.strip():
                    guess_x = raw_meta_ws.rfind(os.linesep)
                    if guess_x >= 0:
                        raw_meta_ws = raw_meta_ws[:guess_x] + 'x' + raw_meta_ws[guess_x:]
                    else: # no newlines found, discard whitespaces
                        raw_meta_ws = 'x'

                to_save = re.sub(r'\b[\s\S]*\b', raw_meta, raw_meta_ws)
                setattr(element, meta, to_save)

            # establish relations
            if self.root_element is None:
                # this is the first element being processed, so it must be root
                self.root_element = element
            else:
                # find parent element by using parent's path
                parent_path = os.path.dirname(element_path)
                parent = self.path_lookup_elem[parent_path]
                # we can't attach child to parent yet, because we need to order siblings first
                # all siblings are added to a set corresponding to a parent
                self.relations_dict[parent].add((order, element))

        # order and attach elements - this loop create whole element structure
        for element, children in self.relations_dict.items():
            # children are sorted by the order tuple
            children_sorted = sorted(children)
            # extract only ET.Elements from above list
            element.extend(child[1] for child in children_sorted)

    def write(self):
        """
        Write XML document on standard output.
        """
        self.xml_string = ET.tostring(self.root_element)
        try:
            self.xml_string = self.xml_string.decode(sys.getdefaultencoding())
        except AttributeError:
            pass
        sys.stdout.write(self.xml_string)
        # everyone likes a newline instead of junk before prompt, right?
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
            # Extracts leading whitespaces, text and trailing whitespaces:
            self.ws_regexp = re.compile(r'^(\s*)([\s\S]*\S)?(\s*)$')

        def append(self, element):
            """
            Overriden append. With every new element pushed on stack, a new directory
            in tree is being created.
            """
            # TODO - method is too big - split into more functions
            try:
                # if element has siblings, then we need to be able to keep their order
                siblings = tuple(self[-1])
            except IndexError: # this will happen for root element
                siblings = (element,)

            assert element in siblings

            # add suffix to keep order of siblings
            uniq_suffix = ',' + str(siblings.index(element))
            # keep real directory name for element
            self.real_dirname[element] = element.tag + uniq_suffix

            # from now on we need element on stack, so we call original append
            super(Makedir.Dirstack, self).append(element)

            # get real directory names and join them into full relative path
            tag_chain = tuple(self.real_dirname[elem] for elem in self)
            element_path = os.path.join(*tag_chain)
            # directory creation
            os.mkdir(element_path)
            # meta files
            for meta in ('text', 'tail'):
                e_meta = getattr(element, meta)
                try:
                    # get leading whitespaces (1), actual text (2), and trailing whitespaces (3)
                    meta_re = self.ws_regexp.match(e_meta)
                except TypeError: # e_meta is None
                    to_write = None
                    to_write_ws = None
                else:
                    to_write = meta_re.group(2) # actual text
                    # record whitespaces and mark where text should be substituted.
                    # do not place mark anywhere if text is empty
                    to_write_ws = meta_re.group(1) + ('x' if to_write else '') + meta_re.group(3)
                if to_write:
                    with open(os.path.join(element_path, '0-' + meta), mode='w+') as file_:
                        file_.write(to_write + os.linesep)
                if to_write_ws:
                    with open(os.path.join(element_path, '.%s.ws' % meta), mode='w+') as file_:
                        file_.write(to_write_ws)
            if element.attrib:
                # glue keys and values with '=' and then save each pair as seperate lines in file
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
            # push current element on stack behind its parent
            # append does the whole magic (in call on root element before loop too)
            stack.append(element)

def main():
    # simple arg parsing. this needs to be rewritten, but now serves well for demo version
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

if __name__ == '__main__':
    main()
