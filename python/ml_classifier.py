"""anomaly_noticer.ml_classifier -- ML spam classifier with auto model discovery."""
import os
import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix
from anomaly_noticer.canon import fix_newlines, mask, squeeze, collapse, shape_features
import anomaly_noticer.data as noticer_data
import importlib.resources as pkg_resources

def _get_model_path():
    with pkg_resources.path(noticer_data, 'model.joblib') as path:
        return str(path)


class MLClassifier:
    """Loads the trained model once, provides fast per-post scoring."""

    def __init__(self, model_path=None, threshold=0.95):
        if model_path is None:
            model_path = _get_model_path()

        artifacts = joblib.load(model_path)
        self.clf = artifacts['clf']
        self.collapsed_tfidf = artifacts['collapsed_tfidf']
        self.squeezed_tfidf = artifacts['squeezed_tfidf']
        self.threshold = threshold

    def predict_proba(self, text):
        """Returns probability [0.0, 1.0] that text is spam."""
        if not text or len(text.strip()) < 5:
            return 0.0

        canon = mask(fix_newlines(text))
        if len(canon) < 5:
            return 0.0

        collapsed = collapse(canon)
        squeezed  = squeeze(canon)

        X_collapsed = self.collapsed_tfidf.transform([collapsed])
        X_squeezed  = self.squeezed_tfidf.transform([squeezed])
        X_shape     = csr_matrix(np.array([shape_features(canon)]))

        X = hstack([X_collapsed, X_squeezed, X_shape])
        return float(self.clf.predict_proba(X)[0, 1])

    def is_spam(self, text):
        """Returns (is_spam: bool, probability: float)."""
        prob = self.predict_proba(text)
        return prob >= self.threshold, prob
