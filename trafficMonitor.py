import cv2
import os
import requests
import threading
import time
import matplotlib.pyplot as plt
import cvlib as cv
import datetime
import json
import csv
from urllib import request, parse
from cvlib.object_detection import draw_bbox
from bs4 import BeautifulSoup

#if an alert has gone off on X camera in the past 5 tries
alertCamera = [False,False,False,False]

#the number of retries since the last time the camera set off an alert
countCamera = [0,0,0,0]


#name of each camera
cameraNames = [ "Unit 101 to Milton Road Roundabout",
		"Milton Road Roundabout to South Science Park",
		"Kings Hedges Entrance Roundabout",
		"Milton Road Roundabout"]

log = 'logs.txt'

periodLog = 'trafficLog.csv'
dirpath = os.getcwd() + '/images'

vehiclesThreshold = [6,10,10,10]

def setupCsv():
	with open(periodLog, 'w', newline='') as file:
			writer = csv.writer(file)
			writer.writerow(["Camera Name", "Period start", "Period end", "Total time in minutes", "Vehicles counted"])
		file.close()

def write_to_log(text):
	f = open(log, "a")
	f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " + text + "\n")
	f.close()	

def send_message_to_slack(text):
	print('Trying to send message to slack')
	post = {"text": "{0}".format(text)}
	try:
		json_data = json.dumps(post)
		req = request.Request("https://hooks.slack.com/services/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",
			data=json_data.encode('ascii'),
			headers={'Content-Type': 'application/json'}) 
		resp = request.urlopen(req)
	except Exception as em:
		write_to_log("Slack message failed to send, Exception: " + em)



def monitor():
	periodTotal = [0, 0, 0, 0]
	periodLength = datetime.timedelta(minutes=5)
	periodStart = datetime.datetime.now()
	baseUrl = "https://www.cambridgesciencepark.co.uk"
	threadPeriodLength =  datetime.timedelta(seconds=30)
	while True:
		print("New monitor started")
		threadPeriodStart = datetime.datetime.now()
		while True:
			i = 0
			try:	
				page = requests.get("https://www.cambridgesciencepark.co.uk/community/park-life/traffic/?cameras=1")
			except requests.exceptions.ConnectionError:
				write_to_log("Connection Failed to: " + link)
				time.sleep(5)
				#If we have exception here, break out of while loop, restart monitoring
				break
			
			soup = BeautifulSoup(page.content, 'html.parser')
			div_container = soup.find('div', class_='tfc-Cameras tfc-ContentHidden js-TrafficCamera')
			if (not div_container == None): 
				links = div_container.findAll('img')
				for link in links:
					link = str(link)
					startIndex = link.index("src=\"") + 5
					endIndex = link.index("\"/>")
					link = baseUrl + link[startIndex:endIndex]
					try:
						img_data = requests.get(link).content
					except requests.exceptions.ConnectionError:
						write_to_log("Connection Failed to: " + link + ", associated to camera at: " + cameraNames[i] +  " skipping.")
						#If we have exception here, break out of for loop. If the period has expired, write to csv, otherwise restart inner while loop (starts again from "New monitor started")
						break

					with open('images/latest_picture.jpg', 'wb') as handler:
						handler.write(img_data)
					im = cv2.imread('images/latest_picture.jpg')
					bbox, label, conf = cv.detect_common_objects(im)

					#the three lines below produce the 'flashy' image to show you what is what
					'''output_image = draw_bbox(im, bbox, label, conf)
					plt.imshow(output_image)
					plt.show()'''

					vehicles = ['car','truck','motorcycle','bus']
					vehiclesCount = 0
					for vehicle in vehicles:
						vehiclesCount += label.count(vehicle)

					write_to_log(" Camera " + cameraNames[i] + " - " + str(vehiclesCount))

					#checks if a camera has sent an alert in the past 5 attempts, if so it wont send another alert, if it's more than five attempts ago then it'll resend the alert
					if not alertCamera[i] and vehiclesCount >= vehiclesThreshold[i]:
						send_message_to_slack('ALERT: Traffic is building up at ' + cameraNames[i])
						send_message_to_slack(link)
						alertCamera[i] = True
					countCamera[i] =+ 1
					if countCamera[i] > 5:
						alertCamera[i] = False
					periodTotal[i] += vehiclesCount
					i+=1
			else:
				write_to_log("Failed to get div from website, skipping")
			
			#If the period for writing to csv has expired, write all totals to file
			if datetime.datetime.now() > (periodStart + periodLength):
				cameraIndex = 0
				while cameraIndex <= 3:
					with open(periodLog, 'a', newline='') as file:
						writer = csv.writer(file)
						writer.writerow([cameraNames[cameraIndex], str(periodStart), str(periodStart + periodLength), str(periodLength), str(periodTotal[cameraIndex])])
						periodTotal[cameraIndex] = 0
						cameraIndex += 1
						file.close()
				periodStart = datetime.datetime.now()

			#If the loop between the four cameras takes less than the thread timer, sleep until that thread timer has expired
			while datetime.datetime.now() < (threadPeriodStart + threadPeriodLength):
				time.sleep(1)

			#Reset thread timer
			threadPeriodStart = datetime.datetime.now()

if not os.path.exists(dirpath):
	os.makedirs(dirpath)

write_to_log('Traffic Monitoring started')
setupCsv()
monitor()

