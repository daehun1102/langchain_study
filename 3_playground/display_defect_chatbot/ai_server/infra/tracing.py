# display_defect_chatbot/ai_server/infra/tracing.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.langchain import LangChainInstrumentor


def setup_tracing(endpoint: str):
    try:
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception:
        pass  # Tracing is optional
