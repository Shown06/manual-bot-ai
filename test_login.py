#!/usr/bin/env python3
"""
Test login functionality
"""

import sqlite3
import bcrypt

def test_login():
    # Connect to database
    conn = sqlite3.connect('manual_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    email = 'test@example.com'
    password = 'testpassword123'

    try:
        # Query user
        cursor.execute('''
            SELECT id, password_hash, plan, subscription_status, tenant_id
            FROM users WHERE email = ?
        ''', (email,))

        user = cursor.fetchone()

        if user:
            print(f"User found: {dict(user)}")

            # Check password
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
                print("✅ Password is valid")
                return True
            else:
                print("❌ Password is invalid")
                return False
        else:
            print("❌ User not found")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    test_login()
