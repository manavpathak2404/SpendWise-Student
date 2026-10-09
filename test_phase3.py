"""
test_phase3.py - Automated validation script for Phase 3
Tests All Transactions paginated table, filtering, sorting, edit, delete, and cross-user authorization.
"""

import unittest
from datetime import date, timedelta
from app import app
from db import get_db_connection, init_db

class TestPhase3TransactionsEditDelete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Clean up test users and data
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email IN ('p3_user_a@test.com', 'p3_user_b@test.com')")
            cursor.close()
            conn.close()

        # Create user A
        cls.client.post('/signup', data={
            'name': 'P3 User A',
            'email': 'p3_user_a@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Create user B
        cls.client.post('/signup', data={
            'name': 'P3 User B',
            'email': 'p3_user_b@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

    def login_as(self, email, password='password123'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_01_pagination_and_creation(self):
        """Create 12 transactions for User A and verify pagination (page 1 has 10, page 2 has 2)."""
        self.login_as('p3_user_a@test.com')
        today = date.today()

        for i in range(1, 13):
            tx_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            self.client.post('/add', data={
                'title': f'Item {i:02d}',
                'amount': f'{100 * i}.00',
                'type': 'expense' if i % 2 == 0 else 'income',
                'category': 'Food' if i % 2 == 0 else 'Salary',
                'date': tx_date
            }, follow_redirects=True)

        # Check page 1
        res_p1 = self.client.get('/transactions?page=1')
        self.assertEqual(res_p1.status_code, 200)
        html_p1 = res_p1.get_data(as_text=True)
        self.assertIn("Total Records: 12", html_p1)
        self.assertIn("Page <strong>1</strong> of <strong>2</strong>", html_p1)
        self.assertIn("Item 01", html_p1)

        # Check page 2
        res_p2 = self.client.get('/transactions?page=2')
        self.assertEqual(res_p2.status_code, 200)
        html_p2 = res_p2.get_data(as_text=True)
        self.assertIn("Page <strong>2</strong> of <strong>2</strong>", html_p2)
        self.assertIn("Item 12", html_p2)

    def test_02_filtering(self):
        """Verify type and category filtering on transactions table."""
        self.login_as('p3_user_a@test.com')

        # Filter by type=expense
        res_exp = self.client.get('/transactions?type=expense')
        self.assertEqual(res_exp.status_code, 200)
        html_exp = res_exp.get_data(as_text=True)
        self.assertIn("Total Records: 6", html_exp)
        self.assertIn("Item 02", html_exp)
        self.assertNotIn("Item 01", html_exp)

        # Filter by category=Food
        res_food = self.client.get('/transactions?category=Food')
        self.assertEqual(res_food.status_code, 200)
        html_food = res_food.get_data(as_text=True)
        self.assertIn("Total Records: 6", html_food)
        self.assertIn("Item 02", html_food)

    def test_03_edit_transaction(self):
        """Verify modifying an existing transaction via /edit/<id>."""
        self.login_as('p3_user_a@test.com')

        # Get User A's transaction id
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM transactions WHERE title = 'Item 01'")
        tx = cursor.fetchone()
        cursor.close()
        conn.close()
        self.assertIsNotNone(tx)
        tx_id = tx['id']

        # Edit transaction
        today = date.today().strftime('%Y-%m-%d')
        edit_res = self.client.post(f'/edit/{tx_id}', data={
            'title': 'Item 01 Updated',
            'amount': '999.00',
            'type': 'expense',
            'category': 'Shopping',
            'date': today
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        html = edit_res.get_data(as_text=True)
        self.assertIn("Item 01 Updated", html)
        self.assertIn("Shopping", html)
        self.assertIn("₹999.00", html)

    def test_04_cross_user_security(self):
        """User B cannot edit or delete User A's transactions."""
        # Find User A's transaction id
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM transactions WHERE title = 'Item 01 Updated'")
        tx = cursor.fetchone()
        cursor.close()
        conn.close()
        tx_id = tx['id']

        # Log in as User B
        self.login_as('p3_user_b@test.com')

        # Try to access edit page of User A's item
        get_res = self.client.get(f'/edit/{tx_id}', follow_redirects=True)
        self.assertIn("Transaction not found or you are not authorized to edit it", get_res.get_data(as_text=True))

        # Try to POST edit on User A's item
        post_edit_res = self.client.post(f'/edit/{tx_id}', data={
            'title': 'Hacked Title',
            'amount': '50.00',
            'type': 'expense',
            'category': 'Food',
            'date': '2026-09-25'
        }, follow_redirects=True)
        self.assertIn("Transaction not found or you are not authorized to edit it", post_edit_res.get_data(as_text=True))

        # Try to POST delete on User A's item
        post_del_res = self.client.post(f'/delete/{tx_id}', follow_redirects=True)
        self.assertIn("Transaction not found or you are not authorized to delete it", post_del_res.get_data(as_text=True))

        # Verify transaction still exists in DB
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT title FROM transactions WHERE id = %s", (tx_id,))
        item = cursor.fetchone()
        cursor.close()
        conn.close()
        self.assertIsNotNone(item)
        self.assertEqual(item['title'], 'Item 01 Updated')

    def test_05_delete_transaction(self):
        """User A deletes their own transaction."""
        self.login_as('p3_user_a@test.com')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM transactions WHERE title = 'Item 01 Updated'")
        tx = cursor.fetchone()
        cursor.close()
        conn.close()
        tx_id = tx['id']

        del_res = self.client.post(f'/delete/{tx_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn("Transaction deleted successfully", del_res.get_data(as_text=True))

        # Verify deleted from DB
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM transactions WHERE id = %s", (tx_id,))
        item = cursor.fetchone()
        cursor.close()
        conn.close()
        self.assertIsNone(item)

    def test_06_delete_requires_post(self):
        """GET request to /delete/<id> is rejected with 405 Method Not Allowed."""
        self.login_as('p3_user_a@test.com')
        res = self.client.get('/delete/999')
        self.assertEqual(res.status_code, 405)


if __name__ == '__main__':
    unittest.main()
