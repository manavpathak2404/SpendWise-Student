"""
test_phase5.py - Automated validation script for Phase 5
Tests currency formatting (Indian style ₹1,20,000.00), UI edge cases, empty states, and navbar buttons.
"""

import unittest
from app import app, format_inr
from db import get_db_connection, init_db

class TestPhase5UIPolishAndCurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Create fresh user for testing UI states
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = 'p5_user@test.com'")
            cursor.close()
            conn.close()

        cls.client.post('/signup', data={
            'name': 'P5 Student',
            'email': 'p5_user@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

    def test_01_indian_currency_formatting(self):
        """Test exact Indian currency comma grouping across orders of magnitude."""
        self.assertEqual(format_inr(0), "₹0.00")
        self.assertEqual(format_inr(5), "₹5.00")
        self.assertEqual(format_inr(50.5), "₹50.50")
        self.assertEqual(format_inr(999.99), "₹999.99")
        self.assertEqual(format_inr(1000), "₹1,000.00")
        self.assertEqual(format_inr(10000), "₹10,000.00")
        self.assertEqual(format_inr(120000), "₹1,20,000.00")
        self.assertEqual(format_inr(1500000.5), "₹15,00,000.50")
        self.assertEqual(format_inr(10000000), "₹1,00,00,000.00")
        self.assertEqual(format_inr(-120000), "-₹1,20,000.00")
        self.assertEqual(format_inr(-50.25), "-₹50.25")
        self.assertEqual(format_inr(None), "₹0.00")
        self.assertEqual(format_inr("not-a-number"), "₹0.00")

    def test_02_single_add_transaction_button_in_navbar(self):
        """Verify only one button linking to /add exists and it is located in the navbar."""
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'p5_user@test.com', 'password': 'password123'})
        
        # Check Dashboard page
        dash_res = self.client.get('/')
        dash_html = dash_res.get_data(as_text=True)
        self.assertEqual(dash_html.count('href="/add"'), 1, 
                         "Dashboard should contain exactly one link/button pointing to /add (in navbar)")

        # Verify that the /add link is inside the <nav> element
        nav_part = dash_html.split('</nav>')[0]
        body_part = dash_html.split('</nav>')[1]
        self.assertIn('href="/add"', nav_part)
        self.assertNotIn('href="/add"', body_part)

        # Check All Transactions page
        tx_res = self.client.get('/transactions')
        tx_html = tx_res.get_data(as_text=True)
        self.assertEqual(tx_html.count('href="/add"'), 1, 
                         "All Transactions page should contain exactly one link/button pointing to /add (in navbar)")

    def test_03_empty_states_rendered_properly(self):
        """Verify empty states display appropriate guidance when no data exists."""
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'p5_user@test.com', 'password': 'password123'})

        # Dashboard empty state
        dash_res = self.client.get('/')
        dash_html = dash_res.get_data(as_text=True)
        self.assertIn("No Transactions Yet", dash_html)
        self.assertIn("empty-state", dash_html)

        # Transactions empty state
        tx_res = self.client.get('/transactions')
        tx_html = tx_res.get_data(as_text=True)
        self.assertIn("No Matching Transactions", tx_html)
        self.assertIn("empty-state", tx_html)

    def test_04_delete_modal_structure(self):
        """Verify base template includes the modal markup for confirmation dialog."""
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'p5_user@test.com', 'password': 'password123'})
        res = self.client.get('/')
        html = res.get_data(as_text=True)
        self.assertIn("deleteConfirmModal", html)
        self.assertIn("Confirm Deletion", html)
        self.assertIn("Delete Permanently", html)


if __name__ == '__main__':
    unittest.main()
