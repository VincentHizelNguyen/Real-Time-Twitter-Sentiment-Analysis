### Report&Slide
[Report & Slide](https://drive.google.com/drive/folders/1Mn0Dk4vS3d5_-eewBjgzzF_uV7oSOEk-?usp=drive_link)

```bash
- Replace X_BEARER_TOKEN in the .env file with your own Twitter API key
- Download Hadoop and replace the Hadoop /bin files in the repository with the correct binaries
- Make sure Docker and MongoDB are running before executing any code
- Place twitter.csv inside:
  Real-Time-Twitter-Sentiment-Analysis/Kafka-PySpark
```

# Overview

This repository contains a Big Data project focused on real-time Twitter sentiment analysis.
The system collects tweet data, processes it in real time, classifies sentiment, stores results, and visualizes them through a web dashboard.

The project emphasizes streaming architecture and technology integration, not production optimization.

# Project Architecture

The system is built using the following components:

Apache Kafka
Real-time data ingestion from the Twitter dataset

Spark Streaming 
Stream processing and sentiment classification

MongoDB
Storage for processed sentiment results

Django
Web framework for the real-time dashboard



# Features

## Real-time Data Ingestion
Tweets are streamed into Kafka from a dataset

## Stream Processing
Spark Streaming processes incoming tweets in real time

## Sentiment Analysis
Tweets are classified into:

Positive
Negative
Neutral

## Data Storage
Processed data is stored in MongoDB

## Visualization
A Django dashboard displays sentiment trends in real time

# Dataset

File: twitter.csv

Source:
https://drive.google.com/file/d/1dNefdXTS8OC7RqYwKhZDud5J5tLli3pf/view

#    Repository Structure
Django-Dashboard : this folder contains Dashboard Django Application
Kafka-PySpark : this folder contains kafka provider and pyspark streaming (kafka consumer).
zk-single-kafka-single.yml : Download and install Apache Kafka in docker.

# Getting Started

## Installation
Clone the repository:
```bash
git clone https://github.com/VincentHizelNguyen/Real-Time-Twitter-Sentiment-Analysis.git
cd Real-Time-Twitter-Sentiment-Analysis
```

### Install Docker Desktop according to your operating system.


Start Kafka and Zookeeper:

```bash
docker-compose -f zk-single-kafka-single.yml up -d
```
MongoDB Setup

Install MongoDB.
MongoDB Compass is recommended for data inspection.

Install Python dependencies:
```bash
pip install -r requirements.txt
```
## Running the Project

Note: MongoDB is required for both Spark Streaming and the Django dashboard.

Start MongoDB:
using command line :

```bash
net start MongoDB
```
Then open MongoDB Compass.

Run Kafka and Spark Streaming

Change directory:
```bash
cd Kafka-PySpark
```
Run kafka Zookeeper and a Broker:

using command line :
```bash
docker exec -it kafka1 /bin/bash
```
or using docker desktop 

```bash
kafka-topics --create --topic twitter --bootstrap-server localhost:9092
kafka-topics --describe --topic twitter --bootstrap-server localhost:9092
```
Run Kafka Producer
1. Kaggle
```bash
python producer-validation-tweets.py
```
Run pyspark streaming (kafka consumer) app:
```bash
spark-submit ^
--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 ^
consumer_spark.py
```

2.X(Tweets real time)
```bash
python producer_x.py
```
Run pyspark streaming (kafka consumer) app:
```bash
spark-submit ^
--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 ^
sparkconsumer_x.py
```


Django Dashboard
```bash
cd Django-Dashboard
python manage.py runserver
```


Access the dashboard at:
```bash
http://127.0.0.1:8000
```

## Final Notes

Docker and MongoDB must be running before Spark

Windows users must configure Hadoop correctly

Most runtime errors come from:

Missing Spark Kafka packages

Wrong Spark / Kafka versions

Incorrect Hadoop setup

## Conclusion

This project demonstrates:

Real-time Big Data streaming architecture

Kafka–Spark–MongoDB integration

Practical sentiment analysis on streaming data

If the pipeline runs end-to-end, the core Big Data concepts are correctly implemented.
