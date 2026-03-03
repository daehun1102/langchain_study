# display_defect_chatbot/ai_server/infra/tracing.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.langchain import LangChainInstrumentor


def setup_tracing(endpoint: str) -> bool:
    try:
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("[tracing] Phoenix 연결 실패, 트레이싱 비활성화: %s", e)
        return False
