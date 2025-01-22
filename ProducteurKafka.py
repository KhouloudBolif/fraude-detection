

import csv
import time
import json
from confluent_kafka import Producer, KafkaException

# Configurer le producteur Kafka
producer_conf = {
    'bootstrap.servers': 'kafka:9092',  # Adresse du serveur Kafka
    'security.protocol': 'PLAINTEXT',  # Protocole sans SSL
}

try:
    producer = Producer(producer_conf)
except KafkaException as e:
    print(f"Erreur lors de la configuration du producteur Kafka : {e}")
    exit(1)

# Callback pour confirmer la livraison des messages
def delivery_report(err, msg):
    if err is not None:
        print(f"Échec de la livraison du message : {err}")
    else:
        print(f"Message envoyé avec succès à {msg.topic()} [{msg.partition()}] offset {msg.offset()}")

# Chemin du fichier CSV et sujet Kafka
csv_file = '/tmp/data_training.csv'  # Vérifiez que ce fichier existe
topic = 'transactions3'

try:
    # Ouvrir et lire le fichier CSV
    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        # Vérifiez que le fichier CSV n'est pas vide et qu'il a des en-têtes
        if not reader.fieldnames:
            print("Erreur : Le fichier CSV ne contient pas d'en-têtes ou est vide.")
            exit(1)

        print(f"Envoi des messages au sujet Kafka '{topic}'...")

        for row in reader:
            # Valider chaque ligne du CSV avant de l'envoyer
            if not row:
                print("Ligne vide détectée, ignorée.")
                continue

            try:
                # Convertir la ligne en JSON
                message = json.dumps(row)
                # Produire le message Kafka
                producer.produce(topic, value=message, callback=delivery_report)
                print(f"Message en cours d'envoi : {message}")
            except Exception as e:
                print(f"Erreur lors de la production du message : {e}")
            
            # Attendre un peu avant d'envoyer le prochain message
            time.sleep(1)
        
        # Attendre que tous les messages soient envoyés avant de terminer
        producer.flush()
        print("Production terminée.")

except FileNotFoundError:
    print(f"Erreur : Le fichier {csv_file} n'a pas été trouvé.")
except Exception as e:
    print(f"Erreur inattendue : {e}")
