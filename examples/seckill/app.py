from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seckill.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

@app.route('/seckill/<int:product_id>', methods=['POST'])
def seckill(product_id):
    try:
        # First check if product exists and has stock
        product = db.session.query(Product).filter_by(id=product_id).first()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Use SQL UPDATE with WHERE clause to atomically decrement stock
        # This ensures only one thread can update the stock at a time
        rows_updated = db.session.execute(
            text('UPDATE product SET stock = stock - 1 WHERE id = :id AND stock > 0'),
            {'id': product_id}
        ).rowcount
        
        if rows_updated == 0:
            return jsonify({'error': 'Sold out'}), 400
        
        # Create order after successful stock update
        order = Order(product_id=product_id)
        db.session.add(order)
        db.session.commit()
        
        return jsonify({'success': True, 'order_id': order.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not db.session.query(Product).first():
            product = Product(name='Limited Edition Product', stock=10)
            db.session.add(product)
            db.session.commit()
    app.run(debug=True)
