import unittest

from component.LogReg import LogReg
from autosklearn.pipeline.util import _test_classifier
import sklearn.metrics


class LogRegComponentTest(unittest.TestCase):

    def test_default_configuration(self):
        for i in range(10):
            predictions, targets = _test_classifier(LogReg, dataset='iris')
            acc_score = sklearn.metrics.accuracy_score(y_true=targets,
                                                       y_pred=predictions)
            print(acc_score)
            self.assertAlmostEqual(0.28, acc_score)

    def test_default_configuration_binary(self):
        for i in range(10):
            predictions, targets = _test_classifier(LogReg,
                                                    make_binary=True)
            acc_score = sklearn.metrics.accuracy_score(y_true=targets,
                                                       y_pred=predictions)
            print(acc_score)
            self.assertAlmostEqual(0.28, acc_score)

    def test_default_configuration_multilabel(self):
        for i in range(10):
            predictions, targets = _test_classifier(LogReg,
                                                    make_multilabel=True)
            acc_score = sklearn.metrics.accuracy_score(y_true=targets,
                                                       y_pred=predictions)
            print(acc_score)
            self.assertAlmostEqual(0.28, acc_score)
