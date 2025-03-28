# This script updates sales data from a marketplace into a Google Sheets document.
# It connects to the Google Sheets API, processes sales data from a CSV file,
# and updates the main worksheet and an unfiltered worksheet based on the sales information.

import requests
import json
import math
import pandas as pd
from time import strftime, localtime
import time
import gspread
import functools
from datetime import datetime

# maxonly = 0

steamid = '76561199183171982' # replace with your own steamid64

def Reconnect():
    # Reconnects to the Google Sheets API and retrieves the necessary worksheets.
    # Returns the scope, Google client, spreadsheet, main worksheet, and unfiltered worksheet.
    global scope
    global gc
    global sh
    global main
    global unfiltered
    print('reconnecting')
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        gc = gspread.service_account(filename='service_account.json')

        #Name of the sheet that contains all other worksheets
        #Can also use gc.open_by_url(URL) if you have multiple
        # of the same name and don't want to change for whatever reason
        sh = gc.open('Master Spreadsheet')
        #Main worksheet name, uses name change if needed
        main = sh.worksheet("TF2")
        #Similarly but for max heads
        # msh = sh.worksheet("MSH")
        #Move all unfound items here
        unfiltered = sh.worksheet("Unrecorded Sales")
    except Exception as e:
        print('Reconnection failed! Trying again...')
        print(e)
        time.sleep(10)
        return Reconnect()
    return scope, gc, sh, main, unfiltered


def rate_limit(max_calls, timespan):
    # Decorator to limit the number of calls to a function within a specified timespan.
    # Prevents exceeding the rate limits imposed by the Google Sheets API.
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if not hasattr(wrapper, 'call_times'):
                wrapper.call_times = []

            wrapper.call_times = [t for t in wrapper.call_times if current_time - t <= timespan]

            if len(wrapper.call_times) < max_calls:
                wrapper.call_times.append(current_time)
                return func(*args, **kwargs)
            else:
                time_to_wait = max(wrapper.call_times) + timespan - current_time
                if time_to_wait > 0:
                    time.sleep(time_to_wait)
                return wrapper(*args, **kwargs)

        return wrapper
    return decorator


@rate_limit(max_calls=50, timespan=60)  # 50 per minute just to be safe since sheets forces a full logout on 429
def limiter(function):
    # A wrapper function that applies the rate limit to the decorated function.
    return function

def dateconvert(date):
    # Converts a date string from the format "dd Month, yyyy HH:MM" to "yyyy-mm-dd".
    date_obj = datetime.strptime(date, "%d %B, %Y %H:%M")
    formatted_date = date_obj.strftime("%Y-%m-%d")
    return formatted_date


def namefix(name, skulist):
    # Adjusts the item name based on specific rules and the provided SKU list.
    # Ensures compatibility with the marketplace naming scheme.
    #Strange filter exception:
    if 'Uncraftable Strange Filter:' in name:
        name = name.split('Uncraftable')[1]
        name = 'Non-Craftable' + name
        return name
    
    # We match marketplace naming scheme to follow spreadsheet for easier matching.
    # KILLSTREAK x QUALITY HANDLING, should be compatible with ks hats afaik
    qlt = skulist.split(';')[1]
    sku = skulist.split(';')[0]

    # Remove killstreaker in the end of item name
    if 'Professional ' in name or 'Specialized ' in name:
        temp = name.rfind('(')
        name = name[:temp].strip()

    qualities = ['Vintage ', 'Genuine ', "Collector's ", "Normal ", 'Strange ']  # Think about strange double qualities later
    effects = ['Isotope ', 'Hot ', 'Energy Orb ', 'Cool ']
    aussieslots = ['primary', 'secondary', 'melee', 'warpaint']
    # Test example : 'Professional Australium Black Box'
    if 'Professional ' in name:
        temp = name.split('Professional ')  # '' + 'Australium BLack Box'
        name = temp[0] + 'Professional Killstreak ' + temp[1]  # Professional Killstreak Australium Black Box
    elif 'Specialized ' in name:
        temp = name.split('Specialized ')
        name = temp[0] + 'Specialized Killstreak ' + temp[1]
    elif 'Basic Killstreak ' in name:
        temp = name.split('Basic ')
        name = temp[0] + temp[1]  # Killstreak [ITEM NAME]

    if 'Australium ' in name and skema[sku]['item_slot'] in aussieslots:
        name = 'Strange ' + name

    if skema[sku]['item_slot'] in aussieslots and sku != '1181':  # hot hand exception
        for effect in effects:
            if effect in name:
                temp = name.split(effect)
                name = effect + temp[0] + temp[1]
        if '★' in name:
            temp = name.split('★')
            name = temp[0] + temp[1]

        if 'Festivized ' in name:
            temp = name.split('Festivized ')
            name = temp[0] + temp[1]

    for quality in qualities:
        if quality == 'Vintage ' and ('Vintage Tyrolean' in name or 'Vintage Merryweather' in name):
            continue
        if quality in name:
            temp = name.split(quality)
            name = quality + temp[0] + temp[1]  # 'Strange' + 'Professional' + 'Kritzkrieg'

    # Effect handling
    if 'Peace Sign' in name or 'TF Logo' in name:
        if 'Strange' in name:
            name = 'Strange Circling ' + name.split('Strange ')[1]
        else:
            name = 'Circling ' + name

    if 'Uncraftable' in name:
        temp = name.split('Uncraftable ')
        name = 'Non-Craftable ' + temp[0] + temp[1]

    if 'Paint: ' in name:
        temp = name.split('Paint: ')
        name = temp[0] + temp[1]

    if 'Unusualifier' in name:
        name = 'Non-Craftable Unusual ' + name

    if skema[sku]['item_slot'] == 'tool':
        if 'Kit' in name and 'Fabricator' not in name:
            name = 'Non-Craftable ' + name

    if 'Strange ' in name and qlt == '6': # Strange Unique
        name = 'Strange Unique ' + name.split('Strange ')[1]

    if skulist == f"{sku};6":
        name = skema[sku]['name']

    if name[0] == "'":
        name = name[1:]

    if name == "Horseless Headless Horsemann's Headtaker":
        name = "Unusual Horseless Headless Horsemann's Headtaker"

    if ' Shred Alert' in name:
        name = name.replace('Taunt: The ', '')

    return name


def qualityFinder(item):  # use item section of the sale as input
    # Determines the quality of an item based on its SKU and other characteristics.
    qualitydict = {'6': 'Unique',
                   '5': 'Unusual',
                   '11': 'Strange',
                   '14': "Collector's",
                   '13': "Haunted",
                   '3': "Vintage",
                   "1": "Genuine",
                   "9": "Self-Made",
                   "0": "Normal",
                   "15": "Decorated Weapon"}
    sku = y[1].split(';')[1]
    quality = qualitydict[sku]
    if '(Battle Scarred)' in y[0] or '(Well-Worn)' in y[0] or '(Field-Tested)' in y[0] or '(Minimal Wear)' in y[0] or '(Factory New)' in y[0]:
        if '★' in y[0]:
            quality = 'Unusual Decorated Weapon'
        else:
            quality = 'Decorated Weapon'

    if 'strange' in y[1]:  # elevated qualities marked with ;strange
        quality = 'Strange ' + quality

    elif sku == '11' and quality != 'Strange':  # in theory should only apply to skins
        quality = 'Strange ' + quality

    return quality

dontupdate = ['Mann Co. Supply Crate Key', 'Refined Metal', 'Tour of Duty Ticket', 'Uncraftable Tour of Duty Ticket', 'Non-Craftable Tour of Duty Ticket']
skema = json.loads(open('itemschema.json', encoding="utf8").read())
looptime = time.time()

Reconnect()

batchUpdate = []
unfilteredBatchUpdate = []
# maxBatchUpdate = []
totalupdates = 0

z = pd.read_csv(f'marketplace_sales_{steamid}_items.csv')
# replace with your steam id64 here
z = z[::-1]

maindf = pd.DataFrame(main.get_all_records())
maindf = maindf[maindf['Sold (USD)'] == '']

# mshdf = pd.DataFrame(msh.get_all_records())
# mshdf = mshdf[mshdf['Sold (USD)'] == '']

for i in range(len(z)):
    y = list(z.iloc[i,])
    #0 = name, 1 = sku, 2 = orderid, 3 = date, 4 = status, 5 = price, 6 = net, 7 = fee
    if y[4] != 'Delivered' and y[4] != 'PendingDelivery':
        continue  # not sold
    gametest = y[1].split(';')[0]
    if gametest == 'd2' or gametest == 'steam':
        continue
    if y[1].split(';')[0] == '-100':
        sku = skema['263']
        y[1] = '263;6'
    elif y[1].split(';')[0] in skema:
        sku = skema[y[1].split(';')[0]]
    else:
        sku = {"name": "UNKNOWN!", "defindex": "UNKNOWN!", "item_slot": "UNKNOWN!", "class": "UNKNOWN!"}
    name = namefix(y[0], y[1])
    if ('(Battle Scarred)' in name or '(Well-Worn)' in name or '(Field-Tested)' in name or '(Minimal Wear)' in name or '(Factory New)' in name) and ' War Paint' not in name:
        slot = 'Skin'  # dumb easy fix for skins
    else:
        slot = sku['item_slot']
    quality = qualityFinder(y)

    if name in dontupdate:
        continue

    # if name == "Max's Severed Head":
    #     if len(list(mshdf.loc[mshdf['Item']==name,'Item'])) != 0:
    #         maxLast = mshdf.loc[mshdf['Item']==name,'Item'].index[0] + 2 # Take latest sale, + 2 to account for header row and index 0
    #       maxBatchUpdate.append({'range': f"D{maxLast}:H{maxLast}", "values": [[dateconvert(y[3]), y[6], f"=D{maxLast}-B{maxLast}", f"=E{maxLast}-C{maxLast}", f"=G{maxLast}/E{maxLast}"]]})
    #       maxBatchUpdate.append({'range': f"I{maxLast}", "values": [[y[2]]]})
    #       mshdf = mshdf.drop(maxLast - 2)
    #       totalupdates = totalupdates + 1
    #       continue

    # if maxonly == 1:
    #     continue

    if len(list(maindf.loc[maindf['Item']==name,'Item'])) == 0:  # no unsold items
        unfilteredBatchUpdate.append([slot, sku['class'], quality, name, dateconvert(y[3]), y[6], y[2]])
    else:
        row = maindf.loc[maindf['Item']==name,'Item'].index[0] + 2 # Take latest sale, + 2 to account for header row and index 0
        batchUpdate.append({'range': f"A{row}:C{row}", "values": [[slot, sku['class'], quality]]})
        batchUpdate.append({'range': f"G{row}:K{row}", "values": [[dateconvert(y[3]), y[6], f"=G{row}-E{row}", f"=H{row}-F{row}", f"=J{row}/F{row}"]]})
        batchUpdate.append({'range': f"L{row}", "values": [[y[2]]]})
        maindf = maindf.drop(row - 2)

    totalupdates = totalupdates + 1

if len(batchUpdate) > 0:
    while True:
        try:
            print(f'Attempting to update {len(batchUpdate)} main items')
            limiter(main.batch_update(batchUpdate, value_input_option='USER_ENTERED'))
            break
        except Exception as e:
            if isinstance(e, gspread.exceptions.APIError):
                if e.args[0]['code'] >= 500 or e.args[0]['code'] == 429:
                    time.sleep(5)
                    Reconnect()
                else:
                    raise(e)
            else:
                raise(e)

if len(unfilteredBatchUpdate) > 0:
    while True:
        try:
            print(f'Attempting to update {len(unfilteredBatchUpdate)} unfiltered items')
            limiter(unfiltered.append_rows(unfilteredBatchUpdate, value_input_option='USER_ENTERED'))
            break
        except Exception as e:
            if isinstance(e, gspread.exceptions.APIError):
                if e.args[0]['code'] >= 500 or e.args[0]['code'] == 429:
                    time.sleep(5)
                    Reconnect()
                else:
                    raise(e)
            else:
                raise(e)

# old max's head logic; added to main sheet for easier tracking
# if len(maxBatchUpdate) > 0:
    # while True:
        # try:
            # print(f'Attempting to update {len(maxBatchUpdate)} Max Heads')
            # maxoutput = limiter(msh.batch_update(maxBatchUpdate, value_input_option='USER_ENTERED'))
            # if maxonly == 1:
            #     print(maxBatchUpdate)
            #     print(maxoutput)
        #    break
        # except Exception as e:
        #     if isinstance(e, gspread.exceptions.APIError):
        #         if e.args[0]['code'] >= 500 or e.args[0]['code'] == 429:
        #             time.sleep(5)
        #             Reconnect()
        #         else:
        #             raise(e)
        # else:
        #     raise(e)

print('Updated this many items:', totalupdates)
print('Process completed in:', time.time() - looptime)