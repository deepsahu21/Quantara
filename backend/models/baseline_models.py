from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
from keras.models import Model
from keras.layers import MultiHeadAttention, LayerNormalization, Dense, Input, Flatten, LSTM, Dropout, Add, Reshape
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
import pandas as pd
from backend.models.evaluate import evaluate_model
import numpy as np


# Load the processed data file
ALL_DATA_PATH = "backend/data/processed_data/final_processed_data.csv"

all_data = pd.read_csv(ALL_DATA_PATH)


# Set variables
X = all_data.drop(
    columns=["target_pct_change", "target_vol_norm", "close_price"]
)
y = all_data["target_vol_norm"]
y_pct_change = all_data["target_pct_change"]  # For realized return calculations

print("x y assigned")


# Split data - use explicit indices to ensure consistency
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
y_test_pct_change = y_pct_change.iloc[split_idx:]  # Corresponding target_pct_change for test set

# Scale data for neural networks (LSTM and Transformer)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
n_features = X_train_scaled.shape[1]

print(f"Data shape: {X_train_scaled.shape[0]} train, {X_test_scaled.shape[0]} test, {n_features} features")


# XGBoost model
xg = XGBRegressor(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.7,
    colsample_bytree=0.7,
    reg_alpha=0.3,
    reg_lambda=2.0,
    objective='reg:squarederror',
    random_state=42,
    device='cuda'
)


# Random Forest model
rf = RandomForestRegressor(
    n_estimators=300,
    max_depth=8,
    min_samples_split=20,
    min_samples_leaf=10,
    max_features='sqrt',
    random_state=42,
    n_jobs=-1
)


# Light GBM model
lgbm = LGBMRegressor(
    n_estimators=100,
    learning_rate=0.01,
    num_leaves=31,
    random_state=42
)


# CatBoost model
cat = CatBoostRegressor(
    iterations=200,
    learning_rate=0.05,
    depth=6,
    loss_function='RMSE',
    verbose=False,
    random_seed=42
)


# ===== LSTM Model =====
def build_lstm_model(n_features, lstm_units=128, dense_units=64, dropout_rate=0.2):
    """Build LSTM model for tabular regression
    
    For tabular data, we use dense layers to create embeddings, then reshape
    to sequence format for LSTM processing.
    """
    inputs = Input(shape=(n_features,))
    
    # Dense embedding layers
    x = Dense(256, activation='relu')(inputs)
    x = Dropout(dropout_rate)(x)
    x = Dense(128, activation='relu')(x)
    x = Dropout(dropout_rate)(x)
    
    # Reshape to sequence format: (batch, timesteps=1, features)
    # We treat the entire feature vector as a single timestep
    x = Reshape((1, 128))(x)
    
    # LSTM layers
    x = LSTM(lstm_units, return_sequences=True)(x)
    x = Dropout(dropout_rate)(x)
    x = LSTM(lstm_units // 2, return_sequences=False)(x)
    x = Dropout(dropout_rate)(x)
    
    # Dense output layers
    x = Dense(dense_units, activation='relu')(x)
    x = Dropout(dropout_rate)(x)
    outputs = Dense(1, activation='linear')(x)
    
    model = Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
    return model

# ===== Transformer Model =====
def build_transformer_model(n_features, d_model=128, num_heads=4, num_layers=2, dropout_rate=0.2):
    """Build Transformer encoder model for tabular regression"""
    inputs = Input(shape=(n_features,))
    
    # Project input to d_model dimensions
    x = Dense(d_model)(inputs)
    
    # Reshape for attention: (batch, seq_len=1, d_model)
    # We treat each sample as a single token
    x = Reshape((1, d_model))(x)
    
    # Transformer encoder layers
    for _ in range(num_layers):
        # Multi-head self-attention
        attn_output = MultiHeadAttention(num_heads=num_heads, key_dim=d_model // num_heads)(x, x)
        attn_output = Dropout(dropout_rate)(attn_output)
        
        # Add & Norm
        x = Add()([x, attn_output])
        x = LayerNormalization()(x)
        
        # Feed-forward network
        ffn_output = Dense(d_model * 2, activation='relu')(x)
        ffn_output = Dropout(dropout_rate)(ffn_output)
        ffn_output = Dense(d_model)(ffn_output)
        ffn_output = Dropout(dropout_rate)(ffn_output)
        
        # Add & Norm
        x = Add()([x, ffn_output])
        x = LayerNormalization()(x)
    
    # Flatten and output
    x = Flatten()(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(dropout_rate)(x)
    outputs = Dense(1, activation='linear')(x)
    
    model = Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
    return model

# ===== Wrapper classes for neural network models =====
class ScaledModelWrapper:
    """Wrapper to handle scaling for neural network models"""
    def __init__(self, model, scaler):
        self.model = model
        self.scaler = scaler
    
    def predict(self, X):
        if hasattr(X, 'values'):
            X = X.values
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled, verbose=0).flatten()


if __name__ == "__main__":
    # Fit models
    xg.fit(X_train, y_train)
    print("fitted xgboost model")

    rf.fit(X_train, y_train)
    print("fitted random forest model")

    lgbm.fit(X_train, y_train)
    print("fitted lightGBM model")

    cat.fit(X_train, y_train)
    print("fitted catboost model")

    lstm = build_lstm_model(n_features, lstm_units=128, dense_units=64, dropout_rate=0.2)
    print("built LSTM model")

    lstm_callbacks = [
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
    ]

    lstm.fit(
        X_train_scaled, y_train.values,
        validation_split=0.1,
        epochs=50,
        batch_size=256,
        callbacks=lstm_callbacks,
        verbose=0
    )
    print("fitted LSTM model")

    transformer = build_transformer_model(n_features, d_model=128, num_heads=4, num_layers=2, dropout_rate=0.2)
    print("built Transformer model")

    transformer_callbacks = [
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
    ]

    transformer.fit(
        X_train_scaled, y_train.values,
        validation_split=0.1,
        epochs=50,
        batch_size=256,
        callbacks=transformer_callbacks,
        verbose=0
    )
    print("fitted Transformer model")

    lstm_wrapped = ScaledModelWrapper(lstm, scaler)
    transformer_wrapped = ScaledModelWrapper(transformer, scaler)

    # RELAXED THRESHOLDS for increased signal frequency while preserving edge
    # These are calibrated to increase Strong+Moderate signals without destroying honesty
    RELAXED_THRESHOLDS = {
        'do_not_trade_threshold': 0.5,   # Keep this - still filter out very weak signals
        'low_threshold': 0.75,            # Relaxed from 1.0
        'moderate_threshold': 1.5,        # Relaxed from 2.0 (Strong now starts at 1.5σ instead of 2.0σ)
        'min_sigma_filter': 1.25          # Minimum signal strength required
    }
    
    print("\n" + "="*80)
    print("EVALUATING WITH RELAXED THRESHOLDS")
    print("="*80)
    print(f"Do Not Trade: < {RELAXED_THRESHOLDS['do_not_trade_threshold']}σ")
    print(f"Low: {RELAXED_THRESHOLDS['do_not_trade_threshold']}σ - {RELAXED_THRESHOLDS['low_threshold']}σ")
    print(f"Moderate: {RELAXED_THRESHOLDS['low_threshold']}σ - {RELAXED_THRESHOLDS['moderate_threshold']}σ")
    print(f"Strong: >= {RELAXED_THRESHOLDS['moderate_threshold']}σ")
    print(f"Minimum σ filter: {RELAXED_THRESHOLDS['min_sigma_filter']}σ")
    print("="*80)
    
    # Evaluate all models with relaxed thresholds
    results = []
    results.append(evaluate_model("XGBoost Regressor", xg, X_train, y_train, X_test, y_test, y_test_pct_change, **RELAXED_THRESHOLDS))
    results.append(evaluate_model("Random Forest Regressor", rf, X_train, y_train, X_test, y_test, y_test_pct_change, **RELAXED_THRESHOLDS))
    results.append(evaluate_model("LightGBM Regressor", lgbm, X_train, y_train, X_test, y_test, y_test_pct_change, **RELAXED_THRESHOLDS))
    results.append(evaluate_model("CatBoost Regressor", cat, X_train, y_train, X_test, y_test, y_test_pct_change, **RELAXED_THRESHOLDS))
    results.append(evaluate_model("LSTM", lstm_wrapped, X_train, y_train, X_test, y_test, y_test_pct_change, **RELAXED_THRESHOLDS))
    results.append(evaluate_model("Transformer", transformer_wrapped, X_train, y_train, X_test, y_test, y_test_pct_change, **RELAXED_THRESHOLDS))
    
    # Print comprehensive summary comparison
    print("\n" + "="*100)
    print("MODEL COMPARISON SUMMARY - Signal Quality Metrics")
    print("="*100)
    
    # Strong-only metrics
    print(f"\n{'Model':<25} {'Strong Win Rate':<18} {'Strong Avg Return':<20} {'Strong Count':<15} {'Sigma':<10}")
    print("-"*100)
    for r in results:
        win_rate_str = f"{r['strong_win_rate']:.2f}%" if r['strong_win_rate'] is not None else "N/A"
        avg_return_str = f"{r['strong_avg_return']:+.4f}%" if r['strong_avg_return'] is not None else "N/A"
        print(f"{r['name']:<25} {win_rate_str:<18} {avg_return_str:<20} {r['strong_count']:<15} {r['sigma']:.4f}")
    
    # Moderate+Strong combined (most important for real trading)
    print(f"\n{'Model':<25} {'M+S Win Rate':<18} {'M+S Avg Return':<20} {'M+S Count':<15} {'M+S %':<10}")
    print("-"*100)
    for r in results:
        ms_metrics = r.get('moderate_strong_metrics', {})
        win_rate_str = f"{ms_metrics.get('win_rate', 0):.2f}%" if ms_metrics.get('win_rate') is not None else "N/A"
        avg_return_str = f"{ms_metrics.get('avg_return', 0):+.4f}%" if ms_metrics.get('avg_return') is not None else "N/A"
        count = ms_metrics.get('count', 0)
        total = len(y_test)
        pct_str = f"{count/total*100:.2f}%" if total > 0 else "N/A"
        print(f"{r['name']:<25} {win_rate_str:<18} {avg_return_str:<20} {count:<15} {pct_str:<10}")
    
    print("="*100)
    
    # Identify lead model based on Moderate+Strong performance
    print("\n" + "="*100)
    print("LEAD MODEL SELECTION (Based on Moderate+Strong Performance)")
    print("="*100)
    
    # Sort by Moderate+Strong win rate, then by avg return
    valid_results = [r for r in results if r.get('moderate_strong_metrics', {}).get('win_rate') is not None]
    if valid_results:
        sorted_results = sorted(valid_results, 
                               key=lambda x: (
                                   x.get('moderate_strong_metrics', {}).get('win_rate', 0),
                                   x.get('moderate_strong_metrics', {}).get('avg_return', 0)
                               ), 
                               reverse=True)
        
        print(f"\n🥇 LEAD MODEL: {sorted_results[0]['name']}")
        ms = sorted_results[0].get('moderate_strong_metrics', {})
        print(f"   Moderate+Strong Win Rate: {ms.get('win_rate', 0):.2f}%")
        print(f"   Moderate+Strong Avg Return: {ms.get('avg_return', 0):+.4f}%")
        print(f"   Moderate+Strong Signal Count: {ms.get('count', 0)}")
        
        if len(sorted_results) > 1:
            print(f"\n🥈 BACKUP MODEL: {sorted_results[1]['name']}")
            ms2 = sorted_results[1].get('moderate_strong_metrics', {})
            print(f"   Moderate+Strong Win Rate: {ms2.get('win_rate', 0):.2f}%")
            print(f"   Moderate+Strong Avg Return: {ms2.get('avg_return', 0):+.4f}%")
    
    print("="*100)


# All models implemented: XGBoost, Random Forest, LightGBM, CatBoost, LSTM, Transformer
