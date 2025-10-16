from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
import pandas as pd





ALL_DATA_PATH = "backend/data/processed_data/merged_data.csv"

all_data = pd.read_csv(ALL_DATA_PATH)




X = all_data.drop(columns = ["close_price"])
y = all_data["close_price"]

print("x y assigned")



X_train, X_test, y_train, y_test = train_test_split(X,y, test_size = .2, random_state = 42)
print("split data assigned")


xg = XGBRegressor(
    n_estimators = 2,
    max_depth = 2,
    learning_rate = 1,
    objective = 'binary:logistic'
)

rf = RandomForestRegressor(
    n_estimators = 100,
    max_depth = None,
    min_samples_split = 2,
    min_samples_leaf = 1,
    random_state = 42,

)


#Fit models

xg.fit(X_train, y_train)
print("fitted xgboost model")
rf.fit(X_train, y_train)
print("fitted random forest model")

#Record accuracy

xg_accuracy = xg.score(X_test, y_test)
rf_accuracy = rf.score(X_test, y_test)


