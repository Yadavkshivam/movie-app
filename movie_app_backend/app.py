from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = 'movieapp.db'

# Helper functions for SQLite operations

def create_connection():
    conn = sqlite3.connect(DATABASE)
    return conn

def execute_query(query, args=()):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(query, args)
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id

def fetch_query(query, args=()):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(query, args)
    result = cursor.fetchall()
    conn.close()
    return result

# Initialize the database
def init_db():
    conn = create_connection()
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            dob DATE NOT NULL,
            phone_number TEXT,
            label INTEGER NOT NULL
        )
    ''')

    # Create Movies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            movie_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            genre TEXT,
            director TEXT,
            release_date DATE,
            duration_minutes INTEGER,
            show_time DATETIME NOT NULL,
            rating REAL,
            description TEXT,
            language TEXT
        )
    ''')

    # Create Bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            show_time DATETIME NOT NULL,
            seats TEXT NOT NULL,
            total_price NUMERIC NOT NULL,
            booking_status TEXT NOT NULL,
            seat_level TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        )
    ''')

    # Create Payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            booking_id INTEGER PRIMARY KEY,
            amount_paid NUMERIC NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings (booking_id)
        )
    ''')

    # Create Food table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food (
            food_id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_item TEXT NOT NULL
        )
    ''')

    # Create FoodBookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_bookings (
            booking_id INTEGER NOT NULL,
            food_id INTEGER NOT NULL,
            total_price NUMERIC NOT NULL,
            PRIMARY KEY (booking_id, food_id),
            FOREIGN KEY (booking_id) REFERENCES bookings (booking_id),
            FOREIGN KEY (food_id) REFERENCES food (food_id)
        )
    ''')

    conn.commit()
    conn.close()

# Initialize the database on app startup
init_db()

# Routes

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    insert_query = '''
        INSERT INTO users (username, email, password, first_name, last_name, dob, phone_number, label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    execute_query(insert_query, (
        data['username'],
        data['email'],
        data['password'],
        data['first_name'],
        data['last_name'],
        datetime.strptime(data['dob'], '%Y-%m-%d').date(),
        data['phone_number'],
        data['label']
    ))
    return jsonify({"message": "User registered successfully!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    select_query = '''
        SELECT * FROM users WHERE email = ? AND password = ?
    '''
    result = fetch_query(select_query, (data['email'], data['password']))
    if result:
        return jsonify({"message": "Login successful!"})
    else:
        return jsonify({"message": "Invalid email or password!"}), 401

@app.route('/search_movies', methods=['GET'])
def search_movies():
    select_query = '''
        SELECT * FROM movies
    '''
    movies = fetch_query(select_query)
    movie_list = [{
        'movie_id': movie[0],
        'title': movie[1],
        'genre': movie[2],
        'director': movie[3],
        'release_date': movie[4],
        'duration_minutes': movie[5],
        'show_time': movie[6],
        'rating': movie[7],
        'description': movie[8],
        'language': movie[9]
    } for movie in movies]
    return jsonify(movie_list)
@app.route('/book_movie', methods=['POST'])
def book_movie():
    data = request.get_json()

    # Ensure all required fields are present
    required_fields = ['user_id', 'movie_id', 'show_time', 'seats', 'total_price']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"Missing required field: {field}"}), 400

    # Determine seat level based on label if provided
    seat_level = determine_seat_level(data.get('label')) if 'label' in data else 'default_level'

    # Insert into bookings table
    insert_booking_query = '''
        INSERT INTO bookings (user_id, movie_id, show_time, seats, total_price, booking_status, seat_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    booking_id = execute_query(insert_booking_query, (
        data['user_id'],
        data['movie_id'],
        datetime.strptime(data['show_time'], '%Y-%m-%d %H:%M:%S'),
        data['seats'],
        data['total_price'],
        'confirmed',
        seat_level
    ))

    # Insert into payments table
    insert_payment_query = '''
        INSERT INTO payments (booking_id, amount_paid, payment_method, payment_status)
        VALUES (?, ?, ?, ?)
    '''
    execute_query(insert_payment_query, (
        booking_id,
        data['total_price'],
        data.get('payment_method', 'N/A'),
        'paid'
    ))

    return jsonify({"message": "Movie booked successfully!"}), 201

def determine_seat_level(label):
    if label > 4:
        return 'silver+'
    elif label > 8:
        return 'gold'
    return silver

@app.route('/book_food', methods=['POST'])
def book_food():
    data = request.get_json()
    insert_food_booking_query = '''
        INSERT INTO food_bookings (booking_id, food_id, total_price)
        VALUES (?, ?, ?)
    '''
    execute_query(insert_food_booking_query, (
        data['booking_id'],
        data['food_id'],
        data['total_price']
    ))
    return jsonify({"message": "Food booked successfully!"}), 201

@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    data = request.get_json()
    update_booking_query = '''
        UPDATE bookings SET booking_status = 'cancelled' WHERE booking_id = ?
    '''
    execute_query(update_booking_query, (data['booking_id'],))
    return jsonify({"message": "Booking cancelled successfully!"})

@app.route('/cancel_food', methods=['POST'])
def cancel_food():
    data = request.get_json()
    delete_food_booking_query = '''
        DELETE FROM food_bookings WHERE booking_id = ? AND food_id = ?
    '''
    execute_query(delete_food_booking_query, (data['booking_id'], data['food_id']))
    return jsonify({"message": "Food booking cancelled successfully!"})

@app.route('/see_booking_status/<int:booking_id>', methods=['GET'])
def see_booking_status(booking_id):
    select_booking_query = '''
        SELECT booking_status FROM bookings WHERE booking_id = ?
    '''
    result = fetch_query(select_booking_query, (booking_id,))
    if result:
        return jsonify({
            'booking_id': booking_id,
            'booking_status': result[0][0]
        })
    else:
        return jsonify({"message": "Booking not found!"}), 404

@app.route('/see_payment_status/<int:booking_id>', methods=['GET'])
def see_payment_status(booking_id):
    select_payment_query = '''
        SELECT payment_status FROM payments WHERE booking_id = ?
    '''
    result = fetch_query(select_payment_query, (booking_id,))
    if result:
        return jsonify({
            'booking_id': booking_id,
            'payment_status': result[0][0]
        })
    else:
        return jsonify({"message": "Payment not found!"}), 404

@app.route('/delete_account/<int:user_id>', methods=['DELETE'])
def delete_account(user_id):
    delete_user_query = '''
        DELETE FROM users WHERE user_id = ?
    '''
    execute_query(delete_user_query, (user_id,))
    return jsonify({"message": "User account deleted successfully!"})

@app.route('/seed_data', methods=['POST'])
def seed_data():
    conn = create_connection()
    cursor = conn.cursor()

    # Seed Users
    users = [
        ("amit", "amit@example.com", "password", "Amit", "Sharma", "1990-01-01", "1234567890", 10),
        ("raj", "raj@example.com", "password", "Raj", "Kumar", "1985-02-02", "0987654321", 14)
    ]
    cursor.executemany('''
        INSERT INTO users (username, email, password, first_name, last_name, dob, phone_number, label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', users)

    # Seed Movies
    movies = [
        ("Inception", "Sci-Fi", "Christopher Nolan", "2010-07-16", 148, "2023-06-18 18:00:00", 8.8, "A thief who steals corporate secrets through the use of dream-sharing technology.", "English"),
        ("Interstellar", "Sci-Fi", "Christopher Nolan", "2014-11-07", 169, "2023-06-19 18:00:00", 8.6, "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.", "English"),
        ("The Dark Knight", "Action", "Christopher Nolan", "2008-07-18", 152, "2023-06-20 18:00:00", 9.0, "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.", "English")
    ]
    cursor.executemany('''
        INSERT INTO movies (title, genre, director, release_date, duration_minutes, show_time, rating, description, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', movies)

    conn.commit()
    conn.close()

    return jsonify({"message": "Database seeded successfully!"}), 201

if __name__ == '__main__':
    app.run(debug=True)