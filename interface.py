from dash import dash_table as dt, dcc
from dash import html
from dash.dash_table.Format import Format, Symbol
from dash.dependencies import Input, Output, State
import dash
import datetime
import json
import pandas as pd

app = dash.Dash(__name__)
transactionsDf = pd.read_csv('data.csv')
transactionsDfColumns = transactionsDf.columns

# TODO: add last 4 digits to make unique
# TODO: add json validation
config = json.load(open('config.json'))
accountOptions = [{'label': account, 'value': account} for account in config['Accounts']]
categoryOptions = [{'label': category, 'value': category} for category in config['Categories']]
subcategoryOptions = {category:config['Categories'][category]['Subcategories'] for category in config['Categories']}

# TODO: fix layout
# TODO: add chart to view old items
app.layout = html.Div(
    [
        dcc.Dropdown(id='Account', options=accountOptions),
        dcc.DatePickerSingle(
            id='Date',
            min_date_allowed=datetime.date(2020, 1, 1),
            max_date_allowed=datetime.date(2025, 12, 31),
            date=datetime.date(2021, 11, 4)
        ),
        dcc.Input(id="Store", type="text", placeholder="Store"),
        dcc.Input(id="Description", type="text", placeholder="Description"),
        dcc.Input(id="Amount", type="number", placeholder="Amount"),
        dcc.Dropdown(id='Category', options=categoryOptions),
        dcc.Dropdown(id='Subcategory', options=[]),
        dcc.Input(id="Notes", type="text", placeholder="Notes"),
        html.Br(),
        html.Button('Add', id='Add'),
        html.Br(),
        html.Br(),
        html.Big('Changes Preview'),
        dt.DataTable(
            id='AddedRows',
            columns=[
                {'name': 'Date', 'id': 'Date', 'type': 'datetime'},
                {'name': 'Store', 'id': 'Store', 'type': 'text'},
                {'name': 'Description', 'id': 'Description', 'type': 'text'},
                {'name': 'Account', 'id': 'Account', 'type': 'text'},
                {'name': 'Amount', 'id': 'Amount', 'type': 'numeric', 'format': Format(symbol=Symbol.yes).scheme('f').precision(2)},
                {'name': 'Category', 'id': 'Category', 'type': 'text'},
                {'name': 'Subcategory', 'id': 'Subcategory', 'type': 'text'},
                {'name': 'Notes', 'id': 'Notes', 'type': 'text'}
            ],
            style_cell={'textAlign': 'left'},
            style_data_conditional=[
                {
                    # Only align numbers right
                    'if': {'column_id': 'Amount'},
                    'textAlign': 'right'
                },
                {
                    # Green for income
                    'if': {
                        'column_id': 'Amount',
                        'filter_query': '{Amount} > 0'
                    },
                    'backgroundColor': 'yellowgreen'
                },
                {
                    # Red for spending
                    'if': {
                        'column_id': 'Amount',
                        'filter_query': '{Amount} < 0'
                    },
                    'backgroundColor': 'orangered'
                }
            ],
            editable=False, # No validation in table
            row_deletable=True,
            page_size=20,
            style_as_list_view=True,
            data=[]
        ),
        html.Br(),
        html.Button('Write', id='Write'),
        html.Div('No changes yet', id='WriteStatus'),
        html.Div(id='Totals'),
    ]
)

@app.callback(
    Output('Subcategory', 'options'),
    Input('Category', "value"),
)
def set_sub_category(Category):
    if Category is None:
        return []
    else:
        return [{'label': subcategory, 'value': subcategory} for subcategory in subcategoryOptions[Category]]

@app.callback(
    Output('AddedRows', 'data'),
    Output('Date', 'date'),
    Output('Store', 'value'),
    Output('Description', 'value'),
    Output('Amount', 'value'),
    Output('Category', 'value'),
    Output('Subcategory', 'value'),
    Output('Notes', 'value'),
    Output('WriteStatus', 'children'),
    Output('Totals', 'children'),
    Input('Add', 'n_clicks'),
    Input('Write', 'n_clicks'),
    State('AddedRows', 'data'),
    State('Account', 'value'),
    State('Date', 'date'),
    State('Store', 'value'),
    State('Description', 'value'),
    State('Amount', 'value'),
    State('Category', 'value'),
    State('Subcategory', 'value'),
    State('Notes', 'value'),
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
    
    # Get the trigger
    trigger = dash.callback_context.triggered[0]['prop_id']

    # If adding a row we return the new data to the DataTable
    if trigger == 'Add.n_clicks':
        newRow = {
            'Date': date,
            'Store': store,
            'Description': description,
            'Account': account,
            'Amount': amount,
            'Category': category,
            'Subcategory': subcategory,
            'Notes': notes,
        }
        data.append(newRow)
        return (data, datetime.date.today(), '', '', None, None, None, '', f'Added {len(data)} rows', '')

    # If writing then we write to the main DataFrame, write to file, and clear the DataTable
    if trigger == 'Write.n_clicks':

        # Write to main DataFrame and backing file
        global transactionsDf
        numChanges = len(data)
        transactionsDf = transactionsDf.append(data, ignore_index=True, sort=False)
        transactionsDf.sort_values(by=['Date', 'Account'], inplace=True)
        transactionsDf.to_csv('data.csv', index=False)
        data.clear()

        # Calculate new totals
        totalStrs = []
        for account in sorted(map(lambda x: x['label'], accountOptions)):
            accountTransactions = transactionsDf[transactionsDf['Account'] == account]
            totalStrs.append(f'{account}: {round(sum(accountTransactions["Amount"]), 2)}')
            totalStrs.append(html.Br())

        return (data, date, store, description, amount, category, subcategory, notes, f'Wrote {numChanges} rows', html.P(totalStrs))

if __name__ == "__main__":

    app.run_server(debug=True)
