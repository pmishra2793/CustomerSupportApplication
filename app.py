import jwt
from flask import Flask, config, render_template, request
from jwt import algorithms
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from datetime import datetime, timedelta
from flask.wrappers import Response
import json
import time

with open('static/config.json') as c:
    params = json.load(c)['params']

app = Flask(__name__)
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['email'],
    MAIL_PASSWORD=params['password']
)
mail = Mail(app)
app.config['SQLALCHEMY_DATABASE_URI'] = params['database_uri']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Th1s1ss3cr3t'
db = SQLAlchemy(app)

class CustomerQuery(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    cust_query = db.Column(db.String(500), nullable=False)
    cust_review = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return 'email = {}, query = {}'.format(self.email, self.cust_query)

def encode_auth_token(user_id):
    """
    Generates the Auth Token
    :return: string
    """
    try:
        payload = {
            'exp': datetime.utcnow() + timedelta(days=0, seconds=300),
            'iat': datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(
            payload,
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    except Exception as e:
        return e

def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer|string
    """
    try:
        payload = jwt.decode(
            auth_token, app.config['SECRET_KEY'],  algorithms='HS256')
        return {"id": payload['sub'], 'Status': True}
    except jwt.ExpiredSignatureError as e:
        return {"Message": 'Signature expired. Please log in again.', 'Status': False}
    except jwt.InvalidTokenError as e:
        return {"Message": 'Invalid token. Please log in again.', 'Status': False}

@app.route("/", methods=['GET', 'POST'])
def cust_data():
    try:
        if request.method == 'POST' and request.form['cust_email'] != None and request.form['cust_query'] != None:
            cust_email = request.form['cust_email']
            cust_query = request.form['cust_query']
            customer_data = CustomerQuery(email=cust_email, cust_query=cust_query)
            db.session.add(customer_data)
            db.session.commit()
            db.session.flush()
            id = customer_data.sno
            mail.send_message(sender=cust_email, recipients=[params['email']], body='Customer Query: ' +
            cust_query + '\n' + 'http://127.0.0.1:5000/customer_query/{}'.format(id), subject='Customer Query')
            return render_template('index.html')
        else:
            return render_template('index.html')
    except Exception as e:
        return Response({'Error : '+str(e)})

@app.route("/customer_query/<int:id>", methods=['GET', 'POST'])
def cust_Query(id):
    try:
        if request.method == 'POST' and request.form['cust_response'] != None:
            cust_response = request.form['cust_response']
            id_data = CustomerQuery.query.filter_by(sno=id).first()
            token_res = encode_auth_token(id)
            mail.send_message(sender=params['email'], recipients=[id_data.email], body=cust_response +
            '\n' + 'http://127.0.0.1:5000/customer_review/{}'.format(token_res), subject='Customer Response')
            return render_template('custquery.html')
        else:
            id_data = CustomerQuery.query.filter_by(sno=id).first()
            cust_query = id_data.cust_query
            return render_template('custquery.html', cust_query=cust_query, sno=id)
    except Exception as e:
        return Response({'Error : '+str(e)})

@app.route("/customer_review/<token>", methods=['GET', 'POST'])
def cut_review(token):
    try:
        decode_resp = decode_auth_token(token)
        if decode_resp['Status'] == False:
            return decode_resp['Message']
        id = decode_resp['id']
        if request.method == 'POST':
            review = request.form.getlist('flexRadioDefault')
            id_data = CustomerQuery.query.filter_by(sno=id).first()
            id_data.cust_review = review[0]
            db.session.add(id_data)
            db.session.commit()
            return render_template('thankyou.html')
        else:
            return render_template('custReview.html', sno=token)
    except Exception as e:
        return Response({'Error : '+str(e)})

if __name__ == '__main__':
    app.run(debug=True)