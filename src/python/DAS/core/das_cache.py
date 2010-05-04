#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
DAS cache wrapper. Communitate with DAS core and cache server(s)
"""

__revision__ = "$Id: das_cache.py,v 1.8 2009/05/22 21:04:40 valya Exp $"
__version__ = "$Revision: 1.8 $"
__author__ = "Valentin Kuznetsov"

# DAS modules
from DAS.core.cache import Cache, NoResults
from DAS.core.das_memcache import DASMemcache
from DAS.core.das_couchcache import DASCouchcache
from DAS.core.das_filecache import DASFilecache

class DASCache(Cache):
    """
    Base DAS cache class based on memcache and couchdb cache back-end
    servers. The class should be initialized with config dict.
    """
    def __init__(self, config):
        Cache.__init__(self, config)
        self.servers = {'memcache': DASMemcache(config),
                        'filecache': DASFilecache(config),
                        'couchcache': DASCouchcache(config),
        }
        self.logger.info('DASCache using servers = %s' % self.servers)

    def incache(self, query):
        """
        Retreieve results from cache, otherwise return null.
        """
        servers = self.servers.keys()
        servers.sort()
        for name in servers:
            self.logger.info("DASCache::incache, using %s" % name)
            srv = self.servers[name]
            res = srv.incache(query)
            if  res:
                return res

    def get_from_cache(self, query, idx=0, limit=None):
        """
        Retreieve results from cache, otherwise return null.
        """
        servers = self.servers.keys()
        servers.sort()
        for name in servers:
            self.logger.info("DASCache::get_from_cache, using %s" % name)
            srv = self.servers[name]
            res = srv.get_from_cache(query, idx, limit)
            if  res:
                return res

    def update_cache(self, query, results, expire):
        """
        Insert results into cache.
        """
        servers = self.servers.keys()
        servers.sort()
        for name in servers:
            self.logger.info("DASCache::update_cache, using %s" % name)
            srv = self.servers[name]
            results = srv.update_cache(query, results, expire)
        for item in results:
            yield item

    def clean_cache(self, cache=None):
        """
        Clean expired results in cache.
        """
        if  cache: # request to update particular cache server
            if  not self.servers.has_key(cache):
                raise Exception("DASCache doesn't support cache='%s'" % cache)
            srv = self.servers[cache]
            srv.clean_cache()
            return
        servers = self.servers.keys()
        servers.sort()
        for name in servers:
            self.logger.info("DASCache::clean_cache, using %s" % name)
            srv = self.servers[name]
            srv.clean_cache()

    def delete_cache(self, dbname='das', cache=None):
        """
        Delete all results in cache.
        """
        if  cache: # request to update particular cache server
            if  not self.servers.has_key(cache):
                raise Exception("DASCache doesn't support cache='%s'" % cache)
            srv = self.servers[cache]
            srv.delete_cache(dbname)
            return
        servers = self.servers.keys()
        servers.sort()
        for name in servers:
            self.logger.info("DASCache::clean_cache, using %s" % name)
            srv = self.servers[name]
            srv.delete_cache(dbname)
