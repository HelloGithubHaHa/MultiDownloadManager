# -*- coding: utf-8 -*-

import requests
import threading
from urllib import parse
from os import path
import time
import sys

def get_filename_from_url(url):
	file_path = parse.urlparse(url).path
	file_name = path.basename(file_path)
	return file_name

def get_file_size_from_url(url):
	res = requests.head(url)
	if 'Content-Length' in res.headers:
		return int(res.headers['Content-Length'])
	return 0

def judge_support_block(url):
	headers = {'Range': 'bytes=0-1'}
	res = requests.head(url, headers=headers)
	if 'Content-Range' in res.headers:
		return True
	return False

def download_block(url, file_name, start, end, thread_id, support_block=True):
	global download_size
	while True:
		headers = {'Range': 'bytes=%d-%d' % (start, end)}
		if support_block == False:
			headers = {}
		try:
			res = requests.get(url, headers=headers, stream=True)
			with open(file_name, 'rb+') as f:
				f.seek(start)
				for chunk in res.iter_content(1024):
					if chunk:
						f.write(chunk)
						download_size[thread_id] += len(chunk)
				res.close()
			break
		except Exception:
			res.close()
			start += download_size[thread_id]
			continue

def show_progress(file_size):
	global download_size
	downloaded_size = 0
	prev_progress = 0
	while True:
		downloaded_size = 0
		for size in download_size:
			downloaded_size += size
		progress = downloaded_size / file_size
		if progress - prev_progress >= 0.001:
			prev_progress = progress
			print('\r下载进度：%.2f%%' % (prev_progress * 100), end='')
		if downloaded_size >= file_size:
			print('\r下载进度：100.00%')
			break

def download_all_block(url, file_name):
	global download_size
	while True:
		try:
			res = requests.get(url, stream=True)
			with open(file_name, 'rb+') as f:
				for chunk in res.iter_content(1024):
					if chunk:
						f.write(chunk)
						download_size += len(chunk)
				res.close()
			break
		except Exception:
			download_size = 0
			continue

def show_downloaded_block():
	global download_size
	prev_download_size = 0
	while True:
		if download_size - prev_download_size > 512:
			prev_download_size = download_size
			print('\r已下载块数：%d' % (prev_download_size), end='')

def format_file_size(file_size):
	s = '%.2f'
	if file_size < 1024:
		return (s % file_size) + 'B'
	file_size /= 1024
	if file_size < 1024:
		return (s % file_size) + 'KB'
	file_size /= 1024
	if file_size < 1024:
		return (s % file_size) + 'MB'
	file_size /= 1024
	return (s % file_size) + 'GB'

download_size = 0
tm = 0
def download_file(url, thread_num):
	global download_size
	global tm
	file_name = get_filename_from_url(url)
	if file_name == '':
		file_name = 'Unknown'

	file_size = get_file_size_from_url(url)
	if file_size > 0:
		print('文件总大小：%s' % (format_file_size(file_size)))

		with open(file_name, 'wb') as f:
			f.truncate(file_size)

		support_block = judge_support_block(url)
		if support_block:
			if thread_num > file_size:
				thread_num = file_size
			each_size = file_size // thread_num
			download_size = [0 for i in range(0, thread_num)]
			tm = time.time()
			for i in range(0, thread_num):
				start = i * each_size
				end = (start + each_size - 1) if (i != thread_num - 1) else (file_size - 1)
				thread = threading.Thread(target=download_block, args=(url, file_name, start, end, i, True))
				thread.setDaemon(True)
				thread.start()
		else:
			download_size = [0]
			tm = time.time()
			thread = threading.Thread(target=download_block, args=(url, file_name, 0, file_size - 1, 0, False))
			thread.setDaemon(True)
			thread.start()
		thread = threading.Thread(target=show_progress, args=(file_size,))
		thread.setDaemon(True)
		thread.start()
		thread.join()
	else:
		download_size = 0
		thread = threading.Thread(target=show_downloaded_block)
		thread.setDaemon(True)
		thread.start()
		tm = time.time()
		download_all_block(url, file_name)
		print('\r已下载块数：%d' % (download_size))

	print('文件下载完成')
	print('下载用时：%fs' % (time.time() - tm))

if __name__ == '__main__':
	thread_num = 8

	argc = len(sys.argv) - 1
	if argc == 1:
		url = sys.argv[1]
	elif argc == 2:
		url = sys.argv[1]
		num = int(sys.argv[2])
		if num > 0:
			thread_num = num
	else:
		print('用法：MultiDownload.py <url> <thread_num>')

	download_file(url, thread_num)