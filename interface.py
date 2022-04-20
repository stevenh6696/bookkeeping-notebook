"""UI for bookkeeping."""
from dash import dash_table as dt, dcc
from dash import html
from dash.dash_table.Format import Format, Symbol
from dash.dependencies import Input, Output, State
from Utils import *
import dash
import datetime
import json
import pandas as pd

from Utils import save_entries_to_dataframe

app = dash.Dash(__name__)

# TODO: add last 4 digits to make unique
# TODO: add json validation
# Get configuration items
with open('config.json') as f:
    config = json.load(f)
    transactions_csv = config['Paths']['Transactions csv']
    account_options = [{'label': account, 'value': account} for account in config['Accounts']]
    category_options = [{'label': category, 'value': category} for category in config['Categories']]
    subcategory_options = {category: config['Categories'][category]['Subcategories']
                           for category in config['Categories']}

# TODO: fix layout
# TODO: add chart to view old items
app.layout = html.Div(
    [
        dcc.Dropdown(id='account', options=account_options),
        dcc.DatePickerSingle(
            id='date',
            min_date_allowed=datetime.date(2020, 1, 1),
            max_date_allowed=datetime.date(2025, 12, 31),
            date=datetime.date(2021, 11, 4)
        ),
        dcc.Input(id='store', type='text', placeholder='Store'),
        dcc.Input(id='description', type='text', placeholder='Description'),
        dcc.Input(id='amount', type='number', placeholder='Amount'),
        dcc.Dropdown(id='category', options=category_options),
        dcc.Dropdown(id='subcategory', options=[]),
        dcc.Input(id='notes', type='text', placeholder='Notes'),
        html.Br(),
        html.Button('Add', id='add'),
        html.Br(),
        html.Br(),
        html.Big('Changes Preview'),
        dt.DataTable(
            id='added_rows',
            columns=[
                {'name': 'Date', 'id': 'date', 'type': 'datetime'},
                {'name': 'Store', 'id': 'store', 'type': 'text'},
                {'name': 'Description', 'id': 'description', 'type': 'text'},
                {'name': 'Account', 'id': 'account', 'type': 'text'},
                {
                    'name': 'Amount',
                    'id': 'amount',
                    'type': 'numeric',
                    'format': Format(symbol=Symbol.yes).scheme('f').precision(2)},
                {'name': 'Category', 'id': 'category', 'type': 'text'},
                {'name': 'Subcategory', 'id': 'subcategory', 'type': 'text'},
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
            editable=False,  # No validation in table
            row_deletable=True,
            page_size=20,
            style_as_list_view=True,
            data=[]
        ),
        html.Br(),
        html.Button('Write', id='write'),
        html.Div('No changes yet', id='write_status'),
        html.Div(id='totals'),
    ]
)


@app.callback(
    Output('subcategory', 'options'),
    Input('category', 'value'),
)
def set_sub_category(category):
    """
    Update allowed subcategories according to selected category

    :param category: Selected category
    :return: List of subcategories for the given category
    """
    if category is None:
        return []
    else:
        return [{'label': subcategory, 'value': subcategory}
                for subcategory in subcategory_options[category]]


@app.callback(
    Output('added_rows', 'data'),
    Output('date', 'date'),
    Output('store', 'value'),
    Output('description', 'value'),
    Output('amount', 'value'),
    Output('category', 'value'),
    Output('subcategory', 'value'),
    Output('notes', 'value'),
    Output('write_status', 'children'),
    Output('totals', 'children'),
    Input('add', 'n_clicks'),
    Input('write', 'n_clicks'),
    State('added_rows', 'data'),
    State('account', 'value'),
    State('date', 'date'),
    State('store', 'value'),
    State('description', 'value'),
    State('amount', 'value'),
    State('category', 'value'),
    State('subcategory', 'value'),
    State('notes', 'value'),
    prevent_initial_call=True
)
def add_or_write(
        add,
        write,
        data,
        account,
        date,
        store,
        description,
        amount,
        category,
        subcategory,
        notes):
    """
    Add a new row or write the rows of displayed changes to the backing DataFrame
    and csv file. Since both modify the DataTable we must use the same callback

    :param add: (unused) Button info for the add button
    :param write: (unused) Button info for the write button
    :param data: Entered transactions
    :param account: Selected account
    :param date: Selected transaction date
    :param store: Merchant for transaction
    :param description: Description for transaction
    :param amount: Transaction amount
    :param category: Category for transaction
    :param subcategory: Subcategory for transaction
    :param notes: Additional notes for transaction
    """

    # Get the trigger
    trigger = dash.callback_context.triggered[0]['prop_id']

    # If adding a row we return the new data to the DataTable
    if trigger == 'add.n_clicks':
        data.append({
            'date': date,
            'store': store,
            'description': description,
            'account': account,
            'amount': amount,
            'category': category,
            'subcategory': subcategory,
            'notes': notes,
        })
        return (data, datetime.date.today(), '', '', None,
                None, None, '', f'Added {len(data)} rows', '')

    # If writing then we write to the main DataFrame, write to file,
    # and clear the DataTables
    if trigger == 'write.n_clicks':

        # Write to main DataFrame and backing file
        num_changes = len(data)
        transactions_df = save_entries_to_dataframe(pd.read_csv(transactions_csv), data)
        totals_str = calculate_totals(transactions_df, [acct for acct in config['Accounts']])

        return (data, date, store, description, amount, category, subcategory,
                notes, f'Wrote {num_changes} rows', totals_str)


if __name__ == '__main__':

    app.run_server(debug=True)
