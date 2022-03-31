# -*- coding: utf-8 -*-

import logging

from ..wpapi.crawler import collect_data, collect_files


class Project:
    """Wordpress API crawler"""

    def __init__(self):
        pass


    def dump(self, domain, all):
        collect_data(domain, get_unknown=all)
        pass

    def getfiles(self, domain):
        collect_files(domain)
        pass

