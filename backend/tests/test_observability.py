"""
Unit Tests for Phase 10 Enterprise Observability & Health Probes
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestObservabilityEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["engine_version"], "5.0.0")

    def test_readiness_endpoint(self):
        response = self.client.get("/readiness")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    def test_liveness_endpoint(self):
        response = self.client.get("/liveness")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "alive")

    def test_metrics_endpoint(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["engine_version"], "5.0.0")

    def test_correlation_id_middleware(self):
        response = self.client.get("/health", headers={"X-Correlation-ID": "test-cid-12345"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Correlation-ID"), "test-cid-12345")
        self.assertTrue("X-Process-Time" in response.headers)


if __name__ == '__main__':
    unittest.main()
