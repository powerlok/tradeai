from __future__ import annotations

import json
import asyncio
import re
import ast
from urllib import error

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.auth import require_user
from app.services.ai_provider import create_ai_provider
from app.services.market_intelligence import MarketIntelligenceService
from app.services.notifications import NotificationService

router = APIRouter()

MCP_TOOLS = [{
    "type": "function",
    "function": {
        "name": "research_assets",
        "description": "Pesquisa dados atuais de uma ou mais criptomoedas na Binance e CoinGecko.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "timeframe": {"type": "string", "enum": ["15m", "1h", "4h", "1d"]},
            },
            "required": ["question"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "get_market_news",
        "description": "Busca notícias recentes e relacionadas aos ativos solicitados em RSS públicos.",
        "parameters": {
            "type": "object",
            "properties": {"symbols": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer", "maximum": 12}},
            "required": ["symbols"],
        },
    },
}]


async def call_mcp_tool(name: str, arguments: dict[str, object]) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": "2025-06-18",
            "Host": "localhost:9000",
        }
        await client.post("http://mcp_market:9000/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "trade-chat", "version": "1.0"}},
        })
        response = await client.post("http://mcp_market:9000/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        response.raise_for_status()
        payload = response.json()
        return payload["result"]["content"][0]["text"]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    signal: str | None = None
    last_price: float | None = None
    spread: float | None = None
    market_state: str | None = None


KNOWN_ASSETS = {
    "BITCOIN": "BTCUSDT", "BTC": "BTCUSDT",
    "ETHEREUM": "ETHUSDT", "ETH": "ETHUSDT",
    "SOLANA": "SOLUSDT", "SOL": "SOLUSDT",
    "BINANCECOIN": "BNBUSDT", "BNB": "BNBUSDT",
    "XRP": "XRPUSDT", "CARDANO": "ADAUSDT", "ADA": "ADAUSDT",
    "DOGECOIN": "DOGEUSDT", "DOGE": "DOGEUSDT",
}


def extract_requested_symbols(message: str, fallback: str = "") -> list[str]:
    candidates = re.findall(r"\b[A-Za-z]{2,12}(?:USDT|USDC|BUSD)?\b", message.upper())
    symbols: list[str] = []
    for candidate in candidates:
        symbol = KNOWN_ASSETS.get(candidate, candidate if candidate.endswith(("USDT", "USDC", "BUSD")) else "")
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    if not symbols and fallback.upper() not in {"", "AUTO"}:
        symbols.append(fallback.upper())
    return symbols[:4]


async def fetch_live_market_context(symbol: str, timeframe: str) -> dict[str, object]:
    """Fetch public Binance data used to ground the assistant's current reading."""
    interval = timeframe if timeframe in {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"} else "1h"
    async with httpx.AsyncClient(base_url="https://api.binance.com", timeout=8) as client:
        ticker_request = client.get("/api/v3/ticker/24hr", params={"symbol": symbol})
        candles_request = client.get("/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": 30})
        orderbook_request = client.get("/api/v3/depth", params={"symbol": symbol, "limit": 5})
        timeframe_requests = {
            research_interval: client.get(
                "/api/v3/klines",
                params={"symbol": symbol, "interval": research_interval, "limit": 30},
            )
            for research_interval in ("15m", "1h", "4h", "1d")
        }
        ticker_response, candles_response, orderbook_response = await asyncio.gather(
            ticker_request, candles_request, orderbook_request, return_exceptions=True
        )
        timeframe_responses = dict(zip(timeframe_requests, await asyncio.gather(*timeframe_requests.values(), return_exceptions=True)))

    context: dict[str, object] = {"source": "Binance public REST", "symbol": symbol, "timeframe": interval}
    if isinstance(ticker_response, httpx.Response) and ticker_response.is_success:
        ticker = ticker_response.json()
        context.update({
            "current_price": float(ticker["lastPrice"]),
            "change_24h_percent": float(ticker["priceChangePercent"]),
            "high_24h": float(ticker["highPrice"]),
            "low_24h": float(ticker["lowPrice"]),
            "volume_24h": float(ticker["volume"]),
            "quote_volume_24h": float(ticker["quoteVolume"]),
            "trades_24h": int(ticker["count"]),
        })
    else:
        context["ticker_24h"] = "indisponível"

    if isinstance(candles_response, httpx.Response) and candles_response.is_success:
        candles = candles_response.json()
        closes = [float(candle[4]) for candle in candles]
        volumes = [float(candle[5]) for candle in candles]
        if closes:
            context.update({
                "candle_open": float(candles[-1][1]),
                "candle_high": float(candles[-1][2]),
                "candle_low": float(candles[-1][3]),
                "candle_close": closes[-1],
                "candle_volume": volumes[-1],
                "change_since_first_candle_percent": ((closes[-1] / closes[0]) - 1) * 100 if closes[0] else None,
                "sma_20": sum(closes[-20:]) / min(len(closes), 20),
                "average_volume_20": sum(volumes[-20:]) / min(len(volumes), 20),
            })
    else:
        context["candles"] = "indisponível"

    if isinstance(orderbook_response, httpx.Response) and orderbook_response.is_success:
        orderbook = orderbook_response.json()
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        if bids and asks:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            context.update({
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": best_ask - best_bid,
                "bid_quantity_top5": sum(float(level[1]) for level in bids),
                "ask_quantity_top5": sum(float(level[1]) for level in asks),
            })
    else:
        context["orderbook"] = "indisponível"

    timeframe_context: dict[str, object] = {}
    for research_interval, response in timeframe_responses.items():
        if not isinstance(response, httpx.Response) or not response.is_success:
            timeframe_context[research_interval] = {"status": "indisponível"}
            continue
        candles = response.json()
        closes = [float(candle[4]) for candle in candles]
        volumes = [float(candle[5]) for candle in candles]
        if not closes:
            timeframe_context[research_interval] = {"status": "indisponível"}
            continue
        sma20 = sum(closes[-20:]) / min(len(closes), 20)
        change = ((closes[-1] / closes[0]) - 1) * 100 if closes[0] else None
        direction = "alta" if closes[-1] > sma20 and (change is None or change > 0) else "baixa" if closes[-1] < sma20 and (change is None or change < 0) else "lateral"
        timeframe_context[research_interval] = {
            "status": "ok",
            "last_close": closes[-1],
            "change_window_percent": change,
            "sma_20": sma20,
            "volume_last": volumes[-1],
            "average_volume_20": sum(volumes[-20:]) / min(len(volumes), 20),
            "direction": direction,
        }
    context["multi_timeframe"] = timeframe_context
    return context


CHAT_SYSTEM_PROMPT = """
Você é um analista de mercado interno especialista para um dashboard de criptomoedas.

Idioma e estilo obrigatórios:
- Responda sempre em português do Brasil, com linguagem humana, natural e profissional.
- Seja direto, claro e breve; não repita a pergunta e não use frases burocráticas ou robóticas.
- Responda apenas com texto simples, sem JSON, tabelas, blocos de código ou raciocínio interno.

Responda somente sobre:
- tendência do mercado
- sinal do modelo
- leitura de preço e spread
- comparação entre ativos
- explicação do gráfico e do painel
- risco e contexto de operação
- interpretação do mercado em linguagem simples
- funcionamento e recursos disponíveis nesta aplicação
- uso das telas, chat, notificações, fontes de dados
- revisão do que pode ser feito no sistema

Regras:
- Nunca responda fora do contexto de criptomoedas, mercado financeiro ou revisão funcional desta aplicação.
- Não prometa lucro, ganhos garantidos ou certeza de operação.
- Não invente dados que não estejam no contexto recebido.
- Nunca preencha lacunas com suposições, notícias ou números não fornecidos.
- Quando houver notícias no contexto, cite somente o título, fonte e data recebidos; não invente manchetes nem eventos.
- Se faltar contexto, diga que não há dados suficientes para uma resposta confiável.
- Se o snapshot da Binance tiver preço, variação, volume ou candles, considere que há dados suficientes para uma análise inicial; não diga que os dados estão indisponíveis.
- Use o bloco `multi_timeframe` como visão principal: compare 15m, 1h, 4h e 1d e informe quando as direções estiverem alinhadas ou divergentes.
- Trate `current_price` como o preço atual e `change_24h_percent` como a variação das últimas 24 horas; não troque os rótulos.
- Os valores da Binance e CoinGecko estão em USD/USDT, salvo indicação explícita; não os apresente como BRL/R$.
- Quando o usuário perguntar se pode comprar, vender ou operar hoje, não responda apenas com uma recusa genérica: analise os dados disponíveis, apresente cenário favorável, riscos, pontos de atenção e o que precisaria ser confirmado.
- Não diga ao usuário para comprar ou vender e não transforme a análise em recomendação personalizada; deixe claro que a decisão e o risco são do usuário.
- Mantenha a resposta curta, clara e útil para um trader.
- Sempre use linguagem direta e prática.
- Ao explicar a aplicação, descreva somente recursos confirmados no contexto do sistema: dashboard, análise multi-timeframe, sinais ML, backtest paper, chat com streaming, notificações, MCP, Binance, CoinGecko, RSS, Redis e providers Ollama/Groq.
- Não invente telas, botões, integrações, permissões ou funcionalidades futuras; diferencie claramente o que existe, o que é limitado e o que ainda precisa ser implementado.
"""


def build_market_context_prompt(
    message: str,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    signal: str | None = None,
    last_price: float | None = None,
    spread: float | None = None,
    market_state: str | None = None,
    live_context: dict[str, object] | None = None,
) -> str:
    parts = [
        "Você é um assistente de análise de mercado para criptomoedas.",
        "Responda sempre em português do Brasil, com tom humano, natural, profissional e direto.",
        "Entregue apenas texto simples e bem escrito; não use JSON, tabelas, blocos de código, títulos excessivos ou raciocínio interno.",
        "Seja resumido: no máximo 5 frases curtas, priorizando a informação mais útil para a pergunta.",
        "Responda sobre análise de criptomoedas ou sobre uma revisão funcional desta aplicação.",
        "Dúvidas sobre a aplicação podem abordar dashboard, telas, chat, streaming, notificações, fontes, MCP, providers de IA e o que o sistema permite fazer.",
        "Para perguntas sobre notícias ou impacto de eventos, use a ferramenta de notícias e diferencie notícia publicada de interpretação técnica.",
        "A pergunta pede o cenário atual: use primeiro e explicitamente os dados do contexto recebido.",
        "Não responda com fatos históricos, definições genéricas ou recomendações de plataformas quando houver dados atuais no contexto.",
        "Não invente valores, tendências, notícias ou promessas de ganho.",
        "Não complete dados ausentes com suposições; use somente o contexto retornado pelas fontes e pelo modelo.",
        "Ao revisar a aplicação, informe apenas recursos confirmados: dashboard, sinais ML, backtest paper, chat streaming, notificações, MCP, Binance, CoinGecko, RSS, Redis, Ollama e Groq.",
        "Se perguntarem por algo não confirmado ou ainda não implementado, diga isso claramente e não apresente como existente.",
        "Se um dado específico estiver indisponível, informe exatamente qual dado falta e analise somente o que estiver disponível.",
        "O snapshot da Binance abaixo é a fonte de dados atual desta resposta. Se ele contiver métricas, use-as diretamente; não diga que não há dados suficientes.",
        "Responda somente em texto simples, sem JSON, sem tabelas e sem explicações longas.",
        "Resuma em no máximo 7 frases curtas: preço atual, variação, leitura 15m/1h/4h/1d, spread/liquidez, sinal ou evidência disponível e principal risco.",
        "Use os nomes dos campos exatamente para não confundir preço atual com fechamento de 24h.",
        "Informe a moeda dos valores como USD/USDT e não converta para BRL sem uma cotação cambial fornecida.",
        "Se perguntarem se é possível comprar ou vender hoje, responda com uma análise condicional baseada nos dados atuais: cenário, evidências, riscos e checklist de confirmação. Não dê uma ordem direta nem apenas recuse.",
        f"Símbolo atual: {symbol}",
        f"Timeframe atual: {timeframe}",
        f"Sinal atual do modelo: {signal or 'indisponível'}",
        f"Último preço: {last_price if last_price is not None else 'indisponível'}",
        f"Spread: {spread if spread is not None else 'indisponível'}",
        f"Estado do mercado: {market_state or 'indisponível'}",
        f"Dados públicos atuais da Binance (fonte e snapshot): {json.dumps(live_context or {'status': 'indisponível'}, ensure_ascii=False)}",
        "", 
        "Instruções finais:",
        "- Responda com foco em análise técnica e contexto de mercado.",
        "- Para perguntas amplas, resuma: preço atual, variação, tendência, spread, liquidez e risco.",
        "- Cite os valores recebidos e deixe claro o timeframe da leitura.",
        "- Diferencie dados de 24h dos dados do candle/timeframe; não trate variação passada como previsão.",
        "- Não limite a análise ao timeframe informado: use todos os timeframes do bloco multi_timeframe; o timeframe informado é apenas a referência do painel.",
        "- Não use a frase genérica 'não posso fornecer recomendações específicas' como resposta única quando houver dados para análise.",
        "- Só declare falta de dados se o snapshot estiver com status indisponível ou se o campo necessário realmente não existir.",
        "- Mantenha a resposta breve, objetiva e clara.",
        "- Não responda sobre temas fora do mercado cripto.",
        "- Se a pergunta pedir algo fora desse escopo, responda de forma curta e diga que você só pode ajudar com análise do mercado; não responder fora do tema do mercado.",
        "",
        f"Pergunta do usuário: {message}",
    ]
    return "\n".join(parts)


def stream_event(event_type: str, **data: object) -> str:
    return json.dumps({"type": event_type, **data}, ensure_ascii=False) + "\n"


def read_next_chunk(iterator, sentinel: object) -> str | object:
    try:
        return next(iterator)
    except StopIteration:
        return sentinel


def normalize_tool_arguments(tool_name: str, arguments: object) -> dict[str, object]:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            try:
                arguments = ast.literal_eval(arguments)
            except (SyntaxError, ValueError):
                arguments = {}
    if not isinstance(arguments, dict):
        return {}
    normalized = dict(arguments)
    if tool_name == "get_market_news":
        symbols = normalized.get("symbols", [])
        if isinstance(symbols, str):
            try:
                symbols = ast.literal_eval(symbols)
            except (SyntaxError, ValueError):
                symbols = [symbols]
        if isinstance(symbols, list):
            normalized["symbols"] = [str(symbol).replace("/", "").upper() for symbol in symbols]
        try:
            normalized["limit"] = min(int(normalized.get("limit", 8)), 12)
        except (TypeError, ValueError):
            normalized["limit"] = 8
    return normalized


async def fetch_direct_research(symbols: list[str], timeframe: str) -> dict[str, object]:
    snapshots = await asyncio.gather(*(
        fetch_live_market_context(symbol, timeframe) for symbol in symbols
    ))
    binance_context = {symbol: snapshot for symbol, snapshot in zip(symbols, snapshots)}
    intelligence = MarketIntelligenceService()
    try:
        broad_context = await intelligence.get_context(symbols)
    finally:
        await intelligence.close()
    return {"binance": binance_context, "market_overview": broad_context}


@router.post("/chat/message")
async def chat_message(payload: ChatRequest, user: dict = Depends(require_user)):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    service = create_ai_provider(timeout_seconds=max(settings.ollama_timeout_seconds, 120))
    requested_symbols = extract_requested_symbols(message, payload.symbol)
    context = {
        "symbols": requested_symbols,
        "timeframe": payload.timeframe,
        "signal": payload.signal,
        "last_price": payload.last_price,
        "spread": payload.spread,
        "market_state": payload.market_state,
    }

    async def generate_events():
        yield stream_event("status", message="Validando o contexto do mercado...")
        if not await asyncio.to_thread(service.ping):
            provider_name = settings.ai_provider.strip().capitalize()
            yield stream_event("error", message=f"O provider de IA ({provider_name}) está indisponível ou não autorizado. Verifique a configuração e a credencial.")
            return

        live_context = {"status": "aguardando pesquisa MCP", "requested_symbols": requested_symbols}
        enriched_prompt = build_market_context_prompt(message=message, symbol=", ".join(requested_symbols) or "não identificado", timeframe=payload.timeframe, signal=payload.signal, last_price=payload.last_price, spread=payload.spread, market_state=payload.market_state, live_context=live_context)
        decision_messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": enriched_prompt},
        ]
        try:
            yield stream_event("status", message="A IA está escolhendo as fontes de pesquisa...")
            decision = await asyncio.to_thread(service.chat_once, decision_messages, MCP_TOOLS)
            tool_calls = decision.get("message", {}).get("tool_calls", [])
            if tool_calls:
                tool_results: dict[str, object] = {}
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    tool_name = function.get("name")
                    if tool_name not in {"research_assets", "get_market_news"}:
                        continue
                    tool_arguments = normalize_tool_arguments(tool_name, function.get("arguments", {}))
                    yield stream_event("status", message=f"Consultando {tool_name} no MCP...")
                    tool_result = await call_mcp_tool(tool_name, tool_arguments)
                    tool_results[tool_name] = json.loads(tool_result)
                if tool_results:
                    live_context = {"mcp_research": tool_results}
                    enriched_prompt = build_market_context_prompt(
                        message=message,
                        symbol=", ".join(requested_symbols) or "não identificado",
                        timeframe=payload.timeframe,
                        signal=payload.signal,
                        last_price=payload.last_price,
                        spread=payload.spread,
                        market_state=payload.market_state,
                        live_context=live_context,
                    )
            else:
                yield stream_event("status", message="Fazendo pesquisa direta de mercado...")
                live_context = await fetch_direct_research(requested_symbols, payload.timeframe)
                enriched_prompt = build_market_context_prompt(message=message, symbol=", ".join(requested_symbols) or "não identificado", timeframe=payload.timeframe, signal=payload.signal, last_price=payload.last_price, spread=payload.spread, market_state=payload.market_state, live_context=live_context)
        except Exception:
            yield stream_event("status", message="MCP indisponível; usando pesquisa direta...")
            try:
                live_context = await fetch_direct_research(requested_symbols, payload.timeframe)
                enriched_prompt = build_market_context_prompt(message=message, symbol=", ".join(requested_symbols) or "não identificado", timeframe=payload.timeframe, signal=payload.signal, last_price=payload.last_price, spread=payload.spread, market_state=payload.market_state, live_context=live_context)
            except (httpx.HTTPError, ValueError, TypeError):
                live_context = {"status": "indisponível", "requested_symbols": requested_symbols}
        yield stream_event("status", message="Consultando a IA com os dados atuais...")
        answer_parts: list[str] = []
        try:
            iterator = service.chat_stream([
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": enriched_prompt},
            ])
            sentinel = object()
            while True:
                content = await asyncio.to_thread(read_next_chunk, iterator, sentinel)
                if content is sentinel:
                    break
                answer_parts.append(content)
                yield stream_event("token", content=content)
        except TimeoutError:
            yield stream_event("error", message="A IA demorou mais que o limite para responder. Tente novamente.")
            return
        except (error.URLError, error.HTTPError, ValueError, json.JSONDecodeError):
            yield stream_event("error", message="Não foi possível consultar a IA de mercado agora.")
            return
        except Exception:
            provider_name = settings.ai_provider.strip().capitalize()
            yield stream_event("error", message=f"O provider de IA ({provider_name}) encerrou a resposta. Tente repetir a pergunta.")
            return

        answer = "".join(answer_parts).strip()
        if not answer:
            answer = "Não consegui interpretar o contexto atual do mercado com os dados disponíveis."
        yield stream_event("status", message="Resposta concluída.")
        await NotificationService().publish(
            str(user.get("sub", "")),
            "chat_response",
            "Resposta da análise pronta",
            f"A análise de {', '.join(requested_symbols) or 'mercado'} foi concluída.",
            {"symbols": requested_symbols, "timeframe": payload.timeframe},
        )
        yield stream_event("done", answer=answer, context={**context, "live_market": live_context})

    return StreamingResponse(
        generate_events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
