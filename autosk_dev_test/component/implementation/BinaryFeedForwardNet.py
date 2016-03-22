"""
Created on Mar 02, 2016

@author: Hector Mendoza
based on Aaron Klein's implementation
"""
import numpy as np
import theano
import theano.tensor as T
import theano.sparse as S
import lasagne
from theano.gof.graph import inputs

DEBUG = True


def iterate_minibatches(inputs, targets, batch_size, shuffle=False):
    assert inputs.shape[0] == targets.shape[0],\
           "The number of training points is not the same"
    if shuffle:
        indices = np.arange(inputs.shape[0])
        np.random.shuffle(indices)
    for start_idx in range(0, inputs.shape[0] - batch_size + 1, batch_size):
        if shuffle:
            excerpt = indices[start_idx:start_idx + batch_size]
        else:
            excerpt = slice(start_idx, start_idx + batch_size)
        yield inputs[excerpt], targets[excerpt]


class BinaryFeedForwardNet(object):
    def __init__(self, input_shape=(100, 28*28),
                 batch_size=100, num_layers=4, num_units_per_layer=(10, 10, 10),
                 dropout_per_layer=(0.5, 0.5, 0.5), std_per_layer=(0.005, 0.005, 0.005),
                 num_output_units=1, dropout_output=0.5, learning_rate=0.01,
                 momentum=0.9, beta1=0.9, beta2=0.9,
                 rho=0.95, solver="sgd", num_epochs=2,
                 is_sparse=False):

        self.batch_size = batch_size
        self.input_shape = input_shape
        self.num_layers = num_layers
        self.num_units_per_layer = num_units_per_layer
        self.dropout_per_layer = dropout_per_layer
        self.num_output_units = num_output_units
        self.dropout_output = dropout_output
        self.std_per_layer = std_per_layer
        self.momentum = momentum
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.beta2 = beta2
        self.rho = rho
        # self.number_updates = number_updates
        self.num_epochs = num_epochs

        if is_sparse:
            input_var = S.csr_matrix('inputs', dtype='float32')
        else:
            input_var = T.dmatrix('inputs')
        target_var = T.lmatrix('targets')
        if DEBUG:
            print("... building network")
            print input_shape
            print("... with number of epochs")
            print(num_epochs)

        self.network = lasagne.layers.InputLayer(shape=input_shape,
                                                 input_var=input_var)
        # Define each layer
        for i in range(num_layers - 1):
            self.network = lasagne.layers.DenseLayer(
                 lasagne.layers.dropout(self.network,
                                        p=self.dropout_per_layer[i]),
                 num_units=self.num_units_per_layer[i],
                 W=lasagne.init.Normal(std=self.std_per_layer[i], mean=0),
                 b=lasagne.init.Constant(val=0.0),
                 nonlinearity=lasagne.nonlinearities.rectify)

        # Define output layer
        self.network = lasagne.layers.DenseLayer(
                 lasagne.layers.dropout(self.network, p=self.dropout_output),
                 num_units=self.num_output_units,
                 W=lasagne.init.GlorotNormal(),
                 b=lasagne.init.Constant(),
                 nonlinearity=lasagne.nonlinearities.sigmoid)

        prediction = lasagne.layers.get_output(self.network)
        loss = lasagne.objectives.binary_crossentropy(prediction,
                                                      target_var)
        # Aggregate loss mean function
        loss = loss.mean()
        params = lasagne.layers.get_all_params(self.network, trainable=True)

        if solver == "nesterov":
            updates = lasagne.updates.nesterov_momentum(loss, params,
                                                        learning_rate=self.learning_rate,
                                                        momentum=self.momentum)
        elif solver == "adam":
            updates = lasagne.updates.adam(loss, params,
                                           learning_rate=self.learning_rate,
                                           beta1=self.beta1, beta2=self.beta2)
        elif solver == "adadelta":
            updates = lasagne.updates.adadelta(loss, params,
                                               learning_rate=self.learning_rate,
                                               rho=self.rho)
        elif solver == "adagrad":
            updates = lasagne.updates.adagrad(loss, params,
                                              learning_rate=self.learning_rate)
        elif solver == "sgd":
            updates = lasagne.updates.sgd(loss, params,
                                          learning_rate=self.learning_rate)
        elif solver == "momentum":
            updates = lasagne.updates.momentum(loss, params,
                                               learning_rate=self.learning_rate,
                                               momentum=self.momentum)
        else:
            updates = lasagne.updates.sgd(loss, params,
                                          learning_rate=self.learning_rate)

        print("... compiling theano functions")
        self.train_fn = theano.function(inputs=[input_var, target_var],
                                        outputs=loss,
                                        updates=updates,
                                        allow_input_downcast=True)

    def fit(self, X, y):
        for epoch in range(self.num_epochs):
            train_err = 0
            train_batches = 0
            for batch in iterate_minibatches(X, y, self.batch_size, shuffle=True):
                inputs, targets = batch
                train_err += self.train_fn(inputs, targets)
                train_batches += 1
            print("  training loss:\t\t{:.6f}".format(train_err / train_batches))
        return self

    def predict(self, X, is_sparse=False):
        predictions = self.predict_proba(X, is_sparse)
        return np.rint(predictions)

    def predict_proba(self, X, is_sparse=False):
        # TODO: Add try-except statements
        if is_sparse:
            X = S.basic.as_sparse_or_tensor_variable(X)
        predictions = lasagne.layers.get_output(self.network, X, deterministic=True).eval()
        return predictions
