# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, jsonify
import pandas.io.sql as sql
import sqlite3
import platform
import datetime
import numpy as np
import pandas as pd
import json
import pygal
import matplotlib.pyplot as plt
from scipy.stats import norm
from bokeh.charts import Histogram
import plotly

from pandas.io.data import DataReader
from sklearn.linear_model import LogisticRegression
from sklearn.lda import LDA
from sklearn.qda import QDA

from bokeh.layouts import gridplot
from bokeh.plotting import figure, show, output_file


######
# USEFULL CODE FOR MIGRATING FROM WINDOWS to LINUX (example to PYTHONANYWHERE) - START
######
is_windows = any(platform.win32_ver())
if is_windows:
    print "windows"
    FULLPATH ="C:\\API_WEB__FLASK_BOOTSTRAP_FINANCIAL_ANALYTICS\\"
else:
    print "linux"
    FULLPATH ='/home/Iv36/API_WEB__FLASK_BOOTSTRAP_FINANCIAL_ANALYTICS/'

######
# USEFULL CODE FOR MIGRATING FROM WINDOWS to LINUX (PYTHONANYWHERE) - END
######


######
# DATABASE - START, here it is only used for user data, but it can be used for anything.
######
connres = sqlite3.connect('./configuration.db', check_same_thread=False)
cursorres = connres.cursor()
cursorres.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, coursekeyword TEXT, name TEXT, email TEXT, username TEXT, password TEXT)''')
connres.commit()
######
# DATABASE - END
######


######
# GLOBAL VARIABLE FOR SESSION - START
######
USER_SESSION = {}
USER_SESSION["USER"]= "none"
######
# GLOBAL VARIABLE FOR SESSION - END
######


######
# FLASK - START
######
app = Flask(__name__) # instancing the Flask object

#In Windows use "localhost" in your browser, what is equivalent to http://localhost:80/, which is also equivalent to http://127.0.0.1:80/
# http means your data will be tranfered using Hypertext Transfer Protocol, most commonly used over the internet
# localhost is a domain name system (DNS) which is equivalent to say 127.0.0.1, in other word "localhost" resolves to 127.0.0.1
# 80, means you will use the internet default port

#In pythonanywhere we will use http://<YOUR USER>.pythonanywhere.com, my one for the viedo is: http://rating.pythonanywhere.com



#Setting a route for python function called index, / is equivalent to "no route"
#This route is is widelly as Index or Home Page.
#@app.route('/') is equivalent to @app.route('/', methods=['GET', 'POST']), meaning GET and POST methods are allowed.
@app.route('/')
def index():
    return render_template('index.html',userlogged="Hello visitor ;-), you are current not logged in. Hola visitante, no te encuentras logeado.")

#Setting a route for python function called user(), now http://localhost:80/user (OR http://<YOUR USER>.pythonanywhere.com/user) will call this python function
#For simplicity, GET means that only URL like calls are allowed.
@app.route('/users', methods=['GET'])
def users():
    userdata = sql.read_sql('select * from users', connres)
    return userdata.to_json()



#Setting a route for python function called createuser(), now http://localhost:80/createuser (OR http://<YOUR USER>.pythonanywhere.com/createuser) will call this python function
# POST means it can only be called by a "form", for simplicity, it means web page form or a software must call this function, and calling it directly in the browser like "http://localhost:80/createuser" will not work because it is not allowed.
@app.route('/createuser', methods=['POST'])
def createuser():
    global USER_SESSION, connres, cursorres
#    print request.form#['name']
    if request.form['coursekeyword'] in ['BIGDATA', 'BIG DATA']:
        try:

#            print "CREATE USER 0.1"
            df_users = sql.read_sql("select username from users", connres)
#            print "CREATE USER 0.2"
            if sum(df_users['username'] == request.form['username']) == 0:
#                print "CREATE USER 1.0 - NEW USER!"
                cursorres.execute('INSERT INTO users (id, coursekeyword, name, email, username, password) VALUES (NULL,?,?,?,?,?)', [request.form['coursekeyword'],request.form['name'],request.form['email'],request.form['username'],request.form['password']])
                connres.commit()
                USER_SESSION["USER"] = request.form['username']
                return render_template('index.html',userlogged="Dear " + request.form['username'] +" your user has been created sucessfully. Now please click LOG IN above to have access to the entire web site content.")
            else:
                return render_template('index.html',userlogged="USER NOT CREATED! Sorry, the username = '" + request.form['username'] +"' is already in use, please choose a different one.")

        except:
            return render_template('index.html',userlogged="AN ERROR HAS OCURRED, USER HAS NOT BEEN CREATED! Please try again!")
    else:
        return render_template('index.html',userlogged="USER NOT CREATED! Sorry, you have included the wrong COURSEKEYWORD, please try again using the correct one.")



############################################################################
#         SETTIING UP SECURITY -EVERY REQUEST BELOW NEEDS PASSWORD - START #
############################################################################
from flask.ext.httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_pw(username, password):
    global USER_SESSION, connres
    USER_SESSION["USER"]= username
    USER_SESSION["PWD"] = password
    try:
        realpassword = str(sql.read_sql("select password from users WHERE username = '"+str(username)+"'", connres)["password"][0])
#        print "realpassword=",realpassword
        USER_SESSION["PWD_VALID"] = realpassword
        if password == realpassword:
                return realpassword
    except:
#        print "users does not exist!"
        return None

@app.route('/login')
@auth.login_required
def login():
#    userdata = sql.read_sql('select * from users', connres)
#    print userdata
    return render_template('index.html',userlogged="Welcome " + USER_SESSION["USER"] + ", you are now logged in.")


@app.route('/userslogged', methods=['GET','POST'])
@auth.login_required
def userslogged():
    userdata = sql.read_sql('select * from users', connres)
    return userdata.to_json()

############################################################################
#         SETTIING UP SECURITY -EVERY REQUEST BELOW NEEDS PASSWORD - END   #
############################################################################


############################################################################
#         USEFULL FUCTIONS FOR TIMESERIES PREDICTIONS - START              #
############################################################################
# SOURCE: http://www.quantstart.com/articles/Forecasting-Financial-Time-Series-Part-1
def create_lagged_series(symbol, start_date, end_date, lags=50,outcome_period=5):
    """This creates a pandas DataFrame that stores the percentage returns of the
    adjusted closing value of a stock obtained from Yahoo Finance, along with
    a number of lagged returns from the prior trading days (lags defaults to 5 days).
    Trading volume, as well as the Direction from the previous day, are also included."""

    # Obtain stock information from Yahoo Finance
#    symbol = "tef.mc"
    ts = DataReader(symbol, "google", start_date-datetime.timedelta(days=2*(lags+outcome_period)), end_date)

    # Create the new lagged DataFrame
    tslag = pd.DataFrame(index=ts.index)
    tslag["Today"] = ts["Close"]
    tslag["Volume"] = ts["Volume"]

    # Create the shifted lag series of prior trading period close values
    for i in xrange(0,lags):
        tslag["Lag%s" % str(i+1)] = ts["Close"].shift(i+1)

    # Create the returns DataFrame
    tsret = pd.DataFrame(index=tslag.index)
    tsret["Volume"] = tslag["Volume"]
    tsret["Today"] = tslag["Today"].pct_change()*100.0

    # If any of the values of percentage returns equal zero, set them to
    # a small number (stops issues with QDA model in scikit-learn)
    for i,x in enumerate(tsret["Today"]):
        if (abs(x) < 0.0001):
            tsret["Today"][i] = 0.0001

    # Create the lagged percentage returns columns
    for i in xrange(0,lags):
        tsret["Lag%s" % str(i+1)] = tslag["Lag%s" % str(i+1)].pct_change()*100.0

    # Create the "Direction" column (+1 or -1) indicating an up/down day
#    tsret["Direction"] = np.sign(tstsret["Today"]))

    tsret["Direction"] = np.sign(ts["Close"] - ts["Close"].shift(outcome_period))

    tsret = tsret[tsret.index >= start_date]
    return tsret

def fit_model(name, model, X_train, y_train, X_test, X_last, pred, pred_last):
    """Fits a classification model (for our purposes this is LR, LDA and QDA)
    using the training data, then makes a prediction and subsequent "hit rate"
    for the test data."""

    # Fit and predict the model on the training, and then test, data
    model.fit(X_train, y_train)
    pred[name] = model.predict(X_test)
    pred_last[name] = model.predict(X_last)

    # Create a series with 1 being correct direction, 0 being wrong
    # and then calculate the hit rate based on the actual direction
    pred["%s_Correct" % name] = (1.0+pred[name]*pred["Actual"])/2.0
    hit_rate = np.mean(pred["%s_Correct" % name])
    print "%s: %.3f" % (name, hit_rate)
    return hit_rate

############################################################################
#         USEFULL FUCTIONS FOR TIMESERIES PREDICTIONS - END                #
############################################################################



############################################################################
#         PREDICTING  Stock Price  - START                                 #
#  - setting up PREDICTION route:                                          #
#  Example of how to make the request in the browser:                      #
#  http://<youruser>.pythonanywhere.com/api/v1/prediction/15/san.mc        #
#  http://ciff.pythonanywhere.com/api/v1/prediction/15/GOOG              #
############################################################################
@app.route('/api/v1/prediction/<period>/<ticker>', methods=['GET', 'POST'])
@auth.login_required
def prediction(period,ticker):
#    global models

    results =  {"TICKER":'ticker no found',"predictedprice5daysfromnow":'',"myactionrecommendaction":''}


    try:
#    ticker = "pop.mc"
#    ticker = "tef.mc"
        results =  {"TICKER":ticker,"PREDICTION_FINAL_TXT": "Error: no he podido predecir que va a pasar con la accion "+ticker}

        historical_period_in_days = 365*2
        start_date = datetime.datetime.today()-datetime.timedelta(days=historical_period_in_days)
        end_date = datetime.datetime.today()
        start_test = datetime.datetime.today()-datetime.timedelta(days=int(historical_period_in_days/2))
        n_lags=50
        n_outcome_period=int(period)
        snpret = create_lagged_series(ticker, start_date, end_date, lags=n_lags, outcome_period=n_outcome_period)


        # Drop 4 previous days, to use the prior days (from 5...to the past) of returns as predictor values, with direction as the response
        X = snpret.drop(['Volume','Today','Lag1','Lag2','Lag3','Lag4'], axis=1)
        y = snpret["Direction"]

        #
        X_last = snpret.tail(1)
#        print X_last
        for i in range(n_lags,n_outcome_period,-1):
            X_last["Lag%s" % str(i)] = X_last["Lag%s" % str(i-n_outcome_period)]
#        print X_last
        X_last = X_last.drop(['Volume','Today','Lag1','Lag2','Lag3','Lag4'], axis=1)

        # The test data is split into two parts: Before and after 1st Jan 2005.

        # Create training and test sets
        X_train = X[X.index < start_test]
        X_test = X[X.index >= start_test]
        y_train = y[y.index < start_test]
        y_test = y[y.index >= start_test]

        # Create prediction DataFrame
        pred = pd.DataFrame(index=y_test.index)
        pred["Actual"] = y_test

        pred_last = pd.DataFrame(index=X_last.index)

        # Create and fit the three models
#        print "Hit Rates:"
        models = [("LR - Logistic Regression", LogisticRegression()), ("LDA - Linear Discriminant Analysis", LDA()), ("QDA - Quadratic Discriminant Analysis", QDA())]

        results["PREDICTION_FINAL_NUM"]  = 0
        for m in models:
            try:
                print "1.0"
                results["MODEL_"+m[0]]=fit_model(m[0], m[1], X_train, y_train, X_test, X_last, pred, pred_last)
                if results["MODEL_"+m[0]] != -1.0:
                    print "1.1"
                    results["PREDICTION_MODEL_"+m[0]] = pred_last[m[0]][0]
                    print "1.2"
                    results["PREDICTION_FINAL_NUM"] += pred_last[m[0]][0]
                    print "1.3"
                else:
                    results["PREDICTION_MODEL_"+m[0]] = 0
            except:
                results["PREDICTION_MODEL_"+m[0]] = 0

        print "2.0"
        if results["PREDICTION_FINAL_NUM"] > 0:
            results["PREDICTION_FINAL_TXT"] = "La accion "+str(ticker)+ " va subir en los proximo "+ str(n_outcome_period) +" dias"
        else:
            results["PREDICTION_FINAL_TXT"] = "La accion "+str(ticker)+ " va bajar en los proximo "+ str(n_outcome_period) +" dias"
        print "3.0"

    except:
        print "ERROR!"
    return jsonify(results)

############################################################################
#         PREDICTING  Stock Price - END                                    #
############################################################################



############################################################################
#         Creating graphs  - START                                         #
#  - setting up PREDICTION route:                                          #
#  Example of how to make the request in the browser:                      #
#  http://<youruser>.pythonanywhere.com/api/v1/grafica/san.mc              #
#  http://ciff.pythonanywhere.com/api/v1/grafica/GOOG                      #
############################################################################
@app.route('/api/v1/grafica/<shortticker>', methods=['GET', 'POST'])
@auth.login_required
def grafica(shortticker):
    def datetime(x):
        return np.array(x, dtype=np.datetime64)

    symbol = shortticker#"GOOG"
    df = DataReader(symbol, "google", '01/01/2016', '08/03/2017')
    df['date'] = df.index


    p1 = figure(x_axis_type="datetime", title="Stock Closing Prices")
    p1.grid.grid_line_alpha=0.3
    p1.xaxis.axis_label = 'Date'
    p1.yaxis.axis_label = 'Price'

    p1.line(datetime(df['date']), df['Close'], color='#A6CEE3', legend=symbol)
    #p1.line(datetime(GOOG['date']), GOOG['adj_close'], color='#B2DF8A', legend='GOOG')
    #p1.line(datetime(IBM['date']), IBM['adj_close'], color='#33A02C', legend='IBM')
    #p1.line(datetime(MSFT['date']), MSFT['adj_close'], color='#FB9A99', legend='MSFT')
    #p1.legend.location = "top_left"

    df_array = np.array(df['Close'])
    df_dates = np.array(df['date'], dtype=np.datetime64)

    window_size = 30
    window = np.ones(window_size)/float(window_size)
    aapl_avg = np.convolve(df_array, window, 'same')

    p2 = figure(x_axis_type="datetime", title="One-Month Average")
    p2.grid.grid_line_alpha = 0
    p2.xaxis.axis_label = 'Date'
    p2.yaxis.axis_label = 'Price'
    p2.ygrid.band_fill_color = "olive"
    p2.ygrid.band_fill_alpha = 0.1

    p2.circle(df_dates, df_array, size=4, legend='close',
              color='darkgrey', alpha=0.2)

    p2.line(df_dates, aapl_avg, legend='avg', color='navy')
    p2.legend.location = "top_left"

    output_file("./templates/stocks.html", title="My Own Bokeh Example")
    show(gridplot([[p1,p2]], plot_width=400, plot_height=400))  # open a browser
    return render_template('stocks.html')

############################################################################
#         Creating graphs  - END                                           #
############################################################################
@app.route('/api/v1/oportunidaddesubida/<ndiasmaximo>/<ticker>', methods=['GET', 'POST'])
@auth.login_required
def oportunidaddesubida(ndiasmaximo,ticker):

    historical_period_in_days = 365
    start_date = datetime.datetime.today() - datetime.timedelta(days=historical_period_in_days)
    end_date = datetime.datetime.today()

    lags = int(ndiasmaximo)
    outcome_period = 5


    ts = DataReader(ticker, "google", start_date-datetime.timedelta(days=2*(lags+outcome_period)), end_date)


    tslag = pd.DataFrame(index=ts.index)
    tslag = ts[['Low', 'High']]

    tslag=tslag.sort_index(axis=0, ascending=False)
    for i in xrange(0,lags):
        tslag["lag%s" % str(i+1)] = (tslag["High"] - tslag["Low"].shift(-(i+1)))/tslag["Low"].shift(-(i+1))
    tslag = tslag[(tslag.index >= start_date) & (tslag.index<=end_date)]
    result = {}
    for item in (tslag.index):
        result[str(item).split('T')[0]]=list(tslag.ix[item,2:].values)
    result2 = {}
    valores = []
    for item in result.keys():
        for j in range(lags):
            valores.append(result[item][j])
    result2['diferencias'] = valores

    rango = {}
    interval = [-0.1, -0.07, -0.05, -0.02, 0.0, 0.02, 0.05, 0.07, 0.1]
    for i in range(len(interval)+1):
        rango[str(i+1)] = []
    for i in range(len(valores)):
        if valores[i]<= -0.10:
            rango['1'].append(valores[i])
        if (valores[i] > -0.10) & (valores[i] <= -0.07):
            rango['2'].append(valores[i])
        if (valores[i] > -0.07) & (valores[i] <= -0.05):
            rango['3'].append(valores[i])
        if (valores[i] > -0.05) & (valores[i] <= -0.02):
            rango['4'].append(valores[i])
        if (valores[i] > -0.02) & (valores[i] <= 0.00):
            rango['5'].append(valores[i])
        if (valores[i] > 0.00) & (valores[i] <= 0.02):
            rango['6'].append(valores[i])
        if (valores[i] > 0.02) & (valores[i] <= 0.05):
            rango['7'].append(valores[i])
        if (valores[i] > 0.05) & (valores[i] <= 0.07):
            rango['8'].append(valores[i])
        if (valores[i] > 0.07) & (valores[i] <= 0.10):
            rango['9'].append(valores[i])
        if (valores[i] > 0.10):
            rango['10'].append(valores[i])

    rangos = []
    percen = {}
    percen['rango'] = 'x < -10%'
    try:
        percen['percentual'] = (round((float(len(rango['1']))/len(valores)),4))
    except:
        percen['percentual'] = (0.0)
    rangos.append(percen)

    for i in range(1,len(interval),1):
        percen = {}
        percen['rango'] = str(interval[i-1]*10)+'% ' + '<= x < ' + str(interval[i]*10)+ '%'
        percen['percentual'] = (round((float(len(rango['%s' %(i+1)]))/len(valores)),4))
        rangos.append(percen)

    percen = {}
    percen['rango'] = 'x > 10%'
    try:
        percen['percentual'] = (round((float(len(rango['10']))/len(valores)),4))
    except:
        percen['percentual'] = (0.0)
    rangos.append(percen)
    per = {}
    per['rangos'] = rangos
    return json.dumps(per)


@app.route('/api/v1/var/<p>/<c>/<ticker>', methods=['GET', 'POST'])
@auth.login_required
def var(p,c,ticker):

    def var_cov_var(P, c, mu, sigma):

        alpha = norm.ppf(1-c, mu, sigma)
        return P - P*(alpha + 1)

    #if __name__ == "__main__":
    historical_period_in_days = 365*7
    start = datetime.datetime.today() - datetime.timedelta(days=historical_period_in_days)
    end = datetime.datetime.today()

    citi = DataReader(ticker, "google", start, end)
    citi["rets"] = citi["Close"].pct_change()

    P = float(p)
    c = float(c)
    mu = np.mean(citi["rets"])
    sigma = np.std(citi["rets"])

    varianza = var_cov_var(P, c, mu, sigma)

    var1= {}
    var1['Value-at-Risk'] = "$%0.2f" % varianza
    return jsonify (var1)

###############################################################################################################
#         INFINITY LOOP LISTENING TO PORT 80 (port=int("80")) TO THE OUTSIDE WORLD (host="0.0.0.0") - START   #
###############################################################################################################
if __name__ == '__main__':
    app.run(
	host="0.0.0.0",
        port=int("80")
#        ,	processes=9
#        debug=True
    )
###############################################################################################################
#         INFINITY LOOP LISTENING TO PORT 80 (port=int("80")) TO THE OUTSIDE WORLD (host="0.0.0.0") - END     #
###############################################################################################################


