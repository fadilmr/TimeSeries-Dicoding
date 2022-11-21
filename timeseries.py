# -*- coding: utf-8 -*-
"""TimeSeries

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1GF8dLUDCe-zZxpD6n19EsAzwaRJtJf-M

# import library
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import tensorflow as tf

"""# Download Dataset using Kaggle API"""

!pip install -q kaggle

from google.colab import files
files.upload()

!mkdir -p ~/.kaggle
!cp kaggle.json ~/.kaggle/
!chmod 600 ~/.kaggle/kaggle.json
!ls ~/.kaggle

!kaggle datasets download -d mahirkukreja/delhi-weather-data

!mkdir delhi-weather-data
!unzip delhi-weather-data.zip -d delhi-weather-data
!ls delhi-weather-data

"""# Read Dataset"""

df = pd.read_csv('delhi-weather-data/testset.csv')
df.head()

df.info()

df.describe()

"""# Pre Processing"""

df = df[['datetime_utc', ' _tempm']]

df.head()

df.isnull().sum()

df[' _tempm'].fillna((df[' _tempm'].mean()), inplace = True)

df.isnull().sum()

df['datetime_utc'] = pd.to_datetime(df['datetime_utc'])

df_temp = df.set_index('datetime_utc', inplace=False)
df_temp.head()

plt.figure(figsize=(20,8))
plt.plot(df_temp)
plt.title('Delhi Weather')
plt.xlabel('Date')
plt.ylabel('temperature')
plt.show()

df_temp = df_temp.resample('D').mean()

df_temp.isna().sum()

df_temp.fillna(df_temp[' _tempm'].mean(),inplace=True)
df_temp.head()

plt.figure(figsize=(20,8))
plt.plot(df_temp)
plt.title('Delhi Weather')
plt.xlabel('Date')
plt.ylabel('temperature')
plt.show()

"""# Model and Training"""

x = df['datetime_utc'].values
y = df[' _tempm'].values

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size = 0.2 , shuffle=False)
x_train = x_train.reshape(-1,1)
x_test = x_test.reshape(-1,1)

scaler = StandardScaler()
x_train_scaled = scaler.fit_transform(x_train)
x_test_scaled = scaler.fit_transform(x_test)

pca = PCA(n_components=0.95)

x_train_reduced = pca.fit_transform(x_train_scaled)
x_test_reduced = pca.transform(x_test_scaled)

def windowed_dataset(series, window_size, batch_size, shuffle_buffer):
    series = tf.expand_dims(series, axis=-1)
    ds = tf.data.Dataset.from_tensor_slices(series)
    ds = ds.window(window_size + 1, shift=1, drop_remainder=True)
    ds = ds.flat_map(lambda w: w.batch(window_size + 1))
    ds = ds.shuffle(shuffle_buffer)
    ds = ds.map(lambda w: (w[:-1], w[-1:]))
    return ds.batch(batch_size).prefetch(1)

# model
train_set = windowed_dataset(x_train_scaled, window_size=60, batch_size=100, shuffle_buffer=5000)
test_set = windowed_dataset(x_test_scaled, window_size=60, batch_size=100, shuffle_buffer=5000)

model = tf.keras.Sequential(
    [
        tf.keras.layers.LSTM(128, return_sequences=True, input_shape=[None, 1]),
        tf.keras.layers.LSTM(64, return_sequences=True),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(8),
        tf.keras.layers.Dense(4),
        tf.keras.layers.Dense(2),
        tf.keras.layers.Dense(1),
    ]
)

optimizer = tf.keras.optimizers.SGD(lr=1e-8, momentum=0.9)
model.compile(loss = tf.keras.losses.Huber(), optimizer = optimizer, metrics = ['mae'])

target = (df_temp[' _tempm'].max() - df_temp[' _tempm'].min()) * (10/100)
print(target)
class callbacks(tf.keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs = None):
        if logs.get('mae') <= target:
            print("\nnilai MAE sudah < 10% dari skala data")
            self.model.stop_training = True
callback = callbacks()

# training
history = model.fit(train_set, epochs = 1000, validation_data=test_set, callbacks=[callback], steps_per_epoch = 1)