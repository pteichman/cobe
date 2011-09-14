# Copyright (C) 2011 Peter Teichman

# Bayesian classifier, useful for class-based scorers

class BayesClass:
    def __init__(self, name):
        self.name = name

        self.train_total = 0
        self.token_total = 0

        self.token_counts = {}

    def train(self, tokens):
        counts = self.token_counts

        for token in tokens:
            try:
                counts[token] += 1
            except KeyError:
                counts[token] = 1
            self.token_total += 1

        self.train_total += 1

    def __repr__(self):
        return repr(self.token_counts)

class BayesClassifier:
    def __init__(self):
        self.classes = {}
        self.train_total = 0

    def train(self, tokens, class_name):
        if len(tokens) == 0:
            return

        tokens = set(tokens)

        cls = self.classes.setdefault(class_name, BayesClass(class_name))
        cls.train(tokens)

        self.train_total += 1

    def classify(self, tokens, class_name=None):
        tokens = set(tokens)

        if class_name is None:
            classes = self.classes
        else:
            classes = dict(class_name=self.classes[class_name])

        results = {}
        for name, cls in classes.items():
            total = cls.token_total
            counts = cls.token_counts

            p = 1.
            for token in tokens:
                p *= float(counts.get(token, 0) + 1) / total

            results[name] = float(cls.train_total)/self.train_total * p

        total = sum(results.values())

        # normalize
        for name, value in results.items():
            results[name] = value / total

        return results
