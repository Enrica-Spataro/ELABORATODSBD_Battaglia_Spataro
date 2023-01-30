import sys

import prometheus_api_client.exceptions
from flask import Flask
from prometheus_api_client import PrometheusConnect, MetricsList, MetricRangeDataFrame
from datetime import timedelta
from prometheus_api_client.utils import parse_datetime
import pandas as pd
import xlsxwriter
import json
from confluent_kafka import Producer
import time
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
import random

app = Flask(__name__)

try:
    prom = PrometheusConnect(url="http://15.160.61.227:29090/", disable_ssl=True)
except prometheus_api_client.exceptions.PrometheusApiClientException as e:
    sys.exit("\nError: Connection to Prometheus failed or data not fetched")


def setting_parameters(metric_name, label_config, start_time_metadata, end_time, chunk_size):
    start = time.time()
    metric_data = prom.get_metric_range_data(
        metric_name=metric_name,
        label_config=label_config,
        start_time=start_time_metadata,
        end_time=end_time,
        chunk_size=chunk_size,
    )
    end = time.time()
    return metric_data, (end - start)


def creating_file_csv(metric_name, metric_object_list):
    # scriviamo il timestamp ed il value in un file csv
    xlxsname = metric_name + str('.xlsx')
    csvname = metric_name + str('.csv')

    workbook = xlsxwriter.Workbook(xlxsname)
    worksheet = workbook.add_worksheet()
    row = 0
    col = 0
    format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss.ms'})

    for item in metric_object_list.metric_values.ds:
        worksheet.write(row, col, item, format)
        row += 1

    row = 0

    for item in metric_object_list.metric_values.y:
        worksheet.write(row, col + 1, item)
        row += 1

    workbook.close()

    read_file = pd.read_excel(xlxsname)
    read_file.to_csv(csvname, index=None)

    return


# this function is used to set the parameters of the kafka producer and to create the message to be sent with the topic "prometheusdata"
def kakfaJsonProducer(fileJson, key):
    broker = "kafka:29092"
    topic = "promethuesdata"
    conf = {'bootstrap.servers': broker}
    p = Producer(**conf)

    def delivery_callback(err, msg):
        if err:
            sys.stderr.write('%% Message failed delivery: %s\n' % err)
        else:
            sys.stderr.write('%% Message delivered to %s [%d] @ %d\n' %
                             (msg.topic(), msg.partition(), msg.offset()))

    try:
        record_key = key
        record_value = json.dumps(fileJson)
        print("Producing record: {}\t{}".format(record_key, record_value))
        p.produce(topic, key=record_key, value=record_value, callback=delivery_callback)

    except BufferError:
        sys.stderr.write('%% Local producer queue is full (%d messages awaiting delivery): try again\n' %
                         len(p))
    p.poll(0)
    sys.stderr.write('%% Waiting for %d deliveries\n,' % len(p))
    p.flush()


# this function is used to calculate the max, min, avg, dev_std value of the metric for 1h, 3h, 12h;
def calculate_values(metric_name, metric_df, start_time):
    file_json[str(metric_name + "," + str(start_time))] = {"max": metric_df['value'].max(),
                                                           "min": metric_df['value'].min(),
                                                           "avg": metric_df['value'].mean(),
                                                           "std": metric_df['value'].std()}
    return file_json


def stationarity(values):

    stationarityTest = adfuller(values, autolag='AIC')

    if stationarityTest[1] <= 0.05:
        result = 'stationary series'
    else:
        result = 'no stationary series'

    return result


def seasonal(values):
    result_seasonal = seasonal_decompose(values, model='additive', period=5)
    serializable_result = {str(k): v for k, v in result_seasonal.seasonal.to_dict().items()}

    return serializable_result


def autocorrelation(values):
    lags = len(values)
    result = 'non autocorrelated series'
    result_autocorr = sm.tsa.acf(values, nlags=lags-1).tolist()
    for lag in result_autocorr:
        if lag <= 0.05:
            result = 'autocorrelated series'

    return result


def predict(metric_df):
    data = metric_df.resample(rule='10s').mean(numeric_only='True')

    tsmodel = ExponentialSmoothing(data.dropna(), trend='add', seasonal='add',
                                   seasonal_periods=5).fit()
    prediction = tsmodel.forecast(10)
    dictPred = {"max": prediction.max(), "min": prediction.min(), "avg": prediction.mean()}

    return dictPred


def valuesCalc(metric_df):
    dictValues = {"autocorrelazione": autocorrelation(metric_df['value']),
                  "stazionarietà": stationarity(metric_df['value']),
                  "stagionalità": seasonal(metric_df['value'])}

    return dictValues


def choose_metrics():
    metric_names = []
    not_zero_metrics = []
    metric_number = 5

    metric_data = prom.get_metric_range_data(
        metric_name='',
        label_config={'job': 'ceph-metrics'}
    )
    for metric in metric_data:
        for first_value, second_value in metric["values"]:
            if second_value != '0' and metric["metric"]["__name__"] not in not_zero_metrics:
                    not_zero_metrics.append(metric["metric"]["__name__"])

    print(len(not_zero_metrics))
    for k in range(0, metric_number):
        metric_names.append(not_zero_metrics[random.randint(0, len(not_zero_metrics))])

    return metric_names


@app.get('/monitoring_system_metadata')
def monitoring_system():
    return diff_metadata


@app.get('/monitoring_system_values')
def monitoring_system2():
    return time_values


if __name__ == "__main__":
    file_json = {}
    time_values = {}
    diff_metadata = {}
    result = {}
    result_predict = {}
    metric_name = choose_metrics()
    predict_metric_name = ['ceph_bluestore_read_lat_sum', 'available',
                   'ceph_bluefs_bytes_written_wal', 'ceph_bluefs_db_used_bytes', 'ceph_cluster_total_used_bytes']

    label_config = {'job': 'ceph-metrics'}
    start_time = ["1h", "3h", "12h"]
    start_time_metadata = parse_datetime("24h")

    end_time = parse_datetime("now")
    chunk_size = timedelta(minutes=1)
    print("Parametri impostati\n")

    for name in range(0, len(metric_name)):
        metric_data, diff_meta = setting_parameters(metric_name[name], label_config, start_time_metadata, end_time,
                                                    chunk_size)
        diff_metadata[metric_name[name]] = {"time metadata: ": str(diff_meta) + " s"}
        metric_object_list = MetricsList(metric_data)
        metric_df = MetricRangeDataFrame(metric_data)
        # creating_file_csv(metric_name[name], metric_object_list[0])
        result[metric_name[name]] = valuesCalc(metric_df)

    kakfaJsonProducer(result, 'etl#1')

    for name in range(0, len(metric_name)):
        for h in range(0, len(start_time)):
            print(metric_name[name],':',str(start_time[h]))
            metric_data, diff_values = setting_parameters(metric_name[name], label_config,
                                                          parse_datetime(start_time[h]), end_time,
                                                          chunk_size)
            time_values[metric_name[name] + "," + start_time[h]] = {start_time[h]: str(diff_values) + " s"}
            metric_object_list = MetricsList(metric_data)
            metric_df = MetricRangeDataFrame(metric_data)
            file_json = calculate_values(metric_name[name], metric_df, start_time[h])
    
    kakfaJsonProducer(file_json, 'etl#2')

    for name in range(0, len(predict_metric_name)):
        print(predict_metric_name[name])
        metric_data, diff_meta = setting_parameters(predict_metric_name[name], label_config, start_time_metadata,
                                                    end_time,
                                                    chunk_size)
        metric_df = MetricRangeDataFrame(metric_data)
        result_predict[predict_metric_name[name]] = predict(metric_df)

    kakfaJsonProducer(result_predict, 'etl#3')

    monitoring_system()
    monitoring_system2()
    app.run(host='0.0.0.0', port=5000, debug=False)




