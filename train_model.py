import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# 1. Load dataset
df = pd.read_csv("sleep_data.csv")  # <-- save your dataset as sleep_data.csv

# 2. Features (X) and Target (y)
X = df[["Sleep_Duration", "Interruptions", "Tiredness_Level", "Screen_Time"]]
y = df["Sleep_Risk"]

# 3. Split dataset
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Train Random Forest model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Test accuracy (optional)
accuracy = model.score(X_test, y_test)
print(f"Model Accuracy: {accuracy:.2f}")

# 6. Save the model
with open("sleep_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained and saved as sleep_model.pkl")
