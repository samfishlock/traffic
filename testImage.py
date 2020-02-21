import sys
from urllib import request, parse
from cvlib.object_detection import draw_bbox
import cvlib as cv
import matplotlib.pyplot as plt
import requests

if sys.argv[1] is not None:
	link = sys.argv[1]
	try:
		img_data = requests.get(link).content
	except requests.exceptions.ConnectionError:
		print("Invalid link")
		exit()
	with open('images/latest_picture.jpg', 'wb') as handler:
		handler.write(img_data)
	im = cv2.imread('images/latest_picture.jpg')
	bbox, label, conf = cv.detect_common_objects(im)

	#the three lines below produce the 'flashy' image to show you what is what
	output_image = draw_bbox(im, bbox, label, conf)
	plt.imshow(output_image)
	plt.show()
else:
	print("Blank or null argument")
	exit()	
