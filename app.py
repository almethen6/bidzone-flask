from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bidzone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class AuctionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    starting_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('auction_item.id'), nullable=False)


@app.route('/')
def index():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    now = datetime.utcnow()
    items = AuctionItem.query.filter(
        AuctionItem.end_time > now,
        AuctionItem.title.contains(search),
        AuctionItem.category.contains(category)
    ).all()
    categories = [c[0] for c in db.session.query(AuctionItem.category).distinct()]
    return render_template('index.html', items=items, categories=categories, search=search, category=category)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered','warning')
        else:
            db.session.add(User(email=email,password=password))
            db.session.commit()
            flash('Registered! Please log in.','success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email,password=password).first()
        if user:
            session['user_id']=user.id
            flash('Logged in successfully','success')
            return redirect(url_for('index'))
        flash('Invalid credentials','danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id',None)
    flash('Logged out','info')
    return redirect(url_for('index'))

@app.route('/add', methods=['GET','POST'])
def add():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method=='POST':
        title=request.form['title']
        description=request.form['description']
        category=request.form['category']
        start_price=float(request.form['starting_price'])
        end_time=datetime.fromisoformat(request.form['end_time'])
        item = AuctionItem(
            title=title, description=description, category=category,
            starting_price=start_price, current_price=start_price,
            end_time=end_time, user_id=session['user_id']
        )
        db.session.add(item)
        db.session.commit()
        flash('Item added','success')
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/item/<int:item_id>', methods=['GET','POST'])
def item_detail(item_id):
    item = AuctionItem.query.get_or_404(item_id)
    bids = Bid.query.filter_by(item_id=item_id).order_by(Bid.time.desc()).all()
    if request.method=='POST':
        if 'user_id' not in session:
            return redirect(url_for('login'))
        amount = float(request.form['bid'])
        if amount <= item.current_price:
            flash('Bid must be higher than current price','danger')
        else:
            bid = Bid(amount=amount, user_id=session['user_id'], item_id=item_id)
            item.current_price = amount
            db.session.add(bid)
            db.session.commit()
            flash('Bid placed','success')
        return redirect(url_for('item_detail',item_id=item_id))
    return render_template('item_detail.html',item=item,bids=bids)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
