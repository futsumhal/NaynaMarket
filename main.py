from flask import Flask,render_template,request,url_for,redirect,flash,session,abort
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime,timezone
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer,SignatureExpired,BadSignature
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
load_dotenv(dotenv_path='mysecret.env')
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
app=Flask(__name__)
app.secret_key = 'my_secret_key'
# Configure flask_mail
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # or your email provider
# app.config['MAIL_PORT'] = 465
# app.config['MAIL_USE_SSL'] = True
# app.config['MAIL_USE_TLS'] = False
# app.config['MAIL_USERNAME'] = 'futsumhal@gmail.com'
# app.config['MAIL_PASSWORD'] = "uummxobdgiavsobg"
# app.config['MAIL_DEFAULT_SENDER'] = 'futsumhal@gmail.com'
mail = Mail(app)
# Configure the app
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///product.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager = LoginManager(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100))
    product_brand = db.Column(db.String(100))
    phone_number = db.Column(db.String(20), nullable=False)
    posted_by = db.Column(db.String(100), nullable=False)
    negotiable = db.Column(db.Boolean, default=False)
    sold=db.Column(db.String(100))
    status = db.Column(db.String(20), default="pending")  # Options: pending, approved, rejected
    views = db.Column(db.Integer, default=0)
    price = db.Column(db.Float)
    description = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    post_date = db.Column(db.DateTime,default=lambda: datetime.now(timezone.utc))
    images = db.relationship('ProductImage', backref='product', lazy=True)
    ratings = db.relationship('Rating', backref='product', cascade="all, delete-orphan", lazy=True)
    location = db.Column(db.String(200))



    def __init__(self, product_name, price, description, image_url,product_brand,sold,phone_number,negotiable,posted_by,location):
        self.product_name = product_name
        self.phone_number=phone_number
        self.posted_by=posted_by
        self.negotiable=negotiable
        self.price = price
        self.description = description
        self.image_url = image_url
        self.product_brand=product_brand
        self.sold=sold
        self.location = location

    def average_rating(self):
        db.session.flush()
        if not self.ratings:
            return 0
        return round(sum(r.value for r in self.ratings) / len(self.ratings), 1)

    def total_ratings(self):
        return len(self.ratings)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)  # 1 to 5 stars
    user_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    user = db.relationship('User', backref='ratings', lazy=True)
class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    subscribed_on = db.Column(db.DateTime, default=db.func.current_timestamp())

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)




# with app.app_context():
#     db.create_all()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


# Create a serializer instance with a secret key
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])


def send_verification_email(user_email):
    token = s.dumps(user_email, salt='email-confirm')
    confirm_url = url_for('confirm_email', token=token, _external=True)

    html_content = f"""
    <!DOCTYPE html>
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 30px;">
        <div style="max-width: 600px; margin: auto; background-color: #fff; border-radius: 10px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          <h2 style="color: #0d6efd;">Welcome to QuickMart! 🎉</h2>
          <p style="font-size: 16px; color: #333;">
            Hi there,
          </p>
          <p style="font-size: 16px; color: #333;">
            Thank you for registering with <strong>QuickMart</strong>! To complete your registration, please verify your email address by clicking the button below:
          </p>
          <p style="text-align: center; margin: 30px 0;">
            <a href="{confirm_url}" style="background-color: #0d6efd; color: white; padding: 12px 25px; border-radius: 5px; text-decoration: none; font-size: 16px;">
              ✅ Verify My Email
            </a>
          </p>
          <p style="font-size: 14px; color: #777;">
            If you didn’t sign up for QuickMart, you can safely ignore this email.
          </p>
          <hr style="margin-top: 40px; border: none; border-top: 1px solid #eee;">
          <p style="font-size: 12px; color: #aaa;">
            © {datetime.now().year} QuickMart. All rights reserved.
          </p>
        </div>
      </body>
    </html>
    """

    message = Mail(
        from_email='futsumhal@gmail.com',
        to_emails=user_email,
        subject='Please confirm your email',
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent to {user_email}, status code: {response.status_code}")
    except Exception as e:
        print(f"Failed to send email: {e}")


@app.route('/verify/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=300)  # 1 hour expiration
    except SignatureExpired:
        flash('The confirmation link has expired.', 'danger')
        return redirect(url_for('login'))
    except BadSignature:
        flash('Invalid or tampered confirmation link.', 'danger')
        return redirect(url_for('login'))

    user = db.session.query(User).filter_by(email=email).first()

    if user:
        if not user.is_verified:
            user.is_verified = True
            db.session.commit()
            flash('Your email has been verified! You can now log in.', 'success')
        else:
            flash('Your email is already verified.', 'info')
    else:
        flash('User not found.', 'danger')

    return redirect(url_for('login'))

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home_page():
    data = Product.query.filter_by(status='approved').order_by(Product.post_date.desc()).all()
    hero_images = [
        url_for('static', filename='assets/img/hero/hero1.jpg'),
        url_for('static', filename='assets/img/hero/hero2.jpg'),
        url_for('static', filename='assets/img/hero/hero3.jpg'),
        url_for('static', filename='assets/img/hero/hero4.jpg'),
        url_for('static', filename='assets/img/hero/hero5.jpg'),
        url_for('static', filename='assets/img/hero/hero6.jpg'),
        url_for('static', filename='assets/img/hero/hero7.jpg'),
        url_for('static', filename='assets/img/hero/hero10.jpg'),
        url_for('static', filename='assets/img/hero/hero12.jpg'),
        url_for('static', filename='assets/img/hero/hero13.jpg'),
        url_for('static', filename='assets/img/hero/hero14.jpg'),
        url_for('static', filename='assets/img/hero/hero17.jpg'),
        url_for('static', filename='assets/img/hero/hero18.jpg'),
        url_for('static', filename='assets/img/hero/hero19.jpg'),
        url_for('static', filename='assets/img/hero/hero20.jpg'),
        url_for('static', filename='assets/img/hero/hero21.jpg'),
        url_for('static', filename='assets/img/hero/hero30.jpg')
    ]
    return render_template("index.html",data=data,hero_images=hero_images)

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/products")
def product_detail():
    product_id = request.args.get("product_id", type=int)
    product =  Product.query.get_or_404(product_id)
    images = ProductImage.query.filter_by(product_id=product_id).all()
    product.views += 1
    db.session.commit()
    return render_template("product-details.html",product=product,images=images)

@app.route("/get_started",methods=["GET","POST"])
def get_started():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')


        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for("login"))

        # Create and save the user
        new_user = User(name=name, email=email)
        new_user.set_password(password) # hash the password
        if email == "futsumhalefom@gmail.com":
            new_user.is_admin = True
        else:
            new_user.is_admin = False
        db.session.add(new_user)
        db.session.commit()

        send_verification_email(new_user.email)


        flash("Account created successfully! Please verify your email by checking your inbox (or spam folder) for a verification link. Once verified, you can log in.", "success")
        return redirect(url_for('login'))
    return render_template("signup.html")

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_verified:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('login'))
            login_user(user)
            return redirect(url_for("home_page"))  # change this to your landing page
        else:
            flash("Invalid email or password.", "danger")
    return render_template('login.html')
@app.route('/sell')
@login_required
def sell_item():
    return render_template('sell.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    product_category = request.form['product_category']

    if 'image' not in request.files:
        return 'No cover image  part'
    cover_file = request.files.get('image')
    extra_files = request.files.getlist('images[]')

    if cover_file.filename == '':
        return 'No cover image selected'

    if cover_file and allowed_file(cover_file.filename):
        # Save cover image
        cover_filename = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(cover_file.filename))
        cover_file.save(cover_filename)
        cover_url = url_for('static', filename=f'uploads/{cover_file.filename}')

        # Save product info
        product = Product(
            product_name=product_category,
            product_brand=request.form["product_brand"],
            negotiable=True if request.form.get('negotiable') == 'True' else False,
            phone_number = f"+251{request.form.get('phone_number')}",
            price=request.form['price'],
            description=request.form['description'],
            posted_by=current_user.name,
            image_url=cover_url,
            sold="7+",
            location = request.form['location']

        )
        db.session.add(product)
        db.session.commit()
        # Save extra images
        for img in extra_files:
            if img and img.filename != '' and allowed_file(img.filename):
                img_filename = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(img.filename))
                img.save(img_filename)
                img_url = url_for('static', filename=f'uploads/{img.filename}')

                product_image = ProductImage(image_url=img_url, product_id=product.id)
                db.session.add(product_image)

        db.session.commit()

        return redirect(url_for('home_page'))
    return 'Invalid file'

@app.route('/logout')
def logout():
    logout_user()

    return redirect(url_for('home_page'))


@app.route('/profile', methods=['GET', 'POST'])
def update_profile():
    if request.method == 'POST':
        # Get the form data
        name = current_user.name
        email = current_user.email
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Validate old password
        if not check_password_hash(current_user.password_hash, old_password):
            flash("Old password is incorrect!", "error")
            return redirect(url_for('update_profile'))

        # Check if new password and confirm password match
        if new_password != confirm_password:
            flash("New passwords don't match!", "error")
            return redirect(url_for('update_profile'))

        # If new password is valid, update the user data
        current_user.name = name
        current_user.email = email

        # Update password if the new password is provided
        if new_password:
            current_user.set_password(new_password)

        db.session.commit()  # Commit changes to the database
        flash("Profile updated successfully!", "success")
        return redirect(url_for('update_profile'))  # Redirect to profile page

    return render_template('profile.html')
@app.route('/rate/<int:product_id>', methods=['POST'])
@login_required
def rate_product(product_id):
    rating_value = int(request.form['rating'])

    # Check if user has already rated this product
    existing_rating = Rating.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing_rating:
        existing_rating.value = rating_value
        # flash("Your rating has been updated!", "success")
    else:
        new_rating = Rating(value=rating_value, user_id=current_user.id, product_id=product_id)
        db.session.add(new_rating)
        # flash("Thanks for rating!", "success")

    db.session.commit()
    return redirect(url_for('home_page', product_id=product_id))

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')


@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        abort(403)

    products = Product.query.order_by(Product.id.desc()).all()
    return render_template('admin/admin_products.html', products=products)

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        abort(403)

    users = User.query.order_by(User.id.desc()).all()
    return render_template('admin/admin_users.html', users=users)
@app.route('/admin/subscribers')
@login_required
def admin_subscribers():
    if not current_user.is_admin:
        abort(403)

    users = NewsletterSubscriber.query.all()
    return render_template('admin/admin_subscribers.html', users=users)

@app.route('/admin/product/<int:product_id>/approve')
@login_required
@admin_required
def approve_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.status = 'approved'
    db.session.commit()
    return redirect(url_for('admin_products'))

@app.route('/admin/product/<int:product_id>/reject')
@login_required
@admin_required
def reject_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.status = 'rejected'
    db.session.commit()
    return redirect(url_for('admin_products'))


@app.route('/admin/product/<int:product_id>/delete')
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    for image in product.images:
        db.session.delete(image)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_products'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        abort(403)

    user = User.query.get_or_404(user_id)

    if user.is_admin:
        flash("You cannot delete an admin!", "danger")
        return redirect(url_for('admin_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.name} has been deleted.", "success")
    return redirect(url_for('admin_users'))

@app.route('/subscribe', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')

    if not email or "@" not in email:
        flash("Please enter a valid email address.")
        return redirect(url_for('home_page'))

    # Check if already subscribed
    if NewsletterSubscriber.query.filter_by(email=email).first():
        flash("This email is already subscribed.")
        return redirect(url_for('home_page'))

    # Save to database
    new_subscriber = NewsletterSubscriber(email=email)
    db.session.add(new_subscriber)
    db.session.commit()

    flash("Your subscription request has been sent. Thank you!",category="newsletter")
    return redirect(url_for('home_page'))

@app.route('/contact', methods=['POST'])
def contact_email():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']

    try:
        msg = Mail(
            from_email='futsumhal@gmail.com',  # Must match your verified sender
            to_emails='futsumhal@gmail.com',  # Your receiving email
            subject=f"QuickMart Contact - {subject}",
            html_content=f"""
                       <strong>From:</strong> {name} &lt;{email}&gt;<br><br>
                       <p>{message}</p>
                   """
        )

        # Send using SendGrid
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(msg)

        flash("Your message has been sent. Thank you!", category="contact")

    except Exception as e:
        flash(f"Failed to send message: {str(e)}",category="contact")

    return redirect(url_for('contact'))

if __name__ == "__main__":
    app.run(debug=True)