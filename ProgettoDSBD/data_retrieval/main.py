from flask import Flask
from prometheus_api_client import PrometheusConnect
import mysql.connector
import sys

# mysql connection
mydb = mysql.connector.connect(
    host="db",
    user="root",
    password="asdf.VHjI.313",
    database='datastorage'
)

mycursor = mydb.cursor()


app = Flask(__name__)


@app.get('/metrics')
def get_values_metrics():
    sql = """SELECT * from metrics;"""
    mycursor.execute(sql)
    fileJson_metrics = {}
    list_metrics = []
    y = 0
    for x in mycursor:
        list_metrics.append(x)
        max_metric = list_metrics[y][1]
        min_metric = list_metrics[y][2]
        avg_metric = list_metrics[y][3]
        std_metric = list_metrics[y][4]
        fileJson_metrics[list_metrics[y][0]] = {"max": max_metric,
                                                "min": min_metric,
                                                "avg": avg_metric,
                                                "std": std_metric}
        y = y + 1
    return fileJson_metrics


@app.get('/metadata')
def get_values_metadata():
    sql = """SELECT * from metadata;"""
    mycursor.execute(sql)
    fileJson_metrics = {}
    list_metrics = []
    y = 0
    for x in mycursor:
        list_metrics.append(x)
        autocorrelation = list_metrics[y][1]
        stazionarity = list_metrics[y][2]
        seasonality = list_metrics[y][3]
        fileJson_metrics[list_metrics[y][0]] = {"autocorrelazione": autocorrelation,
                                                "stazionarietà": stazionarity,
                                                "stagionalità": seasonality}
        y = y + 1
    return fileJson_metrics


@app.get('/prediction')
def get_values_predict():
    sql = """SELECT * from prediction;"""
    mycursor.execute(sql)
    fileJson_metrics = {}
    list_metrics = []
    y = 0
    for x in mycursor:
        list_metrics.append(x)
        max_metric = list_metrics[y][1]
        min_metric = list_metrics[y][2]
        avg_metric = list_metrics[y][3]
        fileJson_metrics[list_metrics[y][0]] = {"max": max_metric, "min": min_metric, "avg": avg_metric}
        y = y + 1
    return fileJson_metrics


@app.get('/all_metrics')
def get_all_metrics():
    sql = """SELECT * from metadata;"""
    mycursor.execute(sql)
    all_metrics = {}
    list_metrics = []
    y = 0
    for x in mycursor:
        list_metrics.append(x)
        all_metrics[y] = list_metrics[y][0]
        y = y + 1

    return all_metrics


if __name__ == "__main__":
    print("\n*** Hello from DATA RETRIEVAL ***")

    app.run(host='0.0.0.0',port=5002, debug=False)

