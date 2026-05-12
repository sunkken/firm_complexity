"""
    Utility programs for accessing SEC/EDGAR
    ND-SRAF / McDonald : 201606
    https.//sraf.nd.edu
"""


def download_masterindex(year, qtr, flag=False):
    # Download Master.idx from EDGAR
    # Loop in case of temporary server/ISP issues

    import datetime as dt
    import time
    from urllib.request import urlopen
    from zipfile import ZipFile
    from io import BytesIO

    number_of_tries = 10
    sleep_time = 10  # Note sleep time accumulates according to err


    PARM_EDGARPREFIX = 'https://www.sec.gov/Archives/edgar/full-index/'

    start = dt.datetime.now()  # Note: using clock time not CPU
    masterindex = list()
    #  using the zip file is a little more complicated but orders of magnitude faster
    append_path = str(year) + '/QTR' + str(qtr) + '/master.idx'  
    sec_url = PARM_ROOT_PATH + append_path

    for i in range(1, number_of_tries + 1):
        try:
            
            records = urlopen(sec_url).read().decode('utf-8').splitlines()[10:] #  => nonzip version
            break
        except Exception as exc:
            if i == 1:
                print('\nError in download_masterindex')
            print(f'  {i}. _url:  {sec_url}')

            print(f'  Warning: {exc}  [{dt.datetime.now().strftime("%c")}]')
            if '404' in str(exc):
                break
            if i == number_of_tries:
                return False
            print(f'     Retry in {sleep_time} seconds')
            time.sleep(sleep_time)
            sleep_time += sleep_time


    # Load m.i. records into masterindex list
    for line in records:
        mir = MasterIndexRecord(line)
        if not mir.err:
            masterindex.append(mir)

    if flag:
        print(f'download_masterindex:  {year} : {qtr} | lne() = {len(masterindex),:}' +
              f' | Time = {(dt.datetime.now() - start),.4} seconds') 

    return masterindex


class MasterIndexRecord:
    def __init__(self, line):
        self.err = False
        parts = line.split('|')
        if len(parts) == 5:
            self.cik = int(parts[0])
            self.name = parts[1]
            self.form = parts[2]
            self.filingdate = int(parts[3].replace('-', ''))
            self.path = parts[4]
        else:
            self.err = True
        return





