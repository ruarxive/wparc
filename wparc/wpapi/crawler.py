# -*- coding: utf-8 -*-
import json
import sys
import yaml
import requests
import os
import pkg_resources
import logging
from urllib.parse import urlparse

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_HEADER = {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Mobile Safari/537.36'}
WP_DEFAULT_PAGESIZE = 100
DEFAULT_TIMEOUT = 360
RETRY_COUNT = 5
DEFAULT_CHUNK_SIZE = 1024*1024

def get_file(url, filename, aria2=False, aria2path=None):
    if os.path.exists(filename):
        logging.info('File %s already collected' % (filename))
        return
    dirpath = os.path.dirname(filename)
    os.makedirs(dirpath, exist_ok=True)
    basename = os.path.basename(filename)
    page = requests.get(url, headers=REQUEST_HEADER, stream=True, verify=False)
    if not aria2:
        f = open(filename, 'wb')
        total = 0
        chunk = 0
        for line in page.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
            chunk += 1
            if line:
                f.write(line)
            total += len(line)
        f.close()
    else:
        if len(dirpath) > 0:
            s = "%s --retry-wait=10 -d %s --out=%s %s" % (aria2path, dirpath, basename, url)
        else:
            s = "%s --retry-wait=10 --out=%s %s" % (aria2path, basename, url)
        os.system(s)



def collect_files(domain):
    if not os.path.exists(os.path.join(domain, 'data', 'wp_v2_media.jsonl ')):
        print("Not found wp_v2_media.jsonl")
        return
    objects = []
    f = open(os.path.join(domain, 'data', 'wp_v2_media.jsonl '), 'r', encoding='utf8')
    for row in f:
        object = json.loads(row)
        objects.append(object['source_url'])
    f.close()

    for url in objects:
        logging.info('Download file %s' % (url))
        parsed = urlparse(url)
        filepath = os.path.join(domain + '/files' + parsed.path)
        get_file(url, filepath)

def get_self_url(data):
#    print('1', data)
    if '_links' not in data.keys():
        return None
    if 'self' not in data['_links'].keys():
        return None
    if isinstance(data['_links']['self'], dict):
        return data['_links']['self']['href']
    elif isinstance(data['_links']['self'], str):
        return data['_links']['self']
    elif isinstance(data['_links']['self'], list):
        if len(data['_links']['self']) == 0:
            return None
        return data['_links']['self'][0]['href']
    return None


def dump_route_list(url, route, filepath):
#    url =  root_url + '/wp-json' + route
    outfile = os.path.join(filepath, route.strip('/').replace('/', '_') + '.jsonl')
    page = 0
    outdata = []
    print(url)
    while True:
        page += 1
        logging.info('Processing page %d of %s' % (page, route))
        rc = 0
        while True:
            if rc == RETRY_COUNT:
                resp = None
                break
            rc += 1
            try:
                resp = requests.get(url + '?page=%d&order=asc&orderby=id&per_page=%d' % (page, WP_DEFAULT_PAGESIZE), headers=REQUEST_HEADER, timeout=DEFAULT_TIMEOUT)
                break
            except KeyboardInterrupt:
                print('- timeout on data retrieval')
        if resp is None:
            print('- error on data retrieval')
            return
        if resp.status_code != 200:
            logging.debug('- HTTP status code is %d, expected 200' % (resp.status_code))
            break
        data = resp.json()
        if isinstance(data, dict):
            logging.debugo('- end of iteration %s' % (route))
            break
        elif isinstance(data, list):
            if len(data) == 0:
                outdata.extend(data)
                logging.debug('- end of iteration %s. Zero objects' % (route))
                break
            else:
                outdata.extend(data)
    f = open(outfile, 'w', encoding='utf8')
    for row in outdata:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    f.close()


def dump_route_dict(url, route, filepath):
#    url =  root_url + '/wp-json' + route
    outfile = os.path.join(filepath, route.strip('/').replace('/', '_') + '.json')
    resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
    if resp.status_code == 200:
        f = open(outfile, 'w', encoding='utf8')
        f.write(resp.text)
        f.close()


def collect_data(domain, get_unknown=True):
    known_routes_filename = pkg_resources.resource_filename('wparc', 'data/known_routes.yml')
    f = open(known_routes_filename, 'r', encoding='utf8')
    known_routes = yaml.load(f, Loader=Loader)
    f.close()
    url = 'https://' + domain + '/wp-json/'
    wptext = requests.get(url, headers=REQUEST_HEADER, timeout=DEFAULT_TIMEOUT)
    wpjson = wptext.json()
    allroutes = list(wpjson['routes'].keys())
    logging.info('Total routes %d' % (len(allroutes)))
    os.makedirs(os.path.join(domain, 'data'), exist_ok=True)
    f = open(os.path.join(domain, 'data', 'wp-json.json'), 'w', encoding='utf8')
    f.write(json.dumps(wpjson, ensure_ascii=False))
    f.close()
    for route in allroutes:
        if route in known_routes['public-list']:
            logging.info("Dump objects route %s" % (route))
            dump_route_list(url=get_self_url(wpjson['routes'][route]), route=route, filepath=os.path.join(domain, 'data'))
        elif route in known_routes['public-dict']:
            logging.info("Dump dict route %s" % (route))
            dump_route_dict(url=get_self_url(wpjson['routes'][route]), route=route, filepath=os.path.join(domain, 'data'))
        elif route in known_routes['protected']:
            pass
#            logging.info("Route %s is protected. Skip" % (route))
        elif route in known_routes['useless']:
#            logging.info("Route %s is useless. Skip" % (route))
            pass
        elif '?P' in route:
            logging.info("[!] Route %s is unknown and has regexp. Skip" % (route))
        else:
            logging.info("[!] Route %s is unknown." % (route))
            if get_unknown:
                endpoints = wpjson['routes'][route]['endpoints']
                if len(endpoints) > 0:
                    if not isinstance(endpoints[0]['args'], list) and 'page' in endpoints[0]['args'].keys() and 'per_page' in endpoints[0]['args'].keys():
                        logging.info("Dump objects route %s" % (route))
                        dump_route_list(url=get_self_url(wpjson['routes'][route]), route=route, filepath=os.path.join(domain, 'data'))
                    else:
                        logging.info("Dump dict route %s" % (route))
                        dump_route_dict(url=get_self_url(wpjson['routes'][route]), route=route, filepath=os.path.join(domain, 'data'))


