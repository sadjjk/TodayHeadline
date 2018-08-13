# -*- coding: utf-8 -*-
# @Author: kjjdas
# @Date:   2018-08-12 21:17:16
# @Last Modified time: 2018-08-13 23:52:20


from urllib.parse import urlencode
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from multiprocessing import Pool 
from hashlib import md5
from config import *
import requests
import pymongo
import json
import re
import os 

client = pymongo.MongoClient(MONGO_URL)
db =  client[MONGO_DB]

def get_page_detail(url):
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        return None
    except RequestException:
        print('请求详情页出错', url)
        return None

def get_page_index(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cut_tab': 1,
        'from': 'search_tab'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    return get_page_detail(url).decode('gbk')


def parse_page_index(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')



def parse_page_detail(html, url):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.select('title')[0].get_text()
    print(title)
    images_pattern = re.compile(
        b'gallery: JSON.parse\((.*?)\),.*?siblingList', re.S)
    result = re.search(images_pattern, html)
    if result:
        data = json.loads(json.loads(result.group(1)))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for img in images:save_image(get_page_detail(img))
            return {
                'title': title,
                'url': url,
                'images': images
            }
def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False


def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f :
            f.write(content)
            f.close()

def main(offset):
    html = get_page_index(offset, KEYWORD)
    for url in parse_page_index(html):
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html, url)
            if result :
                save_to_mongo(result)

if __name__ == '__main__':
    groups = [x*20 for x in range(GROUP_START,GROUP_END +1)]
    pool = Pool()
    pool.map(main,groups)