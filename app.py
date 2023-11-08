#!/bin/env python3
# coding = utf-8
import requests
import json
import configparser

from rembg import remove
from flask import Flask, request, jsonify, render_template
from pygrocy import Grocy, EntityType

from spider.barcode_spider import BarCodeSpider

config = configparser.ConfigParser()
config.read('config.ini')
GROCY_URL = config.get('Grocy', 'GROCY_URL')
GROCY_PORT = config.getint('Grocy', 'GROCY_PORT')
GROCY_API = config.get('Grocy', 'GROCY_API')
GROCY_DEFAULT_QUANTITY_UNIT_ID = config.getint('Grocy', 'GROCY_DEFAULT_QUANTITY_UNIT_ID')
GROCY_DEFAULT_BEST_BEFORE_DAYS = config.get('Grocy', 'GROCY_DEFAULT_BEST_BEFORE_DAYS')
GROCY_LOCATION = {}
for key in config['GrocyLocation']:
    GROCY_LOCATION[key] = config.get('GrocyLocation', key)
X_RapidAPI_Key = config.get('RapidAPI', 'X_RapidAPI_Key')

app = Flask(__name__)
grocy = Grocy(GROCY_URL, GROCY_API, GROCY_PORT, verify_ssl = True)

def add_product(dict_good, client):
    good_name = ""
    if "description" in dict_good:
        good_name = dict_good["description"]
    elif "description_cn" in dict_good:
        good_name = dict_good["description_cn"]
    if not good_name:
        return False

    data_grocy = {
        "name": good_name,
        "description": "",
        "location_id": GROCY_LOCATION[client],
        "qu_id_purchase": GROCY_DEFAULT_QUANTITY_UNIT_ID,
        "qu_id_stock": GROCY_DEFAULT_QUANTITY_UNIT_ID,
        "default_best_before_days": GROCY_DEFAULT_BEST_BEFORE_DAYS,
        "default_consume_location_id": GROCY_LOCATION[client],
        "move_on_open": "1"
    }

    if ("gpc" in dict_good) and dict_good["gpc"]:
        best_before_days = gpc_best_before_days(int(dict_good["gpc"]))
        if best_before_days:
            data_grocy["default_best_before_days"] = best_before_days

    # add product
    response_grocy = grocy.add_generic(EntityType.PRODUCTS, data_grocy)

    # # add gds info
    grocy.set_userfields(
        EntityType.PRODUCTS,
        int(response_grocy["created_object_id"]),
        "GDSInfo",
        json.dumps(dict_good, ensure_ascii=False)
    )

    # add barcode, ex. 06921168593910
    data_barcode = {
        "product_id": int(response_grocy["created_object_id"]),
        "barcode": dict_good["gtin"]
    }
    grocy.add_generic(EntityType.PRODUCT_BARCODES, data_barcode)
    # add barcode, EAN-13, ex. 6921168593910
    if dict_good["gtin"].startswith("0"):
        data_barcode = {
            "product_id": int(response_grocy["created_object_id"]),
            "barcode": dict_good["gtin"].strip("0")
        }
        grocy.add_generic(EntityType.PRODUCT_BARCODES, data_barcode)

    # add picture
    pic_url = ""
    if ("picfilename" in dict_good) and dict_good['picfilename']:
        pic_url = dict_good["picfilename"]
    elif ("picture_filename" in dict_good) and dict_good['picture_filename']:
        pic_url = dict_good["picture_filename"]

    if pic_url:
        try:
            response_img = requests.get(pic_url,{'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"})
            if response_img.status_code == 200:
                image_data = response_img.content
                with open("img.png", 'wb') as o:
                    output_data = remove(image_data)
                    o.write(output_data)
            grocy.add_product_pic(int(response_grocy["created_object_id"]),"img.png")
        except requests.exceptions.RequestException as err:
            print("Request error:", err)

    grocy.add_product_by_barcode(dict_good["gtin"],1.0,0.0)
    return True

def gpc_best_before_days(Code):
    with open('gpc_brick_code.json') as json_file:
        gpc_data = json.load(json_file)

    best_before_days = {}
    best_before_days["7"] = [50370000, 50380000, 50350000,]
    best_before_days["14"] = [50250000, 10000025, 10006970, 10000278, 10006979, ]
    best_before_days["152"] = [50270000, 50310000,]
    best_before_days["305"] = [94000000, 50000000, 10120000, 10110000,]
    best_before_days["670"] = []
    best_before_days["1005"] = [53000000, 47100000, 47190000, 51000000, 10100000,]

    for item in gpc_data["Schema"]:
        if item["Code"] == Code:
            codes = [
                item["Code"],
                item["Code-1"],
                item["Code-2"],
                item["Code-3"]
            ]
            for day, filter_codes in best_before_days.items():
                if any(code in filter_codes for code in codes):
                    return day
                
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/add', methods=['POST'])
def add():
    data = request.json
    client = data.get("client", "")
    aimid = data.get("aimid", "")
    barcode = data.get("barcode", "")

    try:
        grocy.product_by_barcode(barcode)
        grocy.add_product_by_barcode(barcode,1.0,0.0)

        response_data = {"message": "Item added successfully"}
        return jsonify(response_data), 200
    except:
        if aimid == "]E0":
            spider = BarCodeSpider(rapid_api_url="https://barcodes1.p.rapidapi.com/", 
                                   x_rapidapi_key=X_RapidAPI_Key,
                                   x_rapidapi_host="barcodes1.p.rapidapi.com")
            good = spider.get_good(barcode)
            if add_product(good, client):
                response_data = {"message": "New item added successfully"}
                return jsonify(response_data), 200
            else:
                response_data = {"message": "Fail to add new item"}
                return jsonify(response_data), 400
        else:
            response_data = {"message": "Unsupport barcode"}
            return jsonify(response_data), 400

@app.route('/consume', methods=['POST'])
def consume():
    try:
        data = request.json
        barcode = data.get("barcode", "")
        grocy.consume_product_by_barcode(barcode)
        response_data = {"message": "Item removed successfully"}
        return jsonify(response_data), 200
    except Exception as e:
        error_message = str(e)
        response_data = {"error": error_message}
        return jsonify(response_data), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9288)
