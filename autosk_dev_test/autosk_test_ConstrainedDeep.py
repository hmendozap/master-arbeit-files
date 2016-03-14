# -*- encoding: utf-8 -*-

import numpy as np
from autosklearn.pipeline.components.classification import add_classifier
import autosklearn.automl as autosk
from component import AdamConstFeedNet
from component import DeepFeedNet

# Use MNIST
dataset_dir = '/data/aad/automl_data/openml/554_bac/'

X_train = np.loadtxt(dataset_dir + 'train.data')
y_train = np.loadtxt(dataset_dir + 'train.solution')

# Load our training data
# X_train = np.load(dataset_dir + 'train.npy')
# y_train = np.load(dataset_dir + 'train_labels.npy')

add_classifier(AdamConstFeedNet)

# Create model
modl = autosk.AutoML(time_left_for_this_task=600, per_run_time_limit=90,
                     delete_tmp_folder_after_terminate=False,
                     tmp_dir='tmp/constr_nn', output_dir='tmp/autosk_out',
                     log_dir='tmp/autosk_log',
                     include_estimators=['AdamConstFeedNet'],
                     include_preprocessors=['no_preprocessing'],
                     ensemble_size=0,
                     ensemble_nbest=0,
                     initial_configurations_via_metalearning=0,
                     seed=50,
                     ml_memory_limit=3072,
                     metadata_directory=None,
                     queue=None,
                     keep_models=True,
                     debug_mode=False,
                     resampling_strategy='holdout',
                     resampling_strategy_arguments=None)

modl.fit(X_train, y_train, dataset_name='Constrained_MNIST')

# X_test = np.load(dataset_dir + 'test.npy')
# y_test = np.load(dataset_dir + 'test_labels.npy')

X_test = np.loadtxt(dataset_dir + 'test.data')
y_test = np.loadtxt(dataset_dir + 'test.solution')

try:
    tot_score = modl.score(X_test, y_test)
    print(tot_score)

    y_pred = modl.predict(X_test)
    # Comparison
    accuracy = np.count_nonzero(y_test == y_pred)
    print (float(accuracy) / X_test.shape[0])
except Exception as E:
    print("Ups, there is an error: %s" % E)