#!/usr/bin/env python
#-*- coding: utf-8 -*-
#pylint: disable=C0301,C0103,R0903,R0912,R0913,R0914,R0915

"""
DAS command line interface
"""
from __future__ import print_function
__author__ = "Valentin Kuznetsov"

import time
import json
import argparse
from pprint import pformat
from DAS.core.das_core import DASCore
from DAS.core.das_query import DASQuery
from DAS.utils.utils import dump
from DAS.utils.ddict import DotDict
from DAS.utils.das_timer import get_das_timer

import sys
if sys.version_info < (2, 6):
    raise Exception("DAS requires python 2.6 or greater")

class DASOptionParser(object):
    """
    DAS cli option parser
    """
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog='PROG')
        self.parser.add_argument("-v", "--verbose", action="store",\
                                          type=int, default=0,\
                                          dest="verbose",\
             help="verbose output")
        self.parser.add_argument("--profile", action="store_true",\
                                          dest="profile",\
             help="profile output")
        self.parser.add_argument("-q", "--query", action="store", type=str,\
                                          default="", dest="query",\
             help="specify query for your request.")
        self.parser.add_argument("--hash", action="store_true", dest="hash",\
             help="look-up MongoDB-QL query and its hash")
        self.parser.add_argument("--services", action="store_true",\
                                          dest="services",\
             help="return a list of supported data services")
        self.parser.add_argument("--keys", action="store",\
                                          dest="service",\
             help="return set of keys for given data service")
        self.parser.add_argument("--print-config", action="store_true",\
                                          dest="dasconfig",\
             help="print current DAS configuration")
        self.parser.add_argument("--no-format", action="store_true",\
                                          dest="plain",\
             help="return unformatted output, useful for scripting")
        self.parser.add_argument("--idx", action="store", type=int,\
                                          default=0, dest="idx",\
             help="start index for returned result set, aka pagination, use w/ limit")
        self.parser.add_argument("--limit", action="store", type=int,\
                                          default=0, dest="limit",\
             help="limit number of returned results")
        self.parser.add_argument("--no-output", action="store_true",\
                                          dest="nooutput",\
             help="run DAS workflow but don't print results")
        self.parser.add_argument("--no-results", action="store_true",\
                                          dest="noresults",\
             help="run DAS workflow but don't write results into the cache")
        self.parser.add_argument("--js-file", action="store", type=str,\
                      default="", dest="jsfile",\
             help="create/update KWS js file for given query")
        self.parser.add_argument("--keylearning-file", action="store", type=str,\
                      default="", dest="kfile",\
             help="create/update KWS keylearning file for given query")
        msg = 'a query cache value'
        self.parser.add_argument("--query-cache", action="store", type=int,
                               default=0, dest="qcache", help=msg)

def iterate(input_results):
    """Just iterate over generator, but don't print it out"""
    for _ in input_results:
        pass

def kws_js(dascore, query, idx, limit, jsfile, verbose=False):
    "Write result of a given query into KWS js file"
    print("Create: %s" % jsfile)
    results = dascore.result(query, idx, limit)
    tstamp = long(time.time())
    with open(jsfile, 'a') as stream:
        for row in results:
            pkey = row['das']['primary_key']
            ddict = DotDict(row)
            value = ddict[pkey]
            if  value == '*' or value == 'null' or not value:
                continue
            jsrow = json.dumps(dict(value=value, ts=tstamp))
            if  verbose:
                print(jsrow)
            stream.write(jsrow)
            stream.write('\n')

def process_document(doc):
    """
    Process a rawcache document record coming from one API of a service.
    Find all the unique output fields and insert them into the cache.
    """
    members = set()
    for key in doc.keys():
        if key not in ('das', '_id', 'das_id', 'cache_id', 'qhash'):
            members |= recursive_walk(doc[key], key)
    return list(members)

def recursive_walk(doc, prefix):
    """
    Recurse through a nested data structure, finding all
    the unique endpoint names. Lists are iterated over but do
    not add anything to the prefix, eg.:

    a: {b: 1, c: {d: 1, e: 1}, f: [{g: 1}, {h: 1}]} ->
    a.b, a.c.d, a.c.e, a.f.g, a.f.h

    (although normally we would expect each member of a list to
    have the same structure)
    """
    result = set()
    if isinstance(doc, dict):
        for key in doc.keys():
            result |= recursive_walk(doc[key], prefix + '.' + key)
    elif isinstance(doc, list):
        for item in doc:
            result |= recursive_walk(item, prefix)
    else:
        result.add(prefix)
    return result

def keylearning_js(dascore, query, kfile, verbose=False):
    "Create keylearning js file from series of given query"
    print("Create: %s" % kfile)
    with open(kfile, 'a') as stream:
        dasquery = DASQuery(query)
        result   = [r for r in dascore.result(dasquery, 0, 1)][0] # get one record only
        if  verbose:
            print(dasquery)
            print(result)
        mongo_q  = dasquery.mongo_query
        skip     = ['das_id', 'cache_id', 'qhash', 'error', 'reason', 'das']
        keys     = [k for k in mongo_q['fields'] if k not in skip]
        keys    += [k.split('.')[0] for k in mongo_q['spec'].keys()]
        keys     = list(set(keys))
        system   = result['das']['system'][0]
        urn      = result['das']['api'][0]
        members  = process_document(result)
        jsrow = json.dumps(dict(keys=keys, members=members, system=system, urn=urn))
        if  verbose:
            print(jsrow)
        stream.write(jsrow)
        stream.write('\n')
        for member in members:
            stems = member.split('.')
            jsrow = json.dumps(dict(member=member, stems=stems))
            stream.write(jsrow)
            stream.write('\n')

def run(dascore, query, idx, limit, nooutput, plain):
    """
    Execute DAS workflow for given set of parameters.
    We use this function in main and in profiler.
    """
    if  not nooutput:
        results = dascore.result(query, idx, limit)
        if  plain:
            for item in results:
                print(item)
        else:
            dump(results, idx)
    else:
        results = dascore.call(query)
        print("\n### DAS.call returns", results)

def main():
    "Main function"
    optmgr  = DASOptionParser()
    opts = optmgr.parser.parse_args()

    t0 = time.time()
    query = opts.query
    if  'instance' not in query:
        query = ' instance=prod/global ' + query
    debug = opts.verbose
    dascore = DASCore(debug=debug, nores=opts.noresults)
    if  opts.hash:
        dasquery = DASQuery(query)
        mongo_query = dasquery.mongo_query
        service_map = dasquery.service_apis_map()
        str_query   = dasquery.storage_query
        print("---------------")
        print("DAS-QL query  :", query)
        print("DAS query     :", dasquery)
        print("Mongo query   :", mongo_query)
        print("Storage query :", str_query)
        print("Services      :\n")
        for srv, val in service_map.items():
            print("%s : %s\n" % (srv, ', '.join(val)))
        sys.exit(0)
    sdict = dascore.keys()
    if  opts.services:
        msg = "DAS services:"
        print(msg)
        print("-"*len(msg))
        keys = list(sdict.keys())
        keys.sort()
        for key in keys:
            print(key)
    elif  opts.service:
        msg = "DAS service %s:" % opts.service
        print(msg)
        print("-"*len(msg))
        keys = sdict[opts.service]
        keys.sort()
        for key in keys:
            print(key)
    elif opts.jsfile:
        kws_js(dascore, query, opts.idx, opts.limit, opts.jsfile, debug)
        sys.exit(0)
    elif opts.kfile:
        keylearning_js(dascore, query, opts.kfile, debug)
        sys.exit(0)
    elif query:

        idx    = opts.idx
        limit  = opts.limit
        output = opts.nooutput
        plain  = opts.plain
        qcache = opts.qcache

        if  opts.profile:
            import cProfile # python profiler
            import pstats   # profiler statistics
            cmd  = 'run(dascore,query,idx,limit,output,plain)'
            cProfile.runctx(cmd, globals(), locals(), 'profile.dat')
            info = pstats.Stats('profile.dat')
            info.sort_stats('cumulative')
            info.print_stats()
        else:
            run(dascore, query, idx, limit, output, plain)
    elif opts.dasconfig:
        print(pformat(dascore.dasconfig))
    else:
        print()
        print("DAS CLI interface, no actions found,")
        print("please use --help for more options.")
    timestamp = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    timer = get_das_timer()
    print("\nDAS execution time:\n")
    if  debug:
        timelist = []
        for _, timerdict in timer.items():
            counter = timerdict['counter']
            tag = timerdict['tag']
            exetime = timerdict['time']
            timelist.append((counter, tag, exetime))
        timelist.sort()
        for _, tag, exetime in timelist:
            print("%s %s sec" % (tag, round(exetime, 2)))
    print("Total %s sec, %s" % (round(time.time()-t0, 2), timestamp))
#
# main
#
if __name__ == '__main__':
    main()
