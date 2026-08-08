import logging

from fastapi import FastAPI

from .settings import TelemetrySettings, get_settings

logger = logging.getLogger(__name__)


def setup_telemetry(
    app: FastAPI,
    settings: TelemetrySettings | None = None,
) -> None:
    settings = settings or get_settings()
    if not settings.enabled:
        logger.info("Telemetry module disabled by configuration.")
        return

    try:
        from opentelemetry import metrics, trace
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
    except ImportError:
        logger.info("OpenTelemetry packages not installed; skipping telemetry setup.")
        return

    resource = Resource.create({SERVICE_NAME: settings.service_name})
    otlp_endpoint = settings.exporter_otlp_endpoint

    if settings.traces_enabled:
        tracer_provider = TracerProvider(resource=resource)
        if otlp_endpoint:
            trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
            logger.info(
                "OpenTelemetry Tracing initialized (endpoint: %s)", otlp_endpoint
            )
        else:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )
            logger.info("OpenTelemetry Tracing initialized with ConsoleSpanExporter.")
        trace.set_tracer_provider(tracer_provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    if settings.metrics_enabled and otlp_endpoint:
        metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
        reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)
        logger.info("OpenTelemetry Metrics initialized (endpoint: %s)", otlp_endpoint)

    if settings.logs_enabled and otlp_endpoint:
        log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(logger_provider)

        log_handler = LoggingHandler(
            level=logging.NOTSET, logger_provider=logger_provider
        )
        logging.getLogger().addHandler(log_handler)
        logger.info("OpenTelemetry Logging initialized (endpoint: %s)", otlp_endpoint)
