from math import ceil
from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["*"])

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://sql12768431:k83Ece4r68@sql12.freesqldatabase.com/sql12768431'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'smartparking'

# Initialize Database
db = SQLAlchemy(app)
# Models

class Slot(db.Model):
    __tablename__ = 'slots'
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(255), nullable=False, default="free")

    # Foreign key to Drivers (One-to-One Relationship)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id', ondelete="SET NULL"), unique=True, nullable=True)
    
    # Relationship with Drivers
    driver = db.relationship('Drivers', back_populates='slot')

class Drivers(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    ownerName = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    vehicle_name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.String(255), unique=True, nullable=False)
    bankNumber = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.now)
    entry_time = db.Column(db.DateTime, nullable=True)
    exit_time = db.Column(db.DateTime, nullable=True)
    
    # One-to-One Relationship with Slot
    slot = db.relationship('Slot', back_populates='driver', uselist=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Feedbacks(db.Model):
    __tablename__ = 'Feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    Feedback_by=db.Column(db.String(255), nullable=False)
    Feedback_desc = db.Column(db.String(255), nullable=False)
    rate = db.Column(db.Integer, nullable=False)

class Bookings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    slot_number = db.Column(db.String(50))
    ownerName = db.Column(db.String(100))
    vehicle_name = db.Column(db.String(100))
    entry_time = db.Column(db.DateTime)  
    exit_time = db.Column(db.DateTime)   

    def __init__(self, user_id,slot_number, ownerName, vehicle_name, entry_time, exit_time):
        self.slot_number = slot_number
        self.ownerName = ownerName
        self.vehicle_name = vehicle_name
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.user_id=user_id
    



@app.route('/get-slots', methods=['GET'])
def get_slots():
    try:
        slots = Slot.query.all()
        
        slot_list = [
            {"id": slot.id, "slot_number": slot.slot_number, "status": slot.status}
            for slot in slots
        ]
 
        return jsonify(slot_list),200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


@app.route('/get-booked-slot/<int:user_id>', methods=['GET'])
def get_booked_slot(user_id):
    try:
        driver = Drivers.query.filter_by(user_id=user_id).first()
        if not driver:
            return jsonify({"error": "Driver not found"}), 404

        slot = Slot.query.filter_by(driver_id=driver.id).first()
        if not slot:
            return jsonify({"error": "No booked slot found"}), 404

        return jsonify({
            "slotId": slot.id,
            "slot_number": slot.slot_number,
            "status": slot.status,
            "bookedAt": driver.entry_time.isoformat() if driver.entry_time else None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/get-slot/<int:slot_id>', methods=['GET'])
def get_slot(slot_id):  # Accept slot_id as a parameter
    try:
        slot = (
            db.session.query(
                Slot.id,
                Slot.slot_number,
                Slot.status,
                Drivers.user_id  # Ensure user_id is fetched as a string
            )
            .outerjoin(Drivers, Slot.driver_id == Drivers.id)  # LEFT JOIN with Drivers
            .filter(Slot.id == slot_id)  # Filter by the given slot_id
            .first()
        )

        if not slot:
            return jsonify({"error": "Slot not found"}), 404

        slot_data = {
            "id": slot.id,
            "slot_number": slot.slot_number,
            "status": slot.status,
            "driver_id": str(slot.user_id) if slot.user_id else None  # Convert user_id to string
        }

        return jsonify(slot_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/get-slots-args', methods=['GET'])
def get_slots_args():
    # Get query parameters for pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Fetch slots from the database with pagination
    slots_query = Slot.query.paginate(page=page, per_page=per_page, error_out=False)
    slots = slots_query.items

    # Prepare the response data
    slots_data = []
    for slot in slots:
        slots_data.append({
            'id': slot.id,
            'slot_number': slot.slot_number,
            'status': slot.status,
            'driver_id': slot.driver.id if slot.driver else None,  # Ensure it's an ID, not an object
        })

    # Calculate the total number of slots and total pages
    total_slots = Slot.query.count()
    total_pages = ceil(total_slots / per_page)

    response = {
        'slots': slots_data,
        'total': total_slots,
        'pages': total_pages,
        'current_page': page,
    }

    return jsonify(response), 200

# add-slot Route
@app.route('/add-slot', methods=['POST'])
def add_slot():    
    data = request.json
    slot_number = data.get('slot_number')
    if not slot_number:
        return jsonify({"error": "Slot number is required"}), 400

    existing_slot = Slot.query.filter_by(slot_number=slot_number).first()
    if existing_slot:
        return jsonify({"error": "Slot already exists"}), 409

    new_slot = Slot(slot_number=slot_number, status="free")
    db.session.add(new_slot)
    db.session.commit()

    return jsonify({"message": "Slot added successfully"}), 201


@app.route('/edit-slot/<int:slot_id>', methods=['PUT'])
def edit_slot(slot_id):
    data = request.json
    slot_number = data.get('slot_number')
    status = data.get('status')

    if not slot_number:
        return jsonify({"error": "Slot number is required"}), 400

    slot = Slot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Slot not found"}), 404

    # Update slot details
    slot.slot_number = slot_number
    slot.status = status
    db.session.commit()

    return jsonify({"message": "Slot updated successfully"}), 200

@app.route('/delete-slot/<int:slot_id>', methods=['DELETE'])
def delete_slot(slot_id):
    slot = Slot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Slot not found"}), 404

    db.session.delete(slot)
    db.session.commit()

    return jsonify({"message": "Slot deleted successfully"}), 200



@app.route('/book-slot/<int:slot_id>/<int:user_id>', methods=['POST'])
def book_slot(slot_id, user_id):
    try:
        # Fetch the slot from the database
        slot = Slot.query.get(slot_id)
        if not slot:
            return jsonify({"error": "Slot not found"}), 404
        
        # Check if the slot is already occupied
        if slot.status == "occupied":
            return jsonify({"error": "Slot already booked"}), 400
        
        # Fetch the driver information
        driver = Drivers.query.filter_by(user_id=user_id).first()
        if not driver:
            return jsonify({"error": "Driver not found"}), 404
        
        # Update the slot's status to "occupied" and associate it with the driver
        slot.status = "occupied"
        slot.driver_id = driver.id
        driver.entry_time = datetime.now()

        # Commit the changes to the database
        db.session.commit()

        return jsonify({"message": "Slot booked successfully", "entry_time": driver.entry_time})

    except Exception as e:
        db.session.rollback() 
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500






@app.route('/cancel-slot/<int:slot_id>', methods=['POST'])
def cancel_slot(slot_id):
    try:
        slot = Slot.query.get(slot_id)

        if not slot:
            return jsonify({"error": "Slot not found"}), 404
   
        slot.status = "free"
        slot.driver_id = None
        db.session.commit()

        return jsonify({"message": "Slot cancelled successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500





@app.route('/exit-slot/<int:slot_id>/<int:user_id>', methods=['POST'])
def exit_slot(slot_id, user_id):
    try:
        driver = Drivers.query.filter_by(user_id=user_id).first()
        if not driver:
            return jsonify({"error": "Driver not found"}), 404

        slot = Slot.query.filter_by(id=slot_id, driver_id=driver.id).first()
        if not slot:
            return jsonify({"error": "Slot not found or not booked by this user"}), 404

        driver.exit_time = datetime.now()

        new_booking = Bookings(
            slot_number=slot.slot_number,
            user_id=driver.user_id,
            ownerName=driver.ownerName,
            vehicle_name=driver.vehicle_name,
            entry_time=driver.entry_time,
            exit_time=driver.exit_time  
        )
        db.session.add(new_booking)

        slot.status = "free"
        slot.driver_id = None

        # Commit changes to the database
        db.session.commit()

        return jsonify({"message": "Slot exited successfully, booking record created!"}), 200

    except Exception as e:
        db.session.rollback()  
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/booking-history', methods=['GET'])
def get_booking_history():
    try:
        # Retrieve user_id from the query string
        user_id = request.args.get('user_id', type=int)

        if user_id == 1000:
            # Fetch all bookings for user_id = 1000
            bookings = Bookings.query.all()
        else:
            # Fetch bookings for a specific user
            bookings = Bookings.query.filter_by(user_id=user_id).all()

        # Format the response data
        booking_data = []
        for booking in bookings:
            booking_data.append({
                "slot_number": booking.slot_number,
                "user_id":booking.user_id,
                "ownerName": booking.ownerName,
                "vehicle_name": booking.vehicle_name,
                "entry_time": booking.entry_time,
                "exit_time": booking.exit_time,
            })

        return jsonify(booking_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.json  
        feedback_by = data.get("feedback_by")
        feedback_desc = data.get("feedback_desc")
        rate = data.get("rate")

        if not feedback_by or not feedback_desc or rate is None:
            return jsonify({"error": "Missing required fields"}), 400

        new_feedback = Feedbacks(
            Feedback_by=feedback_by,
            Feedback_desc=feedback_desc,
            rate=rate
        )
        db.session.add(new_feedback)
        db.session.commit()

        return jsonify({"message": "Feedback submitted successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# Login Route
@app.route('/login', methods=['POST'])
def login():
    user_id = request.json.get('user_id')
    password = request.json.get('password')
    
    driver = Drivers.query.filter_by(user_id=user_id).first()
    
    if driver and driver.check_password(password):
        session['user_id'] = driver.user_id
        return jsonify({
            "message": "Login Success",
            "user": {
                "user_id": driver.user_id,
                "vehicleName": driver.vehicle_name,
                "ownerName": driver.ownerName,
                "bankNumber": driver.bankNumber,
                "role": driver.role,
                "slot": driver.slot.slot_number if driver.slot else None
            }
        })
    else:
        return jsonify({"message": "Login Failed"}), 401

# Register Route
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        ownerName = data.get('ownerName')
        password = data.get('password')
        vehicle_name = data.get('vehicle_name')
        user_id = data.get('user_id')
        bankNumber = data.get('bankNumber')

        if not all([ownerName, password, vehicle_name, user_id, bankNumber]):
            return jsonify({"error": "All fields are required"}), 400

        existing_driver = Drivers.query.filter_by(user_id=user_id).first()
        if existing_driver:
            return jsonify({"error": "User ID already exists"}), 409

        driver = Drivers(
            ownerName=ownerName,
            vehicle_name=vehicle_name,
            user_id=user_id,
            bankNumber=bankNumber
        )
        driver.set_password(password)

        db.session.add(driver)
        db.session.commit()

        return jsonify({"message": "Driver Registered"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/get-user-id/<string:user_id>', methods=['GET'])
def get_user_id(user_id):
    driver = Drivers.query.filter_by(user_id=user_id).first()
    print(driver)
    if not driver:
        return jsonify({"error": "User not found"}), 404  # Handle invalid user_id
    
    return jsonify({"id": driver.id}), 200



@app.route('/update-user', methods=['POST'])
def update_user():
    try:
        data = request.get_json()
        print(data)
        user_id = data.get('user_id')
        owner_name = data.get('ownerName')
        vehicle_name = data.get('vehicleName')
        bank_number = data.get('bankNumber')
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')

        driver = Drivers.query.filter_by(user_id=user_id).first()
        if not driver:
            return jsonify({"error": "User not found"}), 404

        # Verify old password
        if old_password and not check_password_hash(driver.password, old_password):
            return jsonify({"error": "Incorrect old password"}), 401

        # Update user details
        driver.ownerName = owner_name
        driver.vehicle_name = vehicle_name
        driver.bankNumber = bank_number
        if new_password:
            driver.password = generate_password_hash(new_password)

        db.session.commit()
        return jsonify({"success": True, "message": "User information updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/drivers', methods=['GET'])
def get_drivers():
    try:
        drivers = Drivers.query.all()
        driver_list = []
        
        for driver in drivers:
            driver_list.append({
                "id": driver.id,
                "ownerName": driver.ownerName,
                "vehicle_name": driver.vehicle_name,
                "user_id": driver.user_id,
                "entry_time": driver.entry_time,
                "exit_time": driver.exit_time,
                "created_at": driver.created_at,
                "BankNumber": driver.bankNumber,

                # Ensure slot data is fetched correctly
                "slot_id": driver.slot.id if driver.slot else None,  
                "slot_number": driver.slot.slot_number if driver.slot else None,  
                "slot_status": driver.slot.status if driver.slot else None  
            })
        
        return jsonify(driver_list), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500





# Logout Route
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logout Success"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()  #debug=True
