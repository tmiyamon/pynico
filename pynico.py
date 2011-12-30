#!/bin/env python
#-*- coding:utf-8 -*-

import mechanize
import urllib
import cookielib
import time
import re
import functools
import time
import datetime

from lxml import etree
import collections


def to_dict(xml, key_prefix=''):
    def xml_to_item(el):
        item = el.text if el.text else ''
        child_dicts = collections.defaultdict(list)
        for child in el.getchildren():
            child_dicts[key_prefix + child.tag].append(xml_to_item(child))

        return dict(child_dicts) or item

    root = etree.parse(xml).getroot()
    return {root.tag: xml_to_item(root)}

class APIResponse(object):
    def __init__(self, d):
        self.__dict__.update(d)

    def __str__(self):
        return self.__dict__.__str__()

class GetFLV(APIResponse):
    def __init__(self, d):
        super(GetFLV, self).__init__(d)

    def is_premium(self):
        return self._is_premium == '1'

    def __str__(self):
        return '<%s: %s>'%(self.__class__.__name__, super(GetFLV, self).__str__())


class NiconicoAPIClient(mechanize.Browser):
    URL_GETTHUMBINFO = "http://ext.nicovideo.jp/api/getthumbinfo/%s"
    URL_THUMB = "http://ext.nicovideo.jp/thumb/%s"
    URL_GETFLV = "http://www.nicovideo.jp/api/getflv?v=%s"
    URL_GETRELATION = "http://www.nicovideo.jp/api/getrelation?page=%(page)d&sort=%(sort)s&order=%(order)s&video=%(video)s"
    URL_LOGIN = "https://secure.nicovideo.jp/secure/login_form"
    URL_MYLIST = "http://www.nicovideo.jp/my/mylist"
    URL_GETWAYBACKKEY = 'http://www.nicovideo.jp/api/getwaybackkey?thread=%(thread_id)s'

    TOKEN_PATTERN = re.compile('NicoAPI\.token \= "(.+)"')

    def __init__(self, user_id=None, passwd=None, factory=None, history=None, request_class=None):
        mechanize.Browser.__init__(self, factory, history, request_class)

        self.user_id = user_id
        self.passwd = passwd

        #cookie Jar
        cj = cookielib.LWPCookieJar()
        self.set_cookiejar(cj)

        # Browser options
        self.set_handle_equiv(True)
        self.set_handle_gzip(False)
        self.set_handle_redirect(True)
        self.set_handle_referer(True)
        self.set_handle_robots(False)

        # Follows refresh 0 but not hangs on refresh > 0
        self.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(),  max_time=1)

        # Want debugging messages?
        # self.set_debug_http(True)
        # self.set_debug_redirects(True)
        # self.set_debug_responses(True)

        # User-Agent (this is cheating,  ok?)
        self.addheaders = [('User-agent',  'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    def login_required(self, func):
        self.login()
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        return wrapper


    def getthumbinfo(self, mov_name):
        return to_dict(self.open(NiconicoAPIClient.URL_GETTHUMBINFO % mov_name))

    def thumb(self, mov_name):
        return self.open(NiconicoAPIClient.URL_THUMB % mov_name).read()

    def getflv(self, mov_name):
        self.login()
        self.open("http://www.nicovideo.jp/watch/%s" % mov_name)
        contents = self.open(NiconicoAPIClient.URL_GETFLV % mov_name)
        ret = {}
        for e in contents.get_data().split('&'):
            k, v = map(urllib.unquote, e.split('='))
            ret['_' + k] = v
        return GetFLV(ret)
        #return GetFLV(dict([map(urllib.unquote, a.split('=')) for a in contents.get_data().split('&')]))

    def getrelation(self, mov_name, page=1, sort='p', order='d'):
        """Call getreleation api
        Args:
            mov_name: A target vide name such as sm***.
            page: A number of page to show.
            sort: A kind of sorting,
                p: by recommendation.
                r: by commented quantity.
                v: by watched quantity.
                m: by 'mylist' quantity.
            order: A kind of order,
                d: by descendant.
                a: by ascendant.
        Returns:
            A dict simply parsed from response xml.
        """

        params = {
            'video': mov_name,
            'page': page,
            'sort': sort,
            'order': order
        }
        return to_dict(self.open(NiconicoAPIClient.URL_GETRELATION % params))


    def login(self, user_id = None, passwd = None):
        _user_id = user_id or self.user_id
        _passwd = passwd or self.passwd

        assert _user_id, "user_id required for login"
        assert _passwd, "passwd required for login"

        self.open(NiconicoAPIClient.URL_LOGIN)
        time.sleep(0.5)

        self.select_form(nr = 0)
        self.form["mail"] = _user_id
        self.form["password"] = _passwd

        return self.submit()

    def gettoken(self):
        self.login()

        input = self.open('http://www.nicovideo.jp/my/mylist')
        for line in input:
            m = NiconicoAPIClient.TOKEN_PATTERN.search(line)
            if m:
                return m.groups()[0]

    def get_movie(self, mov_name):
        return self.retrieve(self._getflv(mov_name)['url'])

    def comments(self, mov_name):
        flv_data = self.getflv(mov_name)
        params = {}

        params['thread_id'] =  flv_data._thread_id
        params['when'] = str(int(time.mktime(datetime.datetime.today().timetuple())))
        params['version'] = '20090904'
        params['click_revision'] = '-1'

        if flv_data.is_premium():
            params['user_id'] = flv_data._user_id
            params['wayback_key'] = self.open(NiconicoAPIClient.URL_GETWAYBACKKEY%params).read().split('=')[1]

            request_xml = """
                <packet>
                <thread thread="%(thread_id)s" version="%(version)s" waybackkey="%(wayback_key)s" when="%(when)s" user_id="%(user_id)s" click_revision="%(click_revision)s"/>
                <thread_leaves thread="%(thread_id)s" waybackkey="%(wayback_key)s" when="%(when)s" user_id="%(user_id)s" score="1">0-9999:9999,9999</thread_leaves>
                </packet>"""%params

        else:
            request_xml = """<thread thread = "%(thread_id)s" version="%(version)s" res_from="%(num)s"></thread>"""%flv_data

        return self.open(flv_data._ms, request_xml).read()


