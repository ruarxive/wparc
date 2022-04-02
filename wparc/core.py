#!/usr/bin/env python
# -*- coding: utf8 -*-
import logging

import click

from .cmds.extractor import Project

# logging.getLogger().addHandler(logging.StreamHandler())
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def enableVerbose():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)


@click.group()
def cli1():
    pass


@cli1.command()
@click.option('--domain', '-d', default=None, help='URL of the Yandex.Disk public resource')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output. Print additional info')
def getfiles(domain, verbose):
    """s public resource files"""
    if verbose:
        enableVerbose()
    if domain is None:
        print('Domain name required, for example "example.com"')
        return
    acmd = Project()
    acmd.getfiles(domain)
    pass


@click.group()
def cli2():
    pass


@cli2.command()
@click.option('--domain', '-d', default=None, help='URL of the public resource to process')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output. Print additional info')
@click.option('--all', '-a', is_flag=True, default=True, help='Include unknown API routes')
@click.option('--https', '-h', is_flag=True, default=False, help='Force HTTPS (default: False)')
def dump(domain, verbose, all, https):
    """Dump Wordpress data from API"""
    if verbose:
        enableVerbose()
    if domain is None:
        print('Domain name required, for example "example.com"')
        return
    acmd = Project()
    acmd.dump(domain, all, https)
    pass

@click.group()
def cli3():
    pass


@cli3.command()
@click.option('--domain', '-d', default=None, help='URL of the public resource to process')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output. Print additional info')
@click.option('--https', '-h', is_flag=True, default=False, help='Force HTTPS (default: False)')
def ping(domain, verbose, https):
    """Dump Wordpress data from API"""
    if verbose:
        enableVerbose()
    if domain is None:
        print('Domain name required, for example "example.com"')
        return
    acmd = Project()
    acmd.ping(domain, https)
    pass


cli = click.CommandCollection(sources=[cli1, cli2, cli3])

# if __name__ == '__main__':
#    cli()
