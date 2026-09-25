from flask import Flask,render_template,request,redirect,url_for,flash,session
from application.database import db
from application.model import Parking_history
from application.model import Parking_lots,Parking_spots,Users,Admin,Reserve_parkingspots
from sqlalchemy import or_
import re
from datetime import datetime, timedelta
import math


app=Flask(__name__)
app.secret_key = 'Secret_key' 


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///Parking_database.sqlite3"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

    if not Admin.query.first():
        default_admin = Admin(
            admin_emailid="admin1234@xyz.com",
            admin_name="Admin",
            admin_pw="myapp1" 
        )
        db.session.add(default_admin)
        db.session.commit()


@app.route('/User/login',methods=['GET','POST'])
def loginuser():
    if request.method=='POST':
        u_emailid=request.form["email_id"]
        u_pw=request.form['password']

        admin = Admin.query.filter_by(admin_emailid=u_emailid, admin_pw=u_pw).first()
        if admin:
            session['user_id'] = admin.admin_id
            return redirect(url_for('Admin_home'))

        user=Users.query.filter_by(u_emailid=u_emailid,u_pw=u_pw).first()
        
        if not user:
            flash("Invalid Email ID or password. Try again",'login_error')
            return redirect(url_for('loginuser'))


        session['user_id']=user.u_id
        return redirect(url_for('u_home'))

    return render_template("Userlogin.html")        

@app.route('/User/registration',methods=['GET','POST'])
def addUser():
    if request.method=='POST':
        u_emailid=request.form["email_id"]
        u_username=request.form['username']
        u_pw=request.form['password']
        c_pw=request.form['confirm_password']
        u_ph_no=request.form["phone_no"]

        u_add=request.form["address"]

        if u_pw!=c_pw:
            flash("Passwords do not match.",'confirm_pw_error')
            return redirect(url_for('addUser'))

        if '@' not in u_emailid or '.' not in u_emailid.split('@')[-1]:
            flash('Enter a valid email ID','email_error')
            return redirect(url_for('addUser'))

        if not u_ph_no.isdigit() or len(u_ph_no)!=10:
            flash("Enter a valid 10-digit phone number.",'phone_error')
            return redirect(url_for('addUser'))
        
        if Users.query.filter_by(u_emailid=u_emailid).first():
            flash("User already registered.",'email_error')
            return redirect(url_for('addUser'))

        if Users.query.filter_by(u_ph_no=u_ph_no).first():
            flash("Phone number already registered.",'phone_error')
            return redirect(url_for('addUser'))

        user=Users(u_emailid=u_emailid,u_username=u_username,u_pw=u_pw,u_ph_no=u_ph_no,u_add=u_add)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('loginuser'))   

    return render_template("UserRegistration.html") 

@app.route('/User/Home')
def u_home():

    user_id=session.get('user_id')
    if 'user_id' not in session:
        flash('Login to access the dashboard','login_error')
        return redirect(url_for('loginuser'))
    
    user = Users.query.get(session['user_id'])

    area=request.args.get("area", "")
    if area:
        p_lots=Parking_lots.query.filter(Parking_lots.lot_area.contains(area)).all()
    else:
        p_lots=Parking_lots.query.all()
    
    p_rechistory = Parking_history.query.filter_by(u_id=session['user_id']).all()

    return render_template("Userdashboard.html",lots=p_lots,history=p_rechistory) 

@app.route('/User/Bookspot/<int:lot_id>', methods=['GET', 'POST'])
def user_bookspot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Login to edit your profile', 'login_error')
        return redirect(url_for('loginuser'))

    spot = Parking_spots.query.filter_by(p_id=lot_id, status='available').first()
    if not spot:
        flash('No available spots in this lot.', 'booking_error')
        return redirect(url_for('u_home'))

    lot = Parking_lots.query.get(lot_id)
    v_no = request.form.get('v_no')

    now = datetime.now()
    leave_time = now + timedelta(hours=1)
    price = lot.price

    reservation = Reserve_parkingspots(
        s_id=spot.s_id,
        u_id=user_id,
        v_no=v_no,
        time_of_parking=now,
        time_of_leaving=leave_time,
        price=price
    )
    db.session.add(reservation)
    db.session.flush() 

    history = Parking_history(
        lot_area=lot.lot_area,
        price=price,
        timestamp=now,
        status='occupied',
        u_id=user_id,
        reservation_id=reservation.r_id
    )
    spot.status = 'occupied'

    db.session.add(history)
    db.session.commit()

    return redirect(url_for('u_home'))


@app.route('/User/release_spot', methods=['POST']) 
def user_releasespot():
    action = request.form['action']
    reservation_id = request.form['reservation_id']
    reservation = Reserve_parkingspots.query.get(reservation_id)

    if action == 'release':
        reservation.spot.status = 'available'

        reservation.time_of_leaving = datetime.now()

        start = (reservation.time_of_parking)
        end = datetime.now()
        
        duration_seconds = (end - start).total_seconds()
        rounded_hours = math.ceil(duration_seconds / 3600)
        total_cost = rounded_hours * reservation.spot.lot.price
        
        reservation.price = total_cost

        history_entry = Parking_history.query.filter_by(u_id=reservation.u_id,reservation_id=reservation.r_id,status='occupied').order_by(Parking_history.timestamp.desc()).first()
        if history_entry:
            history_entry.status = 'released'
            history_entry.time_of_leaving = reservation.time_of_leaving
            history_entry.price = total_cost

        db.session.commit()

    return redirect(url_for('u_home'))

@app.route('/User/Summary')
def user_summary():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view your summary.", "login_error")
        return redirect(url_for('loginuser'))

    history = Parking_history.query.filter_by(u_id=user_id, status='released').all()

    cost_by_lot = {}
    for i in history:
        if i.lot_area not in cost_by_lot:
            cost_by_lot[i.lot_area] = 0
        cost_by_lot[i.lot_area] += i.price or 0

    lot_names = list(cost_by_lot.keys())
    costs = list(cost_by_lot.values())

    return render_template("Usersummary.html", lots=lot_names, costs=costs)




@app.route('/User/EditProfile',methods=['GET','POST'])
def User_editprofile():
    user_id=session.get('user_id')

    if not user_id:
        flash('Login to edit your profile','login_error')
        return redirect(url_for('loginuser'))

    user = Users.query.get_or_404(user_id)

    if request.method=='POST':

        emailid=request.form['email_id']
        ph_no=request.form['phone_no']
        
        if '@' not in emailid or '.' not in emailid.split('@')[-1]:
            flash('Enter a valid email ID','email_error')
            return redirect(url_for('User_editprofile'))

        if not ph_no.isdigit() or len(ph_no)!=10:
            flash("Enter a valid 10-digit phone number.",'phone_error')
            return redirect(url_for('User_editprofile'))
        
        if Users.query.filter(Users.u_emailid==emailid,Users.u_id!=user_id).first():
            flash("User already registered.",'email_error')
            return redirect(url_for('User_editprofile'))

        if Users.query.filter(Users.u_ph_no==ph_no,Users.u_id!=user_id).first():
            flash("Phone number already registered.",'phone_error')
            return redirect(url_for('User_editprofile'))
        
        
        user.u_emailid=emailid
        user.u_username=request.form['username']
        user.u_pw=request.form['password']
        user.u_ph_no=ph_no
        user.u_add=request.form['address']

        db.session.commit()
        return redirect(url_for('u_home'))

    return render_template("UserEditProfile.html",user=user)

@app.route('/Admin/Home')
def Admin_home():
    lots = Parking_lots.query.all()
    for i in lots:
        i.occupied_spots=Parking_spots.query.filter(Parking_spots.p_id==i.p_id,Parking_spots.status=='occupied').count()
        i.related_spots = Parking_spots.query.filter_by(p_id=i.p_id).all()

        for spot in i.related_spots:
            if spot.status=='occupied':
                spot.available_spot=spot.reservation[-1] if spot.reservation else None
    return render_template("Admindashboard.html",lots=lots) 

@app.route('/Admin/Add_lot',methods=['GET','POST'])
def Admin_addlot():
    if request.method=='POST':
        lot_area=request.form["area"]
        lot_add=request.form["address"]
        lot_price=float(request.form["price"])
        lot_spots=int(request.form["spots"])

        lot=Parking_lots(lot_area=lot_area,lot_add=lot_add,total_spots=lot_spots,price=lot_price)
        db.session.add(lot)
        db.session.flush()
        for i in range(lot_spots):
            spot=Parking_spots(p_id=lot.p_id,status="available")
            db.session.add(spot)

        db.session.commit()

    return redirect(url_for('Admin_home'))

@app.route('/Admin/Edit_lot/<int:lot_id>',methods=['POST'])
def Admin_editlot(lot_id):
    l=Parking_lots.query.get_or_404(lot_id)

    l.lot_area=request.form["area"]
    l.lot_add=request.form["address"]
    l.price=float(request.form["price"])
    l.total_spots=int(request.form["spots"])

    db.session.commit()

    return redirect(url_for('Admin_home'))

@app.route('/Admin/Delete_lot/<int:lot_id>',methods=['POST'])
def Admin_deletelot(lot_id):
    l=Parking_lots.query.get_or_404(lot_id)
    s=Parking_spots.query.filter(Parking_spots.p_id==lot_id).all()

    for i in s:
        if i.status.lower()=='occupied':
            flash("Occupied Spot. Can't delete","danger")
            return redirect(url_for('Admin_home'))

    for i in s:
        db.session.delete(i)

    db.session.delete(l)
    db.session.commit()

    return redirect(url_for('Admin_home'))

@app.route('/Admin/Spot_edit/<int:s_id>',methods=['POST'])
def Admin_editspot(s_id):
    s=Parking_spots.query.get_or_404(s_id)

    if s.status=='occupied':
        flash("Occupied Spot. Can't delete","danger")
        return redirect(url_for('Admin_home'))

    l=s.lot
    db.session.delete(s)
    db.session.flush()

    remaining_spots = Parking_spots.query.filter_by(p_id=l.p_id).count()
    l.total_spots = remaining_spots

    db.session.commit()

    return redirect(url_for('Admin_home'))


@app.route('/Admin/Search', methods=['GET'])
def Admin_search():
    field=request.args.get('attributes')
    q=request.args.get('query')


    if not field:
        
        all_lots = Parking_lots.query.all()
        for lot in all_lots:
            lot.related_spots = Parking_spots.query.filter_by(p_id=lot.p_id).all()
            lot.occupied_spots = Parking_spots.query.filter_by(p_id=lot.p_id, status='occupied').count()
        return render_template('Adminsearch.html', lots=all_lots)

    
    if field=='lot_area':
        search_results=Parking_lots.query.filter(Parking_lots.lot_area.ilike(f"%{q}%")).all()

    elif field=='lot_add':
        search_results=Parking_lots.query.filter(Parking_lots.lot_add.ilike(f"%{q}%")).all()


    elif field=='spots':
        if not q.isdigit():
            flash("Enter a valid number.")
            return render_template('Adminsearch.html', lots=[])
        search_results=Parking_lots.query.filter_by(total_spots=int(q)).all()

    elif field=='price':
        try:
            price = float(q)
        except ValueError:
            flash("Enter a valid price.")
            return render_template('Adminsearch.html', lots=[])
        search_results=Parking_lots.query.filter_by(price=price).all()
    
    for lot in search_results:
        lot.related_spots = Parking_spots.query.filter_by(p_id=lot.p_id).all()
        lot.occupied_spots = Parking_spots.query.filter_by(p_id=lot.p_id, status='occupied').count()

    if not search_results:
        flash("No results found.")
        return render_template("Adminsearch.html", lots=[])


    return render_template('Adminsearch.html', lots=search_results)



@app.route('/Admin/Search/Edit_lot/<int:lot_id>',methods=['POST'])
def Admin_search_editlot(lot_id):
    l=Parking_lots.query.get_or_404(lot_id)


    l.lot_area=request.form["area"]
    l.lot_add=request.form["address"]
    l.price=float(request.form["price"])
    l.total_spots=int(request.form["spots"])

    
    db.session.commit()

    return redirect(url_for('Admin_search'))

@app.route('/Admin/Search/Delete_lot/<int:lot_id>',methods=['POST'])
def Admin_search_deletelot(lot_id):
    
    s=Parking_spots.query.filter(Parking_spots.p_id==lot_id).all()

    for i in s:
        if i.status.lower()=='occupied':
            flash("Occupied Spot. Can't delete","danger")
            return redirect(url_for('Admin_search'))

    for i in s:
        reservations = Reserve_parkingspots.query.filter_by(s_id=i.s_id).all()
        for r in reservations:
            r.s_id = None 
        db.session.delete(i)

    l=Parking_lots.query.get_or_404(lot_id)
    if l:
        db.session.delete(l)
        db.session.commit()
    

    db.session.commit()

    return redirect(url_for('Admin_search'))

@app.route('/Admin/Search/Spot_edit/<int:s_id>',methods=['POST'])
def Admin_search_editspot(s_id):
    s=Parking_spots.query.get_or_404(s_id)

    if s.status=='occupied':
        flash("Occupied Spot. Can't delete","danger")
        return redirect(url_for('Admin_search'))

    db.session.delete(s)
    db.session.commit()

    return redirect(url_for('Admin_search'))

@app.route('/Admin/Users')
def Admin_users():
    users=Users.query.all()

    return render_template('Adminusers.html',users=users)

@app.route('/Admin/EditProfile',methods=['GET','POST'])
def Admin_editprofile():
    admin_id=session.get('user_id')

    if not admin_id:
        flash('Login to edit your profile','login_error')
        return redirect(url_for('loginuser'))

    admin=Admin.query.get_or_404(admin_id)

    if request.method=='POST':

        admin_emailid=request.form['email_id']

        if '@' not in admin_emailid or '.' not in admin_emailid.split('@')[-1]:
            flash('Enter a valid email ID','email_error')
            return redirect(url_for('Admin_editprofile'))

        admin.admin_emailid=admin_emailid
        admin.admin_name=request.form['name']
        admin.admin_pw=request.form['password']

        db.session.commit()
        return redirect(url_for('Admin_home'))

    return render_template("AdminEditProfile.html",admin=admin)


@app.route('/Admin/Summary')
def Admin_summary():
    lots = Parking_lots.query.all()

    revenue = []
    spot_status = []

    for i in lots:
        released_histories = Parking_history.query.filter_by(lot_area=i.lot_area, status='released').all()
        total_revenue = sum(h.price for h in released_histories if h.price)

        occupied_count = Parking_spots.query.filter_by(p_id=i.p_id, status='occupied').count()
        available_count = Parking_spots.query.filter_by(p_id=i.p_id, status='available').count()

        revenue.append({'lot_area': i.lot_area, 'revenue': total_revenue})
        spot_status.append({
            'lot_id': i.p_id,
            'lot_area': i.lot_area,
            'available': available_count,
            'occupied': occupied_count
        })
        
    return render_template('Adminsummary.html', revenue=revenue, spot_status=spot_status)

if __name__ == '__main__':
    app.run(debug=True)

