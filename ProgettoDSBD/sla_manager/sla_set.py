import json

from flask import Flask
app = Flask(__name__)

# this function is used to generate the vector containing the metrics to be analyzed and monitored with the sla manager
def hello(default_metrics, data):
    metrics_sla = []
    print("\n*** Hello from SLA MANAGER ***\n")
    choose = input("\nDo you want to choose metrics or to use defaults ones?\nSelect 1 for choose, 0 for default")
    if choose == '1':
        print("\n Select your 5 metric by using metric codes")
        for key in data:
            print("Metric code: " + str(key) + " - " + data.get(key) + "\n")

        k = 0
        while len(metrics_sla) < 5:
            metric = input('\nInsert metric: ')
            if 0 <= int(metric) <= len(data):
                if data[metric] not in metrics_sla:
                    metrics_sla.append(data[metric])
                    k = k + 1
                else:
                    print("Cannot insert duplicate metrics; Please insert another metric \n\n")
            else:
                print("This metric code is not valid. Please retry \n\n")
    else:
        metrics_sla = default_metrics

    return metrics_sla


if __name__ == "__main__":

    predict_metric_name = ['ceph_bluestore_read_lat_sum', 'available',
                           'ceph_bluefs_bytes_written_wal', 'ceph_bluefs_db_used_bytes',
                           'ceph_cluster_total_used_bytes']

    data = json.load(open("output.json"))

    metrics = hello(predict_metric_name, data)

    with open("metrics.json", "w") as outfile:
        json.dump(metrics, outfile)

    fileJsonSLA = {}
    for key in range(0, len(metrics)):
        x = input(
            'Do you want to insert min and max for metric ' + metrics[key] + '? y/n\n')
        if x == 'y':
            min = input("Insert min: ")
            max = input("Insert max: ")
            fileJsonSLA[metrics[key]] = {'min': min, 'max': max}
            print("\n", fileJsonSLA[metrics[key]])
        elif x == 'n':
            fileJsonSLA[metrics[key]] = {'min': False, 'max': False}
        else:
            print("\nWrong input -> please retry!\n")
            key = key - 1

    with open("fileJsonSLA.json", "w") as outfile:
        json.dump(fileJsonSLA, outfile)


