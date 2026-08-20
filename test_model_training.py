import requests
import json

# Login
r = requests.post('http://localhost:8000/api/auth/login', json={'username':'user','password':'6aQGrTRZ-u7StavG1wQtqw'})
jwt = r.json()['access_token']
print('✓ Logged in\n')

# Get model info
r = requests.get('http://localhost:8000/api/ml/models/info', headers={'Authorization': f'Bearer {jwt}'})
print('Model Info:')
print(json.dumps(r.json(), indent=2)[:500])
print()

# Train model
print('Training model...')
r = requests.post('http://localhost:8000/api/ml/models/train',
    json={'symbol':'BTCUSDT', 'timeframe':'1h', 'model_type':'rf', 'cv_folds':3},
    headers={'Authorization': f'Bearer {jwt}'})
print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f"Symbol: {data['symbol']}")
    print(f"Model Type: {data['model_type']}")
    print(f"Status: {data['status']}")
    print(f"Train Samples: {data['n_train']}")
    print(f"Test Samples: {data['n_test']}")
    print(f"Metrics: {json.dumps(data['metrics'], indent=2)[:500]}")
    print(f"\nTop 3 Important Features:")
    top_features = sorted(data['feature_importance'].items(), key=lambda x: x[1], reverse=True)[:3]
    for feat, imp in top_features:
        print(f"  {feat}: {imp:.4f}")
else:
    print('Error:', r.text[:200])
