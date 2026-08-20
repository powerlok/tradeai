from app.ml.registry import approve_version

approvals = [
    ("SOLUSDT", "4h", "rf", "v20260820213111604937"),
    ("SOLUSDT", "1d", "rf", "v20260820213317478268"),
]
for symbol, timeframe, model_type, version in approvals:
    record = approve_version(symbol, timeframe, model_type, version)
    print(symbol, timeframe, model_type, record["version"], record["status"])
