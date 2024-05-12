from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import numpy as np
import xgboost as xgb
import time
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from firebase import firebase
from sklearn.metrics import accuracy_score, confusion_matrix

firebase_1 = firebase.FirebaseApplication(
    'https://tender-management-f21dc-default-rtdb.firebaseio.com/', None)

processed_transactions = set()


def initialize_firebase():
    cred = credentials.Certificate(
        "rfpos-164f0-firebase-adminsdk-wrba8-0848a91446.json"
    )  # replace with your credentials file
    firebase_admin.initialize_app(cred, {
        'databaseURL':
        'https://rfpos-164f0-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })


def load_historical_data():
    ref = db.reference('/credit_card_transactions')
    historical_data = ref.get()
    historical_transactions = np.array(
        [transaction['amt'] for transaction in historical_data.values()])
    labels = np.array(
        [transaction['is_fraud'] for transaction in historical_data.values()])
    return historical_transactions, labels


def train_xgboost(historical_data, labels):
    model = xgb.XGBClassifier()
    model.fit(historical_data.reshape(-1, 1), labels)
    return model


def calculate_outlier_status(model, real_time_data):
    real_time_transactions = np.array(
        [transaction['amt'] for transaction in real_time_data.values()])
    ref12 = db.reference('/outliers')
    ref11 = db.reference('/not_outliers')
    ref13 = db.reference('/messages')
    for i, transaction in enumerate(real_time_data.values()):
        if transaction['trans_num'] not in processed_transactions:
            print("Transaction Details:")
            print("Amount:", transaction['amt'])
            is_outlier = model.predict(
                real_time_transactions[i].reshape(1, -1))
            print("XGBoost - Outlier Status:",
                  "Outlier" if is_outlier == 1 else "Not an outlier")
            if is_outlier == 1:
                ref12.push(transaction)
                body1 = "We have detected fraud in your credit card transaction.\n Transaction number: " + str(
                    transaction['trans_num']) + "\n Amount: " + str(
                        transaction['amt']) + "\n Date and Time: " + str(
                            transaction['trans_date_trans_time'])
                ref13.push({'message': body1})
            else:
                ref11.push(transaction)
            processed_transactions.add(transaction['trans_num'])
            print("")


def process_real_time_data(model, labels):
    ref = db.reference('/credit_card_transactions_other')
    while True:
        real_time_data = ref.get()
        if real_time_data:
            calculate_outlier_status(model, real_time_data)
        time.sleep(3)  # Adjust the sleep duration as needed


def main():
    initialize_firebase()
    historical_data, labels = load_historical_data()
    xgboost_model = train_xgboost(historical_data, labels)

    process_real_time_data(xgboost_model, labels)


if __name__ == "__main__":
    main()
