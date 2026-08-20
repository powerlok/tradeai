import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getMarket, type Candle, type LivePrice, type OrderBookSummary, type Signal } from '../api';

export function useMarketData(token: string, symbol: string, timeframe: string) {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [livePrice, setLivePrice] = useState<LivePrice | null>(null);
  const [orderBook, setOrderBook] = useState<OrderBookSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    controllerRef.current?.abort();
    setLoading(true);
    setError('');
    const controller = new AbortController();
    controllerRef.current = controller;
    const currentRequest = ++requestId.current;
    try {
      const market = await getMarket(token, symbol, timeframe, controller.signal);
      if (currentRequest !== requestId.current) return;
      setSignal(market.signal);
      setCandles(market.candles);
      setLivePrice(market.livePrice);
      setOrderBook(market.orderBook);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === 'AbortError') return;
      setError(requestError instanceof Error ? requestError.message : 'Falha ao atualizar o mercado');
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
    return () => controller.abort();
  }, [token, symbol, timeframe]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const timer = window.setInterval(refresh, 5000);
    return () => {
      window.clearInterval(timer);
      controllerRef.current?.abort();
    };
  }, [refresh]);

  const chartData = useMemo(() => candles.map((candle) => ({
    time: new Date(candle.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    price: candle.close,
  })), [candles]);

  return { signal, candles, chartData, livePrice, orderBook, loading, error, refresh };
}
