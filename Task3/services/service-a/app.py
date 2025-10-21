from flask import Flask, jsonify
import requests
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

resource = Resource(attributes={
    "service.name": "service-a-orders",
    "service.version": "1.0.0",
    "deployment.environment": "production"
})

provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

jaeger_endpoint = os.getenv("EXPORTER_ENDPOINT", "http://simplest-collector:4317")
otlp_exporter = OTLPSpanExporter(
    endpoint=jaeger_endpoint,
    insecure=True
)

span_processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(span_processor)

app = Flask(__name__)

FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

SERVICE_B_URL = os.getenv("SERVICE_B_URL", "http://service-b:8080")

@app.route('/')
def index():
    with tracer.start_as_current_span("process-order") as span:
        span.set_attribute("order.id", "ORDER-234567")
        span.set_attribute("customer.id", "CUSTOMER-890")

        span.add_event("Order received", {
            "order.type": "new",
            "order.priority": "high"
        })
        
        try:
            span.add_event("Calling calculation service")
            response = requests.get(f"{SERVICE_B_URL}/calculate", timeout=10)
            
            if response.status_code == 200:
                calculation_data = response.json()
                span.add_event("Calculation completed", {
                    "calculation.total": calculation_data.get("total_price", 0)
                })
                
                return jsonify({
                    "service": "service-a-orders",
                    "message": "Order processed successfully",
                    "order_id": "ORDER-234567",
                    "calculation": calculation_data,
                    "status": "success"
                })
            else:
                span.set_attribute("error", True)
                span.add_event("Calculation service error", {
                    "http.status_code": response.status_code
                })
                return jsonify({
                    "service": "service-a-orders",
                    "message": "Error in calculation service",
                    "status": "error"
                }), 500
                
        except requests.exceptions.RequestException as e:
            span.set_attribute("error", True)
            span.record_exception(e)
            span.add_event("Service B connection failed")
            
            return jsonify({
                "service": "service-a-orders",
                "message": f"Failed to connect to calculation service: {str(e)}",
                "status": "error"
            }), 500


@app.route('/health')
def health():
    return jsonify({
        "service": "service-a-orders",
        "status": "healthy",
        "version": "1.0.0"
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
