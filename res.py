import requests
import datetime
import time
import csv
import sys
import random

headers = {
	 'origin': 'https://resy.com',
	 'accept-encoding': 'gzip, deflate, br',
	 'x-origin': 'https://resy.com',
	 'accept-language': 'en-US,en;q=0.9',
	 'authorization': 'ResyAPI api_key="VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5"',
	 'content-type': 'application/x-www-form-urlencoded',
	 'accept': 'application/json, text/plain, */*',
	 'referer': 'https://resy.com/',
	 'authority': 'api.resy.com',
	 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
}

def login(username,password):
	data = {
	  'email': username,
	  'password': password
	}

	response = requests.post('https://api.resy.com/3/auth/password', headers=headers, data=data)
	res_data = response.json()
	if (res_data['em_address'] == username):
		print "Logged in."
	else:
		print "Login failed. Exiting"
		quit()
	auth_token = res_data['token']
	payment_method_string = '{"id":' + str(res_data['payment_method_id']) + '}'
	return auth_token,payment_method_string

def find_table(res_date,party_size,table_time,auth_token,venue_id):
	#convert datetime to string
	day = res_date.strftime('%Y-%m-%d')
	params = (
	 ('x-resy-auth-token',  auth_token),
	 ('day', day),
	 ('lat', '0'),
	 ('long', '0'),
	 ('party_size', str(party_size)),
	 ('venue_id',str(venue_id)),
	)
	response = requests.get('https://api.resy.com/4/find', headers=headers, params=params)
	data = response.json()
	results = data['results']
	if len(results['venues']) > 0:
		open_slots = results['venues'][0]['slots']
		if len(open_slots) > 0:
			available_times = [(k['date']['start'],datetime.datetime.strptime(k['date']['start'],"%Y-%m-%d %H:%M:00").hour) for k in open_slots]
			closest_time = min(available_times, key=lambda x:abs(x[1]-table_time))[0]

			best_table = [k for k in open_slots if k['date']['start'] == closest_time][0]

			return best_table
		else:
			print "No open slots found."
	else:
		print "No matching venue found. Check venue ID."
		quit()

def make_reservation(auth_token,payment_method_string,config_id,res_date,party_size):
	print "Making the reservation now!"
	#convert datetime to string
	day = res_date.strftime('%Y-%m-%d')
	party_size = str(party_size)
	params = (
		 ('x-resy-auth-token', auth_token),
		 ('config_id', str(config_id)),
		 ('day', day),
		 ('party_size', str(party_size)),
	)
	details_request = requests.get('https://api.resy.com/3/details', headers=headers, params=params)
	details = details_request.json()
	book_token = details['book_token']['value']
	headers['x-resy-auth-token'] = auth_token
	data = {
	  'book_token': book_token,
	  'struct_payment_method': payment_method_string,
	  'source_id': 'resy.com-venue-details'
	}
	response = requests.post('https://api.resy.com/3/book', headers=headers, data=data)
	print response.json()
	resID = response.json()["specs"]["reservation_id"]
	if resID > 0:
		print "Successfully got reservation ID " + str(resID)
	else:
		print "Looks like reservation failed. Bailing out."
		quit()

def try_table(date,party_size,table_time,auth_token,payment_method_string,restaurant):
	day = datetime.datetime.strptime(date,'%m/%d/%Y')
	print "Searching for a table on " +date+ "..."
	
	best_table = find_table(day,party_size,table_time,auth_token,restaurant)
	#print best_table
	if best_table is not None:
		hour = datetime.datetime.strptime(best_table['date']['start'],"%Y-%m-%d %H:%M:00").hour
		print "Found a table at hour " + str(hour)
		if (hour >= 18) and (hour <= 20):
			config_id = best_table['config']['token']
			make_reservation(auth_token,payment_method_string,config_id,day,party_size)
			return 1
		else:
			print "That's not in the ideal range. We'll try again."
			return 0
	else:
		#print "Nothing found."
		return 0

def sleepRandom():
	sleepSeconds = 60*60 - 15*60 + random.randrange(30*60)
	print "Sleeping for " + str(sleepSeconds) + " seconds..."
	time.sleep(sleepSeconds)

def readconfig():
	dat = open('requests.config').read().split('\r\n')
	return [k.split(':')[1] for k in dat]


def main():
	username, password, venue, dates, guests = readconfig()
	auth_token,payment_method_string = login(username,password)
	party_size = int(guests)
	table_time = 19
	restaurant = int(venue)

	reserved = 0
	while reserved == 0:
		try:
			for date in dates.split(','):
				if reserved == 0:
					reserved = try_table(date,party_size,table_time,auth_token,payment_method_string,restaurant)
			if reserved == 0:
				sleepRandom()
		except Exception, e:
			print("Unexpected error:", str(e))
			with open('failures.csv','ab') as outf:
				writer = csv.writer(outf)
				writer.writerow([time.time()])

main()
