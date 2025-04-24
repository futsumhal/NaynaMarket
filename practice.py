from flask import Flask, request, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configure the app
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)


# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100))
    price = db.Column(db.Float)
    description = db.Column(db.String(500))
    image_url = db.Column(db.String(500))

    def __init__(self, product_name, price, description, image_url):
        self.product_name = product_name
        self.price = price
        self.description = description
        self.image_url = image_url


# Create the database
# with app.app_context():
#     db.create_all()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route to render the form (upload page)
@app.route('/')
def index():
    return render_template('sell.html')


# Route to handle form submission
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'product_image' not in request.files:
        return 'No file part'

    file = request.files['product_image']
    if file.filename == '':
        return 'No selected file'

    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Save product info in the database
        image_url = url_for('static', filename=f'uploads/{file.filename}')
        product = Product(
            product_name=request.form['product_name'],
            price=request.form['price'],
            description=request.form['description'],
            image_url=image_url
        )
        db.session.add(product)
        db.session.commit()

        return redirect(url_for('product_page', product_id=product.id))


# Route to display the product page with image
@app.route('/product/<int:product_id>')
def product_page(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)


if __name__ == "__main__":
    app.run(debug=True)
