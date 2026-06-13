import json

class ZScoreAnomalyDetector:

    def __init__(self, window=50, threshold=3.0):
        self.window    = window
        self.threshold = threshold
        self.stats     = {}

    @classmethod
    def load(cls, filepath):
        """Load model from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        model = cls(window=data['window'], threshold=data['threshold'])
        model.stats = data['stats']
        return model

    def score(self, metric, value):
        stat = self.stats[metric]
        if stat['std'] == 0:
            return 0
        return abs(value - stat['mean']) / stat['std']

    def predict(self, metric, value):
        z = self.score(metric, value)
        if z > self.threshold * 1.5:
            severity = 'critical'
        elif z > self.threshold:
            severity = 'warning'
        else:
            severity = 'normal'

        return {
            'is_anomaly': z > self.threshold,
            'z_score':    round(z, 2),
            'severity':   severity,
            'mean':       round(self.stats[metric]['mean'], 1),
            'std':        round(self.stats[metric]['std'], 1),
        }