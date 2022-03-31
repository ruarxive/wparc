wparc: a command-line tool to backup public data from Wordpress websites using Wordpress API
########################################################################################################################

wparc is a command line tool used to backup data from Wordpress based websites.
It uses /wp-json/ API provided by default Wordpress installation and extracts all data and media files

.. contents::

.. section-numbering::



Main features
=============

* Data extraction
* Download all media files


Installation
============


Any OS
-------------

A universal installation method (that works on Windows, Mac OS X, Linux, …,
and always provides the latest version) is to use pip:


.. code-block:: bash

    # Make sure we have an up-to-date version of pip and setuptools:
    $ pip install --upgrade pip setuptools

    $ pip install --upgrade wparc


(If ``pip`` installation fails for some reason, you can try
``easy_install wparc`` as a fallback.)


Python version
--------------

Python version 3.6 or greater is required.

Usage
=====


Synopsis:

.. code-block:: bash

    $ wparc [command] [flags]


See also ``python -m wparc`` and ``wparc [command] --help`` for help for each command.



Commands
========

Dump command
----------------
Dumps all data routes listed in /wp-json/ API endpoint


Dumps all data from "https://agentura.ru" website

.. code-block:: bash

    $ wparc dump --domain agentura.ru



Getfiles command
----------------
Downloads all media file listed in "wp_v2_media.jsonl" file that should be dumped using command "dump"

Downloads all media from "dissident.memo.ru" website 

.. code-block:: bash

    $ wparc getfiles --domain dissident.memo.ru

