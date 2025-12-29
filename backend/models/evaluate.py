from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import numpy as np


def classify_confidence(prediction, sigma, 
                       do_not_trade_threshold=0.5,
                       low_threshold=1.0,
                       moderate_threshold=2.0,
                       min_sigma_filter=1.25):
    """
    Classify prediction into confidence buckets based on magnitude relative to residual sigma.
    
    Parameters:
    -----------
    prediction : float
        Model prediction (target_vol_norm)
    sigma : float
        Residual standard deviation
    do_not_trade_threshold : float
        Multiplier for sigma below which we "do not trade" (default: 0.5)
    low_threshold : float
        Multiplier for sigma below which confidence is "low" (default: 1.0)
    moderate_threshold : float
        Multiplier for sigma below which confidence is "moderate" (default: 2.0)
    min_sigma_filter : float
        Minimum |prediction|/sigma required to generate any signal (default: 1.25)
        If prediction doesn't meet this, returns 'do_not_trade' regardless
    
    Returns:
    --------
    'strong_positive', 'strong_negative', 'moderate_positive', 'moderate_negative',
    'low_positive', 'low_negative', or 'do_not_trade'
    """
    abs_pred = abs(prediction)
    abs_pred_sigma = abs_pred / sigma if sigma > 0 else 0
    
    # Minimum sigma filter: require minimum signal strength
    if abs_pred_sigma < min_sigma_filter:
        return 'do_not_trade'
    
    # "Do not trade" - too uncertain (below relaxed threshold)
    if abs_pred_sigma < do_not_trade_threshold:
        return 'do_not_trade'
    
    # Low confidence
    elif abs_pred_sigma < low_threshold:
        return 'low_positive' if prediction > 0 else 'low_negative'
    
    # Moderate confidence
    elif abs_pred_sigma < moderate_threshold:
        return 'moderate_positive' if prediction > 0 else 'moderate_negative'
    
    # Strong confidence
    else:
        return 'strong_positive' if prediction > 0 else 'strong_negative'


def evaluate_model(name, model, X_train, y_train, X_test, y_test, y_test_pct_change=None,
                   do_not_trade_threshold=0.5,
                   low_threshold=1.0,
                   moderate_threshold=2.0,
                   min_sigma_filter=1.25):
    """
    Evaluate model with signal-quality metrics for Quantara.
    
    Parameters:
    -----------
    name : str
        Model name
    model : fitted model
        Trained model
    X_train, y_train : arrays
        Training data
    X_test, y_test : arrays
        Test data (y_test is target_vol_norm)
    y_test_pct_change : array, optional
        Actual target_pct_change for test set (needed for realized return calculations)
    do_not_trade_threshold : float
        Multiplier for sigma below which we "do not trade" (default: 0.5)
    low_threshold : float
        Multiplier for sigma below which confidence is "low" (default: 1.0)
    moderate_threshold : float
        Multiplier for sigma below which confidence is "moderate" (default: 2.0)
    min_sigma_filter : float
        Minimum |prediction|/sigma required to generate any signal (default: 1.25)
    """
    # Get predictions
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    # Calculate residual sigma (standard deviation of residuals)
    residuals_test = y_test - y_test_pred
    sigma = np.std(residuals_test)
    
    # Traditional metrics (still useful for reference)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    train_rmse = root_mean_squared_error(y_train, y_train_pred)
    test_rmse = root_mean_squared_error(y_test, y_test_pred)
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    
    # ===== SIGNAL QUALITY METRICS =====
    
    # Classify all test predictions into confidence buckets
    confidence_buckets = np.array([
        classify_confidence(pred, sigma, 
                           do_not_trade_threshold=do_not_trade_threshold,
                           low_threshold=low_threshold,
                           moderate_threshold=moderate_threshold,
                           min_sigma_filter=min_sigma_filter)
        for pred in y_test_pred
    ])
    
    # Count confidence bucket distribution
    unique, counts = np.unique(confidence_buckets, return_counts=True)
    bucket_counts = dict(zip(unique, counts))
    total_predictions = len(y_test_pred)
    
    # Calculate percentages
    bucket_pcts = {
        'strong_positive': bucket_counts.get('strong_positive', 0) / total_predictions * 100,
        'strong_negative': bucket_counts.get('strong_negative', 0) / total_predictions * 100,
        'moderate_positive': bucket_counts.get('moderate_positive', 0) / total_predictions * 100,
        'moderate_negative': bucket_counts.get('moderate_negative', 0) / total_predictions * 100,
        'low_positive': bucket_counts.get('low_positive', 0) / total_predictions * 100,
        'low_negative': bucket_counts.get('low_negative', 0) / total_predictions * 100,
        'do_not_trade': bucket_counts.get('do_not_trade', 0) / total_predictions * 100,
    }
    
    # Helper function to calculate metrics for a given mask
    def calculate_signal_metrics(mask, signal_name):
        """Calculate win rate and returns for signals matching the mask"""
        count = np.sum(mask)
        win_rate = None
        avg_return = None
        positive_avg_return = None
        negative_avg_return = None
        
        if count > 0 and y_test_pct_change is not None:
            y_test_pct_actual = y_test_pct_change.values if hasattr(y_test_pct_change, 'values') else y_test_pct_change
            
            # Predicted direction
            pred_directions = np.sign(y_test_pred[mask])
            # Actual direction
            actual_directions = np.sign(y_test_pct_actual[mask])
            
            # Win rate
            correct_directions = (pred_directions == actual_directions)
            win_rate = np.mean(correct_directions) * 100
            
            # Average return
            returns = y_test_pct_actual[mask]
            avg_return = np.mean(returns) * 100
            
            # Separate by positive/negative
            positive_mask = mask & (y_test_pred > 0)
            negative_mask = mask & (y_test_pred < 0)
            
            if np.sum(positive_mask) > 0:
                positive_avg_return = np.mean(y_test_pct_actual[positive_mask]) * 100
            
            if np.sum(negative_mask) > 0:
                negative_avg_return = np.mean(y_test_pct_actual[negative_mask]) * 100
        
        return {
            'count': count,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'positive_avg_return': positive_avg_return,
            'negative_avg_return': negative_avg_return
        }
    
    # Strong-only metrics
    strong_mask = np.isin(confidence_buckets, ['strong_positive', 'strong_negative'])
    strong_metrics = calculate_signal_metrics(strong_mask, 'Strong')
    
    # Moderate-only metrics
    moderate_mask = np.isin(confidence_buckets, ['moderate_positive', 'moderate_negative'])
    moderate_metrics = calculate_signal_metrics(moderate_mask, 'Moderate')
    
    # Moderate + Strong combined (this is where most real systems make money)
    moderate_strong_mask = np.isin(confidence_buckets, 
                                   ['strong_positive', 'strong_negative', 
                                    'moderate_positive', 'moderate_negative'])
    moderate_strong_metrics = calculate_signal_metrics(moderate_strong_mask, 'Moderate+Strong')
    
    # Extract individual values for backward compatibility
    strong_count = strong_metrics['count']
    strong_win_rate = strong_metrics['win_rate']
    strong_avg_return = strong_metrics['avg_return']
    strong_positive_avg_return = strong_metrics['positive_avg_return']
    strong_negative_avg_return = strong_metrics['negative_avg_return']
    
    # ===== PRINT RESULTS =====
    print(f"\n{'='*70}")
    print(f"{name} - Signal Quality Evaluation")
    print(f"{'='*70}")
    
    # Traditional metrics (brief)
    print(f"\n[Traditional Metrics]")
    print(f"Test RMSE: {test_rmse:.4f} | Test R²: {test_r2:.4f}")
    
    # Residual sigma
    print(f"\n[Residual Sigma]")
    print(f"σ (residual std): {sigma:.4f}")
    
    # Confidence bucket distribution
    print(f"\n[Confidence Bucket Distribution]")
    print(f"Strong Positive:  {bucket_pcts['strong_positive']:5.2f}% ({bucket_counts.get('strong_positive', 0)} samples)")
    print(f"Strong Negative:  {bucket_pcts['strong_negative']:5.2f}% ({bucket_counts.get('strong_negative', 0)} samples)")
    print(f"Moderate Positive: {bucket_pcts['moderate_positive']:5.2f}% ({bucket_counts.get('moderate_positive', 0)} samples)")
    print(f"Moderate Negative: {bucket_pcts['moderate_negative']:5.2f}% ({bucket_counts.get('moderate_negative', 0)} samples)")
    print(f"Low Positive:     {bucket_pcts['low_positive']:5.2f}% ({bucket_counts.get('low_positive', 0)} samples)")
    print(f"Low Negative:     {bucket_pcts['low_negative']:5.2f}% ({bucket_counts.get('low_negative', 0)} samples)")
    print(f"Do Not Trade:     {bucket_pcts['do_not_trade']:5.2f}% ({bucket_counts.get('do_not_trade', 0)} samples)")
    
    # Strong signal performance
    print(f"\n[Strong Signal Performance]")
    if strong_count > 0:
        print(f"Strong signals: {strong_count} ({strong_count/total_predictions*100:.2f}% of test set)")
        if strong_win_rate is not None:
            print(f"Strong-only Win Rate (directional accuracy): {strong_win_rate:.2f}%")
        if strong_avg_return is not None:
            print(f"Strong-only Avg Realized Return: {strong_avg_return:+.4f}%")
            if strong_positive_avg_return is not None:
                print(f"  → Strong Positive avg return: {strong_positive_avg_return:+.4f}%")
            if strong_negative_avg_return is not None:
                print(f"  → Strong Negative avg return: {strong_negative_avg_return:+.4f}%")
        else:
            print("  (target_pct_change not provided - cannot calculate realized returns)")
    else:
        print("No strong signals generated!")
    
    # Moderate signal performance
    print(f"\n[Moderate Signal Performance]")
    if moderate_metrics['count'] > 0:
        print(f"Moderate signals: {moderate_metrics['count']} ({moderate_metrics['count']/total_predictions*100:.2f}% of test set)")
        if moderate_metrics['win_rate'] is not None:
            print(f"Moderate-only Win Rate: {moderate_metrics['win_rate']:.2f}%")
        if moderate_metrics['avg_return'] is not None:
            print(f"Moderate-only Avg Realized Return: {moderate_metrics['avg_return']:+.4f}%")
    
    # Moderate + Strong combined (most important for real trading)
    print(f"\n[Moderate + Strong Combined Performance] ⭐")
    if moderate_strong_metrics['count'] > 0:
        print(f"Moderate+Strong signals: {moderate_strong_metrics['count']} ({moderate_strong_metrics['count']/total_predictions*100:.2f}% of test set)")
        if moderate_strong_metrics['win_rate'] is not None:
            print(f"Moderate+Strong Win Rate: {moderate_strong_metrics['win_rate']:.2f}%")
        if moderate_strong_metrics['avg_return'] is not None:
            print(f"Moderate+Strong Avg Realized Return: {moderate_strong_metrics['avg_return']:+.4f}%")
            if moderate_strong_metrics['positive_avg_return'] is not None:
                print(f"  → Positive signals avg return: {moderate_strong_metrics['positive_avg_return']:+.4f}%")
            if moderate_strong_metrics['negative_avg_return'] is not None:
                print(f"  → Negative signals avg return: {moderate_strong_metrics['negative_avg_return']:+.4f}%")
    else:
        print("No Moderate+Strong signals generated!")
    
    print(f"{'='*70}\n")
    
    # Return metrics as dictionary for programmatic use
    return {
        'name': name,
        'sigma': sigma,
        'test_rmse': test_rmse,
        'test_r2': test_r2,
        'bucket_pcts': bucket_pcts,
        'bucket_counts': bucket_counts,
        'strong_count': strong_count,
        'strong_win_rate': strong_win_rate,
        'strong_avg_return': strong_avg_return,
        'strong_positive_avg_return': strong_positive_avg_return,
        'strong_negative_avg_return': strong_negative_avg_return,
        'moderate_metrics': moderate_metrics,
        'moderate_strong_metrics': moderate_strong_metrics,
    }


def predict_with_confidence(model, X_input, sigma, rolling_vol,
                            do_not_trade_threshold=0.5,
                            low_threshold=0.75,
                            moderate_threshold=1.5,
                            min_sigma_filter=1.25):
    """
    Make a prediction and convert to dashboard-ready format.
    
    This function converts model predictions (target_vol_norm) to percent changes
    and classifies confidence for dashboard display.
    
    Parameters:
    -----------
    model : fitted model
        Trained model
    X_input : array-like
        Input features for prediction
    sigma : float
        Residual sigma from model evaluation (used for confidence classification)
    rolling_vol : float
        Current rolling volatility (used to convert sigma units to percent)
    do_not_trade_threshold : float
        Multiplier for sigma below which we "do not trade" (default: 0.5)
    low_threshold : float
        Multiplier for sigma below which confidence is "low" (default: 0.75)
    moderate_threshold : float
        Multiplier for sigma below which confidence is "moderate" (default: 1.5)
    min_sigma_filter : float
        Minimum |prediction|/sigma required to generate any signal (default: 1.25)
    
    Returns:
    --------
    dict with keys:
        - mu_sigma: predicted target_vol_norm
        - mu_pct: predicted percent change
        - confidence: 'Strong', 'Moderate', 'Low', or 'Do Not Trade'
        - direction: 'positive' or 'negative'
        - expected_move_pct: absolute expected move in percent
        - confidence_bucket: detailed bucket name
    """
    # Get prediction in sigma units
    mu_sigma = model.predict(X_input)[0]
    
    # Convert to percent: mu_pct = mu_sigma * rolling_vol
    mu_pct = mu_sigma * rolling_vol
    
    # Classify confidence with same thresholds used in evaluation
    confidence_bucket = classify_confidence(
        mu_sigma, sigma,
        do_not_trade_threshold=do_not_trade_threshold,
        low_threshold=low_threshold,
        moderate_threshold=moderate_threshold,
        min_sigma_filter=min_sigma_filter
    )
    
    # Map to display-friendly confidence level
    if 'strong' in confidence_bucket:
        confidence = 'Strong'
    elif 'moderate' in confidence_bucket:
        confidence = 'Moderate'
    elif 'low' in confidence_bucket:
        confidence = 'Low'
    else:
        confidence = 'Do Not Trade'
    
    # Get direction
    direction = 'positive' if mu_sigma > 0 else 'negative'
    
    return {
        'mu_sigma': mu_sigma,
        'mu_pct': mu_pct,
        'confidence': confidence,
        'direction': direction,
        'expected_move_pct': abs(mu_pct),
        'confidence_bucket': confidence_bucket
    }
