"""
Integration Tests for Authentication API Flow (Registration, Login, Protected Route, Refresh)
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestAuthIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.test_email = "authtest@example.com"
        self.test_password = "Password123!"

    def test_auth_full_lifecycle(self):
        # 1. Register
        reg_response = self.client.post("/api/auth/register", json={
            "email": self.test_email,
            "full_name": "Auth Test User",
            "password": self.test_password
        })
        # If user already registered in previous run, expect 400, else 200
        self.assertIn(reg_response.status_code, [200, 400])

        # 2. Successful Login
        login_response = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(login_response.status_code, 200)
        tokens = login_response.json()
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

        access_token = tokens["access_token"]

        # 3. Access Protected Route /api/auth/me
        me_response = self.client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(me_response.status_code, 200)
        user_data = me_response.json()
        self.assertEqual(user_data["email"], self.test_email)

        # 4. Failed Login with Wrong Password
        bad_login = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "WrongPassword999!"
        })
        self.assertEqual(bad_login.status_code, 401)
        self.assertIn("Invalid email or password", bad_login.json()["detail"])

        # 5. Access Protected Route with Invalid Token
        bad_me = self.client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid.jwt.token"
        })
        self.assertEqual(bad_me.status_code, 401)


if __name__ == '__main__':
    unittest.main()
