import urllib.request
import urllib.parse
import threading
import argparse
import re
import os
import time

class DownloadThread(threading.Thread):
	def __init__(self, download_item, url, start, end, thread_id):
		threading.Thread.__init__(self)
		self.__download_item = download_item
		self.__url = url
		self.__start = start
		self.__end = end
		self.__thread_id = thread_id

	def run(self):
		while True:
			headers = {
				'Range': 'bytes={0}-{1}'.format(self.__start, self.__end),
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
			}
			try:
				req = urllib.request.Request(self.__url, headers=headers, method='GET')
				res = urllib.request.urlopen(req)
				with open(self.__download_item.get_fullname(), 'rb+') as f:
					f.seek(self.__start)
					while True:
						chunk = res.read(1024)
						if chunk:
							f.write(chunk)
							self.__download_item.downloaded_size_list[self.__thread_id] += len(chunk)
						else:
							if self.__download_item.downloaded_size_list[self.__thread_id] >= (self.__end - self.__start + 1):
								break
					res.close()
				break
			except:
				if res:
					res.close()
				self.__start += self.__download_item.downloaded_size_list[self.__thread_id]
				continue

class DownloadAllThread(threading.Thread):
	def __init__(self, download_item, url):
		threading.Thread.__init__(self)
		self.__download_item = download_item
		self.__url = url

	def run(self):
		while True:
			headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
			}
			try:
				req = urllib.request.Request(self.__url, headers=headers, method='GET')
				res = urllib.request.urlopen(req)
				with open(self.__download_item.get_fullname(), 'w') as f:
					empty_time = 0
					while True:
						chunk = res.read(1024)
						if chunk:
							f.write(chunk)
							self.__download_item.downloaded_size_list[0] += len(chunk)
						else:
							empty_time += 1
							if empty_time > 8:
								break
					res.close()

					print()
					print('下载完成')
				break
			except:
				if res:
					res.close()
				continue

class DownloadItem:
	filename_pattern = re.compile('filename\\s*=\\s*([\'\"]?)([^\\s\'\";]+)\1', re.I)
	@staticmethod
	def get_headers_and_url(url, headers={}):
		req = urllib.request.Request(url, headers=headers, method='HEAD')
		res = urllib.request.urlopen(req)
		res_headers = dict(res.getheaders())
		res_url = res.geturl()
		res.close()
		return res_headers, res_url

	def __init__(self, url, filename='',  filepath='.', thread_num=8):
		self.__url = url
		self.__filename = filename
		self.__filepath = filepath
		self.__thread_num = thread_num
		self.__downloaded_size = 0
		self.__prepare()

	def __get_filename(self, headers):
		if self.__filename == '':
			if 'Content-disposition' in headers:
				disposition = headers['Content-disposition']
				match_obj = DownloadItem.filename_pattern.search(disposition)
				self.__filename == match_obj.group(2) if match_obj else ''
		if self.__filename == '':
			filename = os.path.basename(urllib.parse.urlparse(self.__url).path)
			self.__filename = filename if (filename != '') else 'Unknown'

	def __is_support_block(self):
		headers = {'Range': 'bytes=0-1'}
		res_headers = DownloadItem.get_headers_and_url(self.__file_location, headers)[0]
		return ('Content-Range' in res_headers)

	def __prepare(self):
		headers, file_location = DownloadItem.get_headers_and_url(self.__url)
		self.__file_location = file_location
		self.__filesize = int(headers['Content-Length']) if ('Content-Length' in headers) else 0
		self.__get_filename(headers)
		self.__support_block = self.__is_support_block()
		if not self.__support_block:
			self.__thread_num = 1
		self.downloaded_size_list = [0 for i in range(0, self.__thread_num)]

		self.__fullname = os.path.join(self.__filepath, self.__filename)

	def get_format_filesize_str(self, size=None):
		filesize, filesize_unit = self.get_format_filesize(size)
		return filesize + filesize_unit

	def refresh(self):
		initial_time = time.monotonic()
		if self.__support_block:
			while True:
				cur_time = time.monotonic()
				used_time = cur_time - initial_time
				used_time_str = '{0:.2f}'.format(used_time) + 's'

				while used_time == 0:
					used_time = time.monotonic()

				filesize_str = self.get_format_filesize_str(self.__filesize)

				download_size = 0
				for size in self.downloaded_size_list:
					download_size += size
				download_size_format_str = self.get_format_filesize_str(download_size)

				download_rate_avg = download_size / used_time
				download_rate_avg_str = self.get_format_filesize_str(download_rate_avg) + '/s'

				download_rate = (download_size - self.downloaded_size) / 1
				self.downloaded_size = download_size
				download_rate_str = self.get_format_filesize_str(download_rate) + '/s'

				if download_rate != 0:
					rest_filesize = self.__filesize - download_size
					rest_time = rest_filesize / download_rate
					rest_time_str = '{0:.2f}'.format(rest_time) + 's'
				else:
					rest_time_str = '未知'

				print('\r' + '文件总大小:', filesize_str, '已下载大小:', download_size_format_str, '下载用时:', used_time_str, '剩余时间:', rest_time_str, '平均下载速度:', download_rate_avg_str, '当前下载速度:', download_rate_str, end='')

				if download_size == self.__filesize:
					print()
					print('下载完成')
					return

				time.sleep(1)
		else:
			while True:
				cur_time = time.monotonic()
				used_time = cur_time - initial_time
				used_time_str = '{0:.2f}'.format(used_time) + 's'

				while used_time == 0:
					used_time = time.monotonic()

				download_size = self.downloaded_size_list[0]
				download_size_format_str = self.get_format_filesize_str(download_size)

				download_rate_avg = download_size / used_time
				download_rate_avg_str = self.get_format_filesize_str(download_rate_avg) + '/s'

				download_rate = (download_size - self.downloaded_size) / 1
				self.downloaded_size = download_size
				download_rate_str = self.get_format_filesize_str(download_rate) + '/s'

				print('\r' + '已下载大小:', download_size_format_str, '下载用时:', used_time_str, '平均下载速度:', download_rate_avg_str, '当前下载速度:', download_rate_str, end='')

				time.sleep(1)

	def start(self):
		if self.__support_block:
			with open(self.__fullname, 'wb') as f:
				f.truncate(self.__filesize)

			self.__thread_list = []
			each_size = self.__filesize // self.__thread_num
			for i in range(0, self.__thread_num):
				start = i * each_size
				end = (start + each_size - 1) if (i != self.__thread_num - 1) else (self.__filesize - 1)
				thread = DownloadThread(self, self.__file_location, start, end, i)
				thread.setDaemon(True)
				thread.start()
				self.__thread_list.append(thread)

			thread = threading.Thread(target=self.refresh)
			thread.setDaemon(True)
			thread.start()

			thread.join()
		else:
			thread = DownloadAllThread(self, self.__file_location)
			thread.setDaemon(True)
			thread.start()

			thread2 = threading.Thread(target=self.refresh)
			thread2.setDaemon(True)
			thread2.start()

			thread.join()

	def get_filesize(self):
		return self.__filesize

	def get_format_filesize(self, size=None):
		if size == None:
			size = self.__filesize
		units = ('B', 'KB', 'MB', 'GB')
		for unit in units:
			if size < 1024:
				return ('{0:.2f}'.format(size), unit)
			size /= 1024
		return ('{0:.2f}'.format(size), 'TB')

	def get_filename(self):
		return self.__filename

	def get_fullname(self):
		return self.__fullname

	def get_file_location(self):
		return self.__file_location

	def is_support_block(self):
		return self.__support_block

	@property
	def downloaded_size(self):
		return self.__downloaded_size
	@downloaded_size.setter
	def downloaded_size(self, value):
		self.__downloaded_size = value

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--thread', default=8, type=int, help='线程数')
	parser.add_argument('url', type=str, help='URL')
	args = parser.parse_args()
	item = DownloadItem(args.url, )
	item.start()