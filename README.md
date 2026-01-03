```bash
.evn thay X_BEARER_TOKEN thanh key cua ban than
tải hadoop va thay the bin cua hadoop trong github thanh cac file tương ứng
khi chay code nhớ mở docker và mongodb
```




Big Data Project: Real-Time Twitter Sentiment Analysis Using Kafka, Spark (MLLib & Streaming), MongoDB and Django.
Overview
This repository contains a Big Data project focused on real-time sentiment analysis of Twitter data (classification of tweets). The project leverages various technologies to collect, process, analyze, and visualize sentiment data from tweets in real-time.

Project Architecture
The project is built using the following components:

Apache Kafka: Used for real-time data ingestion from Twitter DataSet.

Spark Streaming: Processes the streaming data from Kafka to perform sentiment analysis.

MongoDB: Stores the processed sentiment data.

Django: Serves as the web framework for building a real-time dashboard to visualize the sentiment analysis results.

chart.js & matplotlib : for plotting.

This is the project plan : project img

Features
Real-time Data Ingestion: Collects live tweets using Kafka from the Twitter DataSet.
Stream Processing: Utilizes Spark Streaming to process and analyze the data in real-time.
Sentiment Analysis: Classifies tweets into different sentiment categories (positive, negative, neutral) 
Data Storage: Stores the sentiment analysis results in MongoDB for persistence.
Visualization: Provides a real-time dashboard built with Django to visualize the sentiment trends and insights.
Data description:

Tweet ID: int
Entity: string
Sentiment: string (Target)
Tweet content: string
The validation database “twitter_validation.csv” 

This is the Data Source: https://drive.google.com/file/d/1dNefdXTS8OC7RqYwKhZDud5J5tLli3pf/view?usp=sharing

Repository Structure
Django-Dashboard : this folder contains Dashboard Django Application
Kafka-PySpark : this folder contains kafka provider and pyspark streaming (kafka consumer).
ML PySpark Model : this folder contains the trained model with jupyter notebook and datasets.
zk-single-kafka-single.yml : Download and install Apache Kafka in docker.
bigdataproject rapport : a brief report about the project (in french).
Getting Started
Prerequisites
To run this project, you will need the following installed on your system:

Docker (for runing Kafka)
Python 3.x
Apache Kafka
Apache Spark (PySpark for python)
MongoDB
Django
Installation
Clone the repository:
```bash
git clone https://github.com/VincentHizelNguyen/Real-Time-Twitter-Sentiment-Analysis.git
cd Real-Time-Twitter-Sentiment-Analysis
```
Installing Docker Desktop

Set up Kafka:

Download and install Apache Kafka in docker using :
```bash
docker-compose -f zk-single-kafka-single.yml up -d
```
Set up MongoDB:

Download and install MongoDB.
It is recommended to install also MongoDBCompass to visualize data and makes working with mongodb easier.
Install Python dependencies:

To install pySpark - PyMongo - Django ...
```bash
pip install -r requirements.txt
```
Running the Project

Note : you will need MongoDB for Running the Kafka and Spark Streaming application and for Running Django Dashboard application.

Start MongoDB:
using command line :

```bash
net start MongoDB
```
then use MongoDBCompass
Running the Kafka and Spark Streaming application :
Change the directory to the application:
```bash
cd Kafka-PySpark
```
Start Kafka in docker:

using command line :
```bash
docker exec -it kafka1 /bin/bash
```
or using docker desktop :

 docker desktop img

Run kafka Zookeeper and a Broker:
```bash
kafka-topics --create --topic twitter --bootstrap-server localhost:9092
kafka-topics --describe --topic twitter --bootstrap-server localhost:9092
```
Run kafka provider app:
1. Kaggle
```bash
python producer-validation-tweets.py
```
Run pyspark streaming (kafka consumer) app:
```bash
python consumer-pyspark.py
```

2.X
```bash
python producer_x_search_to_mongo.py
```


