# OTel Observability Demo

Repositório de teste para coletar **métricas, logs e traces** de uma aplicação
via **OpenTelemetry Collector**, encaminhando:

- **Traces** → Grafana Tempo
- **Métricas** → Prometheus
- **Logs** → OpenSearch

Tudo visualizado no **Grafana**, com os três datasources já provisionados.

## Arquitetura

```
demo-app (FastAPI + OTel SDK)
      │  OTLP gRPC (4317)
      ▼
otel-collector (opentelemetry-collector-contrib)
      │
      ├── traces  ──► Tempo (4317) ───────────┐
      ├── metrics ──► exposed em :8889 ◄── Prometheus (scrape)
      └── logs    ──► OpenSearch (9200) ──┬──►┘
                                           │       Grafana (3000)
                                           │  datasources: Prometheus, Tempo, OpenSearch
                                           ▼
                              OpenSearch Dashboards (5601)
```

## Serviços (docker-compose)

| Serviço        | Porta  | Descrição                              |
|----------------|--------|-----------------------------------------|
| app            | 8000   | FastAPI instrumentada com OTel SDK      |
| otel-collector | 4317/4318 | Recebe OTLP, roteia p/ os backends   |
| prometheus     | 9090   | Scrape das métricas expostas pelo collector |
| tempo          | 3200   | Armazena traces                         |
| opensearch     | 9200   | Armazena logs                           |
| opensearch-dashboards | 5601 | UI de consulta do OpenSearch (Discover / Dev Tools) |
| grafana        | 3000   | Dashboards (admin / admin)              |

## Como rodar

```bash
docker compose up --build
```

Aguarde todos os containers subirem (OpenSearch demora um pouco mais).

## Gerando telemetria

```bash
curl http://localhost:8000/
curl http://localhost:8000/work
```

Chame `/work` várias vezes — ele gera spans aninhados, uma métrica de contador
e, ocasionalmente (20% das vezes), um log de erro.

## Onde ver os dados

- **Grafana**: http://localhost:3000 (login `admin` / `admin`)
  - Dashboard **Demo App Overview** já provisionado (abre na home) com:
    total de requests, taxa de requests por rota, contagem de logs de erro,
    logs recentes e traces recentes — tudo lendo dos 3 datasources
    automaticamente.
  - Explore → datasource **Tempo** → busque traces do serviço `demo-app`
  - Explore → datasource **Prometheus** → query `demo_app_requests_total`
  - Explore → datasource **OpenSearch** → índice `otel-logs*`
- **Prometheus** direto: http://localhost:9090
- **OpenSearch** direto: http://localhost:9200/otel-logs*/_search?pretty
  (segurança desabilitada — só para teste local)
- **OpenSearch Dashboards**: http://localhost:5601 (sem login)

### Consultar logs no OpenSearch Dashboards

O índice `otel-logs` só existe depois que a app grava pelo menos um log — se
o container `opensearch` acabou de subir, gere tráfego antes (seção acima).

1. ☰ → **Dashboards Management** → **Index patterns** → **Create index pattern**
2. Nome: `otel-logs*` → confirme que aparece "matches 1 source: otel-logs" → **Next step**
3. Time field: `@timestamp` → **Create index pattern**
4. ☰ → **Discover** → selecione `otel-logs*` no dropdown → ajuste o time range
   (ex.: "Last 15 minutes")

Campos úteis: `body` (mensagem do log), `severity.text` (INFO/ERROR),
`resource.service.name` (`demo-app`), `traceId`/`spanId` (correlação com o
trace no Tempo).

Para consultas via DSL: ☰ → **Dev Tools**:

```json
GET otel-logs/_search
{
  "query": { "match_all": {} },
  "sort": [{ "@timestamp": "desc" }]
}
```

> **Dados são efêmeros**: o `docker-compose.yml` não declara volume para o
> OpenSearch. Todo `docker compose down` (ou recriação do container) apaga o
> índice — normal para um ambiente de teste, mas se quiser persistir entre
> reinícios, adicione um volume no serviço `opensearch`.

## Notas

- Segurança do OpenSearch está desabilitada (`plugins.security.disabled=true`)
  — **não use essa config em produção**, é só para facilitar o teste local.
- O exporter `opensearch` do `otel-collector-contrib` está em evolução; se a
  versão `latest` da imagem mudar o schema de config, ajuste
  `otel-collector-config.yaml` conforme o changelog do
  [opentelemetry-collector-contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib).
- Plugin do Grafana para OpenSearch (`grafana-opensearch-datasource`) é
  instalado automaticamente via `GF_INSTALL_PLUGINS` no primeiro start.
- Grafana está pinado em `11.3.1` (não `latest`): a v13.x testada tinha um bug
  de renderização com dashboards vindos de provisionamento por arquivo — o
  modelo do dashboard ficava correto no backend mas nenhum painel montava na
  UI. `11.3.1` renderiza os mesmos painéis normalmente.
- Os datasources usam `uid` fixo (`prometheus`, `tempo`, `opensearch`) em
  `grafana/provisioning/datasources/datasources.yaml` — é isso que permite o
  dashboard (`grafana/provisioning/dashboards/demo-app-overview.json`)
  referenciá-los de forma determinística sem depender de UIDs gerados
  automaticamente.
- O campo `jsonData.version` do datasource OpenSearch precisa ser um semver
  válido da versão real do OpenSearch (ex.: `2.15.0`); `"2.x"` quebra as
  queries do plugin (`grafana-opensearch-datasource`) com erro
  `Invalid Semantic Version`.
