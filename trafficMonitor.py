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

dirpath = os.getcwd() + '/images'

vehiclesThreshold = [6,10,10,10]

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
		print("EXCEPTION: " + str(em))

def monitor():
	periodLog = 'trafficLog.csv'
	periodTotal = 0
	periodLength = datetime.timedelta(minutes=30)
	periodStart = datetime.datetime.now()
	with open(periodLog, 'w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(["Period start", "Period end", "Vehicles counted"])
		print("Beginning of time ;-)")
		while True:
			i = 0
			baseUrl = "https://www.cambridgesciencepark.co.uk"
			page = requests.get("https://www.cambridgesciencepark.co.uk/community/park-life/traffic/?cameras=1")
			soup = BeautifulSoup(page.content, 'html.parser')
			div_container = soup.find('div', class_='tfc-Cameras tfc-ContentHidden js-TrafficCamera')
			links = div_container.findAll('img')
			for link in links:
				link = str(link)
				startIndex = link.index("src=\"") + 5
				endIndex = link.index("\"/>")
				link = baseUrl + link[startIndex:endIndex]
				try:
					img_data = requests.get(link).content
				except requests.exceptions.ConnectionError:
					f = open(log, "a")
					f.write(currentDT.strftime("%Y-%m-%d %H:%M:%S") +' Connection Failed to: ' + link + ', associated to camera at: ' + cameraNames[i] +  ' skipping.\n')
					time.sleep(5)
					break

				with open('images/latest_picture.jpg', 'wb') as handler:
					handler.write(img_data)
				im = cv2.imread('images/latest_picture.jpg')
				bbox, label, conf = cv.detect_common_objects(im)
				#the three lines below produce the 'flashy' image to show you what is what
				#output_image = draw_bbox(im, bbox, label, conf)
				#plt.imshow(output_image)
				#plt.show()
				vehicles = ['car','truck','motorcycle','bus']
				vehiclesCount = 0
				for vehicle in vehicles:
					vehiclesCount += label.count(vehicle)

				currentDT = datetime.datetime.now()
				f = open(log, "a")
				f.write(currentDT.strftime("%Y-%m-%d %H:%M:%S") +' Camera ' + cameraNames[i] + ' - ' + str(vehiclesCount) + '\n')
				f.close()
				#checks if a camera has sent an alert in the past 5 attempts, if so it wont send another alert, if it's more than five attempts ago then it'll resend the alert
				if not alertCamera[i] and vehiclesCount >= vehiclesThreshold[i]:
					send_message_to_slack('ALERT: Traffic is building up at ' + cameraNames[i])
					send_message_to_slack(link)
					alertCamera[i] = True
				countCamera[i] =+ 1
				if countCamera[i] > 5:
					alertCamera[i] = False
				i+=1

				periodTotal += vehiclesCount

			if datetime.datetime.now() < periodStart + periodLength:
				writer.writerow([str(periodStart), str(periodStart + periodLength), str(periodTotal)])
				periodTotal = 0
				periodStart = datetime.datetime.now()


send_message_to_slack('Traffic Monitoring started')

if not os.path.exists(dirpath):
	os.makedirs(dirpath)

monitor()

