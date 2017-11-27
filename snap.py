""" Stores every alteration of a provided page (url) """

import urllib3
from bs4 import BeautifulSoup
http = urllib3.PoolManager()

base_url = "http://deutschpatrioten.de/"

request = http.request('GET', base_url)

soup = BeautifulSoup(request.data, 'html.parser')

# alle topics beginnen mit id = "boardLinkxy"
anchors = soup.find_all('a')
links = []
for a in anchors:
    id = a.get('id')
    try:
        if id.startswith("boardLink"):
            links.append(a.get('href'))
    except AttributeError:
        next

print(links)



# print(soup.find('base'))

# print(soup.prettify())

# def substring(s, n):
    # """ returns substrings of length n """
    # for start in range(0, len(s), n):
      #  yield s[start:start + n]

# print(json.loads(request.data.decode('utf-8')))

# for substr in substring(request.data, 100):
  # print(substr)