from datetime import date
from datetime import datetime
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import dash
import json
import pandas as pd


app = dash.Dash(__name__)
transactionsDf = pd.read_csv('data.csv').convert_dtypes()

# TODO: add last 4 digits to make unique
# TODO: add json validation
config = json.load(open('config.json'))
accountOptions = [{'label': account, 'value': account} for account in config['Accounts']]
categoryOptions = [{'label': category, 'value': category} for category in config['Categories']]
subcategoryOptions = {category:config['Categories'][category]['Subcategories'] for category in config['Categories']}
new = []

app.layout = html.Div(
    [
        dcc.DatePickerSingle(
            id='Date',
            min_date_allowed=date(2020, 1, 1),
            max_date_allowed=date(2025, 12, 31),
            date=date(2021, 11, 4)
        ),
        dcc.Input(id="Store", type="text", placeholder="Store"),
        dcc.Input(id="Description", type="text", placeholder="Description"),
        dcc.Dropdown(id='Account', options=accountOptions),
        dcc.Input(id="Amount", type="number", placeholder="Amount"),
        dcc.Dropdown(id='Category', options=categoryOptions),
        dcc.Dropdown(id='Sub-Category', options=[]),
        dcc.Input(id="Notes", type="text", placeholder="Notes"),
        html.Br(),
        html.Button('Add', id='Add'),
        html.Br(),
        html.Div(id='TempMessage'),
        html.Br(),
        html.Div(id='AddedSoFar'),
        html.Br(),
        html.Button('Write', id='Write'),
        html.Div(id='WriteStatus'),
        html.Div(id='Totals'),
    ]
)

@app.callback(
    Output('Sub-Category', 'options'),
    Input('Category', "value"),
)
def set_sub_category(Category):
    if Category is None:
        return []
    else:
        return [{'label': subcategory, 'value': subcategory} for subcategory in subcategoryOptions[Category]]

@app.callback(
    Output('TempMessage', 'children'),
    Input('Date', "date"),
    Input('Store', "value"),
    Input('Description', "value"),
    Input('Account', "value"),
    Input('Amount', "value"),
    Input('Category', "value"),
    Input('Sub-Category', "value"),
    Input('Notes', "value"),
)
def temp_message(Date, Store, Description, Account, Amount, Category, Sub_Category, Notes):
    dateStr = 'None'
    if Date is not None:
        date_object = datetime.strptime(Date, "%Y-%m-%d")
        dateStr = date_object.strftime('%B %d, %Y')
    return html.P([
        f'Date: {dateStr}',
        html.Br(),
        f'Store: {Store}',
        html.Br(),
        f'Description: {Description}',
        html.Br(),
        f'Account: {Account}',
        html.Br(),
        f'Amount: {Amount}',
        html.Br(),
        f'Category: {Category}',
        html.Br(),
        f'Sub-Category: {Sub_Category}',
        html.Br(),
        f'Notes: {Notes}'
    ])

@app.callback(
    Output('AddedSoFar', 'children'),
    Input('Add', 'n_clicks'),
    State('Date', "date"),
    State('Store', "value"),
    State('Description', "value"),
    State('Account', "value"),
    State('Amount', "value"),
    State('Category', "value"),
    State('Sub-Category', "value"),
    State('Notes', "value")
)
def add(Add, Date, Store, Description, Account, Amount, Category, Sub_Category, Notes):
    if Add is not None:
        newRow = {
            'Date': datetime.strptime(Date, "%Y-%m-%d").strftime('%d-%b-%C'),
            'Store': Store,
            'Description': Description,
            'Account': Account,
            'Amount': Amount,
            'Category': Category,
            'Subcategory': Sub_Category,
            'Notes': Notes,
        }
        new.append(newRow)
        return f'Added {len(new)} rows so far {newRow}'
    else:
        return f'No new rows yet'

@app.callback(
    Output('WriteStatus', 'children'),
    Output('Totals', 'children'),
    Input('Write', 'n_clicks')
)
def write(Write):
    if Write is None:
        return ('Have not written to disk yet', '')
    else:
        global transactionsDf
        transactionsDf = transactionsDf.append(new, ignore_index=True, sort=False)
        transactionsDf.to_csv('data.csv', index=False)
        new.clear()

        totalStrs = []
        for account in sorted(map(lambda x: x['label'], accountOptions)):
            accountTransactions = transactionsDf[transactionsDf['Account'] == account]
            totalStrs.append(f'{account}: {round(sum(accountTransactions["Amount"]), 2)}')
            totalStrs.append(html.Br())
        return ('Written to disk', html.P(totalStrs))

if __name__ == "__main__":

    app.run_server(debug=True)
