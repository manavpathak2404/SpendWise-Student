"""
test_phase2.py - Automated validation script for Phase 2
Tests Dashboard metrics, Add Transaction validation, persistence, and user isolation.
"""

import unittest
from datetime import date
from app import app
from db import get_db_connection, init_db

class TestPhase2DashboardAndAdd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Clean up test users
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email IN ('student_a@test.com', 'student_b@test.com')")
            cursor.close()
            conn.close()

        # Create user A
        cls.client.post('/signup', data={
            'name': 'Student A',
            'email': 'student_a@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Create user B
        cls.client.post('/signup', data={
            'name': 'Student B',
            'email': 'student_b@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

    def login_as(self, email, password='password123'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_01_empty_dashboard(self):
        """Dashboard for new user shows zero balances and empty state."""
        self.login_as('student_a@test.com')
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("No Transactions Yet", html)
        self.assertIn("Total Balance", html)
        self.assertIn("₹0.00", html)

    def test_02_add_transaction_validation_errors(self):
        """Add transaction rejects negative amounts, invalid titles, and incorrect categories."""
        self.login_as('student_a@test.com')
        
        # Test missing title and negative amount
        res = self.client.post('/add', data={
            'title': '',
            'amount': '-150.00',
            'type': 'expense',
            'category': 'Food',
            'date': '2026-09-25'
        })
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Title is required", html)
        self.assertIn("Amount must be strictly greater than ₹0", html)

        # Test zero amount
        res = self.client.post('/add', data={
            'title': 'Test Item',
            'amount': '0',
            'type': 'expense',
            'category': 'Food',
            'date': '2026-09-25'
        })
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Amount must be strictly greater than ₹0", html)

        # Test mismatched category (Salary is income, but type is expense)
        res = self.client.post('/add', data={
            'title': 'Test Item',
            'amount': '500',
            'type': 'expense',
            'category': 'Salary',
            'date': '2026-09-25'
        })
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Please select a valid expense category", html)

    def test_03_add_income_and_expense_success(self):
        """Add valid income and expense transactions and check dashboard metrics."""
        self.login_as('student_a@test.com')
        today = date.today().strftime('%Y-%m-%d')

        # Add Income: Monthly Allowance ₹5,000
        res_inc = self.client.post('/add', data={
            'title': 'Monthly Allowance',
            'amount': '5000.00',
            'type': 'income',
            'category': 'Allowance',
            'date': today
        }, follow_redirects=True)
        self.assertEqual(res_inc.status_code, 200)
        html_inc = res_inc.get_data(as_text=True)
        self.assertIn("Transaction &#39;Monthly Allowance&#39; added successfully!", html_inc)
        self.assertIn("₹5,000.00", html_inc)

        # Add Expense: College Books ₹1,200
        res_exp = self.client.post('/add', data={
            'title': 'College Books',
            'amount': '1200.00',
            'type': 'expense',
            'category': 'Education',
            'date': today
        }, follow_redirects=True)
        self.assertEqual(res_exp.status_code, 200)
        html_exp = res_exp.get_data(as_text=True)
        self.assertIn("Transaction &#39;College Books&#39; added successfully!", html_exp)
        
        # Verify Total Balance = 5000 - 1200 = 3800
        self.assertIn("₹3,800.00", html_exp)
        # Verify Total Expense = 1200
        self.assertIn("₹1,200.00", html_exp)
        # Verify recent transactions table shows both
        self.assertIn("Monthly Allowance", html_exp)
        self.assertIn("College Books", html_exp)

    def test_04_user_data_isolation(self):
        """Ensure Student B cannot see transactions created by Student A."""
        self.login_as('student_b@test.com')
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        
        # Student B should have empty state
        self.assertIn("No Transactions Yet", html)
        self.assertNotIn("Monthly Allowance", html)
        self.assertNotIn("College Books", html)
        self.assertIn("₹0.00", html)


if __name__ == '__main__':
    unittest.main()
