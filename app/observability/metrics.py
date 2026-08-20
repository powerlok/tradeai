from prometheus_client import Counter, start_http_server
import threading

# Counters exported for Prometheus
trades_ingested = Counter(
    'trades_ingested_total', 'Total number of trades ingested', ['symbol']
)
orderbook_snapshots_ingested = Counter(
    'orderbook_snapshots_ingested_total', 'Total number of orderbook snapshots persisted', ['symbol']
)
websocket_reconnects = Counter(
    'websocket_reconnects_total', 'Number of websocket reconnect attempts'
)


def _start_server(port: int = 8001):
    start_http_server(port)


def start_metrics_server(port: int = 8001):
    t = threading.Thread(target=_start_server, args=(port,), daemon=True)
    t.start()


def inc_trade(symbol: str):
    try:
        trades_ingested.labels(symbol=symbol).inc()
    except Exception:
        pass


def inc_snapshot(symbol: str):
    try:
        orderbook_snapshots_ingested.labels(symbol=symbol).inc()
    except Exception:
        pass


def inc_ws_reconnect():
    try:
        websocket_reconnects.inc()
    except Exception:
        pass
