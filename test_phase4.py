"""
test_phase4.py - Automated validation script for Phase 4
Tests /api/chart-data endpoint, category aggregations, 6-month historical calculations, and user isolation.
"""

import unittest
from datetime import date
from app import app
from db import get_db_connection, init_db

class TestPhase4ChartsAndFiltering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Clean up test users and data
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email IN ('p4_user_a@test.com', 'p4_user_b@test.com')")
            cursor.close()
            conn.close()

        # Create user A
        cls.client.post('/signup', data={
            'name': 'P4 User A',
            'email': 'p4_user_a@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Create user B
        cls.client.post('/signup', data={
            'name': 'P4 User B',
            'email': 'p4_user_b@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

    def login_as(self, email, password='password123'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_01_chart_api_auth_required(self):
        """Unauthenticated call to /api/chart-data redirects to /login."""
        self.client.get('/logout')
        res = self.client.get('/api/chart-data')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

    def test_02_empty_chart_data(self):
        """New user gets empty categories and 6 month labels with 0s."""
        self.login_as('p4_user_b@test.com')
        res = self.client.get('/api/chart-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn('categories', data)
        self.assertIn('monthly', data)
        self.assertEqual(data['categories']['labels'], [])
        self.assertEqual(data['categories']['data'], [])
        self.assertEqual(len(data['monthly']['labels']), 6)
        self.assertEqual(data['monthly']['income'], [0.0] * 6)
        self.assertEqual(data['monthly']['expense'], [0.0] * 6)

    def test_03_category_aggregation(self):
        """Verify expenses by category aggregation for Doughnut Chart."""
        self.login_as('p4_user_a@test.com')
        today = date.today().strftime('%Y-%m-%d')

        # Add 2 Food expenses (600 + 400 = 1000)
        self.client.post('/add', data={'title': 'Lunch', 'amount': '600.00', 'type': 'expense', 'category': 'Food', 'date': today})
        self.client.post('/add', data={'title': 'Dinner', 'amount': '400.00', 'type': 'expense', 'category': 'Food', 'date': today})
        # Add Education expense (800)
        self.client.post('/add', data={'title': 'Notebooks', 'amount': '800.00', 'type': 'expense', 'category': 'Education', 'date': today})
        # Add Allowance income (should not appear in expense categories)
        self.client.post('/add', data={'title': 'Scholarship', 'amount': '15000.00', 'type': 'income', 'category': 'Scholarship', 'date': today})

        res = self.client.get('/api/chart-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        cat_labels = data['categories']['labels']
        cat_data = data['categories']['data']

        self.assertIn('Food', cat_labels)
        self.assertIn('Education', cat_labels)
        self.assertNotIn('Scholarship', cat_labels)  # Income must NOT appear in expense breakdown

        food_idx = cat_labels.index('Food')
        edu_idx = cat_labels.index('Education')

        self.assertEqual(cat_data[food_idx], 1000.0)
        self.assertEqual(cat_data[edu_idx], 800.0)

    def test_04_monthly_aggregation(self):
        """Verify monthly income and expense mapping for current month."""
        self.login_as('p4_user_a@test.com')
        res = self.client.get('/api/chart-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Last item in monthly is the current month
        current_month_income = data['monthly']['income'][-1]
        current_month_expense = data['monthly']['expense'][-1]

        self.assertEqual(current_month_income, 15000.0)
        self.assertEqual(current_month_expense, 1800.0)

    def test_05_chart_user_isolation(self):
        """User B's chart data remains empty and isolated from User A."""
        self.login_as('p4_user_b@test.com')
        res = self.client.get('/api/chart-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data['categories']['labels'], [])
        self.assertEqual(data['categories']['data'], [])
        self.assertEqual(data['monthly']['income'][-1], 0.0)
        self.assertEqual(data['monthly']['expense'][-1], 0.0)


if __name__ == '__main__':
    unittest.main()
