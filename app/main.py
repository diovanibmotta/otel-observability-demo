import logging
import os
import random
import time

from fastapi import FastAPI

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "demo-app")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")

resource = Resource.create({"service.name": SERVICE_NAME})

# --- Traces ---
trace.set_tracer_provider(TracerProvider(resource=resource))
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True))
)
tracer = trace.get_tracer(__name__)

# --- Metrics ---
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True),
    export_interval_millis=5000,
)
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))
meter = metrics.get_meter(__name__)
request_counter = meter.create_counter(
    "demo_app_requests_total", description="Total HTTP requests handled"
)

# --- Logs ---
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTEL_ENDPOINT, insecure=True))
)
otel_log_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(otel_log_handler)
root_logger.addHandler(logging.StreamHandler())

log = logging.getLogger("demo-app")

app = FastAPI(title="OTel Demo App")
FastAPIInstrumentor.instrument_app(app)


@app.get("/")
def root():
    request_counter.add(1, {"route": "/"})
    log.info("root endpoint called")
    return {"message": "hello"}


@app.get("/work")
def work():
    request_counter.add(1, {"route": "/work"})
    with tracer.start_as_current_span("do-work"):
        delay = random.uniform(0.05, 0.4)
        time.sleep(delay)

        with tracer.start_as_current_span("sub-task"):
            time.sleep(random.uniform(0.01, 0.1))

        if random.random() < 0.2:
            log.error("simulated error in /work")
            return {"status": "error"}

        log.info("work done in %.2fs", delay)
        return {"status": "ok", "duration": round(delay, 3)}
