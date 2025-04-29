import os
import logging
import time
import re

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Get environment variables
chrome_path = os.getenv('chrome')

service = Service(chrome_path + "/chromedriver.exe")
options = webdriver.ChromeOptions()
options.binary_location = chrome_path + "/chrome.exe"
options.page_load_strategy = 'none'
caps = DesiredCapabilities.CHROME
# as per latest docs
# caps['goog:loggingPrefs'] = {'performance': 'ALL'}
caps = DesiredCapabilities().CHROME
caps["pageLoadStrategy"] = "none"  # Do not wait for the full page load

IDENTIFICATION_FILE = "identification.txt"
INPUT_FILE = "input.txt"
OUTPUT_FILE = "output.txt"
ERROR_FILE = "error.txt"

SEARCH_URL = "https://www.serversupply.com/products/part_search/query_parts.asp?q="
TIMEOUT_SECONDS = 30

web_driver = None

class Request:

    def __init__(self, req_string:str):
        if req_string is not None and req_string.strip() != "":    
            # Strike ID	SKU	Brand	MPN	Model	UPC	Asin    MyPrice
            # Strike ID	SKU	Model Number	Title	Product URL	Image URL	UPC	Manufacturer	MPN	Category	ASIN	Price	Shipping	weight	dimensions	Lip

            req_splits = req_string.strip().split('\t')
            self.strike_id = req_splits[0]
            self.sku = req_splits[1]
            self.model = req_splits[2]
            self.title = req_splits[3]
            self.product_url = req_splits[4]
            self.image_url = req_splits[5]
            self.upc = req_splits[6]
            self.brand = req_splits[7]
            self.mpn = req_splits[8]
            self.category = req_splits[9]
            self.asin = req_splits[10]
            self.price = req_splits[11]
            self.shipping = req_splits[12]
            self.weight = req_splits[13]
            self.dimesion = req_splits[14]
            self.lip = req_splits[15]
            self.input_string = req_string.strip()

class Product:
    def __init__(self, price:str="na", condition:str="na", availability:str="na") -> None:
        self.price = price
        self.condition = condition
        self.availability = availability

def log_and_console_info(message: str):
    print(f'INFO : {message}')
    logging.info(f'INFO : {message}')


def log_and_console_error(message: str):
    print(f'ERROR : {message}')
    logging.error(f'ERROR : {message}')


def print_data_count():
    input_count = output_count = error_count = 0
    with open(INPUT_FILE, 'r', encoding='utf8', errors='replace') as input_file:
        input_count = len(input_file.readlines())

    if(os.path.exists(OUTPUT_FILE)):
        with open(OUTPUT_FILE, 'r', encoding='utf8', errors='replace') as output_file:
            output_count = len(output_file.readlines())
            output_count = output_count - 1  # Excluding the titles

    if(os.path.exists(ERROR_FILE)):
        with open(ERROR_FILE, 'r', encoding='utf8', errors='replace') as error_file:
            error_count = len(error_file.readlines())

    log_and_console_info("\n")
    log_and_console_info("########################################")
    log_and_console_info(f"##### Total Input is         : {input_count}")
    log_and_console_info(f"##### Total Output is        : {output_count}")
    log_and_console_info(f"##### Total Error is         : {error_count}")
    log_and_console_info("########################################")


def initiate_web_driver():
    global web_driver

    quit_web_driver()

    log_and_console_info("Getting Web Driver started!")
    web_driver = webdriver.Chrome(desired_capabilities=caps, service=service, options=options)
    web_driver.maximize_window()
    # web_driver.implicitly_wait(10)


def quit_web_driver():
    global web_driver
    if web_driver != None:
        log_and_console_info("Quiting Web Driver before starting!")
        web_driver.quit()
        web_driver = None


def write_into_error_file(input_string: str):
    log_and_console_error("Writing into the error file!")

    error_file = open(ERROR_FILE, "a")
    error_file.write(input_string)
    error_file.write("\n")
    error_file.close()


# def update_identification_file(prod_id: str):
#     identification_file = open(IDENTIFICATION_FILE, "a")
#     identification_file.write(prod_id + "\t" + str(datetime.now()) + "\n")
#     identification_file.close()


# def get_identification_value():
#     log_and_console_info(f"Opening identification file {IDENTIFICATION_FILE}")
#     indent_ids = []
#     idents = []
#     last_id = 'none'
#     if(os.path.exists(IDENTIFICATION_FILE)):
#         with open(IDENTIFICATION_FILE, 'r') as f:
#             idents = f.readlines()
#         if(len(idents)):
#             for ident in idents:
#                 indent_ids.append(ident.split('\t')[0])

#             last_id = indent_ids[-1]
#     return last_id

def update_identification_file(prod_id: str):
    with open(IDENTIFICATION_FILE, "a", encoding='utf8', errors='ignore') as identification_file:
        identification_file.write(f"{prod_id}\t{datetime.now()}\n")

def get_identification_value() -> str:
    log_and_console_info(f"Opening identification file {IDENTIFICATION_FILE}")
    if os.path.exists(IDENTIFICATION_FILE):
        with open(IDENTIFICATION_FILE, 'r', encoding='utf8', errors='ignore') as f:
            lines = f.readlines()
            if lines:
                return lines[-1].split('\t')[0]
    return 'none'


def create_output_file():
    if(not os.path.exists(OUTPUT_FILE)):
        output_file = open(OUTPUT_FILE, "a")
        # Add the headers in the output file
        output_file.write("Strike ID\tSKU\tBrand\tMPN\tModel\tUPC\tAsin\tMy Price\tStatus")
        for i in range(1, 11):
            output_file.write(f"\tPrice {i}\tCondition {i}\tAvailability {i}")
        output_file.write("\n")
        output_file.close()


def open_inputs_from_file(filename: str):
    log_and_console_info(f"Opening input file {filename}")
    inputs = []
    with open(filename, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if line.strip() not in [None, '']:
            inputs.append(Request(line))
    return inputs

def get_product_details(req:Request, prod_url: str):
    product = None
    condition = availability = "na"
    try:
        log_and_console_info(f"Calling product url - {prod_url}")
        web_driver.get(prod_url)
        # time.sleep(30)
        try:
            wrapper = WebDriverWait(web_driver, TIMEOUT_SECONDS).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span.skumodel'))
                )
        except TimeoutException:
            log_and_console_error("Timeout exception occurred in details page.")
        sku_elements = web_driver.find_elements(By.CSS_SELECTOR, 'span.skumodel')
        sku = ""
        for skumodel in sku_elements:
            if skumodel.text.lower().__contains__("part number"):
                sku = skumodel.text.split(":")[-1].strip()
                break

        modified_sku = re.sub('[^a-zA-Z0-9]', '', sku).upper().lstrip("0")
        modified_req_sku = re.sub('[^a-zA-Z0-9]', '', req.sku).upper().lstrip("0")

        if modified_sku == modified_req_sku:

            ## Getting edtails from the right corner
            # price = web_driver.find_element(By.CSS_SELECTOR, 'span.pricebig.protected').text.replace("$","").replace(",","")
            # table_rows = web_driver.find_elements(By.CSS_SELECTOR,'section.section-content > div.container > div.row > div > div.card > table > tbody > tr')
            # for tr in table_rows:
            #     tds = tr.find_elements(By.CSS_SELECTOR, 'td')
            #     if len(tds) == 2:
            #         if tds[1].text.lower().__contains__("condition"):
            #             condition = tds[1].text.split(":")[-1].strip()
            #         elif tds[1].text.lower().__contains__("availability"):
            #             availability = tds[1].text.split(":")[-1].strip()

            #     if condition != "na" and availability != "na":
            #         break
            # product = Product(price=price, condition=condition, availability=availability)
            li_elements = web_driver.find_elements(By.CSS_SELECTOR, 'div.card-body.detail_overviewd > li')
            spec_elements = []
            if len(li_elements):                
                spec_elements = li_elements
            else:
                spec_elements = web_driver.find_elements(By.CSS_SELECTOR, 'div.card-body.detail_overviewd > p')
        
            price = web_driver.find_element(By.CSS_SELECTOR, 'span.pricebig.protected').text.replace("$","").replace(",","")
            
            for spec in spec_elements:
                spec_text = spec.text
                # log_and_console_info(b_text)
                if spec_text.lower().__contains__("condition"):                
                    for spec in spec_text.split("\n"):
                        if spec != "" and spec.__contains__(":"):
                            k,v = spec.split(":")
                            if k.lower().strip() == "condition":
                                condition = v.strip().replace(".","")
                            if k.lower().strip() == "availability":
                                availability = v.strip().replace(".","")
                    
                    product = Product(price=price, condition=condition, availability=availability)
                    break
            log_and_console_info(f"Product details [price={price}, condition={condition}, availability={availability}]")
        else:
            log_and_console_info(f"MPN mismatch [expected={sku}, found={req.sku}]")           
            

    except Exception as ex:
        log_and_console_error(f"Exception occurred while getting the details of the product. {prod_url}")
        logging.error(ex, exc_info=True)
    return product

def scrape_product(request : Request):
    product_list = []
    try:
        search_url = SEARCH_URL + request.mpn.strip()
        log_and_console_info(f"Search URL is {search_url}")
        web_driver.get(search_url)
        time.sleep(1)
        if web_driver.title.lower() == "not found":
            return product_list
        
        try:
            wrapper = WebDriverWait(web_driver, TIMEOUT_SECONDS).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'section.section-content.bg.padding-y'))
                )
        except TimeoutException:
            log_and_console_error("Timeout exception occurred in search page.")
            # check for div.productbox
        result_element = web_driver.find_elements(By.CSS_SELECTOR,'section.section-content.bg.padding-y')
        if len(result_element):
            search_results = []
            if len(result_element[0].find_elements(By.CSS_SELECTOR, 'article.card.card-product')):
                # layout one
                search_results = web_driver.find_elements(By.CSS_SELECTOR, 'section.section-content.bg.padding-y div.card-body div.img-wrap')
            elif len(result_element[0].find_elements(By.CSS_SELECTOR, 'div.productbox')):
                # layout two
                search_results = web_driver.find_elements(By.CSS_SELECTOR, 'section.section-content.bg.padding-y div.productbox div.imgBox')

            product_urls = []
            for result in search_results:
                product_urls.append(result.find_element(By.CSS_SELECTOR, 'a').get_attribute("href"))
            for detail_url in product_urls:
                product = get_product_details(request, detail_url)
                if product is not None and product.price != "na":
                    product_list.append(product)

    except Exception as ex:
        log_and_console_error(f"Exception occurred {ex}")

    log_and_console_info(f"Number of products found is {len(product_list)}")

    return product_list

def main():
    pid = 0
    try:
        logging.basicConfig(filename='app_log.txt', format='%(asctime)s %(message)s', level=logging.INFO)
        program_start_time = datetime.now()
        log_and_console_info(f"##### Starting the crawling at {program_start_time}")

        # Create the output file with headers
        create_output_file()

        # Returns 'none' if there is no identification file created
        last_id = get_identification_value()
        log_and_console_info(f'Identification file last id : {last_id}')

        inputs = open_inputs_from_file(INPUT_FILE)
        total_input_count = len(inputs)
        initiate_web_driver()
        # Looping the list of inputs as range to get the index of the input
        for i in range(len(inputs)):
            request = inputs[i]
            ###################### Identification block ######################
            # If last_id is 'none' [identification file not created] or 'found_last_value' [last value in identification is ound in input file], then start program
            # If last_id is a valid input id and matched with input list, then set found_last_value to last_id
            if(last_id != 'none' and last_id != 'found_last_value'):
                if(last_id != request.strike_id):
                    continue  # Skipping the input if that is not the last value written in identification file
                elif(last_id == request.strike_id):
                    last_id = 'found_last_value'
                    continue  # Setting new value and Skipping the input last value, if that is the last value written in identification file

            log_and_console_info(f"################ Processing input {i+1} of {total_input_count} ################")
            
            pid = pid + 1          

            log_and_console_info(f"Searching product with Strike_id={request.strike_id}, sku={request.sku} , brand={request.brand}, MPN={request.mpn}, UPC={request.upc}, ASIN={request.asin}")

            #################################   Extract Details   #################################
            start = datetime.now()

            try:
                response_list = scrape_product(request)
                response_str = ""
                if len(response_list):
                    response_str = "FOUND"
                    for res in response_list:
                        response_str = "\t".join([response_str, res.price, res.condition, res.availability])
                else:
                    response_str = "NOT FOUND"                

                output_file = open(OUTPUT_FILE, "a", encoding='utf8', errors='ignore')
                # Strike ID	SKU	Brand	MPN	Model	UPC	Asin
                output_file.write(f"{request.strike_id}\t{request.sku}\t{request.brand}\t{request.mpn}\t{request.model}\t{request.upc}\t{request.asin}\t{request.price}\t{response_str}\n")
                output_file.close()

                log_and_console_info(f'Time taken to scrape this product {datetime.now() - start}')

                # Updating the identification file with the sku
                update_identification_file(request.strike_id)
            except Exception as ex:
                log_and_console_error(f"Error searching the product. {ex}")
                write_into_error_file(request.input_string)

        log_and_console_info(f"##### Program execution time is {datetime.now() - program_start_time}")

        print_data_count()

    except Exception as error:
        log_and_console_error(f'Error occurred {error}')
        logging.error(error, exc_info=True)
    finally:
        log_and_console_info('Quiting the program!')
        if(web_driver != None):
            log_and_console_info('Quiting the webdriver!')
            web_driver.quit()

if __name__ == '__main__':
    main()
