"""UI for adding data from statements."""
from dash import dash_table as dt, dcc
from dash import html
from dash.dash_table.Format import Format, Symbol
from dash.dependencies import Input, Output, State
from Utils import *
import dash
import datetime
import json
import operator
import pandas as pd

app = dash.Dash(__name__)

# Get configuration items
with open('config.json') as f:
    config = json.load(f)
    path = config['Paths']['Statement Root']
    transactions_csv = config['Paths']['Transactions csv']
    category_options = [{'label': category, 'value': category} for category in config['Categories']]
    category_options = sorted(category_options, key=operator.itemgetter('label'))

# Create app layout
app.layout = html.Div(
    [
        html.Big('Minimum date for statements'),
        dcc.DatePickerSingle(
            id='min-date',
            min_date_allowed=datetime.date(2019, 1, 1),
            date=datetime.date.today()
        ),
        html.Br(),
        html.Big('Changes Preview'),
        dt.DataTable(
            id='added-rows',
            columns=[
                {'name': 'Date', 'id': 'date', 'type': 'datetime', 'editable': False},
                {'name': 'Store', 'id': 'store', 'type': 'text', 'editable': False},
                {'name': 'Description', 'id': 'description', 'type': 'text'},
                {'name': 'Account', 'id': 'account', 'type': 'text', 'editable': False},
                {
                    'name': 'Amount',
                    'id': 'amount',
                    'type': 'numeric',
                    'format': Format(symbol=Symbol.yes).scheme('f').precision(2),
                    'editable': False,
                },
                {'name': 'Category', 'id': 'category', 'type': 'text', 'presentation': 'dropdown'},
                {
                    'name': 'Subcategory',
                    'id': 'subcategory',
                    'type': 'text',
                    'presentation': 'dropdown'
                },
                {'name': 'Notes', 'id': 'notes', 'type': 'text'}
            ],
            style_cell={'textAlign': 'left'},
            style_data_conditional=[
                {
                    # Only align numbers right
                    'if': {'column_id': 'amount'},
                    'textAlign': 'right'
                },
                {
                    # Green for income
                    'if': {
                        'column_id': 'amount',
                        'filter_query': '{amount} > 0'
                    },
                    'backgroundColor': 'yellowgreen'
                },
                {
                    # Red for spending
                    'if': {
                        'column_id': 'amount',
                        'filter_query': '{amount} < 0'
                    },
                    'backgroundColor': 'orangered'
                }
            ],
            dropdown={'category': {'options': category_options}},
            dropdown_conditional=[{
                    'if': {
                        'column_id': 'subcategory',
                        'filter_query': f'{{category}} eq "{category}"'
                    },
                    'options': sorted([
                        {'label': subcategory, 'value': subcategory}
                        for subcategory in config['Categories'][category]['Subcategories']
                    ], key=operator.itemgetter('label'))
                } for category in config['Categories']],
            editable=True,  # No validation in table
            row_deletable=True,
            page_size=20,
            style_as_list_view=True,
            data=[]
        ),
        html.Br(),
        html.Button('Import statements', id='import-statements'),
        html.Button('Write', id='write'),
        html.Div('No changes yet', id='write-status'),
    ]
)


@app.callback(
    Output('added-rows', 'data'),
    Output('write-status', 'children'),
    Input('import-statements', 'n_clicks'),
    Input('write', 'n_clicks'),
    State('added-rows', 'data'),
    State('min-date', 'date'),
    prevent_initial_call=True
)
def import_or_write(import_statement, write, entries, min_date):
    """
    Import statements or persist entered changes

    Create new editable entries that can be persisted in to the backing csv file

    :param import_statement: (unused) Button info for the import-statement button
    :param write: (unused) Button info for the write button
    :param min_date: Minimum date for statements
    :return: Tuple containing data to be displayed and a status message
    """

    # Get the trigger
    trigger = dash.callback_context.triggered[0]['prop_id']

    # Import statements
    if trigger == 'import-statements.n_clicks':
        return (import_statements_to_table(min_date), 'No changes yet')

    # Write changes to csv
    if trigger == 'write.n_clicks':
        return ([], append_data_to_csv(entries, [acct for acct in config['Accounts']]))


def import_statements_to_table(min_date: str):
    """
    Import statements after a given date into a table for editing

    :param min_date: Minimum date to search for statements
    :return: List of dictionaries representing transactions
    """

    # Get relevant files
    min_date_as_date = datetime.datetime.strptime(min_date, '%Y-%m-%d')
    files = find_files(path, min_date_as_date)

    # Get all entries
    data = []
    for filename in files:
        account_name = find_account_name(config['Accounts'], filename)
        lines = read_pdf_to_lines(path, filename)

        # Special case for statements that don't show negative amounts
        account_info = config['Accounts'][account_name]
        negate = account_info['Type'] == 'Credit'
        if 'Negative Separator' in account_info:
            split_index = find_matching_line(lines, account_info['Negative Separator'])
            entries = find_entries(lines[:split_index], negate)
            entries += find_entries(lines[split_index:], not negate)
        # Parse normally
        else:
            entries = find_entries(lines, negate)

        add_account_to_entries(entries, account_name)
        data += entries

    return sorted(data, key=operator.itemgetter('date', 'account'))


def append_data_to_csv(entries: list, account_options: list):
    """
    Write entries to backing csv file

    :param entries: Transactions to add to backing csv file
    :param account_options: Accounts to calculate the balances for
    :return: Dash html paragraph containing balances of each account
    """

    transactions_df = save_entries_to_dataframe(pd.read_csv(transactions_csv), entries)
    return calculate_totals(transactions_df, account_options)


if __name__ == '__main__':

    app.run_server(debug=True)
