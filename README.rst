**xml_browser.py** - Edit XML documents as a directory structure

.. image:: http://i.imgur.com/QuMBiuB.gif
   :align: center

Note::

    This is a demo version. I'm publishing it early, so I can get feedback from you. If some people find this
    utility useful, I'll keep developing (hopefully with some help :)). Otherwise, it will just stay here as
    a fun idea of mine that I will maybe play around with. As this is a demo version, it lacks quite some
    features I'm willing to add some day (you can find the list below). Please open an issue if you notice any
    misconception - I'd like to eliminate them as soon as possible.

xml_browser converts arbitrary XML documents to a directory structure. This enables user to browse and edit XML in a simple and (as the author hopes) intuitive way.

This utility was written in Python 3, but is intended to be portable. It was just quickly tested under Python 2, so it may be not working in older versions.

.. contents:: Table of contents

Why?
====

The main target is editing XML from within shell scripts. Representing XML as a directory structure makes it easy to do editing with basic shell tools. Also, some advantage of this approach is that operating on a directory structure makes shell code more comprehensive. For example, if script does ``sed`` on ``root,0/some_element,1/0-text`` then you probably suspect what is going on.

xml_browser is easy to get and run in volatile environment. You could just setup virtualenv and install xml_browser with pip, or even just get the script via http. No need to preinstall anything or download precompiled binaries. xml_browser is pure Python utility and has no external dependencies.

How to use it?
==============

The ``makedir``
---------------

Take following XML as an example::

    <documentRoot>
      <a foo="bar" baz="bax">
        This is a xml_browser demo.
        <b>yup</b>
        tail
      </a>
      <z />
    </documentRoot>

Let's say above is the content of `example.xml` file. To create a directory structure based on this file, run::

    xml_browser.py makedir < example.xml

xml_browser reads data from standard input - that way it is easy to pipe results of a command (e.g. ``curl``) directly, without doing too much of a shell magic, like process substitution.

By running the command, we'll get following dirtree::

    documentRoot,0
    ├── a,0
    │   ├── 0-attributes
    │   ├── 0-text
    │   ├── b,0
    │   │   ├── 0-tail
    │   │   ├── 0-text
    │   │   ├── .tail.ws
    │   │   └── .text.ws
    │   ├── .tail.ws
    │   └── .text.ws
    ├── .text.ws
    └── z,1
        └── .tail.ws

    3 directories, 10 files

You can notice directories corresponding with every element from `example.xml` and some files inside them.
All directories have suffixes that are appended to element names as an ordering information. This way we know, that ``<a>`` element goes before ``<z>``. We will discuss ordering in detail later.

What about files, why do their names start with ``0-``? The answer is simple - no valid XML tag can start with a number, so it will not clash with any tag name (`text` as a tag name is not that unusual). Tags cannot start with hyphen (``-``) either, but if it was the first character of a filename, then you'd need to use ``--`` in almost every shell command to parse it correctly. Also, ``0-`` is rather easy to type.

`0-attributes` holds information about element attributes in a propfile format, e.g::

    a=1
    b= 2

Note that there are no quotes. Leading and trailing whitespaces of a value are taken litteraly (no stripping!). Attribute names can have leading and trailing whitespaces but - in contrary to values - they will be stripped. So, following line of `0-attributes`: ``"   attribute_name    =  value   "`` will evaluate to ``"attribute_name"`` and ``"  value   "`` respectively.

`0-text` contains stripped text of element with a newline appended at the end. `0-tail` is almost the same thing, but a tail is a text that goes right *after* element. It's stripped in the same way.

When you edit `0-tail` or `0-text` and assemble directory tree to a XML document you can see that leading and trailing whitespaces are preserved. It is possible thanks to `.text.ws` and `.tail.ws` files. They consist of whitespaces and a ``x`` character somewhere between them. This ``x`` serves as a substitution mark - it will be replaced with stripped text from `0-text`/`0-tail`. Usually we don't need to manipulate whitespaces, so they are kept in hidden files.

Obtaining data from directory tree
..................................

Moving around manually doesn't need explaining, I believe. Let's focus a bit on usage in shell scripts.

For automated tasks ``find``, ``grep`` and globbing are your friends.

The simplest case is when you know the structure of your XML::

    text_of_b=$(cat documentRoot,0/a,*/b,0/0-text)

The * is used here just to show, that we can do that this way. Tag names cannot contain commas, so it is used to separate tag name from ordering. Note that * is specified after a comma, so only `a` tag will be matched. if the pattern was ``a*``, then names like ``alaska`` would match as well.

What if we want to find every `foo` element in the whole document? Let's try to ``find`` a way::

    find root,0 -type d -name "foo,*"

What if we want to find every `foo` element with a ``bar`` argument having value ``baz``?::

    find root,0 -type d -name "foo,*" -exec grep -q 'bar=baz' {}/0-attributes -print

Let's expand above case and call a compound command for every match::

    find root,0 -type d -name "foo,*" -exec grep -q 'bar=baz' {}/0-attributes -print | \
    while read -r match; do
      cat $match/0-text
      # we could do that in -exec in find or with xargs, but I'm too lazy to come up with a more complex example.
      # that would fit for a loop. But you see, you can run lots of commands here for every hit!
    done

What if we want to make above the right way?::

    find root,0 -type d -name "foo,*" -exec grep -q 'bar=baz' {}/0-attributes -print0 | \
    while IFS= read -r -d '' match; do
      cat "$match/0-text"
    done

We could do this without ``find`` too, but I consider this less readable - and we need to play around with `IFS`::

        IFS=$'\n'
    for match in $(grep -lR 'bar=baz' root,0/* | grep 'foo,[^/]*/0-attributes'); do
      cat "$(dirname "$match")/0-text" 2> /dev/null
    done

These examples are rather lengthy, but not that hard to construct. xml_browser is intended to be used in shell, so using some ``find``, ``grep`` and some loops is not improper.


Editing
-------

Editing data is similar to reading it. You can use ``sed`` or ``awk`` in commands above, so let's focus on xml_browser specific thing - node ordering.

Consider following::

    <reallySimple>
      <a/>
      <a/>
      <b/>
      <a/>
      <c/>
      <c/>
      Some tail text
    </reallySimple>

As you already know, we'll get following subdirectories inside `reallySimple,0` directory::

    a,0  a,1  b,2  a,3  c,4  c,5

Easy. But how to add a node? It's obvious how to append a node at the end (e.g. ``mkdir new,6``, you may want to move `0-tail` to the new last element). But how to insert it between some existing nodes? Time for some theory.

Numbers at the time of assembling directory structure into a XML document are used solely for ordering, so it does not matter if you have, let's say, `a,0`, `a,1`, `over,2` or something like `a,-100`, `a,4.5` and `over,9000` - the result will be exactly the same. You can specify any float.

*But bash sucks at floats!* - you might say. That's true. You can append more commas and numbers to the dirname. So to insert `middle` element between `a,3` and `c,4`, do::

    mkdir middle,3,1

You need to know, that ordering operates on tuples of floats. Tuple for `a,0` is ``(0.0,)``, for `middle,3,1` it's ``(3.0, 1.0)``, so if you create a directory named `foo,3,-3` the tuple will be ``(3.0, -3.0)`` and the element will be placed between `a,3` and `middle,3,1` - that's how tuple ordering work, element by element.

xml_browser's ``makedir`` will always generate subsequent integers starting from 0, so it is possible to access elements easily, as the names are predictable. So if you need to read and manipulate data/nodes, do the reading part first, before you will alter ordering.

The ``assemble``
----------------

When you're done editting, you can assemble the directory tree to a XML document. Just call::

    xml_browser.py assemble documentRoot,0 > result.xml

You need to provide root directory of you structure after ``assemble``. Like with ``makedir``, result is written on standard output, so you can pipe it to any command or redirect to a file.

Planned features
================

- Support for namespaces - ElementTree doesn't handle them correctly.
- Fancy formatting/generating options
- Options for creating dirtree - creation mode, handling already existing tree.
- Waiting for your suggestions!

License
=======

MIT (c) Adrian Włosiak 2016
