# -*- coding: utf-8 -*-
"""submission2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xNMIqvtVjiJ7WZK1r0yh0UnlgQDudtw6
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import zipfile
import tensorflow as tf
import os
from keras.layers import Dense, LSTM
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import Callback, ReduceLROnPlateau, EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam

df = pd.read_csv('AP001.csv')

print("Ukuran Sampel ",df.shape[0])

df.describe(include='all')

df.isna().sum()

columns_to_drop = ['Ozone (ug/m3)', 'Benzene (ug/m3)', 'Toluene (ug/m3)', 'Temp (degree C)',
                       'RH (%)', 'WS (m/s)', 'WD (deg)', 'SR (W/mt2)', 'BP (mmHg)', 'VWS (m/s)',
                       'Xylene (ug/m3)', 'RF (mm)', 'AT (degree C)']

df_cleaned = df.drop(columns = columns_to_drop,axis = 1)

df_cleaned.isna().sum()

df_cleaned = df_cleaned.dropna()

df_cleaned.isna().sum()

df_cleaned.shape[0]

df_cleaned = df_cleaned.drop(columns='To Date')

df_cleaned['From Date'] = pd.to_datetime(df_cleaned['From Date'])
df_cleaned = df_cleaned.rename(columns={'From Date':'datetime'})

df_cleaned.describe(include='all')

def plot_stacked_line_chart(df):
  first_column = df.columns[0]
  plt.figure(figsize=(10, 6))
  for column in df.columns[1:]:
    plt.plot(df[first_column],df[column],label=f'{first_column}-{column}')
  plt.xlabel(first_column)
  plt.ylabel('Values')
  plt.title(f'{first_column} Against Other Columns')
  plt.legend()
  plt.show()

plot_stacked_line_chart(df_cleaned)

"""### Date terhadap CO"""

df_used = df_cleaned['CO (mg/m3)'].values
df_used

df_used.shape[0]

"""### Normalisasi Data"""

from sklearn.preprocessing import MinMaxScaler, StandardScaler
co_reshaped = np.array(df_used).reshape(-1, 1)
standard_scaler = StandardScaler()
standard_scaler.fit(co_reshaped)
co_normalized = standard_scaler.transform(co_reshaped)
co_normalized = co_normalized.flatten()
print(co_normalized)

X_train, X_val = train_test_split(co_normalized, test_size=0.2, shuffle=False)

def windowed_dataset(series, window_size, batch_size, shuffle_buffer):
    series = tf.expand_dims(series, axis=-1)
    ds = tf.data.Dataset.from_tensor_slices(series)
    ds = ds.window(window_size + 1, shift=1, drop_remainder=True)
    ds = ds.flat_map(lambda w: w.batch(window_size + 1))
    ds = ds.shuffle(shuffle_buffer)
    ds = ds.map(lambda w: (w[:-1], w[-1:]))
    return ds.batch(batch_size).prefetch(1)

train_set = windowed_dataset(X_train, window_size=60, batch_size=100, shuffle_buffer=1000)
validation_set = windowed_dataset(X_val, window_size=60, batch_size=100, shuffle_buffer=1000)

model = tf.keras.models.Sequential([
  tf.keras.layers.LSTM(60, return_sequences=True),
  tf.keras.layers.Dropout(0.2),
  tf.keras.layers.LSTM(60),
  tf.keras.layers.Dense(70, activation="relu"),
  tf.keras.layers.Dropout(0.2),
  tf.keras.layers.Dense(50, activation="relu"),
  tf.keras.layers.Dropout(0.2),
  tf.keras.layers.Dense(30, activation="relu"),
  tf.keras.layers.Dropout(0.2),
  tf.keras.layers.Dense(10, activation="relu"),
  tf.keras.layers.Dense(1),
])

threshold_mae = (df_cleaned['CO (mg/m3)'].max() - df_cleaned['CO (mg/m3)'].min()) * 10/100

threshold_mae

class MyCallBack(tf.keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs={}):
      if(logs.get('val_mae') < threshold_mae):
        print(f"\nMAE telah tercapai {threshold_mae}")
        self.model.stop_training = True

on_stop = MyCallBack()

checkpoint_path = "time_series"
checkpoint_callback = ModelCheckpoint(checkpoint_path,
                                      save_weights_only=True,
                                      monitor="mae",
                                      save_best_only=True)

optimizer = tf.keras.optimizers.Adam(learning_rate=1.0000e-04)
model.compile(loss=tf.keras.losses.Huber(),
              optimizer=optimizer,
              metrics=["mae"])
history = model.fit(train_set,epochs=100,validation_data = validation_set,callbacks = [on_stop, checkpoint_callback])

