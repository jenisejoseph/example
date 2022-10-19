import requests
import math
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import yfinance as yf
import numpy as np
import dash_bootstrap_components as dbc
import dash_auth
from datetime import datetime
today=datetime.now()
today_str=today.strftime('%Y-%m-%d')


tickers=pd.read_csv('capcushSymbolList.csv')
tickers.set_index('Symbol',inplace=True)
symbols=[]
for tic in tickers.index:
    mydict={}
    mydict['label']=tic+' ('+tickers.loc[tic]['Name']+')' #SPY (SPDR S&P 500 ETF Trust)
    mydict['value']=tic
    symbols.append(mydict)

strats=pd.read_csv('capcushStrategyList.csv')
strats.set_index('Strategy',inplace=True)
strategies=[]
for s in strats.index:
    mydict={}
    mydict['label']=strats.loc[s]['Name'] #Cap & Cushion 10% Buffer
    mydict['value']=s
    strategies.append(mydict)

exps=pd.read_csv('capcushAppExpirations.csv')

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                meta_tags=[{'name': 'viewport',
                            'content': 'width=device-width, initial-scale=1.0'}]
                )

controls = [
    # dbc.CardImg(
    #                     src="https://jgarden79.github.io/PM_vis/NewLidoLogo@300x.png",
    #                     top=True,
    #                     style={"width": "12rem"},
    #                 ),

    dbc.Card(
    [
        html.Div(
            [
                dbc.Label("Select Underlying Asset (e.g. SPY, QQQ, etc.)"),
                dcc.Dropdown(
                    id="symbol_picker",
                        options=symbols,
                        value='SPY',#sets a default value
                        multi=False,
                ),
            ]
        ),
        html.Div(
            [
                dbc.Label("Select Strategy:"),
                dcc.Dropdown(
                    id="strategy_picker",
                            options=strategies,
                            value='capcush_9',#sets a default value
                            multi=False,
                ),
            ]
        ),
        html.Div(
            [
                dbc.Label("Select Expiration"),
                dcc.Dropdown(id="expiry_picker",
                            options=[],
                            value='2023-03-17',#sets a default value
                            multi=False,
                ),
            ]
        ),
        html.Div(
            [
                dbc.Label("Enter Bond Asset YTM", html_for="bond_rate"),
                dbc.Input(id="bond_rate",
                          placeholder='Enter YTM',
                          value=2.04),
                dbc.FormText("e.g. 2.29",
                color="secondary",
                ),
            ]
        ),
        html.Div(
            [
                dbc.Button("Submit",
                            id='submit_button',
                            color="success",
                            n_clicks=0,
                ),
            ]
        ),
    ],
    body=True,
)
]
app.layout = dbc.Container(
    [
        html.H1(
                dbc.Row([
                        dbc.Col(html.Img(src="https://jgarden79.github.io/PM_vis/NewLidoLogo@300x.png",height='50px'),width=3),
                        dbc.Col("Defined Outcome Strategies",width=5)])),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(controls, md=3),
                dbc.Col(dcc.Graph(id='my_graph',
                                 figure={'data':[{'x':np.arange(0,5,1),
                                                 'y':np.arange(-1,1,0.25)}],
                                                 'layout':{'title':'Default Title',
                                                 'xaxis':{'title':'<b>Price at Expiration<b>'},
                                                 'yaxis':dict(title='<b>Return at Expiration<b>',tickformat=',.0%'),
                                                 'hovermode':'closest'}
                                        }
                                )
                        ),
                # dbc.Col(dash_table.DataTable([{'{} Return'.format('ticker'):0,'Strategy Return':0}],id='tbl_1'),md=2,),
            ],
            align="center",
        ),
       html.Hr(),
       dbc.Row(
            [
                # dbc.Col('This is a test column.',align='center'),
                dbc.Col(dash_table.DataTable([{'{} Return'.format('ticker'):0,'Strategy Return':0}],id='tbl_2'),md=3,
                        ),

            ],
            align='center'
       ),
    ],
    fluid=True,
)

@app.callback(
     Output('expiry_picker','options'),
     Input('symbol_picker','value')
 )

def set_expirations(chosen_symbol):
    dff=exps[exps['Symbol']==chosen_symbol]
    return [{'label':e,'value':e} for e in dff['Expiration'].unique()]

@app.callback(Output('my_graph','figure'),
                 Input('submit_button','n_clicks'),
                 [State('symbol_picker','value'),
                 State('strategy_picker','value'),
                 State('expiry_picker','value'),
                 State('bond_rate','value')
                 ])

def update_graph(n_clicks,ticker,strat_type,expiry,rate):

     #Function to extract and organize options data
     def get_options_chain(ticker,expiry):
         #access Tradier Developer Sandbox API, extract options chain, organize data into Calls and Puts
         response = requests.get(options_url,
             params={'symbol':ticker,
                     'expiration':expiry,
                     'greeks': 'true'},
             headers={'Authorization':ACCESS_TOKEN, 'Accept': 'application/json'})

         raw_data = response.json()
         chain_df=pd.DataFrame(raw_data['options']['option'])
         chain_df['mid']=(chain_df['bid']+chain_df['ask']).div(2)
         #expand 'Greeks' columns from dictionary to indivdual columns
         delta=chain_df['greeks'].apply(pd.Series)['delta']
         iv=chain_df['greeks'].apply(pd.Series)['mid_iv']
         #set columns for 'prices' DF
         columns=['symbol','underlying','expiration_date','strike','close','bid','ask','mid',
                  'volume','open_interest','average_volume',
                  'expiration_type','option_type','trade_date']

         prices=pd.concat([chain_df[columns],delta,iv],axis=1)
         get_options_chain.calls=prices.loc[prices.option_type=='call']
         get_options_chain.puts=prices.loc[prices.option_type=='put']

     #Function to get last traded prices
     def get_last(ticker):
         #access Tradier Developer Sandbox API, extract options chain, organize data into Calls and Puts
         response = requests.get(quotes_url,
             params={'symbols': ticker, 'greeks': 'false'},
             headers={'Authorization': ACCESS_TOKEN, 'Accept': 'application/json'})
         quote_data = response.json()
         get_last.last=quote_data['quotes']['quote']['last']

     ##############################################
     API_BASE_URL='https://sandbox.tradier.com/v1/' #Developers Sandbox
     ACCESS_TOKEN=open(r'C:\Users\Jenise.Joseph\Desktop\PythonAppProj\TAPIT.txt').read()
     quotes_url='{}markets/quotes'.format(API_BASE_URL)
     options_url='{}markets/options/chains'.format(API_BASE_URL)
     expiry_url='{}markets/options/expirations'.format(API_BASE_URL)
     ##############################################

     if strat_type=='capcush_9':
         buffer_target=0.09
     elif strat_type=='capcush_15':
         buffer_target=0.15

     strat_name='{:.0%} Buffer'.format(buffer_target)

     get_options_chain(ticker,expiry)
     active_calls=get_options_chain.calls
     active_puts=get_options_chain.puts
     get_last(ticker)
     last=get_last.last

     #Calculate Long Call Strike & Premium
     atm=active_calls['strike'].iloc[np.argmin(np.abs((active_calls['strike']-last)))]
     long_call=active_calls['strike'].iloc[np.argmin(np.abs((active_calls['strike']-last)))]
     long_call_prem=active_calls['mid'].loc[active_calls['strike']==long_call].iloc[0]
     dlt_long_call=active_calls['delta'].loc[active_calls['strike']==long_call].iloc[0]

     #Calculate Short Put Strike for Desired Annual Buffer
     short_put=active_puts['strike'].iloc[np.argmin(np.abs((active_puts['strike']-(last*(1-buffer_target)))))]
     short_put_prem=active_puts['mid'].loc[active_puts['strike']==short_put].iloc[0]
     dlt_short_put=active_puts['delta'].loc[active_puts['strike']==short_put].iloc[0]
     short_put_pct=short_put/last

     biz_days=np.busday_count(today.strftime('%Y-%m-%d'),expiry)
     exp=datetime.strptime(expiry,'%Y-%m-%d')
     cal_days=(exp-today).days

     #Notional Value of Trade (last x $100)
     notional=last*100
     mgt_fee=0
     fee=notional*(mgt_fee/100)*(cal_days/365)

     bond_notional=notional

     #Caluclate Expected Interest Received from Bond Asset
     interest=(cal_days/365)*(rate/100)*bond_notional

     #Calculate Cost of Long ATM Call minus Short OTM Put
     call_tv=long_call_prem-(atm-long_call)
     rr_tv=(call_tv*100)-(short_put_prem*100)-interest

     #Calculate Strike Price for Short OTM Call, as well as Net Trade Cost
     short_call_prem=active_calls['mid'].iloc[np.argmin(np.abs((active_calls['mid']-(rr_tv/100))))]
     short_call=active_calls['strike'].loc[active_calls['mid']==short_call_prem].iloc[0]
     dlt_short_call=active_calls['delta'].loc[active_calls['mid']==short_call_prem].iloc[0]
     short_call_pct=short_call/last

     net_cost=long_call_prem-short_put_prem-short_call_prem
     net_delta=dlt_long_call-dlt_short_put-dlt_short_call

     loss_accept=(last-long_call)/last

     buffer=(short_put/last)-1
     cap=(short_call/last)-1
     # Function to calculate options payoffs at EXPIRY
     def call_payoff(stock_range,strike,premium):
         return np.where(stock_range>strike,stock_range-strike,0)-premium
     def put_payoff(stock_range,strike,premium):
         return np.where(stock_range<strike,strike-stock_range,0)-premium
     # Define stock price range at expiration and calculate individual leg payoffs
     up_dn=0.4
     stock_range=np.arange((1-up_dn)*last,(1+up_dn)*last,1)
     long_call_payoff=call_payoff(stock_range,long_call,long_call_prem)
     short_call_payoff=call_payoff(stock_range,short_call,short_call_prem)*-1
     short_put_payoff=put_payoff(stock_range,short_put,short_put_prem)*-1
     # Calculate Strategy Payoff
     strategy=(long_call_payoff+short_call_payoff+short_put_payoff+(interest/100))/last
     stock_ret=(stock_range/(last))-1

     ##############################################
     # Create DataFrame of stock prices from -50% to +50%, every 5%
     pct_range=np.arange(0-up_dn,0+up_dn+0.05,0.05)
     price_range=(pct_range+1)*last
     # Calculate payoffs for individual legs
     lc_payoff=call_payoff(price_range,long_call,long_call_prem)
     sc_payoff=call_payoff(price_range,short_call,short_call_prem)*-1
     sp_payoff=put_payoff(price_range,short_put,short_put_prem)*-1
     # Calculate Strategy Payoff
     strat=(lc_payoff+sc_payoff+sp_payoff+(interest/100))/last
     bh_ret=(price_range/(last))-1

     data=pd.DataFrame({'{} Return'.format(ticker):bh_ret,
                        'Strategy Return':strat}).sort_values(by='{} Return'.format(ticker),ascending=False)
     data.set_index('{} Return'.format(ticker),inplace=True)
     styled_data=data.style.format({'{} Return'.format(ticker): "{:.2%}",'Strategy Return': "{:.2%}"})
     ###############################################
     fig=go.Figure()
     fig.add_trace(go.Scatter(x=stock_range,
                         y=strategy,
                         mode='lines',
                         line=dict(color='green',width=4),
                         name='Strategy'))
     fig.add_trace(go.Scatter(x=stock_range,
                         y=stock_ret,
                         mode='lines',
                         line=dict(color='black',width=2,dash='dash'),
                         name=ticker))
     fig.add_hline(y=0,line_color='red')
     fig.add_vline(x=last,line_width=1,line_dash='dash',line_color='gray')
     fig.add_annotation(x=last,y=0.1,
                         text='Current price: <b>${:.2f}<b>'.format(last),
                         font=dict(size=12),
                         textangle=-90
                         )
     fig.update_layout(title=f'<b>{ticker} {strat_name} Strategy, Payoff Diagram at Expiration ({expiry})<b>',
                         xaxis=dict(title=f'<b>{ticker} Price at Expiration, {expiry}<b>',
                                     tickprefix='$',
                                     tickformat=',.'),
                         yaxis=dict(title='<b>Return at Expiration<b>',
                                     tickformat=',.0%',
                                     range=[0-up_dn,0+up_dn]),
                         hovermode='x unified',
                         legend=dict(
                             yanchor='top',y=0.99,
                             xanchor='left',x=0.01,
                             bordercolor='black',borderwidth=2,
                             font=dict(size=16)),
                         autosize=False,width=900,height=600#width=1120,height=640
                         )
     return fig

if __name__ == '__main__':
    app.run_server()
