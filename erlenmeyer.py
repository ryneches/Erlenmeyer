#!/usr/bin/env python

from flask import Flask
from flask import request, session, redirect, url_for
from flask import render_template
from flask import g, flash, send_from_directory
from os import path
from md5 import md5
from datetime import datetime, timedelta
from contextlib import closing
from werkzeug import secure_filename
from PIL import Image
import sqlite3
import re
from unicodedata import normalize

# configuration
DATABASE = 'erlenmeyer.db'
DEBUG = True
TRAP_BAD_REQUEST_KEY_ERRORS = True
TRAP_HTTP_EXCEPTIONS = True
SECRET_KEY = 'OMG so secret'
USERNAME = 'admin'
PASSWORD = 'default'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
DEFAULT_AVATAR = 'shanana.png'
THUMB_SIZE = 128
#SERVER_NAME = '/erlenmeyer'

# globals
ARTICLE_COLS = ['id', 'slug', 'username', 'date', 'headline', 'lat', 'lng', 'body', 'active' ]
USER_COLS    = ['id', 'username', 'password', 'realname', 'avatar', 'thumb']

app = Flask(__name__)
app.config.from_object(__name__)

class RegistrationException(Exception) :
    pass

class UserException(Exception) :
    pass

class ImageException(Exception) :
    pass

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    """Create new database tables"""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

def make_thumbnail( infile ) :
    """
    Take a path to an image file, and make a thumbnail sized verson of
    it.
    """
    size = app.config['THUMB_SIZE'],  app.config['THUMB_SIZE']
    file, ext = path.splitext(infile)
    im = Image.open(infile)
    im.thumbnail(size, Image.ANTIALIAS)
    thumb_filename = file + "_thumb.png"
    im.save( thumb_filename, "PNG")
    return thumb_filename

def get_user( username ) :
    """
    Get the details on a user.
    """
    cur = g.db.execute('select ' + ', '.join(USER_COLS) + ' from users where username = ? order by id desc', 
                        (username,) )
    row = cur.fetchone()
    
    # the user isn't in the database
    if not row :
        return False
    
    # bag it up
    return dict( zip( USER_COLS, row ) )

def get_article_by_id( id ) :
    """
    Get an article by ID.
    """
    cur = g.db.execute('select ' + ', '.join(ARTICLE_COLS) + ' from articles where id = ? order by id desc',
                        (id,) )
    row = cur.fetchone()
    
    # bail if the article isn't in there
    if not row :
        return False
    
    # bag it up
    return append_YMD( dict( zip( ARTICLE_COLS, row ) ) )

def get_articles_by_date( year, month=False, day=False, slug=False ) :
    """
    Get articles with a given date. Year is mandatory, month, day
    and slug are optional.
    """
    print year
    year = format( int(year), '04d' )
    
    if not month and not day :
        date_sub = '%Y'
        date_str = year
    if month and not day :
        # make sure month string has padded zeros
        month = format( int(month), '02d' )
        date_sub = '%Y %m'
        date_str = ' '.join( (year, month) )
    if month and day :
        month    = format( int(month), '02d' )
        day      = format( int(day),   '02d' )
        date_sub = '%Y %m %d'
        date_str = ' '.join( (year, month, day) )
    if not month and day :
        # get all the articles for a given day for any month
        # this doesn't make any sense, but we can do it...
        day      = format( int(day),   '02d' )
        date_sub = '%Y %d'
        date_str = ' '.join( (year, day) )
    
    if month and day and slug :
        command = 'select ' + ', '.join(ARTICLE_COLS)   \
            + ' from articles where strftime( ?, date ) = ? and slug = ? order by id desc'
        cur = g.db.execute( command, 
                          ( '\'' + date_sub + '\'',
                            '\'' + date_str + '\'',
                            slug ) )
    else :
        command = 'select ' + ', '.join(ARTICLE_COLS)   \
            + ' from articles where strftime( ?, date ) = ? order by id desc'
 
        cur = g.db.execute( command, 
                        ( '\'' + date_sub + '\'',
                          '\'' + date_str + '\'' ) )

    rows = cur.fetchall()
  
    articles = []
    # bag 'em up
    for row in rows :
        article = dict( zip( ARTICLE_COLS, row ) )
        article = append_YMD( article )
        articles.append( article )
        
    return articles

def get_user_articles( username ) :
    """
    Get summary information for records registered by a user.
    """
    cur = g.db.execute('select ' + ', '.join(ARTICLE_COLS) + ' from articles where username = ? order by id desc', 
                        (username,) )
    rows = cur.fetchall()
    articles = []
    
    # bag 'em up
    for row in rows :
        article = dict( zip( ARTICLE_COLS, row ) )
        article = append_YMD( article )
        articles.append( article )
        
    return articles

def append_YMD( article ) :
    d = datetime.strptime( article['date'], '%Y-%m-%d %H:%M:%S.%f')
    article['year']   = format( d.year,   '04d' )
    article['month']  = format( d.month,  '02d' )
    article['day']    = format( d.day,    '02d' )
    article['hour']   = format( d.hour,   '02d' )
    article['minute'] = format( d.minute, '02d' )
    return article

def change_article_status( id, status ) :
    """
    Set an article's status to active. The value for status must be
    either True or False.
    """
    g.db.execute('update articles set active = ? where id = ?', (status, id) )
    g.db.commit()

def add_user( form ) :
    """
    Create a new user in the database.
    """
    # check that the user actually filled out the form
    if not form['username'] or          \
       not form['realname'] or          \
       not form['password'] or          \
       not form['password_check'] :
        raise UserException( 'Looks like you\'re not done filling out the form!' )
    
    # check that the passwords match
    if not form['password'] == form['password_check'] :
        raise UserException( 'Those passwords don\'t match!' )
    
    # check to see if the user already exists
    if get_user( form['username'] ) :
        raise UserException( 'This user already exists!' )
    
    # try to save the user's avatar file, or use the default one
    if request.files['avatar'] :
        file = request.files['avatar']
        
        # check that it's an allowed file type
        if not allowed_file( file.filename ) :
            raise UserException( 'This image file type is not supported.' )
        ext = file.filename.lower().split('.')[-1]
        filename = secure_filename( form['username'] + '.' + ext )
        file_path = path.join( app.config['UPLOAD_FOLDER'], filename )
        file.save( file_path )
    else :
        file_path = path.join( app.config['UPLOAD_FOLDER'], app.config['DEFAULT_AVATAR'] )
    
    thumb_path = make_thumbnail( file_path )
    
    values = (  form['username'], 
                md5( form['password'] ).hexdigest(),
                form['realname'], file_path, thumb_path )   
    
    # SQL is gross
    g.db.execute('insert into users (username, password, realname, avatar, thumb) values (?,?,?,?,?)', values )
    g.db.commit()
    return True

def update_avatar( username, file ) :
    
    # check that it's an allowed file type
    if not allowed_file( file.filename ) :
        raise UserException( 'This image file type is not suppported.' )
    ext = file.filename.lower().split('.')[-1]
    filename = secure_filename( username + '.' + ext )
    file_path = path.join( app.config['UPLOAD_FOLDER'], filename )
    file.save( file_path )
    thumb_path = make_thumbnail( file_path )
    values = ( file_path, thumb_path, username )
    g.db.execute('update users set avatar=? and thumb=? where username=?', values )
    g.db.commit()

def add_article( user, form, thetime=False ) :
    """
    Add a new article.
    """
    if thetime :
        t = thetime
    else :
        t = datetime.now()
    
    # all new articles are created with active=False
    values = (  slugify(form['headline']),
                user['username'],
                t,
                float(form['lat']),
                float(form['lng']),
                form['headline'],
                form['body'],
                False )
    g.db.execute('insert into articles (slug, username, date, lat, lng, headline, body, active) values (?,?,?,?,?,?,?,?)', values )
    g.db.commit()
    return True

def modify_article( id, body, headline ) :
    """
    Replace an article's headline and body.
    """
    g.db.execute('update articles set body=? where id=?', (body, id,) )
    g.db.execute('update articles set headline=? where id=?', (headline, id) )
    g.db.commit()
    
    return True

def valid_login( username, password ) :
    """
    Check to see if a user's submitted password matches the stored
    hash.
    """
    p = md5( password ).hexdigest()
    user = get_user( username )
    if user and user['password'] == p :
        return True
    else :
        return False

@app.route( '/' )
def index() :
    """
    The application root.
    """
    if 'username' in session :
        return render_template( 'index.html', 
                                username=session['username'],
                                authenticated = True )
    else :
        return render_template( 'index.html' )

@app.route( '/login', methods = ['GET', 'POST'] )
def login() :
    '''
    Handle login requests.
    '''
    if request.method == 'POST' :
        username = request.form['username']
        password = request.form['password']
        if valid_login( username, password ) :
            session['username'] = username
            return redirect(url_for('profile', username=username ))
        else :
            flash( 'Who are you again?', 'alert-error' )
            return redirect( url_for( 'login' ) )
    else : 
        return render_template( 'login.html' )

@app.route( '/logout' )
def logout() :
    '''
    Log the user out.
    '''
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route( '/signup', methods = ['GET', 'POST'] )
def signup() :
    """
    Sign up a new user.
    """
    if request.method == 'POST' :
        username = request.form['username']
        try :
            add_user( request.form )
        except UserException as e :
            flash( e.message, 'alert-error' )
            return redirect( url_for( 'signup' ) )
        flash( 'New user added', 'alert-success' )
        session['username'] = username
        return redirect( url_for( 'profile', username=username ) )
    else :
        if 'username' in session :
            return render_template( 'signup.html',
                                    username = session['username'],
                                    authenticated = True )
        else :
            return render_template( 'signup.html' )

@app.route( '/publish', methods = ['POST'] )
def publish() :
    """
    Publish a new article.
    """
    # You have to be loggined in to publish stuff
    if not 'username' in session :
        flash( 'You must create an account to register samples!', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    user = get_user( session['username'] )
    result = add_article( user, request.form )
    if not result :
        flash( 'Something has gone wrong. Article not saved.', 'alert-error' )
    else :
        flash( 'Article ' + request.form['headline'] + ' uploaded!', 'alert-success' )
    return redirect( url_for( 'profile', username=session['username'] ) )

@app.route( '/edit/<int:id>', methods = ['POST', 'GET'] )
def edit( id ) :
    """
    Edit an existing article.
    """
    # You have to be logged in to edit articles
    if not 'username' in session :
        flash( 'You must be logged in to edit articles.', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    article = get_article_by_id( id )
    username = session['username']
    
    # route the user to a populated editing page
    if not article :
        flash( 'That article doesn\'t exist.', 'alert-error' )
        return redirect( url_for( 'profile', 
                                  username = username ) )   
    
    if request.method == 'GET' :
        return render_template( 'edit.html',
                                username = username,
                                article = article,
                                authenticated = True )
    
    # get the new article body and headline and store it
    if request.method == 'POST' :
        
        body     = request.form['body']
        headline = request.form['headline']
        result = modify_article( id, body, headline )
        
        if not result :
            flash( 'Something has gone wrong. Article not updated.', 'alert-error' )
        else :
            flash( 'Article ' + headline + ' updated!', 'alert-success' )
        
        # land the user back in the profile page
        return redirect( url_for( 'profile', username=session['username'] ) )

@app.route( '/activate/<int:id>', methods = ['GET'] )
def activate( id ) :
    """
    Activate an article.
    """
    # You have to be logged in to chage article status
    if not 'username' in session :
        flash( 'You must be logged in to change an article\'s status.', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    change_article_status( id, True )
    return redirect( url_for( 'profile', username=session['username'] ) )

@app.route( '/deactivate/<int:id>', methods = ['GET'] )
def deactivate( id ) :
    """
    Deactivate an article.
    """
    # You have to be logged in to chage article status
    if not 'username' in session :
        flash( 'You must be logged in to change an article\'s status.', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    change_article_status( id, False )
    return redirect( url_for( 'profile', username=session['username'] ) )

@app.route( '/<int:year>', methods = ['GET'] )
def get_year_articles( year ) :
    """
    Harf up some articles for a given year.
    """
    articles = get_articles_by_date( year )
    
    return render_template( 'blog.html',
                            articles = articles )

@app.route( '/<int:year>/<int:month>', methods = ['GET'] )
def get_year_month_articles( year, month ) :
    """
    Harf up some articles for a given year.
    """
    articles = get_articles_by_date( year, month=month )
    
    return render_template( 'blog.html',
                            articles = articles )

@app.route( '/<int:year>/<int:month>/<int:day>', methods = ['GET'] )
def get_year_month_day_articles( year, month, day ) :
    """
    Harf up some articles for a given year.
    """
    articles = get_articles_by_date( year, month, day )
    
    return render_template( 'blog.html',
                            articles = articles )

@app.route( '/<int:year>/<int:month>/<int:day>/<slug>', methods = ['GET'] )
def get_year_month_day_slug_articles( year, month, day, slug ) :
    """
    Harf up an article.

    This is a stub.
    """
    articles = get_articles_by_date( year, month, day, slug )
    return render_template( 'blog.html',
                            articles = articles )

@app.route( '/newavatar', methods = ['POST'] )
def newavatar() :
    """
    Update a user's avatar.
    """
    # You have to be logged in to update avatars
    if not 'username' in session :
        flash( 'You must be logged in to update your avatar.', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    username = session['username']
    if not 'avatar' in request.files :
        flash( 'Wern\'t you uploading a file or something', 'alert-error' )
        return redirect( url_for( 'profile', username=username ) )
    file = request.files['avatar']
    update_avatar( username, file )
    #flash( 'Your avatar has been updated!', 'alert-success' )
    return redirect( url_for( 'profile', username=username ) )    

@app.route( '/user/<username>' )
def profile( username ) :
    """
    The user profile page.
    """
    user = get_user( username )
    
    if not user :
        return 'User does not exist.'
    else :
        articles = get_user_articles( username )
        if 'username' in session :
            return render_template( 'profile.html', 
                                    user = user,
                                    username = username,
                                    articles = articles,
                                    authenticated = True )
        else :
            return render_template( 'profile.html',
                                    articles = articles ) 

@app.route( '/favicon.ico' )
def favicon() :
    return redirect( url_for( 'static', filename='favicon.ico' ) )

if __name__ == '__main__' :
    app.debug = True
    app.run()
