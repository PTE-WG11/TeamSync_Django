#!/usr/bin/env python
"""
Database initialization script for TeamSync.
Creates database and runs migrations.
"""
import os
import sys
import subprocess
import pymysql

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'charset': 'utf8mb4'
}

DB_NAME = 'teamsync'


def create_database():
    """Create database if not exists."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        if cursor.fetchone():
            print(f"Database '{DB_NAME}' already exists.")
        else:
            # Create database
            cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"Database '{DB_NAME}' created successfully.")
        
        cursor.close()
        conn.close()
        return True
    
    except pymysql.Error as e:
        print(f"Error creating database: {e}")
        return False


def run_migrations():
    """Run Django migrations."""
    try:
        # Make migrations
        print("\nMaking migrations...")
        result = subprocess.run(
            [sys.executable, 'manage.py', 'makemigrations'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Run migrations
        print("\nRunning migrations...")
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return True
    
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False


def create_superuser():
    """Create superuser."""
    print("\nCreating superuser...")
    print("Please enter superuser details:")
    
    try:
        result = subprocess.run(
            [sys.executable, 'manage.py', 'createsuperuser'],
            capture_output=False
        )
        return True
    except Exception as e:
        print(f"Error creating superuser: {e}")
        return False


def main():
    """Main function."""
    print("=" * 50)
    print("TeamSync Database Initialization")
    print("=" * 50)
    
    # Create database
    if not create_database():
        print("\nFailed to create database. Exiting.")
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        print("\nFailed to run migrations. Exiting.")
        sys.exit(1)
    
    # Create superuser
    create_superuser()
    
    print("\n" + "=" * 50)
    print("Database initialization completed!")
    print("=" * 50)


if __name__ == '__main__':
    main()
