#!/bin/env python3
# coding = utf-8
import requests
import logging
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO)

class BarCodeSpider:
    '''
    条形码爬虫类
    '''
    logger = logging.getLogger(__name__)

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    
    base_url = 'https://bff.gds.org.cn/gds/searching-api/ProductService/homepagestatistic'
    domestic_url = "https://bff.gds.org.cn/gds/searching-api/ProductService/ProductListByGTIN"
    domestic_url_simple = "https://bff.gds.org.cn/gds/searching-api/ProductService/ProductSimpleInfoByGTIN"
    imported_url = "https://bff.gds.org.cn/gds/searching-api/ImportProduct/GetImportProductDataForGtin"
    imported_url_blk = "https://www.barcodelookup.com/"

    @classmethod
    def get_domestic_good(cls, barcode):
        session = requests.session()
        session.headers.update({'User-Agent': cls.user_agent})
        response = session.get(cls.base_url)
        if response.status_code != 200:
            cls.logger.error(
                "error in getting base_url status_code is {}".format(
                    response.status_code))
            return None
        
        payload = {'PageSize': '30', 'PageIndex': '1', 'SearchItem': str(barcode)}
        response_domestic_url = session.get(cls.domestic_url, params=payload)
        if response_domestic_url.status_code != 200:
            cls.logger.error(
                "error in getting domestic_url status_code is {}".format(
                    response_domestic_url.status_code))
            return None

        good = json.loads(response_domestic_url.text)
        if good["Code"] != 1 or good["Data"]["Items"] == []:
            cls.logger.error("error, item no found")
            return None

        base_id = good["Data"]["Items"][0]["base_id"]
        payload = {'gtin': str(barcode), 'id': base_id}
        response_domestic_url_simple = session.get(cls.domestic_url_simple, params=payload)
        if response_domestic_url_simple.status_code != 200:
            return cls.rework_good(good["Data"]["Items"][0])

        simpleInfo = json.loads(response_domestic_url_simple.text)
        if simpleInfo["Code"] != 1:
            return cls.rework_good(good["Data"]["Items"][0])
        if simpleInfo["Data"] != "":
            good["Data"]["Items"][0]["simple_info"] = simpleInfo["Data"]
            return cls.rework_good(good["Data"]["Items"][0])
        
        return cls.rework_good(good["Data"]["Items"][0])
    
    @classmethod
    def get_imported_good(cls, barcode):
        session = requests.session()
        session.headers.update({'User-Agent': cls.user_agent})
        response = session.get(cls.base_url)
        if response.status_code != 200:
            cls.logger.error(
                "error in getting base_url status_code is {}".format(
                    response.status_code))
            return None

        payload = {'PageSize': '30', 'PageIndex': '1', 'Gtin': str(barcode), "Description": "", "AndOr": "0"}
        response_imported_url = session.get(cls.imported_url, params=payload)
        if response_imported_url.status_code != 200:
            cls.logger.error(
                "error in getting imported_url status_code is {}".format(
                    response_imported_url.status_code))
            return None
        
        good = json.loads(response_imported_url.text)
        if good["Code"] != 1 or good["Data"]["Items"] == []:
            cls.logger.error("error, item no found")
            return None
        
        if (len(good["Data"]["Items"]) == 1) and (good["Data"]["Items"][0]["description_cn"] != None):
            return cls.rework_good(good["Data"]["Items"][0])

        if (len(good["Data"]["Items"]) == 1) and (good["Data"]["Items"][0]["description_cn"] == None):
            good_blk = cls.get_imorted_good_from_blk(barcode)
            return good_blk
          
        if len(good["Data"]["Items"]) >= 2:
            for item in good["Data"]["Items"]:
                if item["realname"] == item["importer_name"]:
                    return cls.rework_good(item)
            return cls.rework_good(good["Data"]["Items"][0])

    @classmethod
    def get_imorted_good_from_blk(cls, barcode):
        good = {}

        chrome_options = Options()
        driver = webdriver.Remote(command_executor='http://chrome:4444/wd/hub',options=chrome_options)
        driver.get(cls.imported_url_blk + str(barcode))

        good["picfilename"] = cls.safe_get_element_text(driver, By.XPATH, "//div[@id='largeProductImage']/img", "src")
        good["description_cn"] = cls.safe_get_element_text(driver, By.XPATH, "//div[@id='largeProductImage']/img", "alt")
        good["specification_cn"] = ""
        product_text_elements = cls.safe_get_element_text(driver, By.XPATH, "//ul[@id='product-attributes']/li[@class='product-text']/span")
        if product_text_elements != None:
            for element in product_text_elements:
                good["specification_cn"] = good["specification_cn"] + element.text + ","

        return good

    @classmethod
    def safe_get_element_text(cls, driver, by, value, attribute=None):
        try:
            element = driver.find_element(by, value)
            if attribute:
                return element.get_attribute(attribute)
            else:
                return element.text
        except Exception as e:
            return None
        
    @classmethod
    def rework_good(cls, good):
        if "id" in good:
            del good["id"]
        if "f_id" in good:
            del good["f_id"]
        if "brandid" in good:
            del good["brandid"]
        if "base_id" in good:
            del good["base_id"]

        if good["branch_code"]:
            good["branch_code"] = good["branch_code"].strip()
        if "picture_filename" in good:
            if good["picture_filename"]:
                good["picture_filename"] = "https://oss.gds.org.cn" + good["picture_filename"]
        if "picfilename" in good:
            if good["picfilename"]:
                good["picfilename"] = "https://oss.gds.org.cn" + good["picfilename"]

        return good

    @classmethod
    def get_good(cls, barcode):
        if barcode.startswith("69") or barcode.startswith("069"):
            return cls.get_domestic_good(barcode)
        else:
            return cls.get_imported_good(barcode)
        
def main():
    #国产商品
    # good = BarCodeSpider.get_good('06917878036526')
    #进口商品
    # good = BarCodeSpider.get_good('4901201103803')
    #国际商品
    good = BarCodeSpider.get_good('3346476426843')
    
    print(good)

if __name__ == '__main__':
    main()

'''
国产商品字典
"keyword": "农夫山泉",
"branch_code": "3301    ",
"gtin": "06921168593910",
"specification": "900毫升",
"is_private": false,
"firm_name": "农夫山泉股份有限公司",
"brandcn": "农夫山泉",
"picture_filename": "https://oss.gds.org.cn/userfile/uploada/gra/1712072230/06921168593910/06921168593910.1.jpg",
"description": "农夫山泉NFC橙汁900ml",
"logout_flag": "0",
"have_ms_product": 0,
"base_create_time": "2018-07-10T10:01:31.763Z",
"branch_name": "浙江分中心",
"base_source": "Source",
"gpc": "10000201",
"gpcname": "即饮型调味饮料",
"saledate": "2017-11-30T16:00:00Z",
"saledateyear": 2017,
"base_last_updated": "2019-01-09T02:00:00Z",
"base_user_id": "源数据服务",
"code": "69211685",
"levels": null,
"levels_source": null,
"valid_date": "2023-02-16T16:00:00Z",
"logout_date": null,
"gtinstatus": 1
'''

'''
进口商品字典
"gtin": "04901201103803",
"description_cn": "UCC117速溶综合咖啡90g",
"specification_cn": "90克",
"brand_cn": "悠诗诗",
"gpc": "10000115",
"gpc_name": "速溶咖啡",
"origin_cn": "392",
"origin_name": "日本",
"codeNet": null,
"codeNetContent": null,
"suggested_retail_price": 0,
"suggested_retail_price_unit": "人民币",
"txtKeyword": null,
"picfilename": "https://oss.gds.org.cn/userfile/importcpfile/201911301903478446204015916.png",
"realname": "磨禾（厦门）进出口有限公司",
"branch_code": "3501",
"branch_name": "福建分中心",
"importer_name": "磨禾（厦门）进出口有限公司",
"certificatefilename": null,
"certificatestatus": 0,
"isprivary": 0,
"isconfidentiality": 0,
"datasource": 0
'''

'''
国际商品字典
'''