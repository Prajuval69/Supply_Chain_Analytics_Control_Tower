import numpy as np
import pandas as pd


def error_metrics(actual, predicted) -> dict:
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if len(actual) == 0 or actual.shape != predicted.shape:
        raise ValueError("Metrics require equal, nonempty arrays")
    if not (np.isfinite(actual).all() and np.isfinite(predicted).all()):
        raise ValueError("Metrics require finite numbers")
    error = predicted-actual
    nonzero = actual != 0
    return {"mae": float(np.abs(error).mean()), "rmse": float(np.sqrt((error**2).mean())),
            "mape": float((np.abs(error[nonzero])/np.abs(actual[nonzero])).mean()*100) if nonzero.any() else None,
            "mape_eligible_count": int(nonzero.sum())}


def features(t):
    t = np.asarray(t, dtype=float)
    return np.column_stack([np.ones(len(t)), t/12, np.sin(2*np.pi*t/12), np.cos(2*np.pi*t/12)])


def predict(history, horizon, model):
    values = np.asarray(history, dtype=float)
    if len(values) < 12 or horizon < 1 or not np.isfinite(values).all():
        raise ValueError("Forecast requires >=12 finite monthly observations and positive horizon")
    if model == "moving_average_3":
        return np.repeat(values[-3:].mean(), horizon)
    if model == "trend_seasonal_regression":
        x = features(np.arange(len(values)))
        penalty = np.diag([0, .1, .1, .1])
        beta = np.linalg.solve(x.T@x+penalty, x.T@values)
        return np.maximum(0, features(np.arange(len(values), len(values)+horizon))@beta)
    raise ValueError(f"Unknown model: {model}")


def forecast(demand: pd.DataFrame, horizon=3):
    monthly = demand.groupby(["product_id", "month"]).demand_quantity.sum().reset_index()
    forecasts, evaluation, selected, holdout = [], [], [], []
    candidates = ["moving_average_3", "trend_seasonal_regression"]
    for pid, group in monthly.groupby("product_id"):
        group = group.sort_values("month")
        y = group.demand_quantity.to_numpy(dtype=float)
        if len(y) < 18:
            raise ValueError("Evaluation requires >=18 monthly observations")
        # Last three months are never used to select the method.
        origins = sorted(set([max(12, len(y)-9), len(y)-6]))
        scores = {}
        for model in candidates:
            all_actual, all_predicted = [], []
            for origin in origins:
                pred = predict(y[:origin], 3, model)
                actual = y[origin:origin+3]
                all_actual.extend(actual)
                all_predicted.extend(pred)
                for h, (a, p) in enumerate(zip(actual, pred), 1):
                    evaluation.append({"product_id": int(pid), "train_end": str(group.iloc[origin-1].month.date()), "forecast_date": str(group.iloc[origin+h-1].month.date()), "horizon": h, "prediction": float(p), "actual": float(a), "model_name": model})
            scores[model] = error_metrics(all_actual, all_predicted)
            selected.append({"product_id": int(pid), "model_name": model, **scores[model]})
        winner = min(candidates, key=lambda m: scores[m]["mae"])
        test_origin = len(y)-3
        test_pred = predict(y[:test_origin], 3, winner)
        for h, (actual, prediction) in enumerate(zip(y[test_origin:], test_pred), 1):
            holdout.append({"product_id": int(pid), "train_end": str(group.iloc[test_origin-1].month.date()), "forecast_date": str(group.iloc[test_origin+h-1].month.date()), "horizon": h, "prediction": float(prediction), "actual": float(actual), "model_name": winner})
        predictions = predict(y, horizon, winner)
        for h, p in enumerate(predictions, 1):
            forecasts.append({"product_id": int(pid), "train_end": str(group.iloc[-1].month.date()), "forecast_date": str((group.iloc[-1].month+pd.offsets.MonthBegin(h)).date()), "horizon": h, "prediction": float(p), "actual": None, "model_name": winner, **scores[winner]})
    model_scores = pd.DataFrame(selected)
    forecast_frame = pd.DataFrame(forecasts)
    model_scores["selected"] = model_scores.apply(lambda r: int(forecast_frame.loc[forecast_frame.product_id == r.product_id, "model_name"].iloc[0] == r.model_name), axis=1)
    return forecast_frame, pd.DataFrame(evaluation), model_scores, pd.DataFrame(holdout)
