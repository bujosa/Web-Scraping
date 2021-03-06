from bs4 import BeautifulSoup
import requests
import pymongo
import dns
import math
import numpy as np
from datetime import datetime
from datetime import timedelta

# Request to mercado mercado libre colombia
response = requests.get("https://carros.tucarro.com.co/directo/_FiltersAvailableSidebar?filter=MODEL")

#Page
mercadoLibre = response.text

#BeastifulSoup page parse on html
soup = BeautifulSoup(mercadoLibre, "html.parser")

# Constants variables
max_vehicle_per_page = 48
limit_car_per_brand = 1969

#Fields
fields = { "brand": "Marca", "model": "Modelo", "year":"Año", "fuelType": "Tipo de combustible", "transmission": "Transmisión", "bodyStyle": "Tipo de carrocería",  "doors":"Puertas",  "engine": "Motor",  "mileage": "Kilómetros", "color": "Color"}

#Variables
count = 0
prices = []
years = []

def convert_url(url):
    result = url.split("?")
    return result[0]

def data_sheet(soup):
    data = {}
    try: 
        columns = soup.find("tbody", class_="andes-table__body").find_all("tr")
    except: 
        return data

    for row in columns:
        key = row.find("th").text
        value = row.find("td").text
        data[key] = value
    
    return data

def days_section(soup):
    title = soup.find("span", class_="ui-pdp-subtitle")

    if title == None:
        return None

    date = title.text.split("Publicado hace ")[1]
    keys = date.split(" ")

    if keys[1] == 'días' or keys[1] == 'día' :
          return int(keys[0])
    elif keys[1] == "año" or keys[1] == 'años' :
      return int(keys[0]) * 365
    else:  
      return int(keys[0]) * 30

def get_array_of_url(url, value):
    brand_url = []
    last_part = "_Desde_"
    brand_url.append(url)
    count = value/max_vehicle_per_page

    if count < 1 or value == max_vehicle_per_page: 
        return brand_url
    else:
        count = math.floor(count)
        for x in range(count+1):
            number = str(x*max_vehicle_per_page + 1)
            last_part_tmp = url+last_part+number
            brand_url.append(last_part_tmp)
    
    return brand_url

def get_car_information(url):
    response = requests.get(url)
    vehicle_detail_page = response.text
    soup = BeautifulSoup(vehicle_detail_page, "html.parser")

    # picture_section validation
    picture_section = soup.find("img", class_="ui-pdp-image ui-pdp-gallery__figure__image")

    if picture_section == None:
        return

    # price_section validation
    price = price_section(soup)

    if price == None:
        return

    # days_section validation
    days = days_section(soup)

    if days > 10:
        return

    # title_section validation
    title = picture_section.get("alt")

    if title == None:
        return
    
    data_sheet_table = data_sheet(soup)

    vehicle = {
       "title":title, 
       "brand": key_error(data_sheet_table, "brand"),
       "model":key_error(data_sheet_table, "model"),
       "price": price,
       "currency": "COP",
       "originalMainPicture":  picture_section.get("data-zoom"),
       "mainPicture": "https://curbo-assets.nyc3.cdn.digitaloceanspaces.com/Curbo%20proximamente.svg",
       "year": key_error(data_sheet_table, "year"),
       "fuelType": key_error(data_sheet_table, "fuelType"),
       "bodyStyle": key_error(data_sheet_table, "bodyStyle"),
       "transmission": key_error(data_sheet_table, "transmission"),
       "engine": key_error(data_sheet_table, "engine"),
       "doors": key_error(data_sheet_table, "doors"),
       "mileage": key_error(data_sheet_table, "mileage"),
       "color": key_error(data_sheet_table, "color"),
       "vehicle_url": url,
       "country": "Colombia",
       "state": state_section(soup),
       "createdAt": datetime.now().isoformat(),
       "postCreatedAt":  (datetime.now() - timedelta(days=days)).isoformat(),
    }

    # vehicle brand and model validation
    if vehicle["brand"] == None or vehicle["model"] == None:
        return
    
    global count
    count += 1
    print(count)
    print(vehicle["vehicle_url"])

    global prices
    global years

    prices.append(int(vehicle["price"]))
    years.append(int(vehicle["year"]))

    VehicleDataManager().addCar(vehicle)

def get_car_url(key, value):
    brand_specific_urls = get_array_of_url(key, value)

    for specific_page in brand_specific_urls:
        response = requests.get(specific_page)
        car_page = response.text
        soup = BeautifulSoup(car_page, "html.parser")

        validator = soup.find("svg", class_="ui-search-icon ui-search-icon--not-found ui-search-rescue__icon")
        
        if validator != None:
            break

        urls = soup.find("section", class_="ui-search-results")

        if urls == None:
            break
        else:
            urls = urls.find_all("li", class_="ui-search-layout__item")

        for url in urls:
            car_url = url.find("a", class_="ui-search-result__content ui-search-link").get("href")
            get_car_information(car_url)

def get_selection_urls(soup):
    brand_href = {}
    
    brand_div = soup.find(class_="ui-search-search-modal-grid-columns")

    if brand_div == None:
        return brand_href
    else:
        brand_div = brand_div.find_all("a", class_="ui-search-search-modal-filter ui-search-link")

    for brand in brand_div:
        key = brand.get("href")
        value_tmp = brand.find("span", class_="ui-search-search-modal-filter-match-count").text
        value = int(value_tmp.replace("(","").replace(")","").replace(",",""))

        url = convert_url(key)

        if value > limit_car_per_brand:
            value = limit_car_per_brand
        brand_href[url] = value

    return brand_href

def get_seller(soup):
    try:
        seller = soup.find("h3", class_="ui-pdp-color--BLACK ui-pdp-size--LARGE ui-pdp-family--REGULAR").text
        return seller
    except:
        return ''

def get_seller_type(soup):
    try:
        sellerType = soup.find("p", class_="ui-pdp-color--GRAY ui-pdp-family--REGULAR ui-vip-profile-info__subtitle").text
        return sellerType
    except:
        return 'Particular'

def key_error(data, key):
    try:
        if key == "year" or key == "mileage":
            return int(data[fields[key]].replace(" km",""))
        else:
            return data[fields[key]]
    except:
        return None

def price_section(soup):
    price_section = soup.find("span", class_="price-tag-fraction")

    if price_section == None:
        return None

    price  = price_section.text.replace(",","")
    price = price.replace(".","")
    return int(price)

# This function is used to get the state of the car
def state_section(soup):
    try: 
        seller_info = soup.findAll("div", class_="ui-seller-info__status-info")
        for seller_info_status in seller_info:
            title = seller_info_status.find("h3", class_="ui-seller-info__status-info__title ui-vip-seller-profile__title").text
            if title == "Ubicación del vehículo":
                return seller_info_status.find("p", class_="ui-seller-info__status-info__subtitle").text.split(" - ")[1]
    except:
        return ''

#Vehicle data manager class
class VehicleDataManager():
    def __init__(self): 
            self.connection = pymongo.MongoClient("YOUR_DATA_BASE")
            db = self.connection['MercadoLibreCO']
            self.collection = db['Direct']

    def addCar(self, vehicleObject):
        self.collection.insert_one(vehicleObject)

selection_url_and_count = get_selection_urls(soup)

for key in selection_url_and_count:
    get_car_url(key, selection_url_and_count[key])
