#!/bin/env python
#-*- coding:utf-8 -*-

import mechanize
import urllib
import cookielib

from lxml import etree
import collections


def to_dict(xml):
    def xml_to_item(el):
        item = el.text if el.text else ''
        child_dicts = collections.defaultdict(list)
        for child in el.getchildren():
            child_dicts[child.tag].append(xml_to_item(child))

        return dict(child_dicts) or item

    root = etree.parse(xml).getroot()
    return {root.tag: xml_to_item(root)}


class NiconicoClient(mechanize.Browser):
    URL_GETTHUMBINFO = "http://ext.nicovideo.jp/api/getthumbinfo/%s"
    URL_THUMB = "http://ext.nicovideo.jp/thumb/%s"
    URL_GETFLV = "http://www.nicovideo.jp/api/getflv?v=%s"
    URL_GETRELATION = "http://www.nicovideo.jp/api/getrelation?page=%(page)d&sort=%(sort)s&order=%(order)s&video=%(video)s"
    URL_LOGIN = "https://secure.nicovideo.jp/secure/login_form"

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


    def getthumbinfo(self, mov_name):
        return to_dict(self.open(NiconicoClient.URL_GETTHUMBINFO % mov_name))

    def thumb(self, mov_name):
        return self.open(NiconicoClient.URL_THUMB % mov_name).read()

    def getflv(self, mov_name):
        self.login()
        self.open("http://www.nicovideo.jp/watch/%s" % mov_name)
        contents = self.open(NiconicoClient.URL_GETFLV % mov_name)
        return dict([map(urllib.unquote, a.split('=')) for a in contents.get_data().split('&')])

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
        return to_dict(self.open(NiconicoClient.URL_GETRELATION % params))


    def login(self):
        assert(self.user_id)
        assert(self.password)
        self.open(NiconicoClient.URL_LOGIN)
        self.select_form(nr = 0)
        self.form["mail"] = self.user_id
        self.form["password"] = self.passwd

        return self.submit()


    def get_movie(self, mov_name):
        return self.retrieve(self._getflv(mov_name)['url'])

    def msg(self, mov_name):
        flv_data = self.getflv(mov_name)
        flv_data['num'] = '-10000'
        request_xml = '<thread thread = "%(thread_id)s" version="20061206" res_from="%(num)s"></thread>'%flv_data
        return to_dict(self.open(flv_data['ms'], request_xml))


