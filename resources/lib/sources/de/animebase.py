# -*- coding: UTF-8 -*-

"""
    grumpybear Add-on (C) 2019
    Credits to Placenta and Covenant; our thanks go to their creators

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Addon Name: grumpybear
# Addon id: plugin.video.grumpybear
# Addon Provider: grumpybear

import re
import urllib
import urlparse


from resources.lib.modules import cleantitle
from resources.lib.modules import tvmaze
from resources.lib.modules import source_utils
from resources.lib.modules import dom_parser
from resources.lib.modules import source_faultlog
from resources.lib.modules.handler.requestHandler import cRequestHandler

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.genre_filter = ['animation', 'anime']
        self.domains = ['anime-base.net']
        self.base_link = 'http://anime-base.net'
        self.search_link = '/suche_ajax.php'

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = None
            for title in [tvshowtitle, localtvshowtitle, tvmaze.tvMaze().showLookup('thetvdb', tvdb).get('name')] + source_utils.aliases_to_array(aliases):
                if url: break
                url = self.__search(title)
            return urllib.urlencode({'url': url}) if url else None
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return

            episode = tvmaze.tvMaze().episodeAbsoluteNumber(tvdb, int(season), int(episode))

            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            data.update({'episode': episode})
            return urllib.urlencode(data)
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []

        try:
            if not url:
                return sources

            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            url = data.get('url')
            episode = int(data.get('episode', 1))

            oRequest = cRequestHandler(urlparse.urljoin(self.base_link, url))
            r = oRequest.request()
            r = {'': dom_parser.parse_dom(r, 'div', attrs={'id': 'gerdub'}), 'subbed': dom_parser.parse_dom(r, 'div', attrs={'id': 'gersub'})}

            for info, data in r.iteritems():
                data = dom_parser.parse_dom(data, 'tr')
                data = [dom_parser.parse_dom(i, 'a', req='href') for i in data if dom_parser.parse_dom(i, 'a', attrs={'id': str(episode)})]
                data = [(link.attrs['href'], dom_parser.parse_dom(link.content, 'img', req='src')) for i in data for link in i]
                data = [(i[0], i[1][0].attrs['src']) for i in data if i[1]]
                data = [(i[0], re.findall('/(\w+)\.\w+', i[1])) for i in data]
                data = [(i[0], i[1][0]) for i in data if i[1]]

                for link, hoster in data:
                    valid, hoster = source_utils.is_host_valid(hoster, hostDict)
                    if not valid: continue

                    sources.append({'source': hoster, 'quality': 'SD', 'language': 'de', 'url': link, 'info': info, 'direct': False, 'debridonly': False})

            return sources
        except:
            source_faultlog.logFault(__name__, source_faultlog.tagScrape, url)
            return sources

    def resolve(self, url):
        try:
            if not url.startswith('http'): url = urlparse.urljoin(self.base_link, url)

            if self.base_link in url:
                oRequest = cRequestHandler(url)
                r = oRequest.request()
                r = dom_parser.parse_dom(r, 'meta', req='content')[0]
                r = r.attrs['content']
                r = re.findall('''url\s*=\s*([^'"]+)''', r, re.I)
                if r:
                    url = r[0]

            return url
        except:
            source_faultlog.logFault(__name__, source_faultlog.tagResolve)
            return

    def __search(self, title):
        try:
            t = cleantitle.get(title)
            oRequest = cRequestHandler(urlparse.urljoin(self.base_link, self.search_link))
            oRequest.setRequestType(1)
            oRequest.addParameters('suchbegriff', title)
            r = oRequest.request()
            r = dom_parser.parse_dom(r, 'a', attrs={'class': 'ausgabe_1'}, req='href')
            r = [(i.attrs['href'], i.content) for i in r]
            r = [i[0] for i in r if cleantitle.get(i[1]) == t]
            if len(r) == 0:
                return

            return source_utils.strip_domain(r[0])
        except:
            try:
                source_faultlog.logFault(__name__, source_faultlog.tagSearch, title)
            except:
                return
            return
