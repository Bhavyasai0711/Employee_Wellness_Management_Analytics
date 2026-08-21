import random
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from Module2_EmployeeHealthData.models import EmployeeHealth

# Global model cache to persist trained classifiers, metrics, and importances in memory
_MODEL_CACHE = {}


def generate_synthetic_data(num_samples=200):
    data = []
    for _ in range(num_samples):
        age = random.randint(20, 62)
        bmi = round(random.uniform(17.0, 36.0), 1)
        heart_rate = random.randint(55, 115)
        sleep_hours = round(random.uniform(4.0, 9.5), 1)
        water = round(random.uniform(1.0, 4.0), 1)
        attendance = round(random.uniform(70.0, 100.0), 1)
        
        stress_level = random.choice(["Low", "Moderate", "High", "Severe"])
        stress_val = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3}[stress_level]
        
        exercise_freq = random.choice(["Never", "1-2 days/week", "3-4 days/week", "5+ days/week", "Daily"])
        exercise_val = {"Never": 0, "1-2 days/week": 1, "3-4 days/week": 2, "5+ days/week": 3, "Daily": 4}[exercise_freq]
        
        # Clinical correlation calculations
        risk_score = 0
        if bmi >= 30 or bmi < 18.5:
            risk_score += 20
        if stress_val >= 2:
            risk_score += 30
        if sleep_hours < 6.0:
            risk_score += 20
        if attendance < 80.0:
            risk_score += 15
        if heart_rate > 95 or heart_rate < 60:
            risk_score += 15
        if exercise_val <= 1:
            risk_score += 15
            
        if risk_score >= 60:
            risk_class = 2  # High
        elif risk_score >= 35:
            risk_class = 1  # Moderate
        else:
            risk_class = 0  # Low
            
        data.append([bmi, age, heart_rate, sleep_hours, water, attendance, stress_val, exercise_val, risk_class])
        
    cols = ["bmi", "age", "heart_rate", "sleep_hours", "daily_water_litres", "attendance_percentage", "stress_val", "exercise_val", "risk_class"]
    return pd.DataFrame(data, columns=cols)


def train_and_evaluate_models():
    records = EmployeeHealth.query.all()
    
    if len(records) >= 15:
        data = []
        for r in records:
            stress_val = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3}.get(r.stress_level, 1)
            ex_map = {"Never": 0, "1-2 days/week": 1, "3-4 days/week": 2, "5+ days/week": 3, "Daily": 4}
            exercise_val = ex_map.get(r.exercise_frequency, 2)
            
            if r.health_risk_score >= 60:
                risk_class = 2
            elif r.health_risk_score >= 35:
                risk_class = 1
            else:
                risk_class = 0
                
            data.append([
                r.bmi, r.age, r.heart_rate, r.sleep_hours,
                r.daily_water_litres, r.attendance_percentage,
                stress_val, exercise_val, risk_class
            ])
        cols = ["bmi", "age", "heart_rate", "sleep_hours", "daily_water_litres", "attendance_percentage", "stress_val", "exercise_val", "risk_class"]
        df = pd.DataFrame(data, columns=cols)
        
        # Merge with synthetic data to assure data density
        syn_df = generate_synthetic_data(150)
        df = pd.concat([df, syn_df], ignore_index=True)
    else:
        df = generate_synthetic_data(200)
        
    X = df.drop(columns=["risk_class"])
    y = df["risk_class"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    
    models = {
        "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=50, max_depth=4, learning_rate=0.1, random_state=42),
        "Neural Network": MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=300, random_state=42)
    }
    
    metrics = {}
    feature_importances = {}
    feature_names = list(X.columns)
    
    for name, clf in models.items():
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
        rec = recall_score(y_test, y_pred, average="macro", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
        
        metrics[name] = {
            "accuracy": round(acc * 100, 1),
            "precision": round(prec * 100, 1),
            "recall": round(rec * 100, 1),
            "f1_score": round(f1 * 100, 1)
        }
        
        if hasattr(clf, "feature_importances_"):
            importances = clf.feature_importances_
        else:
            # MLP uniform weight mapping
            importances = np.ones(len(feature_names)) / len(feature_names)
            
        feature_importances[name] = {feat: round(float(imp), 3) for feat, imp in zip(feature_names, importances)}
        
    _MODEL_CACHE["models"] = models
    _MODEL_CACHE["metrics"] = metrics
    _MODEL_CACHE["feature_importances"] = feature_importances
    _MODEL_CACHE["feature_names"] = feature_names
    
    return metrics, feature_importances


def predict_employee_risk(record, model_type="Random Forest"):
    if "models" not in _MODEL_CACHE:
        train_and_evaluate_models()
        
    models = _MODEL_CACHE.get("models", {})
    clf = models.get(model_type)
    if not clf:
        clf = list(models.values())[0] if models else None
        
    if not clf:
        return "Unknown", 0.0
        
    stress_val = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3}.get(record.stress_level, 1)
    ex_map = {"Never": 0, "1-2 days/week": 1, "3-4 days/week": 2, "5+ days/week": 3, "Daily": 4}
    exercise_val = ex_map.get(record.exercise_frequency, 2)
    
    X_input = pd.DataFrame([[
        record.bmi, record.age, record.heart_rate, record.sleep_hours,
        record.daily_water_litres, record.attendance_percentage,
        stress_val, exercise_val
    ]], columns=_MODEL_CACHE["feature_names"])
    
    pred_class = clf.predict(X_input)[0]
    
    if hasattr(clf, "predict_proba"):
        probs = clf.predict_proba(X_input)[0]
        prob = float(probs[pred_class])
    else:
        prob = 1.0
        
    class_map = {0: "Low", 1: "Moderate", 2: "High"}
    return class_map.get(pred_class, "Low"), round(prob * 100, 1)


def get_model_cache():
    if "models" not in _MODEL_CACHE:
        train_and_evaluate_models()
    return _MODEL_CACHE
