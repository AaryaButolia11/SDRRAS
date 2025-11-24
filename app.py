from flask import Flask, render_template, request, jsonify
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'disaster_db')

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def create_db_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            database=DB_NAME
        )
        if connection.is_connected():
            print("Successfully connected to MySQL database")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    return None

def init_database():
    """Initialize database and create tables if they don't exist"""
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
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
            
            connection.commit()
            print("Database tables initialized successfully")
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            cursor.close()
            connection.close()

def send_sms(phone_number, message):
    """Send SMS using Twilio"""
    try:
        # Format phone number (add +91 for India if not present)
        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number.lstrip('0')
        
        message_response = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"SMS sent successfully. SID: {message_response.sid}")
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/subscribe', methods=['POST'])
def subscribe():
    """Subscribe a phone number for alerts"""
    try:
        data = request.get_json()
        phone_number = data.get('phone')
        area = data.get('area', 'Not specified')
        
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400
        
        connection = create_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Check if phone number already exists
        cursor.execute(
            "SELECT * FROM subscribers WHERE phone_number = %s",
            (phone_number,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing subscription
            cursor.execute(
                "UPDATE subscribers SET is_active = TRUE, area = %s WHERE phone_number = %s",
                (area, phone_number)
            )
            message = "Your subscription has been reactivated!"
        else:
            # Insert new subscription
            cursor.execute(
                "INSERT INTO subscribers (phone_number, area) VALUES (%s, %s)",
                (phone_number, area)
            )
            message = "Successfully subscribed for disaster alerts!"
        
        connection.commit()
        
        # Send confirmation SMS
        sms_message = f"SDRRAS Alert: {message} You will receive updates for {area} area."
        send_sms(phone_number, sms_message)
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Failed to subscribe'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/emergency-request', methods=['POST'])
def emergency_request():
    """Handle emergency chat requests"""
    try:
        data = request.get_json()
        phone_number = data.get('phone')
        category = data.get('category')
        area = data.get('area')
        message = data.get('message', '')
        
        if not all([phone_number, category, area]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        connection = create_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Insert emergency request
        cursor.execute("""
            INSERT INTO emergency_requests (phone_number, category, area, message)
            VALUES (%s, %s, %s, %s)
        """, (phone_number, category, area, message))
        
        connection.commit()
        
        # Send confirmation SMS
        category_emojis = {
            'sos': '🆘',
            'medical': '🏥',
            'shelter': '🏠',
            'food': '🍲'
        }
        emoji = category_emojis.get(category, '⚠️')
        
        sms_text = f"SDRRAS Emergency: {emoji} Your {category.upper()} request for {area} has been registered. Help is on the way!"
        send_sms(phone_number, sms_text)
        
        return jsonify({
            'success': True,
            'message': 'Emergency request submitted successfully'
        }), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Failed to submit request'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/resource-request', methods=['POST'])
def resource_request():
    """Handle resource requests"""
    try:
        data = request.get_json()
        resource_type = data.get('resource')
        quantity = data.get('quantity')
        area = data.get('area')
        phone = data.get('phone')
        
        if not all([resource_type, quantity, area]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        connection = create_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Insert resource request
        cursor.execute("""
            INSERT INTO resource_requests (resource_type, quantity, area, requester_phone)
            VALUES (%s, %s, %s, %s)
        """, (resource_type, quantity, area, phone))
        
        connection.commit()
        
        # Send confirmation SMS if phone provided
        if phone:
            sms_text = f"SDRRAS: Your request for {quantity}x {resource_type} in {area} has been submitted. We'll process it soon!"
            send_sms(phone, sms_text)
        
        return jsonify({
            'success': True,
            'message': 'Resource request submitted successfully'
        }), 200
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Failed to submit request'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/broadcast-alert', methods=['POST'])
def broadcast_alert():
    """Send alert to all subscribers in specific area (admin function)"""
    try:
        data = request.get_json()
        alert_message = data.get('message')
        target_area = data.get('area', None)
        
        if not alert_message:
            return jsonify({'error': 'Message is required'}), 400
        
        connection = create_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Get active subscribers
        if target_area:
            cursor.execute(
                "SELECT phone_number FROM subscribers WHERE is_active = TRUE AND area = %s",
                (target_area,)
            )
        else:
            cursor.execute(
                "SELECT phone_number FROM subscribers WHERE is_active = TRUE"
            )
        
        subscribers = cursor.fetchall()
        
        success_count = 0
        for (phone,) in subscribers:
            if send_sms(phone, f"SDRRAS ALERT: {alert_message}"):
                success_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Alert sent to {success_count} subscribers'
        }), 200
        
    except Error as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Failed to broadcast alert'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    # Initialize database tables
    init_database()
    app.run(debug=True, port=5000)