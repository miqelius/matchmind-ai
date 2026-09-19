import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

class MatchPredictor:
    def __init__(self):
        # ლოგისტიკური რეგრესიის მოდელი ბაზისური პროგნოზებისთვის
        self.model = LogisticRegression()
        self._train_dummy_model()

    def _train_dummy_model(self):
        # საწყისი სავარჯიშო მონაცემები: [მასპინძლის ფორმა, სტუმრის ფორმა, ურთიერთშეხვედრების უპირატესობა]
        X_train = np.array([
            [3, 1, 1.2],
            [1, 3, 0.8],
            [2, 2, 1.0],
            [3, 0, 1.5],
            [0, 3, 0.5],
            [1, 1, 1.0]
        ])
        # შედეგები: 1 თუ მასპინძელმა მოიგო, 0 წინააღმდეგ შემთხვევაში
        y_train = np.array([1, 0, 1, 1, 0, 0])
        self.model.fit(X_train, y_train)

    def predict_match(self, home_form: float, away_form: float, h2h: float):
        features = np.array([[home_form, away_form, h2h]])
        probs = self.model.predict_proba(features)[0]
        home_prob = round(probs[1] * 100, 1)
        away_prob = round(probs[0] * 100, 1)
        
        # ალბათობების გადაყვანა სიმულირებულ კუშებში
        home_odd = round(100 / home_prob * 1.05, 2) if home_prob > 0 else 2.0
        away_odd = round(100 / away_prob * 1.05, 2) if away_prob > 0 else 2.0
        
        return {
            "home_prob": home_prob,
            "away_prob": away_prob,
            "home_odd": home_odd,
            "away_odd": away_odd
        }

    def evaluate_prediction(self, y_true, y_prob):
        # Brier Score-ის მეტრიკა სიზუსტის შესაფასებლად
        return float(brier_score_loss(y_true, y_prob))

predictor = MatchPredictor()
