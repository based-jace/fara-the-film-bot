# -*- coding: utf-8 -*-
"""
Created on Fri Feb 22 05:10:09 2019

@author: footjohnson
"""

from bs4 import BeautifulSoup # For Web Scraping
from googlesearch import search
import requests, re

def scrape(search_term): # Scrapes Wikipedia
	wiki_url = wiki_search(search_term)
	if wiki_url == None: # If wikipedia page not found
		return None
	
	release_date = ''
	director = ''
	
	movie_info = [search_term] # search_term == movie title
	
	page = requests.get(wiki_url)
	soup = BeautifulSoup(page.content, "lxml")
	
	try:
		for data in soup.select("table.infobox.vevent"): # Grabs right-hand info box
			for data1 in data.select("tr"):
				for i, data2 in enumerate(data1.contents):
					if('Directed by' in data2.contents[0]): # Grabs Director
						director = data2.next_sibling.get_text()
					if('Release date' in data2.get_text()): # Grabs Release Date
						regex = re.compile('\(([^)]+)')
						release_date = regex.search(data2.next_sibling
						    .get_text().strip()).group(1)
	except Exception as e:
		pass
		
	movie_info += [director, release_date, wiki_url]
	
	return movie_info # To enter into the Google Sheet

def wiki_search(search_term): # Searches for film's wikipedia page using Google
	search_phrase = search_term + " movie wikipedia"
	
	for i in search(search_phrase, num=5, pause=5, stop=1, lang="en"):
		if "wikipedia" in i and '/list_of' not in i.lower():
			return i
	return None # Wikipedia page not found