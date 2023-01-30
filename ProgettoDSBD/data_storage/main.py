from confluent_kafka import Consumer
import json
import mysql.connector

mydb = mysql.connector.connect(
    host="db",
    user="root",
    password="asdf.VHjI.313",
    database=''
)

c = Consumer({
    'bootstrap.servers': 'kafka:29092',
    'group.id': 'mygroup',
    'auto.offset.reset': 'latest'
})

c.subscribe(['promethuesdata'])

mycursor = mydb.cursor()


def table_check(cursor, connection, name):
    sql_table = "SHOW TABLES LIKE \'" + name + "\';"
    table = cursor.execute(sql_table)
    row_table = connection.get_rows(table)
    if row_table[0]:
        return True
    else:
        return False


sql_db = "SHOW databases LIKE 'datastorage'"
database = mycursor.execute(sql_db)
row = mydb.get_rows(database)

if row[0]:
    print("Database exists!")
    sql_db = "DROP databases datastorage"
    database = mycursor.execute(sql_db)
    sql = "CREATE DATABASE datastorage"
    mycursor.execute(sql)
else:
    print("Database not exists!")
    sql = "CREATE DATABASE datastorage"
    mycursor.execute(sql)
    print("Database datastorage created!")

use_DB = mycursor.execute('use datastorage')

if table_check(mycursor, mydb, "metadata"):
    print("\nThe table metadata exists!")
else:
    print("\nThe table metadata not exists!")
    sql = "CREATE TABLE metadata (metric_name varchar(255), " \
          "autocorrelation varchar(255), stationarity varchar(255), seasonality text, PRIMARY KEY (metric_name));"
    mycursor.execute(sql)
    print("\nTable metadata created!")

    for x in mycursor:
        print(x)

if table_check(mycursor, mydb, "metrics"):
    print("\nThe table metrics exists!")
else:
    print("\nThe table metrics not exists!")
    sql = "CREATE TABLE metrics (metric_info varchar(255), " \
          "max DOUBLE, min DOUBLE, average DOUBLE, std DOUBLE, PRIMARY KEY (metric_info));"
    mycursor.execute(sql)
    print("\nTable metrics created!")

    for x in mycursor:
        print(x)

if table_check(mycursor, mydb, "prediction"):
    print("\nThe table prediction exists!")
else:
    print("\nThe table prediction not exists!")
    sql = "CREATE TABLE prediction (metric_name varchar(255), " \
          "max DOUBLE, min DOUBLE, avg DOUBLE, PRIMARY KEY (metric_name));"
    mycursor.execute(sql)
    print("\nTable prediction created!")

    for x in mycursor:
        print(x)
while True:
    msg = c.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Consumer error: {}".format(msg.error()))
        continue

    if str(msg.key()) == "b'etl#1'":
        fileJson2 = json.loads(msg.value())
        print("\n\n\nPrinting json file n1\n" + str(fileJson2))
        sql = """INSERT INTO metadata (metric_name, autocorrelation, stationarity, seasonality) VALUES (%s,%s,%s,%s);"""

        for key in fileJson2:
            autocorrelation = str(fileJson2[key]["autocorrelazione"])
            stationarity = str(fileJson2[key]["stazionarietà"])
            seasonality = str(fileJson2[key]["stagionalità"])
            val = (key, autocorrelation, stationarity, seasonality)
            mycursor.execute(sql, val)
            mydb.commit()

            for x in mycursor:
                print(x)
        print("\nStored file n. 1")

    elif str(msg.key()) == "b'etl#2'":

        fileJson = json.loads(msg.value())
        print("\n\n\nPrinting json file n2\n" + str(fileJson))

        sql = """INSERT INTO metrics (metric_info, max, min, average, std) VALUES (%s,%s,%s,%s,%s);"""

        for key in fileJson:
            max = fileJson[key]["max"]
            min = fileJson[key]["min"]
            avg = fileJson[key]["avg"]
            std = fileJson[key]["std"]
            val = (key, max, min, avg, std)
            mycursor.execute(sql, val)
            mydb.commit()

            for x in mycursor:
                print(x)

        print("\nStored file n. 2")

    elif str(msg.key()) == "b'etl#3'":

        fileJson3 = json.loads(msg.value())
        print("\n\n\nPrinting json file n3\n" + str(fileJson3))

        sql = """INSERT INTO prediction (metric_name, max, min, avg) VALUES (%s,%s,%s,%s);"""

        for key in fileJson3:
            max = fileJson3[key]["max"]
            min = fileJson3[key]["min"]
            avg = fileJson3[key]["avg"]
            val = (key, max, min, avg)
            mycursor.execute(sql, val)
            mydb.commit()

            for x in mycursor:
                print(x)
        print("\nStored file n. 3")

c.close()
