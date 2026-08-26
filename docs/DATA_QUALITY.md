# Data Quality Engine

## Escopo

A Fase 1 valida candles antes da persistência e antes do consumo pelo Feature Engine e pelo Dataset Builder. Nenhuma ordem real é habilitada por esta fase.

## Estados

- `VALID`: registro estruturalmente consistente.
- `WARNING`: registro utilizável, mas exige atenção operacional.
- `INVALID`: registro rejeitado; não é persistido pelo collector e não alimenta features, dataset ou sinal.

## Validações de candle

- Campos obrigatórios: `open_time`, `close_time`, `open`, `high`, `low`, `close`, `volume`.
- Números precisam ser finitos; `NaN` e infinito são inválidos.
- `close_time` deve ser maior que `open_time`.
- Preços OHLC devem ser positivos.
- `high` deve ser maior ou igual a open, low e close.
- `low` deve ser menor ou igual a open, high e close.
- Volume negativo é inválido.
- Candle cujo `close_time` ainda não passou recebe `WARNING` por `incomplete_candle`.
- Faixa `(high - low) / close` acima de `25%` recebe `WARNING` por `extreme_range`. Esse limite é um alerta operacional, não uma afirmação estatística sobre o ativo.

## Validações de série

`validate_candle_series()` verifica, quando chamada com o intervalo esperado em milissegundos:

- timestamps duplicados;
- timestamps fora de ordem;
- gaps maiores que o timeframe informado.

Essas condições são `WARNING` porque a série pode continuar sendo analisada depois de inspeção. Registros individualmente inválidos continuam sendo `INVALID`.

## Integração

- `app/quality/data_quality.py`: engine puro e determinístico.
- `app/market/candle_sync.py`: rejeita candles `INVALID` antes do insert.
- `app/ml/features.py`: remove candles `INVALID` antes de calcular indicadores.
- `app/ml/dataset.py`: remove candles `INVALID` antes de construir a matriz de treino.

Não houve alteração de schema nesta fase, portanto não há migration. A qualidade de registros históricos é reavaliada no momento de consumo; a persistência de status/auditoria fica para uma fase posterior quando o contrato de banco for definido.

## Testes

`tests/test_data_quality.py` cobre:

- candle válido;
- OHLC e volume inválidos;
- candle incompleto e faixa extrema;
- duplicidade, ordenação e gaps.

Regra de segurança: `WARNING` não é convertido automaticamente em `INVALID`; `INVALID` nunca deve alimentar treinamento ou geração de sinal.
