# -*- coding: utf-8 -*-

import logging

from ..wpapi.crawler import collect_data, collect_files, ping


class Project:
    """Wordpress API crawler"""

    def __init__(self):
        pass


    def dump(self, domain, all, https):
        collect_data(domain, get_unknown=all, force_https=https)
        pass

    def getfiles(self, domain):
        collect_files(domain)
        pass

    def ping(self, domain, https):
        ping(domain, force_https=https)

