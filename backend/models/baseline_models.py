from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score





#Load the merged data file
ALL_DATA_PATH = "backend/data/processed_data/final_processed_data.csv"

all_data = pd.read_csv(ALL_DATA_PATH)


#Set variables
X = all_data.drop(columns = ["target_pct_change", "close_price"])
y = all_data["target_pct_change"]

print("x y assigned")



X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)


xg = XGBRegressor(
    n_estimators = 100,
    max_depth = 3,
    learning_rate = .1,
    objective = 'reg:squarederror',
    random_state = 42,
    device = 'cuda'
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

#Record accuracy and evaluate models...


# Evaluate XGBoost
xg_preds_train = xg.predict(X_train)
xg_preds_test = xg.predict(X_test)

xg_train_mae = mean_absolute_error(y_train, xg_preds_train)
xg_test_mae = mean_absolute_error(y_test, xg_preds_test)
xg_train_rmse = root_mean_squared_error(y_train, xg_preds_train)
xg_test_rmse = root_mean_squared_error(y_test, xg_preds_test)
xg_train_r2 = r2_score(y_train, xg_preds_train)
xg_test_r2 = r2_score(y_test, xg_preds_test)

print("\nXGBoost results...\n")
print(f"Train → MAE: {xg_train_mae:.4f}, RMSE: {xg_train_rmse:.4f}, R²: {xg_train_r2:.4f}")
print(f"Test  → MAE: {xg_test_mae:.4f}, RMSE: {xg_test_rmse:.4f}, R²: {xg_test_r2:.4f}")



# --- Evaluate Random Forest ---
rf_preds_train = rf.predict(X_train)
rf_preds_test = rf.predict(X_test)

rf_train_mae = mean_absolute_error(y_train, rf_preds_train)
rf_test_mae = mean_absolute_error(y_test, rf_preds_test)
rf_train_rmse = root_mean_squared_error(y_train, rf_preds_train)
rf_test_rmse = root_mean_squared_error(y_test, rf_preds_test)
rf_train_r2 = r2_score(y_train, rf_preds_train)
rf_test_r2 = r2_score(y_test, rf_preds_test)

print("\n RF results...\n")
print(f"Train → MAE: {rf_train_mae:.4f}, RMSE: {rf_train_rmse:.4f}, R²: {rf_train_r2:.4f}")
print(f"Test  → MAE: {rf_test_mae:.4f}, RMSE: {rf_test_rmse:.4f}, R²: {rf_test_r2:.4f}")
