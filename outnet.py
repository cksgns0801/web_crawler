import scrapy
import json
from cloth_crawler.items import OutnetItem
import datetime
import requests
import shutil # to save it locally
from lxml import html
# from bson.binary import Binary
import os
import boto3
from glob import glob
from tqdm import tqdm
import sys

class OutnetSpider(scrapy.Spider):
    name = 'outnet'

    start_urls = ['https://www.theoutnet.com/en-us/shop/clothing']
    
    custom_settings = {
        'RETRY_TIMES': 10,
    }

    def start_requests(self):
        start_urls = ['https://www.theoutnet.com/en-us/shop/clothing',
                    'https://www.theoutnet.com/en-us/shop/shoes',
                    'https://www.theoutnet.com/en-us/shop/bags',
                    'https://www.theoutnet.com/en-us/shop/accessories']
        for url in start_urls:
            yield scrapy.Request(
                url=url,
                headers = {'User-Agent' : 'PostmanRuntime/7.26.8'},
                meta={'category_parents':url.split('/')[-1]},
                callback=self.parse_category,
            )
    
    def parse_category(self, response):
        """
            상위 카테고리와 URL 연결 loop
        """
        tree = html.fromstring(response.text)
        category_parents = response.meta['category_parents']
        category = tree.xpath('//div[@class="AccordionSection3__contentChildWrapper"]/a/@href')
        category_link = tree.xpath('//div[@class="AccordionSection3__contentChildWrapper"]/a/span/text()')


        category_list = [['https://www.theoutnet.com'+category[i],category_link[i]] for i in range(len(category_link))]
        
        for item in category_list:
        # item=[0,1]
            if item[1]!='All': # 모두보기 탭이 하나 더 있어서 제거함
                url = item[0] # (카테고리, url)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_item, 
                    headers = {'User-Agent' : 'PostmanRuntime/7.26.8'},
                    meta={'category_parents':category_parents, 'category_child':item[1]}
                )
        
    def parse_item(self, response):
        """
            상품 이미지들의 각 url로의 parsing
        """
        category_parents = response.meta['category_parents']
        category_child = response.meta['category_child']
        tree = html.fromstring(response.text)

        # 상품 list 표 grid 요소 전체 리스트로 가져오기
        item = tree.xpath('//div[@class="ProductGrid52 ProductListWithLoadMore52__listingGrid"]/a/@href')

        for r in item:
            yield scrapy.Request(url=r,
                    callback=self.parse, 
                    headers = {'User-Agent' : 'PostmanRuntime/7.26.8'},
                    meta={'category_parents': category_parents,'category_child': category_child, "url":r}
            )

        '''if has_page != []: # 의류에 대한 다음 페이지 가 있을 때
            yield scrapy.Request(
                url=head+has_page[0],
                callback=self.parse_item, 
                meta={'category_parents':  category_parents,'category_child': category_child, 'url':head+has_page[0]}
            )'''


    def parse(self, response):
        """
            [모든 사이트] 제품 상세페이지에서 데이터 이미지, 브랜드, 가격, 사이즈 등을 parsing
        """
        tree = html.fromstring(response.text)
        title = response.url

        with open('./html' + title, 'w') as html_file:
            html_file.write(response.text)

        BUCKET_NAME = 'sm-html-crawler'
        REGION_NAME = 'ap-northeast-2'
        
        s3 = boto3.client('s3', 
            aws_access_key_id='**', 
            aws_secret_access_key='**', 
            region_name=REGION_NAME
        )
        

        s3.upload_file('./html' + title, BUCKET_NAME, 'outnet/'+title)