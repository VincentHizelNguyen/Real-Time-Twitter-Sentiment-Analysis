### Report&Slide
[Report & Slide](https://drive.google.com/drive/folders/1Mn0Dk4vS3d5_-eewBjgzzF_uV7oSOEk-?usp=drive_link)

```bash
- Replace X_BEARER_TOKEN in the .env file with your own Twitter API key
- Download Hadoop and replace the Hadoop /bin files in the repository with the correct binaries
- Make sure Docker and MongoDB are running before executing any code
- Place twitter.csv inside:
  Real-Time-Twitter-Sentiment-Analysis/Kafka-PySpark/producer

```

# Overview

This repository contains a Big Data streaming project for real-time Twitter sentiment analysis.

The system ingests tweet data from two sources:

A Kaggle CSV dataset

Live Twitter/X API (v2, recent search)

All data is published to Apache Kafka, processed in real time using Spark Structured Streaming, classified by sentiment, stored in MongoDB, and partially persisted to Parquet files for offline analysis.

The project focuses on streaming architecture, data flow, and system integration,
not on production-level optimization or scalability tuning.
# Project Architecture
The system is built using the following components:

Apache Kafka
Message queue for ingesting tweet events from CSV producers and X API producers

Spark Structured Streaming
Real-time stream processing, sentiment classification, window aggregation, and data enrichment

MongoDB
NoSQL database for storing labeled tweets and aggregated sentiment statistics

Local Distributed Storage 
Parquet files written by Spark for raw labeled data and bad records

Django
Web framework used to visualize sentiment trends from MongoDB

# Features

## Real-time Data Ingestion
Tweets are ingested into Kafka from:

A Kaggle CSV dataset (producer_csv.py)

Twitter/X API v2 recent search (producer_x.py)## Stream Processing
Spark Streaming processes incoming tweets continuously as data arrives.
## Sentiment Analysis
Tweets are classified into:

Positive
Negative
Neutral
## Stream Processing

Spark Structured Streaming consumes data from Kafka and performs:

JSON parsing and schema validation

Timestamp normalization

Data cleaning and enrichment

Broadcast join with a small language dimension table

#E# Sentiment Analysis

Each tweet is classified using VADER sentiment analysis into:

Positive

Negative

Neutral


## Data Storage

Processed data is written to:

MongoDB

tweets_labeled : raw labeled tweets

sentiment_agg : window-based sentiment aggregation


## Visualization

A Django-based dashboard reads data from MongoDB and displays:

Real-time sentiment trends

Aggregated sentiment counts

File: twitter.csv

Source:
[Data](https://drive.google.com/file/d/1dNefdXTS8OC7RqYwKhZDud5J5tLli3pf/view)

#    Repository Structure
Django-Dashboard
This folder contains the Django application used for the visualization dashboard.

Kafka-PySpark
This folder contains Kafka producers and PySpark streaming consumers.

zk-single-kafka-single.yml
Docker Compose configuration for running Apache Kafka and Zookeeper.
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
kafka-topics --create --topic twitter_raw --bootstrap-server localhost:9092
kafka-topics --describe --topic twitter_raw --bootstrap-server localhost:9092
```
## Run Kafka Producers
1. CSV Producer (Kaggle Dataset)
python producer_csv.py

2. Twitter/X Real-time Producer
python producer_x.py

Run Spark Structured Streaming Consumer
spark-submit ^
--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 ^
spark_streaming_to_mongo_hdfs.py

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

Most runtime errors are caused by:

Missing Spark Kafka or MongoDB connectors

Version mismatch between Spark, Kafka, and Scala

Incorrect Hadoop configuration on Windows

## Conclusion

This project demonstrates:

An end-to-end real-time Big Data streaming pipeline

Kafka → Spark Structured Streaming → MongoDB integration

Practical sentiment analysis on streaming Twitter data

If the pipeline runs end-to-end without data loss, the core Big Data concepts are correctly implemented.
