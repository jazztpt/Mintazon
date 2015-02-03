from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import csv
import time
import copy
from re import sub
from decimal import Decimal


def find_in_list(lst, key, value):
    for i, dct in enumerate(lst):
        if dct[key] == value:
            return i
    return -1

def clean_list_of_orders_from_csv(file_path):
    #####
    # create list of dictionaries from csv file 
    #####
    with open(file_path) as amazon_orders_csvfile:
        reader = csv.DictReader(amazon_orders_csvfile)
        # TODO: are there any rows?
        orders = [] ### a list of all multi-item orders (some will need to be split)
        j = 0
        for row in reader:
            j+=1
            row["Total+Tax"] = Decimal(sub(r'[^\d.]', '', row["Item Subtotal"])) + \
                Decimal(sub(r'[^\d.]', '', row["Item Subtotal Tax"]))
            ### clean up the table: put same orders together
            ### create an "order" if there isn't one already and and add rows to it
            order_index = find_in_list(orders, "ID", row['Order ID'])
            if order_index == -1:
                order = {"ID": row["Order ID"], "rows": [row], "Total": row["Total+Tax"]}
                orders.append(order)
            else:
                order = orders[order_index]
                order["Total"] = order["Total"] + row["Total+Tax"]
                order["rows"].append(row)
    return orders


def main():
    ###
    # create Amazon order history reports: http://www.amazon.com/gp/help/customer/display.html?nodeId=200131240
    ###
    # TODO: is there a file?
    filepath = raw_input("Enter the path to your Amazon orders csv file:")
    orders = clean_list_of_orders_from_csv(filepath)
    if len(orders) == 0:
        print "There are no orders to process."
        return
    driver = webdriver.Chrome()
    driver.implicitly_wait(30)
    driver.get("https://wwws.mint.com/transaction.event#")
    print "waiting 4 seconds for login to refresh"
    time.sleep(4)

    ### log in ###
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "form-login-username"))
        )
    except:
        driver.quit()

    email_input = driver.find_element_by_id("form-login-username")
    email_input.send_keys(raw_input("Mint username (your email address): "))
    password_input = driver.find_element_by_id("form-login-password")
    password_input.send_keys(raw_input("Mint password: "))
    login_button = driver.find_element_by_id("submit").click()

    print "waiting 5 seconds for txn page to load"
    time.sleep(5)

    for order in orders:
        # first clear any search and wait
        try:
            clear_search_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((BY.ID, "search-clear"))
            )
            clear_search_button[0].click()
            print "clicked clear search button"
            time.sleep(5)
        except:
            print "no clear search button"
            pass
        ### 
        # search transactions 
        ###
        try:
            search_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search-input"))
            )
            print order["Total"]
            search_field.clear()
            search_field.send_keys(str(order["Total"]))
            search_field.send_keys(Keys.RETURN)
            time.sleep(6)

        except:
            pass
            driver.quit()

        table_rows = driver.find_elements_by_xpath("//table[@id='transaction-list']/tbody/tr[not(contains(@class, 'hide'))]")
        print "rows in txn table: %d" % len(table_rows)
        amount = driver.find_element_by_id("txnEdit-amount_input")
        merchant = driver.find_element_by_id("txnEdit-merchant_input")
        print amount.get_attribute("value")
        amount_decimal = Decimal(sub(r'[^\d.]', '', amount.get_attribute("value")))
        if len(order["rows"]) == 1:

            if len(table_rows) == 1:
                if amount_decimal == order["Total"] and \
                        merchant.get_attribute("value") == "Amazon":
                    category_input_id = driver.find_element_by_id("txnEdit-category_input")
                    ### if mint category != amazon category 
                    if category_input_id.get_attribute("value") != order["rows"][0]["Category"]:
                        print "CHANGING CATEGORY: " + category_input_id.get_attribute("value") + "==>" + \
                            order["rows"][0]["Category"]
                        category_input_id.clear()
                        category_input_id.send_keys(order["rows"][0]["Category"])
                        time.sleep(3)
                        category_input_id.send_keys(Keys.RETURN)
                else:
                    print "wrong amount or merchant: %s" % merchant.get_attribute("value")
            else:
                print "ambiguous: %d rows found in search for %f" % (len(table_rows), amount_decimal)
        else:
            print "this is a SPLIT transaction."


    driver.close()

main()