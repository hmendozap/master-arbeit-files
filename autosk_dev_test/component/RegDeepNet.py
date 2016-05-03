import numpy as np
import scipy.sparse as sp

from HPOlibConfigSpace.configuration_space import ConfigurationSpace
from HPOlibConfigSpace.conditions import EqualsCondition, InCondition
from HPOlibConfigSpace.hyperparameters import UniformFloatHyperparameter, \
    UniformIntegerHyperparameter, CategoricalHyperparameter, Constant

from autosklearn.pipeline.components.base import AutoSklearnRegressionAlgorithm
from autosklearn.pipeline.constants import *


class RegDeepNet(AutoSklearnRegressionAlgorithm):

    def __init__(self, number_updates, batch_size, num_layers, num_units_layer_1,
                 dropout_layer_1, dropout_output, std_layer_1,
                 learning_rate, solver, lambda2, activation,
                 num_units_layer_2=10, num_units_layer_3=10, num_units_layer_4=10,
                 num_units_layer_5=10, num_units_layer_6=10,
                 dropout_layer_2=0.5, dropout_layer_3=0.5, dropout_layer_4=0.5,
                 dropout_layer_5=0.5, dropout_layer_6=0.5,
                 std_layer_2=0.005, std_layer_3=0.005, std_layer_4=0.005,
                 std_layer_5=0.005, std_layer_6=0.005,
                 momentum=0.99, beta1=0.9, beta2=0.9, rho=0.95,
                 lr_policy='fixed', gamma=0.01, power=1.0, epoch_step=2,
                 leakiness=1./3., tanh_alpha=2./3., tanh_beta=1.7159,
                 random_state=None):
        self.number_updates = number_updates
        self.batch_size = batch_size
        # Hacky implementation of condition on number of layers
        self.num_layers = ord(num_layers) - ord('a')
        self.dropout_output = dropout_output
        self.learning_rate = learning_rate
        self.lr_policy = lr_policy
        self.lambda2 = lambda2
        self.momentum = momentum if momentum is not None else 0.9
        self.beta1 = 1-beta1 if beta1 is not None else 0.9
        self.beta2 = 1-beta2 if beta2 is not None else 0.99
        self.rho = rho if rho is not None else 0.95
        self.solver = solver
        self.activation = activation
        self.gamma = gamma if gamma is not None else 0.01
        self.power = power if power is not None else 1.0
        self.epoch_step = epoch_step if epoch_step is not None else 2
        self.leakiness = leakiness if leakiness is not None else 1./3.
        self.tanh_alpha = tanh_alpha if tanh_alpha is not None else 2./3.
        self.tanh_beta = tanh_beta if tanh_beta is not None else 1.7159

        # Empty features and shape
        self.n_features = None
        self.input_shape = None
        self.m_issparse = False
        self.m_isregression = True

        # To avoid eval call. Could be done with **karws
        args = locals()

        self.num_units_per_layer = []
        self.dropout_per_layer = []
        self.std_per_layer = []
        for i in range(1, self.num_layers):
            self.num_units_per_layer.append(int(args.get("num_units_layer_" + str(i))))
            self.dropout_per_layer.append(float(args.get("dropout_layer_" + str(i))))
            self.std_per_layer.append(float(args.get("std_layer_" + str(i))))
        self.estimator = None

    def _prefit(self, X, y):
        self.batch_size = int(self.batch_size)
        self.n_features = X.shape[1]
        self.input_shape = (self.batch_size, self.n_features)

        assert len(self.num_units_per_layer) == self.num_layers - 1,\
            "Number of created layers is different than actual layers"
        assert len(self.dropout_per_layer) == self.num_layers - 1,\
            "Number of created layers is different than actual layers"

        self.num_output_units = 1  # Regression
        # Normalize the output
        self.mean_y = np.mean(y)
        self.std_y = np.std(y)
        y = (y - self.mean_y) / self.std_y
        if len(y.shape) == 1:
            y = y[:, np.newaxis]

        self.m_issparse = sp.issparse(X)

        return X, y

    def fit(self, X, y):

        Xf, yf = self._prefit(X, y)

        epoch = (self.number_updates * self.batch_size)//X.shape[0]
        number_epochs = min(max(2, epoch), 50)  # Cap the max number of possible epochs

        from implementation import FeedForwardNet
        self.estimator = FeedForwardNet.FeedForwardNet(batch_size=self.batch_size,
                                                       input_shape=self.input_shape,
                                                       num_layers=self.num_layers,
                                                       num_units_per_layer=self.num_units_per_layer,
                                                       dropout_per_layer=self.dropout_per_layer,
                                                       std_per_layer=self.std_per_layer,
                                                       num_output_units=self.num_output_units,
                                                       dropout_output=self.dropout_output,
                                                       learning_rate=self.learning_rate,
                                                       lr_policy=self.lr_policy,
                                                       lambda2=self.lambda2,
                                                       momentum=self.momentum,
                                                       beta1=self.beta1,
                                                       beta2=self.beta2,
                                                       rho=self.rho,
                                                       solver=self.solver,
                                                       activation=self.activation,
                                                       num_epochs=number_epochs,
                                                       gamma=self.gamma,
                                                       power=self.power,
                                                       epoch_step=self.epoch_step,
                                                       leakiness=self.leakiness,
                                                       tanh_alpha=self.tanh_alpha,
                                                       tanh_beta=self.tanh_beta,
                                                       is_sparse=self.m_issparse,
                                                       is_binary=False,
                                                       is_regression=self.m_isregression)
        self.estimator.fit(Xf, yf)
        return self

    def predict(self, X):
        if self.estimator is None:
            raise NotImplementedError
        preds = self.estimator.predict(X, self.m_issparse)
        return preds * self.std_y + self.mean_y

    def predict_proba(self, X):
        if self.estimator is None:
            raise NotImplementedError()
        return self.estimator.predict_proba(X, self.m_issparse)

    @staticmethod
    def get_properties(dataset_properties=None):
        return {'shortname': 'reg_feed_nn',
                'name': 'Regression Feed Forward Neural Network',
                'handles_regression': True,
                'handles_classification': False,
                'handles_multiclass': False,
                'handles_multilabel': False,
                'is_deterministic': True,
                'input': (DENSE, SPARSE, UNSIGNED_DATA),
                'output': (PREDICTIONS,)}

    @staticmethod
    def get_hyperparameter_search_space(dataset_properties=None):
        # Hacky way to condition layers params based on the number of layers
        # 'c'=1, 'd'=2, 'e'=3 ,'f'=4', g ='5', h='6' + output_layer
        layer_choices = [chr(i) for i in range(ord('c'), ord('i'))]

        batch_size = UniformIntegerHyperparameter("batch_size",
                                                  32, 4096,
                                                  log=True,
                                                  default=32)

        number_updates = UniformIntegerHyperparameter("number_updates",
                                                      50, 3500,
                                                      log=True,
                                                      default=200)

        num_layers = CategoricalHyperparameter("num_layers",
                                               choices=layer_choices,
                                               default='c')

        # <editor-fold desc="Number of units in layers 1-6">
        num_units_layer_1 = UniformIntegerHyperparameter("num_units_layer_1",
                                                         64, 4096,
                                                         log=True,
                                                         default=256)

        num_units_layer_2 = UniformIntegerHyperparameter("num_units_layer_2",
                                                         64, 4096,
                                                         log=True,
                                                         default=128)

        num_units_layer_3 = UniformIntegerHyperparameter("num_units_layer_3",
                                                         64, 4096,
                                                         log=True,
                                                         default=128)

        num_units_layer_4 = UniformIntegerHyperparameter("num_units_layer_4",
                                                         10, 6144,
                                                         log=True,
                                                         default=10)

        num_units_layer_5 = UniformIntegerHyperparameter("num_units_layer_5",
                                                         10, 6144,
                                                         log=True,
                                                         default=10)

        num_units_layer_6 = UniformIntegerHyperparameter("num_units_layer_6",
                                                         10, 6144,
                                                         log=True,
                                                         default=10)
        # </editor-fold>

        # <editor-fold desc="Dropout in layers 1-6">
        dropout_layer_1 = UniformFloatHyperparameter("dropout_layer_1",
                                                     0.0, 0.99,
                                                     default=0.5)

        dropout_layer_2 = UniformFloatHyperparameter("dropout_layer_2",
                                                     0.0, 0.99,
                                                     default=0.5)

        dropout_layer_3 = UniformFloatHyperparameter("dropout_layer_3",
                                                     0.0, 0.99,
                                                     default=0.5)

        dropout_layer_4 = UniformFloatHyperparameter("dropout_layer_4",
                                                     0.0, 0.99,
                                                     default=0.5)

        dropout_layer_5 = UniformFloatHyperparameter("dropout_layer_5",
                                                     0.0, 0.99,
                                                     default=0.5)

        dropout_layer_6 = UniformFloatHyperparameter("dropout_layer_6",
                                                     0.0, 0.99,
                                                     default=0.5)
        # </editor-fold>

        dropout_output = UniformFloatHyperparameter("dropout_output",
                                                    0.0, 0.99,
                                                    default=0.5)

        lr = UniformFloatHyperparameter("learning_rate", 1e-6, 1.0,
                                        log=True,
                                        default=0.01)
        # TODO: Check with Aaron if lr for smorm3s should be categorical

        l2 = UniformFloatHyperparameter("lambda2", 1e-7, 1e-2,
                                        log=True,
                                        default=1e-4)

        # <editor-fold desc="Std for layers 1-6">
        std_layer_1 = UniformFloatHyperparameter("std_layer_1", 1e-6, 0.1,
                                                 log=True,
                                                 default=0.005)

        std_layer_2 = UniformFloatHyperparameter("std_layer_2", 0.001, 0.1,
                                                 log=True,
                                                 default=0.005)

        std_layer_3 = UniformFloatHyperparameter("std_layer_3", 0.001, 0.1,
                                                 log=True,
                                                 default=0.005)

        std_layer_4 = UniformFloatHyperparameter("std_layer_4", 0.001, 0.1,
                                                 log=True,
                                                 default=0.005)

        std_layer_5 = UniformFloatHyperparameter("std_layer_5", 0.001, 0.1,
                                                 log=True,
                                                 default=0.005)

        std_layer_6 = UniformFloatHyperparameter("std_layer_6", 0.001, 0.1,
                                                 log=True,
                                                 default=0.005)
        # </editor-fold>

        solver_choices = ["adam", "adadelta", "adagrad",
                          "sgd", "momentum", "nesterov",
                          "smorm3s"]

        solver = CategoricalHyperparameter(name="solver",
                                           choices=solver_choices,
                                           default="smorm3s")

        beta1 = UniformFloatHyperparameter("beta1", 1e-4, 0.1,
                                           log=True,
                                           default=0.1)

        beta2 = UniformFloatHyperparameter("beta2", 1e-4, 0.1,
                                           log=True,
                                           default=0.01)

        rho = UniformFloatHyperparameter("rho", 0.05, 0.99,
                                         log=True,
                                         default=0.95)

        momentum = UniformFloatHyperparameter("momentum", 0.3, 0.999,
                                              default=0.9)

        # TODO: Add policy based on this sklearn sgd
        policy_choices = ['fixed', 'inv', 'exp', 'step']

        lr_policy = CategoricalHyperparameter(name="lr_policy",
                                              choices=policy_choices,
                                              default='fixed')

        gamma = UniformFloatHyperparameter(name="gamma",
                                           lower=1e-3, upper=1e-1,
                                           default=1e-2)

        power = UniformFloatHyperparameter("power",
                                           0.0, 1.0,
                                           default=0.5)

        epoch_step = UniformIntegerHyperparameter("epoch_step",
                                                  2, 20,
                                                  default=5)

        output_activations = ['linear']

        other_tasks_activations = ['sigmoid', 'tanh', 'scaledTanh', 'elu',
                                   'relu', 'leaky', 'linear']

        nonlinearities = CategoricalHyperparameter(name='activation',
                                                   choices=other_tasks_activations,
                                                   default='tanh')

        leakiness = UniformFloatHyperparameter('leakiness',
                                               0.01, 0.99,
                                               default=0.3)

        # http://lasagne.readthedocs.io/en/latest/modules/nonlinearities.html
        # #lasagne.nonlinearities.ScaledTanH
        # For normalized inputs, tanh_alpha = 2./3. and tanh_beta = 1.7159,
        # according to http://yann.lecun.com/exdb/publis/pdf/lecun-98b.pdf

        # TODO: Review the bounds
        tanh_alpha = UniformFloatHyperparameter('tanh_alpha', 0.5, 1.0,
                                                default=2. / 3.)
        tanh_beta = UniformFloatHyperparameter('tanh_beta', 1.1, 3.0,
                                               log=True,
                                               default=1.7159)

        # TODO: Add weight initialization function

        cs = ConfigurationSpace()
        # cs.add_hyperparameter(number_epochs)
        cs.add_hyperparameter(number_updates)
        cs.add_hyperparameter(batch_size)
        cs.add_hyperparameter(num_layers)
        cs.add_hyperparameter(num_units_layer_1)
        cs.add_hyperparameter(num_units_layer_2)
        cs.add_hyperparameter(num_units_layer_3)
        cs.add_hyperparameter(num_units_layer_4)
        cs.add_hyperparameter(num_units_layer_5)
        cs.add_hyperparameter(num_units_layer_6)
        cs.add_hyperparameter(dropout_layer_1)
        cs.add_hyperparameter(dropout_layer_2)
        cs.add_hyperparameter(dropout_layer_3)
        cs.add_hyperparameter(dropout_layer_4)
        cs.add_hyperparameter(dropout_layer_5)
        cs.add_hyperparameter(dropout_layer_6)
        cs.add_hyperparameter(dropout_output)
        cs.add_hyperparameter(std_layer_1)
        cs.add_hyperparameter(std_layer_2)
        cs.add_hyperparameter(std_layer_3)
        cs.add_hyperparameter(std_layer_4)
        cs.add_hyperparameter(std_layer_5)
        cs.add_hyperparameter(std_layer_6)
        cs.add_hyperparameter(lr)
        cs.add_hyperparameter(l2)
        cs.add_hyperparameter(solver)
        cs.add_hyperparameter(beta1)
        cs.add_hyperparameter(beta2)
        cs.add_hyperparameter(momentum)
        cs.add_hyperparameter(rho)
        cs.add_hyperparameter(lr_policy)
        cs.add_hyperparameter(gamma)
        cs.add_hyperparameter(power)
        cs.add_hyperparameter(epoch_step)
        cs.add_hyperparameter(nonlinearities)
        cs.add_hyperparameter(leakiness)
        cs.add_hyperparameter(tanh_alpha)
        cs.add_hyperparameter(tanh_beta)

        args = locals()
        max_num_layers = 7  # Maximum number of layers coded

        # TODO: Could be in a function in a new module
        for i in range(2, max_num_layers):
            # Condition layers parameter on layer choice
            layer_unit_param = args.get("num_units_layer_" + str(i))
            layer_cond = InCondition(child=layer_unit_param, parent=num_layers,
                                     values=[l for l in layer_choices[i - 1:]])
            cs.add_condition(layer_cond)
            # Condition dropout parameter on layer choice
            layer_dropout_param = args.get("dropout_layer_" + str(i))
            layer_cond = InCondition(child=layer_dropout_param, parent=num_layers,
                                     values=[l for l in layer_choices[i - 1:]])
            cs.add_condition(layer_cond)
            # Condition std parameter on layer choice
            layer_std_param = args.get("std_layer_" + str(i))
            layer_cond = InCondition(child=layer_std_param, parent=num_layers,
                                     values=[l for l in layer_choices[i - 1:]])
            cs.add_condition(layer_cond)

        # Conditioning on solver
        momentum_depends_on_solver = InCondition(momentum, solver,
                                                 values=["momentum", "nesterov"])
        beta1_depends_on_solver = EqualsCondition(beta1, solver, "adam")
        beta2_depends_on_solver = EqualsCondition(beta2, solver, "adam")
        rho_depends_on_solver = EqualsCondition(rho, solver, "adadelta")

        cs.add_condition(momentum_depends_on_solver)
        cs.add_condition(beta1_depends_on_solver)
        cs.add_condition(beta2_depends_on_solver)
        cs.add_condition(rho_depends_on_solver)

        # Conditioning on learning rate policy
        lr_policy_depends_on_solver = InCondition(lr_policy, solver,
                                                  ["adadelta", "adagrad", "sgd",
                                                   "momentum", "nesterov"])
        gamma_depends_on_policy = InCondition(child=gamma, parent=lr_policy,
                                              values=["inv", "exp", "step"])
        power_depends_on_policy = EqualsCondition(power, lr_policy, "inv")
        epoch_step_depends_on_policy = EqualsCondition(epoch_step, lr_policy, "step")

        cs.add_condition(lr_policy_depends_on_solver)
        cs.add_condition(gamma_depends_on_policy)
        cs.add_condition(power_depends_on_policy)
        cs.add_condition(epoch_step_depends_on_policy)

        # Conditioning on activation function
        leakiness_depends_on_activation = EqualsCondition(child=leakiness,
                                                          parent=nonlinearities,
                                                          value="leaky")
        tanh_alpha_depends_on_activation = EqualsCondition(child=tanh_alpha,
                                                           parent=nonlinearities,
                                                           value="scaledTanh")
        tanh_beta_depends_on_activation = EqualsCondition(child=tanh_beta,
                                                          parent=nonlinearities,
                                                          value="scaledTanh")

        cs.add_condition(leakiness_depends_on_activation)
        cs.add_condition(tanh_alpha_depends_on_activation)
        cs.add_condition(tanh_beta_depends_on_activation)
        return cs
