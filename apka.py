from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SECRET_KEY'] = '123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Uzytkownik(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazwa_uzytkownika = db.Column(db.String(20), unique=True)
    haslo = db.Column(db.String(20))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tresc = db.Column(db.Text)
    autor_id = db.Column(db.Integer, db.ForeignKey('uzytkownik.id'))
    autor = db.relationship('Uzytkownik', backref=db.backref('posty', lazy=True))


with app.app_context():
    db.create_all()

@app.route('/')
def index():
    posty = Post.query.all()
    return render_template('index.html', posty=posty)

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
        nazwa_uzytkownika = request.form['nazwa_uzytkownika']
        haslo = request.form['haslo']
        uzytkownik = Uzytkownik.query.filter_by(nazwa_uzytkownika=nazwa_uzytkownika).first()
        if uzytkownik and haslo:
            session['uzytkownik'] = nazwa_uzytkownika
            return redirect(url_for('index'))

    return render_template('logowanie.html')

@app.route('/wyloguj')
def wyloguj():
    session.pop('uzytkownik', None)
    return redirect(url_for('index'))

@app.route('/dodaj_post', methods=['GET', 'POST'])
def dodaj_post():
    if 'uzytkownik' not in session:

        return redirect(url_for('logowanie'))

    if request.method == 'POST':
        tresc = request.form['tresc']
        uzytkownik = Uzytkownik.query.filter_by(nazwa_uzytkownika=session['uzytkownik']).first()
        nowy_post = Post(tresc=tresc, autor=uzytkownik)
        db.session.add(nowy_post)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('dodaj_post.html')

@app.route('/moje_posty')
def moje_posty():
    if 'uzytkownik' not in session:

        return redirect(url_for('logowanie'))

    uzytkownik = Uzytkownik.query.filter_by(nazwa_uzytkownika=session['uzytkownik']).first()
    posty = Post.query.filter_by(autor_id=uzytkownik.id).all()

    return render_template('moje_posty.html', posty=posty)

if __name__ == '__main__':
    app.run(debug=True)
