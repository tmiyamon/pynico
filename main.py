#!/bin/env python
#-*- coding:utf-8 -*-

import mechanize
import urllib
import cookielib

class NiconicoClient(mechanize.Browser):
    URL_LOGIN = "https://secure.nicovideo.jp/secure/login_form"

    def __init__(self, user_id, passwd, factory=None, history=None, request_class=None):
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
        self.set_debug_http(True)
        self.set_debug_redirects(True)
        self.set_debug_responses(True)

        # User-Agent (this is cheating,  ok?)
        self.addheaders = [('User-agent',  'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]


    def login(self):
        self.open(NiconicoClient.URL_LOGIN)
        self.select_form(nr = 0)
        self.form["mail"] = self.user_id
        self.form["password"] = self.passwd

        return self.submit()

    def _getflv(self, mov_name):
        self.login()
        self.open("http://www.nicovideo.jp/watch/%s" % mov_name)
        contents = self.open("http://www.nicovideo.jp/api/getflv?v=%s" % mov_name)
        return dict([map(urllib.unquote, a.split('=')) for a in contents.get_data().split('&')])

    def get_movie(self, mov_name):
        return self.retrieve(self._getflv(mov_name)['url'])

    # def get_comment(self, mov_name):
        # flv_data = self._getflv(mov_name)
        # flv_data['num'] = '-10000'
        # request_xml = '<thread thread = "%(thread_id)s" version="20061206" res_from="%(num)s"></thread>'%flv_data
        # resonse_xml = self.open(flv_data['ms'], request_xml)
        # tree = ElementTree.parse(response_xml)

