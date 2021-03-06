#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
DAS QL module include definition of DAS operators,
filters, aggregators, etc.
"""

__revision__ = "$Id: das_ql.py,v 1.4 2010/04/30 16:35:03 valya Exp $"
__version__ = "$Revision: 1.4 $"
__author__ = "Valentin Kuznetsov"

import inspect
from DAS.core.das_aggregators import ResultObject
from DAS.utils.das_config import das_readconfig
from DAS.utils.das_db import db_connection

DAS_RECORD_KEYS = ['das_id', 'cache_id', 'das', 'qhash', 'error', 'reason']
DAS_FILTERS   = ['grep', 'unique', 'sort']
DAS_OPERATORS = ['=', 'between', 'last', 'in']
DAS_SPECIALS  = ['date', 'system', 'instance']
DAS_DB_KEYWORDS = ['records', 'queries', 'popular', '_id']
DAS_RESERVED  = DAS_FILTERS + DAS_OPERATORS + DAS_SPECIALS
URL_MAP       = {
    '!=' : '%21%3D',
    '<=' : '%3C%3D',
    '>=' : '%3E%3D',
    '<'  : '%3C',
    '>'  : '%3E',
    '='  : '%3D',
    ' '  : '%20'
}
MONGO_MAP     = {
    '>'  : '$gt',
    '<'  : '$lt',
    '>=' : '$gte',
    '<=' : '$lte',
    'in' : '$in',
    '!=' : '$ne',
    'nin': '$nin',
#    'between':'$in',
}
def mongo_operator(das_operator):
    """
    Convert DAS operator into MongoDB equivalent
    """
    if  das_operator in MONGO_MAP:
        return MONGO_MAP[das_operator]
    return None

def das_filters():
    """
    Return list of DAS filters
    """
    return DAS_FILTERS

def das_operators():
    """
    Return list of DAS operators
    """
    return DAS_OPERATORS

def das_special_keys():
    """
    Return list of DAS special keywords
    """
    return DAS_SPECIALS

def das_reserved():
    """
    Return list of DAS reserved keywords
    """
    return DAS_RESERVED

def das_db_keywords():
    """
    Return list of DAS special keywords for retrieving information DAS DBs
    """
    return DAS_DB_KEYWORDS

def das_record_keys():
    """
    Return list of DAS special keys used in DAS records
    """
    return DAS_RECORD_KEYS

def das_aggregators():
    """
    Inspect ResultObject class and return its member function,
    which represents DAS aggregator functions
    """
    alist = []
    for name, _ftype in inspect.getmembers(ResultObject):
        if  name.find("__") != -1:
            continue
        alist.append(name)
    return alist

def das_mapreduces():
    """
    Return list of DAS mapreduce functions
    """
    mlist   = []
    config  = das_readconfig()
    dburi   = config['mongodb']['dburi']
    dbname  = config['dasdb']['dbname']
    colname = config['dasdb']['mrcollection']
    conn    = db_connection(dburi)
    coll    = conn[dbname][colname]
    for row in coll.find({}):
        if  set(row.keys()) == set(['map', 'reduce', 'name', '_id']):
            mlist.append(row['name'])
    return mlist

