# fraude-detection

# Guide de Démarrage du Projet

Ce document explique les étapes pour lancer le projet en utilisant Docker, Spark, Kafka et Cassandra.

## Prérequis

- Docker et Docker Compose installés
- Python 3 et Pip installés

## Étapes pour lancer le projet
### Télècharger data "training_data.csv" depuis ce drive : 
https://drive.google.com/file/d/1WoW8fIdfvFbC8S-6NwESR9-wSFOpZDFV/view?usp=sharing
### 1. Lancer Docker Compose

```bash
docker-compose up
```

### 2. Copier les fichiers nécessaires dans les conteneurs

- Copier le fichier `streaming_consumer.py` dans Spark Master :

```bash
docker cp "pathvers\streaming_consumer.py" spark-master:/opt/bitnami/spark/
```

- Copier le fichier `ProducteurKafka.py` dans Kafka :

```bash
docker cp "pathvers\ProducteurKafka.py" kafka:/tmp/ProducteurKafka.py
```

- Copier le fichier de données d'entraînement :

```bash
docker cp "pathvers\training_data\data_training.csv" kafka:/tmp/data_training.csv
```

- Copier le modèle de fraude dans Spark Master :

```bash
docker cp "pathvers\fraud_rf_model" spark-master:/opt/bitnami/spark/
```

### 3. Créer un topic Kafka

```bash
docker exec -it kafka kafka-topics.sh --create --topic transactions3 --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
```

### 4. Lancer le producteur Kafka

Accéder au conteneur Kafka :

```bash
docker exec -it kafka bash
```

Lancer le script du producteur :

```bash
python3 /tmp/ProducteurKafka.py
```

> **Note** : Si Python3 n'est pas installé dans le conteneur, installez-le avec :
>
> ```bash
> apt update && apt install python3 -y
> ```
>
> Puis relancez le producteur.

### 5. Configurer Cassandra

Accéder au conteneur Cassandra :

```bash
docker exec -it cassandra bash
```

Lancer l'interface CQLSH :

```bash
cqlsh
```

Créer une keyspace :

```sql
CREATE KEYSPACE IF NOT EXISTS my_keyspace WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 1};
```

Basculer vers la keyspace :

```sql
USE my_keyspace;
```

Créer une table :

```sql
CREATE TABLE IF NOT EXISTS my_keyspace.fraud (
    type INT,
    amount DOUBLE,
    oldbalanceOrg DOUBLE,
    newbalanceOrig DOUBLE,
    oldbalanceDest DOUBLE,
    newbalanceDest DOUBLE,
    isFlaggedFraud INT,
    prediction INT,
    PRIMARY KEY (type, amount)
);
```

### 6. Lancer Spark et le Consumer

Accéder au conteneur Spark Master :

```bash
docker exec -it spark-master bash
```

Lancer le consumer avec Spark :

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1,com.datastax.spark:spark-cassandra-connector_2.12:3.1.0 streaming_consumer.py
```

> **Note** : Si une erreur liée à `numpy` survient, installez `numpy` :
>
> ```bash
> pip install numpy
> ```
>
> Puis relancez la commande `spark-submit`.

### 7. Vérifier les données dans Cassandra

Dans l'interface CQLSH, exécutez :

```sql
SELECT * FROM my_keyspace.fraud;
```

## Conclusion

Félicitations ! Vous avez configuré et lancé avec succès le streaming. Les données doivent maintenant être insérées dans Cassandra, et vous pouvez les consulter en utilisant la commande ci-dessus.


