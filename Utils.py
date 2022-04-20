from dash import html
import datetime
import os
import pandas as pd
import pdfplumber
import re

"""
Matchers to match for a transaction
"""
entry_matchers = [
    re.compile("(?P<date>\d{2}\/\d{2})(?:\/\d{2}\\*?)?\s+(?P<purchase>[^$]+?)\s+(?P<price>[-$]*[\d,]+\.\d{2})"),
    re.compile('\s(?P<date>\w{3} \d{2})\s+(?P<purchase>[^$]+)\s+(?P<price>[-$ ]*[\d,]+\.\d{2})'),
]


def find_files(filepath: str, min_date: datetime.date):
    """
    Find files from later than the provided date

    :param filepath: Folder to check for files
    :param min_date: Minimum date that the files should be after
    :return: List of filenames
    """

    date_matcher = re.compile('(?P<date>\d{4}-\d{2}-\d{2})\.pdf')

    relevant_files = []
    for filename in os.listdir(filepath):

        # Check if has file has date
        match = date_matcher.search(filename)
        if match is None:
            continue

        # Only save files more recent than the given date
        parsed_date = datetime.datetime.strptime(match.group('date'), '%Y-%m-%d')
        if parsed_date >= min_date:
            relevant_files.append(filename)

    return relevant_files


def find_account_name(accounts: list, filename: str):
    """
    Find matching account name given a filename

    :param accounts: List of dictionaries with account names as keys, containing expected
                     filename prefixes
    :param filename: Filename to be matched with
    :return: Matched account name
    """

    for account_name in accounts:

        prefix = accounts[account_name]['Statement Prefix']
        if prefix is None:
            continue

        if filename.startswith(prefix):
            return account_name

    raise NameError('File path does not match any known account statement prefix')


def read_pdf_to_lines(folder: str, filename: str):
    """
    Read a PDF file

    :param folder: Folder containing the file
    :param filename: Filename of the PDF file
    :return: List of lines from the PDF
    """

    filepath = os.path.join(folder, filename)
    with pdfplumber.open(filepath) as pdf:
        lines = []

        for page in pdf.pages:
            lines += [line for line in page.extract_text().split('\n')]

    return lines


def find_matching_line(lines: list, text: str):
    """
    Find the index of the line matching the given text

    :param lines: Lines to match against
    :param text: Text to match
    :return: Index of matching line in the list
    :raises ValueError: If no lines match the given text
    """

    for i, line in enumerate(lines):
        if line == text:
            return i

    raise ValueError('No matching lines found')


def find_entries(lines: list, reverse_amount=False):
    """
    Find transactions from a list of strings

    :param lines: Lines to be parsed for transactions
    :param reverse_amount: Whether to reverse the amount shown on the statement
    :return: list of dictionaries representing transactions
    """

    # Find a matcher to use
    matcher = None
    for test_matcher in entry_matchers:
        if any(test_matcher.search(line) is not None for line in lines):
            matcher = test_matcher
            break
    if matcher is None:
        raise ValueError('No suitable matchers found')

    # Parse for transactions
    entries = []
    for match in map(lambda line: matcher.search(line), lines):
        if match is None:
            continue
        amount = format_price(match.group('price'))
        amount = amount if not reverse_amount else -amount
        entries.append({
            'date': parse_date(match.group('date')),  # format to datetime.date
            'store': match.group('purchase'),
            'amount': amount})

    return entries


def parse_date(date_string: str):
    """
    Parse a date string into a datetime object

    :param date_string: String representing a date
    :return: datetime.date object
    """

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


def format_price(price_string: str):
    """
    Format a price string by removing unneeded characters

    :param price_string: String representing a price
    """

    return float(re.sub('[$,]', '', price_string))


def add_account_to_entries(entries: list, account: str):
    """
    Add account info to a transaction entry in place

    :param entries: List of dictionaries representing transactions
    :param account: Account name to be added to all transactions
    """

    for entry in entries:
        entry['account'] = account


def save_entries_to_dataframe(transactions_df: pd.DataFrame, data: list):
    """
    Add more transactions in list form to the dataframe and persist the changes

    :param transactions_df: Original DataFrame containing transactions
    :param data: List of dictionaries representing transactions to be added
    :return: The modified transactions_df
    """

    entries_df = pd.DataFrame(data)
    transactions_df = pd.concat([transactions_df, entries_df], ignore_index=True, sort=False)
    transactions_df.sort_values(by=['date', 'account'], inplace=True)
    transactions_df.to_csv('data.csv', index=False)
    print(transactions_df.last)
    data.clear()

    return transactions_df


def calculate_totals(transactions_df: pd.DataFrame, account_options: list):
    """
    Calculate the total amounts for each account given using the transactions given

    :param transactions_df: DataFrame containing transactions
    :param account_options: Accounts to generate balances for
    :return: Balances as a  Dash html paragraph
    """

    total_strs = ['New account balances:']

    # Calculate balances for each account given
    for account in sorted(account_options):
        account_transactions = transactions_df[transactions_df['account'] == account]
        total_strs.append(html.Br())
        total_strs.append(f'\t{account}: {round(sum(account_transactions["amount"]), 2)}')

    return html.P(total_strs)
