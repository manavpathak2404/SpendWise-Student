"""
test_phase1.py - Automated validation script for Phase 1
Tests database connectivity, table schema, user signup, password hashing, and authentication sessions.
"""

import sys
import unittest
from app import app
from db import get_db_connection, init_db
from werkzeug.security import check_password_hash

class TestPhase1Auth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure DB is initialized
        init_db()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        # Clean up any previous test user
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email IN ('teststudent@example.com', 'badstudent@example.com')")
            cursor.close()
            conn.close()

    def test_01_db_schema(self):
        """Verify users and transactions tables exist with expected columns."""
        conn = get_db_connection()
        self.assertIsNotNone(conn, "Database connection should succeed")
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("DESCRIBE users;")
        user_cols = {row['Field']: row['Type'] for row in cursor.fetchall()}
        self.assertIn('id', user_cols)
        self.assertIn('name', user_cols)
        self.assertIn('email', user_cols)
        self.assertIn('password_hash', user_cols)

        cursor.execute("DESCRIBE transactions;")
        tx_cols = {row['Field']: row['Type'] for row in cursor.fetchall()}
        self.assertIn('id', tx_cols)
        self.assertIn('user_id', tx_cols)
        self.assertIn('title', tx_cols)
        self.assertIn('amount', tx_cols)
        self.assertIn('type', tx_cols)
        self.assertIn('category', tx_cols)
        self.assertIn('date', tx_cols)
        
        cursor.close()
        conn.close()

    def test_02_signup_validation_failure(self):
        """Verify inline validation errors when submitting invalid signup form."""
        res = self.client.post('/signup', data={
            'name': '',
            'email': 'not-an-email',
            'password': '123',
            'confirm_password': '456'
        })
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Full name is required", html)
        self.assertIn("Please provide a valid email address", html)
        self.assertIn("Password must be at least 6 characters long", html)

    def test_03_signup_success(self):
        """Verify successful signup creates record with hashed password."""
        res = self.client.post('/signup', data={
            'name': 'Test Student',
            'email': 'teststudent@example.com',
            'password': 'SecretPassword123!',
            'confirm_password': 'SecretPassword123!'
        }, follow_redirects=False)
        
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # Verify password is truly hashed in database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s", ('teststudent@example.com',))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(user)
        self.assertNotEqual(user['password_hash'], 'SecretPassword123!')
        self.assertTrue(check_password_hash(user['password_hash'], 'SecretPassword123!'))

    def test_04_signup_duplicate_email(self):
        """Verify duplicate email registration is rejected with an inline error."""
        res = self.client.post('/signup', data={
            'name': 'Another Student',
            'email': 'teststudent@example.com',
            'password': 'SecretPassword123!',
            'confirm_password': 'SecretPassword123!'
        })
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("An account with this email address already exists", html)

    def test_05_login_invalid_credentials(self):
        """Verify login rejection with wrong password."""
        res = self.client.post('/login', data={
            'email': 'teststudent@example.com',
            'password': 'WrongPassword!'
        })
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Invalid email or password", html)

    def test_06_login_success_and_session(self):
        """Verify successful login initiates user session."""
        res = self.client.post('/login', data={
            'email': 'teststudent@example.com',
            'password': 'SecretPassword123!'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/', res.headers['Location'])

        # Test authenticated dashboard access
        dash_res = self.client.get('/')
        self.assertEqual(dash_res.status_code, 200)
        dash_html = dash_res.get_data(as_text=True)
        self.assertIn("Test Student", dash_html)

    def test_07_unauthenticated_redirect(self):
        """Verify unauthenticated user cannot access protected routes."""
        with self.client.session_transaction() as sess:
            sess.clear()
        res = self.client.get('/', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

    def test_08_logout(self):
        """Verify logout clears session and redirects to login."""
        # Log in first
        self.client.post('/login', data={
            'email': 'teststudent@example.com',
            'password': 'SecretPassword123!'
        })
        # Log out
        res = self.client.get('/logout', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # Verify dashboard requires login now
        dash_res = self.client.get('/', follow_redirects=False)
        self.assertEqual(dash_res.status_code, 302)
        self.assertIn('/login', dash_res.headers['Location'])


if __name__ == '__main__':
    unittest.main()
