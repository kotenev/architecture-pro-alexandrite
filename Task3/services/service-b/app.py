from flask import Flask, jsonify
import os
import time
import random
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor

resource = Resource(attributes={
    "service.name": "service-b-calculation",
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

tracer = trace.get_tracer(__name__)

def calculate_base_price():
    time.sleep(0.1)
    return random.uniform(100, 500)


def calculate_tax(base_price, tax_rate=0.20):
    time.sleep(0.05)
    return base_price * tax_rate

def calculate_discount(base_price, discount_rate=0.10):
    time.sleep(0.05)
    return base_price * discount_rate

@app.route('/calculate')
def calculate():
    with tracer.start_as_current_span("calculate-order-price") as span:
        span.set_attribute("calculation.type", "full")
        
        with tracer.start_as_current_span("calculate-base-price") as base_span:
            base_price = calculate_base_price()
            base_span.set_attribute("price.base", base_price)
            base_span.add_event("Base price calculated")
        
        with tracer.start_as_current_span("calculate-tax") as tax_span:
            tax_rate = 0.20
            tax = calculate_tax(base_price, tax_rate)
            tax_span.set_attribute("tax.rate", tax_rate)
            tax_span.set_attribute("tax.amount", tax)
            tax_span.add_event("Tax calculated")
        
        with tracer.start_as_current_span("calculate-discount") as discount_span:
            discount_rate = 0.10
            discount = calculate_discount(base_price, discount_rate)
            discount_span.set_attribute("discount.rate", discount_rate)
            discount_span.set_attribute("discount.amount", discount)
            discount_span.add_event("Discount calculated")
        
        total_price = base_price + tax - discount
        
        span.set_attribute("price.total", total_price)
        span.add_event("Total price calculated", {
            "calculation.steps": 3,
            "calculation.success": True
        })
        
        return jsonify({
            "service": "service-b-calculation",
            "base_price": round(base_price, 2),
            "tax": round(tax, 2),
            "discount": round(discount, 2),
            "total_price": round(total_price, 2),
            "currency": "RUB",
            "status": "success"
        })

@app.route('/health')
def health():
    return jsonify({
        "service": "service-b-calculation",
        "status": "healthy",
        "version": "1.0.0"
    })

@app.route('/')
def index():
    return jsonify({
        "service": "service-b-calculation",
        "message": "Calculation service is running",
        "endpoints": {
            "/calculate": "Calculate order price",
            "/health": "Health check"
        }
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8081))
    app.run(host='0.0.0.0', port=port, debug=False)
