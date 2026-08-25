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
      └── logs    ──► OpenSearch (9200)       │
                                               ▼
                                           Grafana (3000)
                              datasources: Prometheus, Tempo, OpenSearch
```

## Serviços (docker-compose)

| Serviço        | Porta  | Descrição                              |
|----------------|--------|-----------------------------------------|
| app            | 8000   | FastAPI instrumentada com OTel SDK      |
| otel-collector | 4317/4318 | Recebe OTLP, roteia p/ os backends   |
| prometheus     | 9090   | Scrape das métricas expostas pelo collector |
| tempo          | 3200   | Armazena traces                         |
| opensearch     | 9200   | Armazena logs                           |
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
  - Explore → datasource **Tempo** → busque traces do serviço `demo-app`
  - Explore → datasource **Prometheus** → query `demo_app_requests_total`
  - Explore → datasource **OpenSearch** → índice `otel-logs*`
- **Prometheus** direto: http://localhost:9090
- **OpenSearch** direto: http://localhost:9200/otel-logs*/_search?pretty
  (segurança desabilitada — só para teste local)

## Notas

- Segurança do OpenSearch está desabilitada (`plugins.security.disabled=true`)
  — **não use essa config em produção**, é só para facilitar o teste local.
- O exporter `opensearch` do `otel-collector-contrib` está em evolução; se a
  versão `latest` da imagem mudar o schema de config, ajuste
  `otel-collector-config.yaml` conforme o changelog do
  [opentelemetry-collector-contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib).
- Plugin do Grafana para OpenSearch (`grafana-opensearch-datasource`) é
  instalado automaticamente via `GF_INSTALL_PLUGINS` no primeiro start.
