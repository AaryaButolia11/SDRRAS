import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

def create_database():
    """Create the disaster_db database if it doesn't exist"""
    try:
        # Connect to MySQL without specifying database
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database
            cursor.execute("CREATE DATABASE IF NOT EXISTS disaster_db")
            print("✓ Database 'disaster_db' created successfully!")
            
            # Use the database
            cursor.execute("USE disaster_db")
            
            # Create subscribers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    phone_number VARCHAR(20) UNIQUE NOT NULL,
                    area VARCHAR(100),
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            print("✓ Table 'subscribers' created successfully!")
            
            # Create emergency_requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emergency_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    phone_number VARCHAR(20) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    area VARCHAR(100) NOT NULL,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending'
                )
            """)
            print("✓ Table 'emergency_requests' created successfully!")
            
            # Create resource_requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resource_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    resource_type VARCHAR(100) NOT NULL,
                    quantity INT NOT NULL,
                    area VARCHAR(100) NOT NULL,
                    requester_phone VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending'
                )
            """)
            print("✓ Table 'resource_requests' created successfully!")
            
            connection.commit()
            print("\n✓ Database setup completed successfully!")
            
    except Error as e:
        print(f"✗ Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    print("Creating database and tables...\n")
    create_database()