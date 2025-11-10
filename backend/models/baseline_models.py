from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
from keras.layers import LSTM, Dense, Dropout
from keras.layers import MultiHeadAttention, LayerNormalization, Dense, Input, Flatten
import pandas as pd
from evaluate import evaluate_model
import numpy as np







#Load the merged data file
ALL_DATA_PATH = "backend/data/processed_data/final_processed_data.csv"

all_data = pd.read_csv(ALL_DATA_PATH)


#Set variables
X = all_data.drop(columns = ["target_pct_change", "close_price"])
y = all_data["target_pct_change"]

print("x y assigned")



X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)


#XGboost model
xg = XGBRegressor(
    n_estimators = 100,
    max_depth = 3,
    learning_rate = .1,
    objective = 'reg:squarederror',
    random_state = 42,
    device = 'cuda'
    )

#Random Forest model
rf = RandomForestRegressor(
    n_estimators = 100,
    max_depth = None,
    random_state = 42

)

# Light GBM model
lgbm = LGBMRegressor(
    n_estimators = 100,
    learning_rate = .01,
    num_leaves = 31,
    random_state = 42
)

#Cat boost model
cat = CatBoostRegressor(
    iterations=200,
    learning_rate=0.05,
    depth=6,
    loss_function='RMSE',
    verbose=False,
    random_seed=42
)




#Fit models

xg.fit(X_train, y_train)
print("fitted xgboost model")
rf.fit(X_train, y_train)
print("fitted random forest model")
lgbm.fit(X_train, y_train)
print("fitted lightGBM model")
cat.fit(X_train, y_train)
print("fitted catboost model")

#Record accuracy and evaluate models...



if __name__ == "__main__":
    evaluate_model("XGBoost Regressor", xg, X_train, y_train, X_test, y_test)
    evaluate_model("Random Forest Regressor", rf, X_train, y_train, X_test, y_test)
    evaluate_model("LightGBM Regressor", lgbm, X_train, y_train, X_test, y_test)
    evaluate_model("CatBoost Regressor", cat, X_train, y_train, X_test, y_test)



#implement lightGBM, CatBoost, LSTM, Transformer models later

