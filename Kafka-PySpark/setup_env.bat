@echo off
REM --- Set Java ---
set JAVA_HOME=C:\Program Files\Java\jdk-17.0.12
set PATH=%JAVA_HOME%\bin;%PATH%

REM --- Set Hadoop ---
set HADOOP_HOME=C:\Users\thuuy\Real-Time-Twitter-Sentiment-Analysis\Kafka-PySpark\hadoop
set PATH=%HADOOP_HOME%\bin;%PATH%

REM --- Set Spark ---
set SPARK_HOME=C:\Users\thuuy\Real-Time-Twitter-Sentiment-Analysis\Kafka-PySpark\spark
set PATH=%SPARK_HOME%\bin;%PATH%

REM --- Test Java & winutils ---
java -version
winutils.exe ls C:\

echo Environment setup done.
pause
