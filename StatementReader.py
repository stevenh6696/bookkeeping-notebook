import datetime
import os
import pdfplumber
import re


entry_matchers = [
    re.compile("(?P<date>\d{2}\/\d{2})(?:\/\d{2}\\*?)?\s+(?P<purchase>[^$]+?)\s+(?P<price>[-$]*[\d,]+\.\d{2})"),
    re.compile('\s(?P<date>\w{3} \d{2})\s+(?P<purchase>[^$]+)\s+(?P<price>[-$ ]*[\d,]+\.\d{2})'),
]


def read_file_to_lines(filepath):
    with pdfplumber.open(filepath) as pdf:
        lines = []

        for page in pdf.pages:
            lines += [line for line in page.extract_text().split('\n')]

    return lines


def determine_account(mappings, filepath):

    filename = os.path.basename(filepath)

    for prefix in mappings:
        if filename.startswith(prefix):
            return mappings[prefix]

    raise NameError('File path does not match any known account statement prefix')


def find_entries(lines):

    matcher = None
    for test_matcher in entry_matchers:
        if any(test_matcher.search(line) is not None for line in lines):
            matcher = test_matcher
            break
    if matcher is None:
        raise ValueError('No suitable matchers found')

    entries = []
    for match in map(lambda line: matcher.search(line), lines):
        if match is None:
            continue
        entries.append({
            'date': format_date(match.group('date')),  # format to date
            'purchase': match.group('purchase'),
            'price': format_price(match.group('price'))})  # format

    return entries


def format_date(date_string):

    for format in ['%m/%d', '%b %d']:
        try:
            parsed_date = datetime.datetime.strptime(date_string, format)
        except ValueError:
            continue
    if parsed_date is None:
        raise ValueError('Could not parse date')

    # Use current year since the parsed one will use 1900
    today = datetime.date.today()
    date_guess = datetime.date(today.year, parsed_date.month, parsed_date.day)

    # If it is in the future then it's from last year
    # Eg. parsing december statement in january
    if date_guess > today:
        date_guess = datetime.date(today.year - 1, parsed_date.month, parsed_date.day)

    return date_guess


def format_price(price_string):

    return float(re.sub('[$,]', '', price_string))
