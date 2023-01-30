from prometheus_api_client import MetricRangeDataFrame
from datetime import timedelta
from prometheus_api_client.utils import parse_datetime
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from flask import Flask
from prometheus_api_client import PrometheusConnect
import json

app = Flask(__name__)

prom = PrometheusConnect(url="http://15.160.61.227:29090", disable_ssl=True)


def setting_parameters(metric_name, label_config, start_time_metadata, end_time, chunk_size):
    metric_data = prom.get_metric_range_data(
        metric_name=metric_name,
        label_config=label_config,
        start_time=start_time_metadata,
        end_time=end_time,
        chunk_size=chunk_size,
    )
    return metric_data


@app.get('/sla_slo')
def return_jsonSLA():
    return fileJsonSLA


# this function is used to generate the json file which will contain all the sla manager metrics with the relative slos
def create_jsonSLA(filejson, label_config, start_time_range, end_time, chunk_size):
    fileJsonSLA = {}
    for k in filejson:
        print("\nProcessing data...")
        print(filejson)
        if filejson[k]["max"] == False or filejson[k]["min"] == False:
            metric_data = setting_parameters(k, label_config, start_time_range, end_time, chunk_size)
            metric_df = MetricRangeDataFrame(metric_data)
            fileJsonSLA[k] = {'min': metric_df['value'].min(), 'max': metric_df['value'].max()}
            print(fileJsonSLA)
        else:
            fileJsonSLA[k] = filejson[k]

    return fileJsonSLA


# this function is used to generate the json file containing any past violations of a metric (analysis performed for
# 1h, 3h and 12h)
def past_violation(metrics_sla, label_config, start_time, end_time, chunk_size, fileJsonSLA):
    past_violation_json = {}
    for key in metrics_sla:
        num_violation = 0
        for h in range(0, len(start_time)):
            print(key)
            metric_data = setting_parameters(key, label_config, parse_datetime(start_time[h]),
                                             end_time, chunk_size)

            metric_df = MetricRangeDataFrame(metric_data)
            for k in metric_df['value']:
                if not int(fileJsonSLA[key]['min']) < k < int(
                        fileJsonSLA[key]['max']):
                    num_violation = num_violation + 1

            past_violation_json[key + ',' + str(start_time[h])] = {
                "metric_name": key,
                "time": start_time[h], "num_violation": num_violation}
            print("\nViolation for metric: " + key + " for: " + str(
                start_time[h]) + " -> " + str(num_violation))

    return past_violation_json


@app.get('/past_violation_json')
def return_past_violation_json():
    return past_violation_json


# this function is used to generate the json file containing any future violations of a metric (analysis performed
# for 10m)
def future_violation(metrics_sla, label_config, end_time, chunk_size, fileJsonSLA):
    future_violation_json = {}
    id = 0
    for key in metrics_sla:
        num_violation = 0

        metric_data = setting_parameters(key, label_config, parse_datetime('1h'),
                                         end_time, chunk_size)
        metric_df = MetricRangeDataFrame(metric_data)
        data = metric_df.resample(rule='10s').mean(numeric_only='True')
        tsmodel = ExponentialSmoothing(data.dropna(), trend='add', seasonal='add', seasonal_periods=5).fit()
        prediction = tsmodel.forecast(6)

        for k in prediction.values:
            if not fileJsonSLA[key]['min'] < k < \
                   fileJsonSLA[key]['max']:
                num_violation = num_violation + 1

        future_violation_json[id] = {"metric_name": key,
                                     "num_violation": num_violation}
        print("\n\nFuture violation for metric: " + key + " -> " + str(
            num_violation))
        id = id + 1

    return future_violation_json


@app.get('/future_violation_json')
def return_future_violation_json():
    return future_violation_json


def statusSLA(past_violation_json):
    status_SLA = {}

    for metric in past_violation_json:
        if len(past_violation_json) == 0:
            metric_data = setting_parameters(past_violation_json[metric]["metric_name"],
                                             label_config, parse_datetime("10m"),
                                             end_time, chunk_size)
            metric_df = MetricRangeDataFrame(metric_data)
            if past_violation_json[metric]["metric_name"] not in status_SLA:
                status_SLA[past_violation_json[metric]["metric_name"]] = {"status": "violation -> no",
                                                                          "max_metric_values": metric_df["value"].max(),
                                                                          "min_metric_values": metric_df["value"].min(),
                                                                          "mean_metric_values": metric_df["value"].mean()}
        else:
            if past_violation_json[metric]["metric_name"] not in status_SLA:
                status_SLA[past_violation_json[metric]["metric_name"]] = {"status": "violation -> yes",
                                                                          "max_metric_values": "---",
                                                                          "min_metric_values": "---",
                                                                          "mean_metric_values": "---"}

    return status_SLA


@app.get('/status_SLA')
def return_statusSLA():
    return status_SLA


if __name__ == "__main__":
    print("\n*** Hello from SLA MANAGER ***")

    label_config = {'job': 'ceph-metrics'}
    start_time = ["1h", "3h", "12h"]
    start_time_range = parse_datetime("30m")
    end_time = parse_datetime("now")
    chunk_size = timedelta(minutes=1)

    metrics_sla = json.load(open("sla_manager/fileJsonSLA.json"))

    print(metrics_sla)
    fileJsonSLA = create_jsonSLA(metrics_sla, label_config, start_time_range, end_time, chunk_size)
    return_jsonSLA()

    past_violation_json = past_violation(metrics_sla, label_config, start_time, end_time, chunk_size, fileJsonSLA)
    return_past_violation_json()

    status_SLA = statusSLA(past_violation_json)
    return_statusSLA()

    future_violation_json = future_violation(metrics_sla, label_config, end_time, chunk_size, fileJsonSLA)
    return_future_violation_json()

    app.run(host='0.0.0.0', port=5003, debug=False)
