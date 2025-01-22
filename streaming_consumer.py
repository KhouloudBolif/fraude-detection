

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
from pyspark.ml.classification import RandomForestClassificationModel
from pyspark.ml.feature import VectorAssembler
from pyspark.sql import functions as F


# Création de la session Spark
spark = SparkSession.builder \
    .master("local[*]") \
    .appName("StreamingConsumerWithCassandra") \
    .config("spark.cassandra.connection.host", "cassandra") \
    .config("spark.cassandra.connection.port", "9042") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1,com.datastax.spark:spark-cassandra-connector_2.12:3.1.0") \
    .getOrCreate()

# Lecture du flux Kafka
kafka_stream_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "transactions3") \
    .option("startingOffsets", "earliest") \
    .load()

# Conversion des messages en chaîne JSON
json_df = kafka_stream_df.selectExpr("CAST(value AS STRING) as message")

# Définir le schéma JSON
schema = StructType([
    StructField("type", StringType(), True),
    StructField("amount", StringType(), True),
    StructField("oldbalanceOrg", StringType(), True),
    StructField("newbalanceOrig", StringType(), True),
    StructField("oldbalanceDest", StringType(), True),
    StructField("newbalanceDest", StringType(), True),
    StructField("isFlaggedFraud", StringType(), True)
])

# Parsing des messages JSON
parsed_df = json_df.withColumn("parsed", from_json(col("message"), schema))

# Aplatir les colonnes JSON
final_df = parsed_df.select(
    col("parsed.type").alias("type"),
    col("parsed.amount").alias("amount"),
    col("parsed.oldbalanceOrg").alias("oldbalanceOrg"),
    col("parsed.newbalanceOrig").alias("newbalanceOrig"),
    col("parsed.oldbalanceDest").alias("oldbalanceDest"),
    col("parsed.newbalanceDest").alias("newbalanceDest"),
    col("parsed.isFlaggedFraud").alias("isFlaggedFraud")
)

# Convertir les colonnes String en Double
final_df = final_df.withColumn("type", col("type").cast(IntegerType())) \
                   .withColumn("amount", col("amount").cast(DoubleType())) \
                   .withColumn("oldbalanceOrg", col("oldbalanceOrg").cast(DoubleType())) \
                   .withColumn("newbalanceOrig", col("newbalanceOrig").cast(DoubleType())) \
                   .withColumn("oldbalanceDest", col("oldbalanceDest").cast(DoubleType())) \
                   .withColumn("newbalanceDest", col("newbalanceDest").cast(DoubleType())) \
                   .withColumn("isFlaggedFraud", col("isFlaggedFraud").cast(IntegerType()))

# Charger le modèle pré-entraîné
model_path = "/opt/bitnami/spark/fraud_rf_model"
rf_model = RandomForestClassificationModel.load(model_path)

# Création des colonnes de caractéristiques à partir des données
feature_columns = [
   "type" ,"amount", "oldbalanceOrg", "newbalanceOrig", 
    "oldbalanceDest", "newbalanceDest", "isFlaggedFraud"
]

# Transformation des colonnes de données en un vecteur de caractéristiques
assembler = VectorAssembler(inputCols=feature_columns, outputCol="features")
final_df = assembler.transform(final_df)

# Prédiction avec le modèle
predictions = rf_model.transform(final_df)

# Aplatir les colonnes pour les résultats de prédiction
from pyspark.sql import functions as F

# Alignement des colonnes avec Cassandra
predictions_final = predictions.select(
    F.col("type").cast("int"),
    F.col("amount").cast("double"),
    F.col("isFlaggedFraud").cast("int").alias("isflaggedfraud"),
    F.col("newbalanceDest").cast("double").alias("newbalancedest"),
    F.col("newbalanceOrig").cast("double").alias("newbalanceorig"),
    F.col("oldbalanceDest").cast("double").alias("oldbalancedest"),
    F.col("oldbalanceOrg").cast("double").alias("oldbalanceorg"),
    F.col("prediction").cast("int")
)


def write_to_cassandra(df, epochId):
    try:
        df.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .option("keyspace", "my_keyspace") \
            .option("table", "fraud") \
            .save()
        print(f"Batch {epochId} written successfully.")
    except Exception as e:
        print(f"Error writing batch {epochId} to Cassandra: {str(e)}")

# Enregistrement des résultats dans Cassandra
query = predictions_final.writeStream \
    .foreachBatch(write_to_cassandra) \
    .outputMode("append") \
    .start()





# Fonction pour écrire dans HDFS au format Parquet
def write_to_hdfs_parquet(df, epochId):
    try:
        # Définir le chemin HDFS
        hdfs_path = "hdfs://hadoop-namenode:9000/user/spark/fraud_predictions_txt/"
        
        # Afficher les données pour vérifier leur contenu
        df.show(truncate=False)
        
        # Écrire les données dans HDFS au format Parquet
        df.write \
            .mode("append") \
            .parquet(hdfs_path)
        
        # Vérifier si le fichier est effectivement écrit
        print(f"Batch {epochId} written to HDFS successfully.")
        
        # Vérification après l'écriture
        print("Checking HDFS directory contents:")
        os.system(f"hdfs dfs -ls {hdfs_path}")

    except Exception as e:
        print(f"Error writing batch {epochId} to HDFS: {str(e)}")

# Enregistrement des résultats dans HDFS en format Parquet
query_hdfs = predictions_final.writeStream \
    .foreachBatch(write_to_hdfs_parquet) \
    .outputMode("append") \
    .start()


# Affichage des données dans la console pour suivi
console_query = predictions_final.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .start()

# Attente de la fin du streaming
console_query.awaitTermination()

# Arrêt de la session Spark en cas de terminaison
spark.stop()



