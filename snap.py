""" Stores every alteration of a provided page (url) """

import urllib3
from bs4 import BeautifulSoup

url = "https://forums.theuniversim.com/index.php?/forum/59-forums-rules-and-important-information/"

http = urllib3.PoolManager()

request = http.request('GET', url)

soup = BeautifulSoup(request.data, 'html.parser')

print(soup.prettify())

# def substring(s, n):
    # """ returns substrings of length n """
    # for start in range(0, len(s), n):
      #  yield s[start:start + n]

# print(json.loads(request.data.decode('utf-8')))

# for substr in substring(request.data, 100):
  # print(substr)