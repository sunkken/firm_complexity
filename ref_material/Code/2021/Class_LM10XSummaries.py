"""

  This module provides a class module for the data input from LM_10X_Summaries_YYYY.csv.
  The module takes as input a string which is a line from the data file.
  Be sure to consume the header line in your loop reading the file.
  Each line is converted into the variables contained in the file.
  The __main__ section below provides a simple example of usage.

ND-SRAF / McDonald : 202201
https://sraf.nd.edu
"""

import datetime as dt
import sys


class cl_LM10XSummaries:
    def __init__(self, _line, missing_values=''):

        parts = _line.strip("\n").split(",")
        self.cik = converter(parts[0], "int", missing_values)
        self.filing_date = converter(parts[1], "int", missing_values)
        self.acc_num = converter(parts[2], "string", missing_values)
        self.conformed_period_report = converter(parts[3], "string", missing_values)
        self.form_type = converter(parts[4], "string", missing_values)
        self.coname = converter(parts[5], "string", missing_values)
        self.sic = converter(parts[6], "int", missing_values)
        self.ffind = converter(parts[7], "int", missing_values)
        self.n_words = converter(parts[8], "int", missing_values)
        self.n_unique = converter(parts[9], "int", missing_values)
        self.n_negative = converter(parts[10], "int", missing_values)
        self.n_positive = converter(parts[11], "int", missing_values)
        self.n_uncertain = converter(parts[12], "int", missing_values)
        self.n_litigious = converter(parts[13], "int", missing_values)
        self.n_strongmodal = converter(parts[14], "int", missing_values)
        self.n_weakmodal = converter(parts[15], "int", missing_values)
        self.n_constraining = converter(parts[16], "int", missing_values)
        self.n_negation = converter(parts[17], "int", missing_values)
        self.grossfilesize = converter(parts[18], "int", missing_values)
        self.netfilesize = converter(parts[19], "int", missing_values)
        self.nontextdoctypechars = converter(parts[20], "int", missing_values)
        self.html_chars = converter(parts[21], "int", missing_values)
        self.xbrl_chars = converter(parts[22], "int", missing_values)
        self.xml_chars = converter(parts[23], "int", missing_values)
        self.n_exhibits = converter(parts[24], "int", missing_values)


def converter(_var, _ctype, missing_values):
    # missing_values should be passed as a string variable
    _attr = missing_values
    if _ctype != 'int' and _ctype != 'float' and _ctype != 'string':
        print('\n\nERROR in converter: _ctype = {0}'.format(_ctype))
        quit()
    if _ctype == 'int':
        if _var:
            _attr = int(_var)
        else:
            try:
                _attr = int(missing_values)
            except TypeError:
                return _attr
    elif _ctype == 'float':
        if _var:
            _attr = float(_var)
        else:
            try:
                _attr = float(missing_values)
            except TypeError:
                return _attr
    elif _ctype == 'string':
        if _var:
            _attr = _var
        else:
            try:
                _attr = str(missing_values)
            except TypeError:
                return _attr

    return _attr


if __name__ == '__main__':

    start = dt.datetime.now()
    print(f"\n\n{start.strftime('%c')}\nPROGRAM NAME: {sys.argv[0]}\n")

    source_file = r'G:\My Drive\SRAF\EDGAR_Data\Loughran-McDonald_10X_Summaries_1993-2021.csv'
    f_in = open(source_file)
    header = f_in.readline()  # Consume header line
    n_test = 10
    n = 0
    for line in f_in:
        lm_sum = cl_LM10XSummaries(line, missing_values="")
        print(lm_sum.__dict__)
        # Sample calculation
        negative_signal = (lm_sum.n_negative + lm_sum.n_weakmodal) / lm_sum.n_words
        doc_structure = (lm_sum.html_chars + lm_sum.xbrl_chars + lm_sum.xml_chars) / lm_sum.netfilesize
        n += 1
        if n > 10:
            break

    print(f"\n\nRuntime: {(dt.datetime.now()-start)}")
    print(f"\nNormal termination.\n{dt.datetime.now().strftime('%c')}\n")  
