from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
from model_preprocesser import preprocess_data




#Load the merged data file
ALL_DATA_PATH = "backend/data/processed_data/merged_data.csv"
all_data = pd.read_csv(ALL_DATA_PATH)

all_data = preprocess_data(all_data)


#Set variables
X = all_data.drop(columns = ["close_price"])
y = all_data["close_price"]

print("x y assigned")



X_train, X_test, y_train, y_test = train_test_split(X,y, test_size = .2, random_state = 42)
print("split data assigned")


xg = XGBRegressor(
    n_estimators = 100,
    max_depth = 3,
    learning_rate = .1,
    objective = 'reg:squarederror',
    random_state = 42,
    device = 'CUDA'
    )

rf = RandomForestRegressor(
    n_estimators = 100,
    max_depth = None,
    random_state = 42

)


#Fit models

xg.fit(X_train, y_train)
print("fitted xgboost model")
rf.fit(X_train, y_train)
print("fitted random forest model")

#Record accuracy

xg_TestAccuracy = xg.score(X_test, y_test)
rf_TestAccuracy = rf.score(X_test, y_test)

xg_TrainAccuracy = xg.score(X_train, y_train)
rf_TrainAccuracy = rf.score(X_train, y_train)


print(f"xgboost train and test accuracy: Train... {xg_TrainAccuracy}\nTest... {xg_TestAccuracy}")
print(f"random train and test forest accuracy: Train... {rf_TrainAccuracy}\nTest... {rf_TestAccuracy}")


