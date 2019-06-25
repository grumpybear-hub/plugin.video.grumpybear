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
import urlparse
import urllib
import time

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import dom_parser
from resources.lib.modules import source_faultlog
from resources.lib.modules import source_utils
from resources.lib.modules import duckduckgo
from resources.lib.modules.handler.requestHandler import cRequestHandler
from resources.lib.modules.handler.ParameterHandler import ParameterHandler

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domains = ['alleserien.com']
        self.base_link = 'http://alleserien.com'
        self.search_link = '/search?page=1&from=1900&to=2018&type=Alle&rating=0&sortBy=latest&search=%s'
        self.search_link_query = '/searchPagination'
        self.link_url = '/getpart'
        self.link_url_movie = '/film-getpart'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            return duckduckgo.search([localtitle] + source_utils.aliases_to_array(aliases), year, self.domains[0], "(.*)\sHD\sStream")
        except:
            return ""

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'localtvshowtitle': localtvshowtitle, 'aliases': aliases, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return

            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            tvshowtitle = data['tvshowtitle']
            aliases = source_utils.aliases_to_array(eval(data['aliases']))
            aliases.append(data['localtvshowtitle'])

            url = self.__search([tvshowtitle] + aliases, data['year'], season)
            if not url: return
            
            urlWithEpisode = url+"?episode="+str(episode)+"?season="+str(season)
            return source_utils.strip_domain(urlWithEpisode)
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if not url:
                return sources
            episode = int(re.findall(r'\?episode=(.*)\?', url)[0])
            season = int(re.findall(r'\?season=(.*)', url)[0])
            url = url.replace('?episode=' + str(episode), '').replace('?season=' + str(season), '')
            url = urlparse.urljoin(self.base_link, url)

            oRequest = cRequestHandler(url)
            content = oRequest.request()

            links = re.findall(r'javascript:location.href = \'(.*?)\'"((?s).*?)epTitle">(.*?)</div>', content)
            season = "Staffel " + str(season)
            episode = "Folge " + str(episode)        

            for x in range(0, len(links)): 
                if season in links[x][2] and episode in links[x][2]:
                    link = links[x][0]
            url = link
            oRequest = cRequestHandler(link)
            content = oRequest.request()

            links = dom_parser.parse_dom(content, 'tr', attrs={'class': 'partItem'})
            links = [(i.attrs['data-id'], i.attrs['data-controlid'], re.findall("(.*)\.png", i.content)[0].split("/")[-1]) for i in
                     links if 'data-id' in i[0]]

            temp = [i for i in links if i[2].lower() == 'vip']

            
            for id, controlId, host in temp:
                link = self.resolve((url, id, controlId, 'film' in url))
                import json
                hash =  re.findall(r'o/(.*)', link)
                oRequest = cRequestHandler(link + '?do=getVideo')
                oRequest.addHeaderEntry('Referer', url)
                oRequest.addHeaderEntry('Origin', 'http://alleserienplayer.com')
                oRequest.addHeaderEntry('Host', 'alleserienplayer.com')
                oRequest.addHeaderEntry('X-Requested-With', 'XMLHttpRequest')
                oRequest.addParameters('do', 'getVideo')
                oRequest.addParameters('hash', hash[0])
                oRequest.addParameters('r', url)
                oRequest.setRequestType(1)

                result = oRequest.request()
                result = json.loads(result)
                for i in result['videoSources']:
                    sources.append({'source': 'CDN', 'quality': source_utils.label_to_quality(i['label']), 'language': 'de', 'url': i['file'],'direct': True, 'debridonly': False, 'checkquality': False}) 

            for i in links:
                multiPart = re.findall('(.*?)-part-\d+', i[2])
                if(len(multiPart) > 0):
                    links = [(i[0], i[1], i[2] + '-part-1' if i[2] == multiPart[0] else i[2]) for i in links]

            links = [(i[0], i[1], re.findall('(.*?)-part-\d+', i[2])[0] if len(re.findall('\d+', i[2])) > 0 else i[2], 'Multi-Part ' + re.findall('\d+', i[2])[0] if len(re.findall('\d+', i[2])) > 0 else None) for i in links]

            for id, controlId, host, multiPart in links:
                valid, hoster = source_utils.is_host_valid(host, hostDict)
                if not valid: continue

                sources.append({'source': hoster, 'quality': 'SD', 'language': 'de', 'url': (url, id, controlId, 'film' in url),
                                'info': multiPart if multiPart else '', 'direct': False, 'debridonly': False, 'checkquality': False})

            return sources
        except Exception as e:
            source_faultlog.logFault(__name__, source_faultlog.tagScrape)
            return sources

    def resolve(self, url):
        try:
            if 'google' in url:
                return url
            url, id, controlId, movieSearch = url

            oRequest = cRequestHandler(url)
            content = oRequest.request()
            token = re.findall("_token':'(.*?)'", content)[0]

            link = urlparse.urljoin(self.base_link, self.link_url_movie if movieSearch else self.link_url)
            oRequest = cRequestHandler(link)
            oRequest.addHeaderEntry('X-Requested-With', 'XMLHttpRequest')
            oRequest.addParameters('_token', token)
            oRequest.addParameters('PartID', id)
            oRequest.addParameters('ControlID', controlId)
            oRequest.setRequestType(1)
            result = oRequest.request()
            if 'false' in result:
                return
            else:
                return dom_parser.parse_dom(result, 'iframe')[0].attrs['src']
        except:
            source_faultlog.logFault(__name__, source_faultlog.tagResolve)
            return

    def __search(self, titles, year, season='0'):
        
        try:
            query = self.search_link % (urllib.quote_plus(cleantitle.query(titles[0])))
            query = urlparse.urljoin(self.base_link, query)

            titles = [cleantitle.get(i) for i in set(titles) if i]

            oRequest = cRequestHandler(query)
            sHtmlContent = oRequest.request()

            url = urlparse.urljoin(self.base_link, self.search_link_query)
            token = re.findall(r"token':'(.*?)'}", sHtmlContent)[0]
            oRequest = cRequestHandler(url)
#            if sSearchText:
#                oRequest.addParameters('search', sSearchText)
#                page = '1'
#                type = 'Alle'
#                sortBy = 'latest'
            oRequest.addHeaderEntry('X-Requested-With', 'XMLHttpRequest')
            oRequest.addParameters('_token', token)
            oRequest.addParameters('from', 1900)
            oRequest.addParameters('page', '1')
            oRequest.addParameters('rating', 0)
            oRequest.addParameters('sortBy', 'latest')
            oRequest.addParameters('to', time.strftime("%Y", time.localtime()))
            oRequest.addParameters('type', 'Alle')
            oRequest.addParameters('search', titles[0])
            oRequest.setRequestType(1)
            searchResult = oRequest.request()

            results = re.findall(r'title=\\"(.*?)\\" href=\\"(.*?)" ', searchResult)
            usedIndex = 0
            #Find result with matching name and season
            for x in range(0, len(results)):
                title = cleantitle.get(results[x][0])

                if any(i in title for i in titles):
                        return source_utils.strip_domain(results[x][1].replace('\\', ''))
                usedIndex += 1

            return
        except:
            try:
                source_faultlog.logFault(__name__, source_faultlog.tagSearch, titles[0])
            except:
                return
            return
