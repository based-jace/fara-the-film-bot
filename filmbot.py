# -*- coding: utf-8 -*-
"""
Created on Sat Feb 16 02:41:26 2019
@author: footjohnson

This script will run a Twitter bot that recommends films based on reaction
to past tweets' likes and re-tweets.
"""

from twython import Twython
from random import randint, seed
from oauth2client.service_account import ServiceAccountCredentials
import requests, sys, getopt, gspread, gzip, csv
import api_stuff as apis
from scrape_n_search import scrape

#----- Settings -----#
# Bot Settings #
BOT_NAME = "Fara the Film Bot" # What the bot calls itself
BOT_SCREEN_NAME = "FilmFara" # The bot's Twitter handle
BOT_MAX_LENGTH = 280 # Custom tweet char length
default_film = 'Desperate Living' # Default Initial Recommendation 
								# argument is -i for "initial"

# Bot Engagement Settings #
MOST_RECENT = 5 # Number of tweets to calculate engagement
MIN_RETWEETS = 0 # Min re-tweets of last tweet acceptable to recommend similar film
# ^ Set to 0 for Test purposes
MIN_LIKES = 0 # Min likes of last tweet acceptable to recommend similar film
# ^ Set to 0 for Test purposes

# Twitter Settings #
MAX_LENGTH = 280 # Max tweet char length

#----- API Setup -----#
# Twitter API Stuff #
tw_API_KEY = apis.tw_API_KEY
tw_API_SECRET = apis.tw_API_SECRET
tw_ACCESS_TOKEN = apis.tw_ACCESS_TOKEN
tw_ACCESS_TOKEN_SECRET = apis.tw_ACCESS_TOKEN_SECRET

# Taste Dive API Stuff #
td_QUOTA = 300 # Max number of Taste Dive Queries per hour
td_API_KEY = apis.td_API_KEY
td_API_URL = 'https://tastedive.com/api/similar?'
td_params = {'k':td_API_KEY, 'q': '', 'type': 'movie'} # Taste Dive API parameters

# Google Drive API Stuff #
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(apis.g_key, scope)
client = gspread.authorize(creds)
sheet = client.open("Past Film Bot Recommendations").sheet1 # Google Sheet

# IMDB Stuff #
IMDB_DOWNLOAD = 'https://datasets.imdbws.com/title.basics.tsv.gz'
# ^ To get new titles n stuff
IMDB_FILE = './title.basics.tsv.gz'
IMDB_FILE_UZ = './title.basics.tsv'

#----- Twitter Client -----#
tw = Twython(tw_API_KEY, tw_API_SECRET, tw_ACCESS_TOKEN, tw_ACCESS_TOKEN_SECRET)

#----- The Actual Code -----#
# Initialization #
last_rec = ''
next_rec = '' 	 	 
first = False  	     # argument is -f for "first run"
prior_tweets = [] # Bot's last 20 tweets
most_recent = '' # Bot's last tweet

if(BOT_MAX_LENGTH > MAX_LENGTH): # Don't exceed Twitter's set tweet length
	BOT_MAX_LENGTH = MAX_LENGTH

# Functions #
def first_tweet(): # Tweets intro-tweet
	tweet = ("Hi! I'm " + BOT_NAME + ". I recommend films to you once " +
	   "a day based on how much you like my past tweets.")
	print(tweet)
	tw.update_status(status=tweet)

def get_last_tweets(): # Gets the last [MOST_RECENT] tweets
	global prior_tweets
	global most_recent
	
	prior_tweets = tw.get_user_timeline(screen_name=BOT_SCREEN_NAME, count=MOST_RECENT)
	most_recent = prior_tweets[0]

def update_tweet(): # Sends next recommendation
	global first
	global most_recent
	global MIN_LIKES
	global MIN_RETWEETS
	global last_rec
	global next_rec
	
	get_last_tweets()
	
	tweet_likes = most_recent['favorite_count']
	tweet_retweets = most_recent['retweet_count']
	next_rec = '' # new film
	
	if first: # first run
		first_tweet()
		next_rec = default_film
		first = False
		tweet_body = "My first film recommendation is " + next_rec
	else:
		if last_rec == '':
			past_recs = sheet.get_all_records() # gets all rows from sheet
			num_recs = len(past_recs)
			if num_recs > 0:
				last_rec = past_recs[num_recs - 1]['Title'] # gets last recommendation
			else:
				last_rec = default_film
		if tweet_likes >= MIN_LIKES and tweet_retweets >= MIN_RETWEETS: 
			# ^ If achieves audience engagement goals
			next_rec = get_similar(last_rec)
		else:
			next_rec = get_new()
		tweet_body = ("Based on yesterday's results, today's recommendation is " + 
			 next_rec)
		
	tweet_body = tweet_body[:BOT_MAX_LENGTH]
	
	wiki_link = record_film(next_rec)[3]
	last_rec = next_rec
	
	if(wiki_link != ''):
		tweet_body += ": " + wiki_link
	
	print(tweet_body) # To console for posterity
	
	tw.update_status(status=tweet_body)

def check_in_list(film): # Checks to see if the film has already been recommended in the past
	global sheet
	movies = sheet.get_all_records() # Gets all rows from Sheet
	for movie in movies: # Each Row
		if movie['Title'].lower() == film.lower():
			print(film + " already recommended")
			return True
	return False

def get_similar(film): # Gets a similar film using Taste Dive
	global td_API_URL
	global td_params
	
	td_params['q'] = 'movie:' + film
	similar_films = requests.get(td_API_URL, params=td_params).json()['Similar']['Results']
	# ^ Grabs similar films from Taste Dive
	for i in similar_films:
		sim_film = i['Name']
		if not check_in_list(sim_film): # If not yet recommended
			return sim_film
	return get_new() # Else get a new one

# Records the film data to the Google Sheet,
# in part by scraping Wikipedia
def record_film(film): # Writes the movie info to the Google Sheet
	global sheet
	
	film_props = scrape(film)
	
	sheet.append_row(film_props)
	
	return film_props

def get_new(): # Gets a new movie from IMDB
	with open(IMDB_FILE, "wb") as file: # Downloads list of movies
		response = requests.get(IMDB_DOWNLOAD)
		file.write(response.content) 
	with open(IMDB_FILE_UZ, "wb") as to_file, gzip.open(IMDB_FILE, "rb") as from_file:
		# ^ Unzips the file to its own file
	    to_file.writelines(from_file.readlines())
	with open(IMDB_FILE_UZ, "rt", encoding="utf-8") as file:
		# ^ Reads the unzipped file
		seed() # Random
		tsv_read = csv.DictReader(file, delimiter="\t") # Reads the tsv file
		rand_film_num = randint(0, (sum(1 for line in tsv_read) - 1)) # Grabs a random number
		file.seek(rand_film_num) # Goes to that line
		found = False # If movie was found
		for i, line in enumerate(tsv_read): # finds the movie
			if i == rand_film_num:
				found = True
			if found and line["titleType"] == 'movie':
				return line["primaryTitle"]

# Logic #
try:
	opts, args = getopt.getopt(sys.argv[1:], "f:i:") # options
except getopt.GetoptError as e:
	print(str(e))
	sys.exit(2)

for o, a in opts:
	if o == '-f' and a in ["True", "False"]:
		first = a
	elif o == '-i':
		default_film = a

update_tweet()

	
	
	
	
	
	
	