# Import some packages
import numpy as np
import pandas as pd
from sklearn.preprocessing import scale
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
import tensorflow
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Activation
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.layers import LeakyReLU
from tensorflow.keras import regularizers
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.metrics import recall_score
from sklearn.metrics import precision_score
import matplotlib.pyplot as plt

# Load the data 
audio = np.load('spoken_train.npy')
audio_test = np.load('spoken_test.npy') 
written = np.load('written_train.npy')
match_train = np.load('match_train.npy') 
written_test = np.load('written_test.npy')

# Feature engineering

# Scale the features for the images 
written = written / 255 

# Find the optimal number of componets for dimensionality reduction for images 
for n_comp in [5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80]:
    pca_wr = PCA(n_components = n_comp, random_state = 811)
    pca_wr.fit(written)
    pca_wr.transform(written)
    print("For {} components variance is equal to {}".format(n_comp, np.sum(pca_wr.explained_variance_ratio_)))

# PCA for images 
pca_wr = PCA(n_components = 50, random_state = 811)
pca_wr.fit(written)
pca_written = pca_wr.transform(written)  

plt.plot(np.cumsum(pca_wr.explained_variance_ratio_))
plt.xlabel('number of components')
plt.ylabel('cumulative explained variance')
plt.show()

# Calculate mean,standard deviation, maximum, minimum per feature (out of the 13), per observation.
def audio_features (spoken, functions):
    return np.concatenate([np.array([function(i, axis = 0) for i in spoken]) for function in functions], axis = 1)

summaries = [np.mean, np.max, np.min, np.std]
audio_f = audio_features(audio, summaries)

# Merge written and audio data
both = np.hstack((pca_written, audio_f))
both.shape

# Scale the data 
scaler = StandardScaler()
final = scaler.fit_transform(both)
final.shape

# Split the data 
X_train, X_val, y_train, y_val = train_test_split(final, match_train, test_size = 0.1, random_state = 811)

# Convert Y into categorical variable
y_train = to_categorical(y_train)
y_val   = to_categorical(y_val)
print(X_train.shape)
print(y_train.shape)

# Define callbacks
callbacks = [EarlyStopping(monitor='val_loss', patience= 100),
             ModelCheckpoint(filepath='best_model.h5', monitor='val_loss', save_best_only=True)]

# Define the model
np.random.seed(0)

def make_model(n_features):
    model = Sequential()
    optimizer = Adam(lr = 0.001)
    
    model.add(Dense(500, input_shape=(final.shape[1],),
              kernel_initializer= 'glorot_normal'))
    model.add(LeakyReLU(alpha=0.3))
    model.add(BatchNormalization())
    model.add(Dropout(0.2))
    
    model.add(Dense(400, kernel_initializer= 'glorot_uniform'))
    model.add(LeakyReLU(alpha=0.01)) 
    model.add(BatchNormalization())
    model.add(Dropout(0.2))
    
    model.add(Dense(300, kernel_initializer= 'glorot_uniform'))
    model.add(LeakyReLU(alpha=0.01))
    model.add(BatchNormalization())
    model.add(Dropout(0.1))
    
    model.add(Dense(200, kernel_initializer= 'glorot_normal'))
    model.add(Activation('relu'))
    model.add(BatchNormalization())
    model.add(Dropout(0.1))
    
    model.add(Dense(2, activation='sigmoid'))
    
    model.compile(loss='binary_crossentropy',
                  optimizer= optimizer,
                  metrics=['accuracy'])

    return model

model = make_model(final.shape[1])
history = model.fit(X_train, y_train, batch_size= 60 , epochs = 200, verbose=1, validation_data = (X_val, y_val), callbacks = callbacks)

# Model performance

score = model.evaluate(X_val, y_val, verbose=0)
print('Validation loss:', score[0]) 
print('Validation accuracy:', score[1])

# Plot the validation accuracy and validation loss against validation accuracy and training accuracy
print(history.history.keys())

#  "Accuracy"
plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='upper left')
plt.show()

# "Loss"
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='upper left')
plt.show()

# Examine the class distribution
match_tr = pd.DataFrame(match_train)
def labelling (frame): # this function is to change the True/False label to 1/0
    if frame == False:
        return 0
    else: 
        return 1
match_tr['label'] = match_tr[0].apply(labelling)
match_tr['label'].value_counts() 
# true ~= 10% false, clearly class imbalance so we should keep an eye on this when evaluting

# Make confusion matrix 
from sklearn.metrics import confusion_matrix

y_pred = model.predict(X_val)

y_pred = y_pred.argmax(axis = -1)
y_vall  = y_val.argmax(axis = -1)

confusion_matrix(y_vall, y_pred, labels=None, sample_weight=None)

# Calculate precision and recall for both classes (0 and 1)
r1 = recall_score(y_vall, y_pred, labels=None, pos_label=1, average='binary', sample_weight=None)
r0 = recall_score(y_vall, y_pred, labels=None, pos_label=0, average='binary', sample_weight=None)
p1 = precision_score(y_vall, y_pred, labels=None, pos_label=1, average='binary', sample_weight=None)
p0  = precision_score(y_vall, y_pred, labels=None, pos_label=0, average='binary', sample_weight=None)
print('Recall for class 1 is {}'.format(r1))
print('Recall for class 0 is {}'.format(r0))
print('Precision for class 1 is {}'.format(p1))
print('Precision for class 0 is {}'.format(p0))
