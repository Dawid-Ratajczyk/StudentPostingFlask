import base64
import io
import logging
import os
from base64 import b64encode

from PIL import Image
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, \
    send_from_directory
from flask_sqlalchemy import SQLAlchemy
load_dotenv()
from ai import prompt_img


app = Flask(__name__)
app.debug=False
app.config['SECRET_KEY'] = '123'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.static_folder = 'static'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

#Database--------------------------------------------------------
db_path = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'instance/data.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_BINDS'] = {
    'data': 'sqlite:///data.db',
    'desc': 'sqlite:///desc.db'
}
db = SQLAlchemy(app)
API_SECURITY_TOKEN = 'foobar'


class Uzytkownik(db.Model):
    __tablename__ = 'uzytkownik'
    id = db.Column(db.Integer, primary_key=True)
    nazwa_uzytkownika = db.Column(db.String(20), unique=True)
    haslo = db.Column(db.String(20))


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    tresc = db.Column(db.Text(350))
    autor_id = db.Column(db.Integer, db.ForeignKey('uzytkownik.id'))
    autor = db.relationship('Uzytkownik', backref=db.backref('posty', lazy=True))
    img = db.Column(db.Text)
    img_name = db.Column(db.Text)

    def toDict(self):
        return {"tresc": self.tresc, "id": self.id, "autorId": self.autor.id, "img": base64.b64encode(self.img).decode()}

class Desc(db.Model):
    __bind_key__ = 'desc'
    __tablename__ = 'desc'
    id = db.Column(db.Integer, primary_key=True)
    desc = db.Column(db.Text(200))




with app.app_context():
    db.create_all()
#Site---------------------------------------------------------------
class IgnoreEndpointFilter(logging.Filter):
    def filter(self, record):
        # record.msg contains request line, e.g. "127.0.0.1 - - [..] "GET /healthz HTTP/1.1" 200 -"
        # You can check against request path here
        return "/picture" not in record.getMessage()

log = logging.getLogger("werkzeug")
log.addFilter(IgnoreEndpointFilter())

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return send_file('static/favicon.gif', mimetype='image/ico')

@app.after_request #Cache for static files and favicon
def add_cache_header(response):
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@app.template_filter('b64encode')
def base64_encode_filter(data):
    if data:
        return b64encode(data).decode('utf-8')
    return None


@app.route('/')
def index():
    posty = Post.query.order_by(Post.id.desc()).all()
    opisy = Desc.query.order_by(Desc.id.desc()).all()
    return render_template('index.html', posty=posty,opisy=opisy)

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
            flash(message='Użytkownik już istnieje', category='warning')
            return redirect(url_for('rejestracja'))

        flash(message='Rejestracja udana', category='succes')
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
            flash(message='Zalogowano', category='succes')
            session['uzytkownik'] = login
            return redirect(url_for('index'))
        flash(message='Błędne dane',category='warning')
    return render_template('logowanie.html')

@app.route('/wyloguj')
def wyloguj():
    flash(message='Wylogowano', category='succes')
    session.pop('uzytkownik', None)
    return redirect(url_for('index'))
#Posty---------------------------------------------------
@app.route('/api/post',methods=['GET'])#Api for getting all the posts as json
def all_posts():
    #if 'Authentication' not in request.headers:
     #   abort(401, "No auth header")
    #if request.headers['Authentication'] != API_SECURITY_TOKEN:
    #    abort(401, "Invalid token")
    result = Post.query.all()
    return [x.toDict() for x in result]

@app.route('/dodaj_post', methods=['GET', 'POST'])#Dodawanie postow
def dodaj_post():
    if 'uzytkownik' not in session:
        return redirect(url_for('logowanie'))
    if request.method == 'POST':

        tresc = request.form['tresc']
        #Jeśli ma zdjęcie to limit do 48 znakow
        has_file = 'file' in request.files and request.files['file'].filename
        max_length = 80 if has_file else 350
        tresc=tresc[:max_length]
        picture = request.files['file'].stream.read()
        last_id=Post.query.count()+1
        try:
            if picture:
                nowy_desc = Desc(
                    id=last_id,
                    desc= prompt_img(base64.b64encode(picture).decode(),tresc,app.logger)
                )
                db.session.add(nowy_desc)
        except Exception as e:
            app.logger.exception(e)

        picture= force_resize_blob(picture,900,900)
        uzytkownik = Uzytkownik.query.filter_by(nazwa_uzytkownika=session['uzytkownik']).first()
        nowy_post = Post(
            tresc=tresc,
            autor_id=uzytkownik.id,
            img = picture,
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
#Image--------------------------------------------------

def force_resize_blob(blob_data, target_width, target_height,):
    image = Image.open(io.BytesIO(blob_data))
    resized_image = image.resize((target_width, target_height), )
    output_blob = io.BytesIO()

    if image.format and image.format.upper() in ['PNG', 'GIF', 'BMP', 'TIFF']:
        resized_image.save(output_blob, format=image.format)
    else:
        resized_image.save(output_blob, format='JPEG', quality=95)

    return output_blob.getvalue()


#Main---------------------------------------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000)
    app.run(debug=False)


