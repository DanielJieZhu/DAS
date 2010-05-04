#!/usr/bin/env python
#pylint: disable-msg=C0301,C0103

"""
DAS admin tool to handle DAS map/reduce records.
"""
__revision__ = "$Id"
__version__ = "$Revision"
__author__ = "Valentin Kuznetsov"

import sys
import time
import types
import traceback
from optparse import OptionParser
from DAS.utils.das_config import das_readconfig

# monogo db modules
from pymongo.connection import Connection
from pymongo import DESCENDING

class DASOptionParser: 
    """
     DAS cli option parser
    """
    def __init__(self):
        self.parser = OptionParser()
        self.parser.add_option("--host", action="store", type="string", 
             default="localhost", dest="host",
             help="specify MongoDB hostname")
        self.parser.add_option("--port", action="store", type="int", 
             default="27017", dest="port",
             help="specify MongoDB port")
        self.parser.add_option("--list", action="store", dest="list",
             default="", type="string",
             help="list map/reduce functions in DAS, accept alias name")
        self.parser.add_option("--delete", action="store", dest="delete",
             default="", type="string",
             help="delete map/reduce functions in DAS, accept alias name")

    def get_opt(self):
        """
        Returns parse list of options
        """
        return self.parser.parse_args()

class MapReduceMgr(object):
    """
    General class to work with DAS mongo dbs.
    """
    def __init__(self, host, port):
        self.host   = host
        self.port   = port
        self.conn   = Connection(host, port)
        self.mapreduce = self.conn['das']['mapreduce']

    def add_mapreduce(self, name, fmap, freduce):
        """
        Add mapreduce record and assign it to given name.
        """
        print "Add %s map/reduce function" % name
        exists = self.mapreduce.find_one({'name':name})
        if  exists:
            raise Exception('Map/reduce functions for %s already exists' % name)
        self.mapreduce.insert(dict(name=name, map=fmap, reduce=freduce))
        self.mapreduce.ensure_index([('name', DESCENDING)])

    def list_mapreduce(self, name=None):
        """
        List existing mapreduce records for given name
        """
        if  name and name != '*':
            result = self.mapreduce.find({'name':name})
        else:
            result = self.mapreduce.find({})
        for row in result:
            yield row

    def delete_mapreduce(self, name=None):
        """
        Delete existing mapreduce records for given name
        """
        print "Delete %s map/reduce function(s)" % name
        if  name and name != '*':
            self.mapreduce.remove({'name':name})
        else:
            self.mapreduce.remove({})
#
# main
#
if __name__ == '__main__':
    OMGR = DASOptionParser()
    (opts, args) = OMGR.get_opt()
    MGR = MapReduceMgr(opts.host, opts.port)

    delete_name = opts.delete
    if  delete_name:
        MGR.delete_mapreduce(delete_name)
        sys.exit(0)

    list_name = opts.list
    if  list_name:
        for row in MGR.list_mapreduce(list_name):
            print row
        sys.exit(0)

    # delete all existing records
    MGR.delete_mapreduce('*')

    # add sum(block.replica.size) map/reduce function
    MAP = """
function() {
    /*
     * emit(a, 1) is suitable for counting
     * emit(null, a) is suitable for summing
     * Here we emit for different cases
     * 1. when there is only {block:{replica:{size:1}}}
     * 2. when there are records as {block:[{replica:{size:1}}]}
     * 3. when all fields are list items, e.g.
     * {block:[{replica:[{size:1}]}]}
     */
    if (this.block) {
        if (this.block.replica) {
            if (this.block.replica.size) 
                emit(null, this.block.replica.size);
        }
        for (var i = 0; i < this.block.length; i++) {
            var info = this.block[i];
            if  (info.replica) {
                if (info.replica.size)
                    emit(null, info.replica.size);
                for (var j=0; j< info.replica.length; j++) {
                    var item = info.replica[j];
                    if  (item.size) {
                        emit(null, item.size);
                    }
                }
            }
        }
    }
}
"""
    REDUCE = """
function (key, values) {
    var total = 0;
    for (var i = 0; i < values.length; i++) {
        total += values[i];
    }
    return total;
}
"""   
    MGR.add_mapreduce('sum(block.replica.size)', MAP, REDUCE)


