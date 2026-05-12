"""
Download url to doc-string or file
  download_to_file(url, fname, f_log)
  doc = download_to_doc(url, f_log)

ND-SRAF / McDonald : 201606 | Last update: 202201
https://sraf.nd.edu
"""


import datetime as dt
import requests
import sys
import time
from urllib.request import urlopen


HEADER = {'Host': 'www.sec.gov', 'Connection': 'close',
         'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest',
         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
         }

def download_to_file(url, fname, f_log=None, number_of_tries=5, sleep_time=5):
    # download file from '_url' and write to 'fname'
    # Loop accounts for temporary server/ISP issues

    for i in range(1, number_of_tries):
        try:
            response = requests.get(url, headers=HEADER)
            if response.status_code == 200:
                with open(fname, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f'  Error in try #{i} download_to_file: URL = {url} | status_code = {response.status_code}')
                if i == number_of_tries + 1:
                    print(f'  Failed download: URL = {url}')
                    if f_log: f_log.write(f'  Failed download: URL = {url}\n')
                
        except Exception as exc:
            if i == 1:
                print('\n==>urlretrieve error in download_to_file.py')
            print(f'  {i}.url  : {url} \n  fname: {fname} \n  exc:  {exc}')
            if '404' in str(exc):
                break
            print(f'     Retry in {sleep_time} seconds')
            time.sleep(sleep_time)
            sleep_time += sleep_time

    print('\n  ERROR:  Download failed for')
    print(f'          url:  {url}')
    print(f'          _fname:  {fname}')
    if f_log:
        f_log.write('\nERROR:  Download failed=>')
        f_log.write(f'  _url: {url}')
        f_log.write(f'  |  _fname: {fname}')
        f_log.write(f'  |  {dt.datetime.now().strftime("%c")}')

    return False


def download_to_doc(url, f_log=None, number_of_tries=5, sleep_time=5):
    # Download url content to string doc
    # Loop accounts for temporary server/ISP issues

    for i in range(1, number_of_tries + 1):
        try:
            response = requests.get(url, headers=HEADER)
            if response.status_code == 200:
                doc = response.content.decode('utf-8', errors='ignore')
                return doc
            else:
                print(f'  Error in try #{i} download_to_file: URL = {url} | status_code = {response.status_code}')
                if i == number_of_tries + 1:
                    print(f'  Failed download: URL = {url}')
                    if f_log: f_log.write(f'  Failed download: URL = {url}\n')
        except Exception as exc:
            if i == 1:
                print('\n==>urlopen error in download_to_doc.py')
            print(f'  {i}. _url:  {url}')
            print(f'     Warning: {exc}  [{dt.datetime.now().strftime("%c")}]')
            if '404' in str(exc):
                break
            print(f'     Retry in {sleep_time} seconds')
            time.sleep(sleep_time)
            sleep_time += sleep_time

    print(f'  ERROR:  Download failed for url: {url}')
    if f_log:
        f_log.write(f'\nERROR:  Download failed=>  _url: {url} |  {dt.datetime.now().strftime("%c")}')

    return None


# Test routine
if __name__ == '__main__':
    
    start = dt.datetime.now()
    print(f"\n\n{start.strftime('%c')}\nPROGRAM NAME: {sys.argv[0]}\n")

    testfail_url = 'http://www.nd.edu/~mcdonald/xyz.html'  # set to throw an error
    test_url = 'http://www.sec.gov/Archives/edgar/data/1046568/0001193125-15-075170.txt'    
    fname = 'D:/Temp/DL_test.txt'
    f_log = open('D:/Temp/DL_log.txt', 'w')
    download_to_file(test_url, fname, f_log)
    doc = download_to_doc(test_url, f_log)

    print(f"\n\nRuntime: {(dt.datetime.now()-start)}")
    print(f"\nNormal termination.\n{dt.datetime.now().strftime('%c')}\n")   
    
