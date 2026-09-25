from .database import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Admin(db.Model):
    __tablename__='Admin'
    admin_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    admin_emailid=db.Column(db.String(100),unique=True,nullable=False)
    admin_name=db.Column(db.String(50),nullable=False)
    admin_pw=db.Column(db.String(50),nullable=False)

class Users(db.Model):
    __tablename__='Users'
    u_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    u_emailid=db.Column(db.String(100),unique=True,nullable=False)
    u_username = db.Column(db.String(50), nullable=False)
    u_ph_no=db.Column(db.Integer,unique=True,nullable=False)
    v_no=db.Column(db.String(20),nullable=True)
    u_add=db.Column(db.String(50),nullable=False)
    u_pw=db.Column(db.String(50),nullable=False)
    rps=db.relationship("Reserve_parkingspots",back_populates='user',lazy=True)


class Parking_history(db.Model):
    __tablename__ = 'Recent_Parking_history'
    p_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lot_area = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    u_id = db.Column(db.Integer, db.ForeignKey('Users.u_id'), nullable=False)
    reservation_id = db.Column(db.Integer, db.ForeignKey('Reserve_Parking_spots.r_id'))


    reservation = db.relationship("Reserve_parkingspots", back_populates="history")
    user = db.relationship("Users", backref='parking_history', lazy=True)

class Parking_lots(db.Model):
    __tablename__='Parking_Lots'
    p_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    lot_area=db.Column(db.String(50),nullable=False)
    lot_add=db.Column(db.String(255),nullable=False)
    total_spots=db.Column(db.Integer,nullable=False)
    price=db.Column(db.Float,nullable=False)
    p_details=db.relationship("Parking_spots",back_populates='lot',lazy=True)

    @property
    def first_available_spot(self):
        return next((spot for spot in self.p_details if spot.status == 'available'), None)


class Parking_spots(db.Model):
    __tablename__='Parking_Spots'
    s_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    p_id=db.Column(db.Integer,ForeignKey('Parking_Lots.p_id'),nullable=False)
    status=db.Column(db.String(20),nullable=False)

    reservation=db.relationship("Reserve_parkingspots",back_populates='spot',lazy=True)
    lot=db.relationship("Parking_lots",back_populates='p_details',lazy=True)


class Reserve_parkingspots(db.Model):
    __tablename__='Reserve_Parking_spots'
    r_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    s_id=db.Column(db.Integer,ForeignKey('Parking_Spots.s_id'),nullable=True)
    u_id=db.Column(db.Integer,ForeignKey('Users.u_id'),nullable=False)
    v_no=db.Column(db.String(20),nullable=False)
    time_of_parking=db.Column(db.DateTime,nullable=False)        
    time_of_leaving=db.Column(db.DateTime,nullable=False)
    price=db.Column(db.Float,nullable=False)

    user=db.relationship("Users",back_populates='rps',lazy=True)
    spot=db.relationship("Parking_spots",back_populates='reservation',lazy=True)
    history = db.relationship("Parking_history", back_populates="reservation", uselist=False)


    



