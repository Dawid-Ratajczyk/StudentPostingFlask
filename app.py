import io
import json
from base64 import b64encode
from json import JSONDecodeError
from pydoc import render_doc

from flask import Flask, render_template, request, redirect, url_for, session, send_file, abort, flash, \
    send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import column

app = Flask(__name__)
app.debug=False
app.config['SECRET_KEY'] = '123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.static_folder = 'static'
#Database--------------------------------------------------------
db = SQLAlchemy(app)
API_SECURITY_TOKEN = 'foobar'


class Uzytkownik(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazwa_uzytkownika = db.Column(db.String(20), unique=True)
    haslo = db.Column(db.String(20))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tresc = db.Column(db.Text(100))
    autor_id = db.Column(db.Integer, db.ForeignKey('uzytkownik.id'))
    autor = db.relationship('Uzytkownik', backref=db.backref('posty', lazy=True))
    img = db.Column(db.Text)
    img_name = db.Column(db.Text)

    def toDict(self):
        return {"tresc": self.tresc, "id": self.id, "autorId": self.autor.id}


with app.app_context():
    db.create_all()
#Site---------------------------------------------------------------
@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return send_file('static/favicon.gif', mimetype='image/ico')

@app.template_filter('b64encode')
def base64_encode_filter(data):
    if data:
        return b64encode(data).decode('utf-8')
    return None


@app.route('/')
def index():
    posty = Post.query.all()
    return render_template('index.html', posty=posty)

@app.route('/styles.css')
def serve_css():
    return send_from_directory('static', 'styles.css')

#User---------------------------------------------------------------
@app.route('/rejestracja', methods=['GET', 'POST'])
def rejestracja():
    if request.method == 'POST':
        nazwa_uzytkownika = request.form['nazwa_uzytkownika']
        haslo = request.form['haslo']

        if Uzytkownik.query.filter_by(nazwa_uzytkownika=nazwa_uzytkownika).first():
            return redirect(url_for('rejestracja'))

        nowy_uzytkownik = Uzytkownik(nazwa_uzytkownika=nazwa_uzytkownika, haslo=haslo)
        db.session.add(nowy_uzytkownik)
        db.session.commit()

        return redirect(url_for('logowanie'))
    return render_template('rejestracja.html')

@app.route('/logowanie', methods=['GET', 'POST'])
def logowanie():
    if request.method == 'POST':
        login = request.form['nazwa_uzytkownika']
        user = Uzytkownik.query.filter_by(nazwa_uzytkownika=login).first()
        if user and user.haslo == request.form['haslo']:
            session['uzytkownik'] = login
            return redirect(url_for('index'))

    return render_template('logowanie.html')

@app.route('/wyloguj')
def wyloguj():
    session.pop('uzytkownik', None)
    return redirect(url_for('index'))
#Posty---------------------------------------------------
@app.route('/api/post',methods=['GET'])
def all_posts():
    if 'Authentication' not in request.headers:
        abort(401, "No auth header")
    if request.headers['Authentication'] != API_SECURITY_TOKEN:
        abort(401, "Invalid token")
    result = Post.query.all()
    return [x.toDict() for x in result]

@app.route('/dodaj_post', methods=['GET', 'POST'])
def dodaj_post():
    if 'uzytkownik' not in session:
        return redirect(url_for('logowanie'))
    if request.method == 'POST':

        tresc = request.form['tresc']
        has_file = 'file' in request.files and request.files['file'].filename
        max_length = 40 if has_file else 200

        tresc=tresc[:max_length]
        try:
            data_object = json.loads(tresc)
            tresc = ",".join([str(x) for x in data_object.values()])
            if len(tresc) > max_length:
                tresc = tresc[:max_length]
        except JSONDecodeError:
            pass

        uzytkownik = Uzytkownik.query.filter_by(nazwa_uzytkownika=session['uzytkownik']).first()
        nowy_post = Post(
            tresc=tresc,
            autor_id=uzytkownik.id,
            img = request.files['file'].stream.read(),
            img_name = request.files['file'].content_type
        )
        db.session.add(nowy_post)
        db.session.commit()
        flash(message='Dodano Post',category='success')
        return redirect(url_for('index'))

    return render_template('dodaj_post.html')


@app.route('/picture/<int:post_id>')
def picture(post_id):
    post = Post.query.get_or_404(post_id)
    img = io.BytesIO(post.img)
    return send_file(img,mimetype=post.img_name)


@app.route('/moje_posty')
def moje_posty():
    if 'uzytkownik' not in session:

        return redirect(url_for('logowanie'))

    uzytkownik = Uzytkownik.query.filter_by(nazwa_uzytkownika=session['uzytkownik']).first()
    posty = Post.query.filter_by(autor_id=uzytkownik.id).all()

    return render_template('moje_posty.html', posty=posty)

#Main---------------------------------------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000)
    app.run(debug=False)
