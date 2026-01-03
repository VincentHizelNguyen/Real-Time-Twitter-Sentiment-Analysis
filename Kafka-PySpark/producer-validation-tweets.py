from time import sleep
import csv
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

with open('twitter_validation.csv', mode='r', encoding='utf-8') as file_obj:
    reader_obj = csv.reader(file_obj)
    for idx, data in enumerate(reader_obj, 1):
        if idx > 300:
            break

        producer.send('numtest', value=data)
        print(f"Sent line {idx}: {data}")
        sleep(0.5)
