from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException
from urllib.parse import urlparse
from time import sleep
import requests as re
import pyautogui
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import json
import os
import sys
import time
import boto3
from botocore.exceptions import NoCredentialsError

def get_start_end_date():
	today = datetime.now()
	current_week_start = today - timedelta(days=today.weekday())
	current_week_monday = datetime.strftime(current_week_start, "%Y-%m-%d")
	today = datetime.strftime(today, "%Y-%m-%d")
	return current_week_monday, today

def get_chrome_options():
	options = Options()
	options.add_argument('--headless')
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	options.add_argument('--log-level=3') #Disable Log
	options.add_argument("--disable-infobars") #Disable anoying info
	script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
	options.add_experimental_option('prefs', {
		'download.default_directory': script_directory+'\\Downloads',  # Change this path to your desired download directory
		'download.prompt_for_download': False,
		'plugins.always_open_pdf_externally': True,
		'download.directory_upgrade': True,
		"plugins.plugins_disabled": ["Chrome PDF Viewer"],
	})
	return options
	
def get_data_from_json_file():
	scrapper_helper_file = open('scrapper_helper.json')
	scrapper_helper_data = json.load(scrapper_helper_file)
	scrapper_helper_file.close()
	return scrapper_helper_data

def save_data_to_json_file(start, end, new_start, new_end):
	json_data_save = dict()
	json_data_save['start_date'] = start
	json_data_save['end_date'] = end
	json_data_save['start_page'] = new_start
	json_data_save['end_page'] = new_end
	json_object = json.dumps(json_data_save)
	f = open('scrapper_helper.json', 'w')
	f.write(json_object)
	f.close()

def move_downloaded_file():
	download_dir = os.path.dirname(os.path.abspath(sys.argv[0])) + '\\Downloads'
	downloaded_files = os.listdir(download_dir)
	latest_file = max(downloaded_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
	
	aws_access_key_id = "AKIA2JDKJ25KWSIOA6OB"
	aws_secret_access_key = "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"
	s3_bucket_name = "pdfcrashbucket"
	s3_object_key = "inbox/scanned/Dublin--25-"+str(round(time.time()*1000))+latest_file
	local_file_path = download_dir+"\\"+latest_file
	
	s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
	
	try:
		s3.upload_file(local_file_path, s3_bucket_name, s3_object_key)
		print(f'Successfully uploaded {local_file_path} to {s3_bucket_name}/{s3_object_key}')
	except FileNotFoundError:
		print(f'The file {local_file_path} was not found.')
	except NoCredentialsError:
		print('AWS credentials were not found or are invalid.')
	except Exception as e:
		print(f'An error occurred: {str(e)}')
	print(latest_file)
	
def scrap():
	options = get_chrome_options()
	try:
		driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
	except Exception as e:
		print("Error while installing the chrome webdriver!!")
		print(e)
		exit()
		
	driver.get("https://weblink.dublin.oh.us/WebLinkPublic/CustomSearch.aspx?SearchName=WeeklyCrashReport&repo=Dublin-Images&cr=1")

	try:
		driver.find_elements(By.XPATH, "//a[text()='Sign Out']")[0].click()
	except Exception as e:
		print("Error in Finding Sign Out Button!!")
		print(e)
		driver.quit()
		exit()
		
	try:
		driver.find_element(By.CLASS_NAME, 'LoginButton').click()
	except Exception as e:
		print("Error in finding Login Button!!")
		print(e)
		driver.quit()
		exit()
		
	try:
		driver.find_elements(By.XPATH, "//a[text()='Weekly Crash Report']")[0].click()
	except Exception as e:
		print("Error in finding Report Link!!")
		print(e)
		driver.quit()
		exit()

	start, end = get_start_end_date()

	try:
		# start = '2023-09-04'
		driver.find_element(By.ID, 'WeeklyCrashReport_Input0_DateBox').send_keys(start)
	except Exception as e:
		print("Error in finding Start Date Input Field!!")
		print(e)
		driver.quit()
		exit()
	sleep(2)

	try:
		# end = '2023-09-08'
		driver.find_element(By.ID, 'WeeklyCrashReport_Input0_end_DateBox').send_keys(end) 
	except Exception as e:
		print("Error in finding End Date Input Field!!")
		print(e)
		driver.quit()
		exit()
	sleep(2)

	try:
		driver.find_element(By.CLASS_NAME, 'CustomSearchSubmitButton').click()
	except Exception as e:
		print("Error in finding Search Button!!")
		print(e)
		driver.quit()
		exit()
	sleep(5)

	no_pages = []

	# try:
		# no_pages = driver.find_elements(By.XPATH, '//span[text()="This document contains no pages."]')
		# print("No Pages Found!!")
	# except:
		# print("Pages Found!!")
		# print(e)

	if len(no_pages) < 1:
		json_data = get_data_from_json_file()
		try:
			driver.find_element(By.CLASS_NAME, 'print').click()
		except Exception as e:
			print("Error in finding Print Button!!")
			print(e)
			driver.quit()
			exit()
		sleep(5)

		try:
			input_box = driver.find_element(By.XPATH, '//*[@id="docPage"]/ngb-modal-window/div/div/pages-to-print/div[2]/div/div/table/tbody/tr/td[2]/input')
			default_value = input_box.get_attribute('value')
			print(default_value)
			
			start_default, end_default = map(int, map(str.strip, default_value.split("-")))
			
			input_box.clear()
			
			if (json_data.get('start_date') == start) and (int(json_data.get('end_page')) >= end_default):
				print("No new data found!!")
				save_data_to_json_file(start, end, json_data.get('start_page'), json_data.get('end_page'))
				driver.quit()
				exit()
			elif json_data.get('start_date') != start:
				new_start = '1'
			else:
				new_start = str(json_data.get('end_page'))
			new_end = str(end_default)
			
			input_box.send_keys('{}-{}'.format(new_start, new_end))
			# input_box.send_keys('1-129')
			print(input_box.get_attribute('value'))
		except Exception as e:
			print("Error in finding Page Number Input Box!!")
			print(e)
			driver.quit()
			exit()

		try:
			driver.find_elements(By.XPATH, "//button[text()='Download & Print']")[0].click()
		except Exception as e:
			print("Error in finding Download Button!!")
			print(e)
			driver.quit()
			exit()
		sleep(120)
		driver.quit()
		save_data_to_json_file(start, end, new_start, new_end)
		move_downloaded_file()
	else:
		driver.quit()
		exit()
		
scrap()