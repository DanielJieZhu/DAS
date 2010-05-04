#!/usr/bin/env python
import urllib2, urllib, httplib
import sys, os, time, types
from Cookie import SimpleCookie
import cookielib

def timestamp():
    """Construct timestamp used by Shibboleth"""
#    cet_time = time.mktime(time.gmtime()) + 1*60+60
#    return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(cet_time))
    return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())


class HTTPSClientAuthHandler(urllib2.HTTPSHandler):
    """Simple HTTPS client authentication class based on provided key/ca information"""
    def __init__(self, key=None, cert=None, level=0):
        urllib2.HTTPSHandler.__init__(self, debuglevel=level)
        self.key = key
        self.cert = cert

    def https_open(self, req):
        """Open request method"""
        #Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.getConnection, req)

    def getConnection(self, host, timeout=300):
        """Connection method"""
        if  self.key:
            return httplib.HTTPSConnection(host, key_file=self.key, cert_file=self.cert)
        return httplib.HTTPSConnection(host)

def run_summary_url(url, params):
    """Construct Run Summary URL from provided parameters"""
    if  url[-1] == '/':
        url = url[:-1]
    if  url[-1] == '?':
        url = url[:-1]
    paramstr = ''
    for key, val in params.items():
        paramstr += '%s=%s&' % (key, val)
    return url + '?' + paramstr[:-1]

def get_run_summary(url, params, key, cert, debug=0):
    """Main routine to get information from Run Summary data service"""
    # setup HTTP handlers
    cookie_handler = urllib2.HTTPCookieProcessor()
    https_handler  = HTTPSClientAuthHandler(key, cert, debug)
    opener = urllib2.build_opener(cookie_handler, https_handler)
    urllib2.install_opener(opener)

    # send request to RunSummary, it set the _shibstate_XXXXX cookie which 
    # will be used for redirection
    f      = opener.open(run_summary_url(url, params))
    data   = f.read()
    f.close()

    # now, request authentication at CERN login page where I'll be redirected
    params = dict(wa='wsignin1.0', 
                  wreply='https://cmswbm.web.cern.ch/Shibboleth.sso/ADFS', 
                  wct=timestamp(), wctx='cookie', 
                  wtrealm='urn:federation:self')
    params = urllib.urlencode(params, doseq=True)

    url    = 'https://login.cern.ch/adfs/ls/auth/sslclient/'
    f      = opener.open(url, params)
    data   = f.read()
    f.close()

    # at this point it sends back the XML form to proceed since my client
    # doesn't support JavaScript and no auto-redirection happened
    # Since XML form is not well-formed XML I'll parsed manually, urggg ...
    param_dict = {}
    for item in data.split('<input '):
        if  item.find('name=') != -1 and item.find('value=') != -1:
            namelist = item.split('name="')
            key = namelist[1].split('"')[0]
            vallist = item.split('value="')
            val = vallist[1].split('"')[0].replace('&quot;', '"').replace('&lt;','<')
            param_dict[key] = val

    # now I'm ready to send my form to Shibboleth authentication
    # request to Shibboleth
    url    = 'https://cmswbm.web.cern.ch/Shibboleth.sso/ADFS'
    params = urllib.urlencode(param_dict)
    f      = opener.open(url, params)
    data   = f.read()
    f.close()
    return data

#
# main
#
if __name__ == '__main__':
    debug= 1
    key  = '/Users/vk/.globus/userkey.pem'
    cert = '/Users/vk/.globus/usercert.pem'
    params = {'RUN':97029, 'DB':'cms_omds_lb', 'FORMAT':'XML'}
    url  = 'https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/RunSummary'
    data = get_run_summary(url, params, key, cert, debug)
    print data
