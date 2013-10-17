#!/usr/bin/env python

from flask import Flask
from flask import request, session, redirect, url_for
from flask import render_template
from flask import g, flash, send_from_directory
from flask import Markup
from os import path
from md5 import md5
from datetime import datetime, timedelta
from contextlib import closing
from werkzeug import secure_filename
from werkzeug.contrib.atom import AtomFeed
from PIL import Image
from urlparse import urljoin
import sqlite3
import re
from unicodedata import normalize
import pandoc
import urllib, urllib2
import json

# Flask configuration
DATABASE = 'erlenmeyer.db'
DEBUG = True
TRAP_BAD_REQUEST_KEY_ERRORS = True
TRAP_HTTP_EXCEPTIONS = True
SECRET_KEY = 'OMG so secret'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
DEFAULT_AVATAR = 'shanana.png'
THUMB_SIZE = 128
#SERVER_NAME = '/erlenmeyer'

# Erlenmeyer configuration
ALLOW_SIGNUP        = True                  # enable/disable user signups
DISQUS_SHORTNAME    = 'ryneches'            # Disqus account name
SUPERUSER           = ''                    # which user is the superuser?
BIBFILE             = 'data/erlenmeyer.bib' # BibTeX database file
CSLFILE             = 'data/plos.csl'       # citation style file
SERVING_SIZE        = 5                     # number of articles to serve by default

# globals
ARTICLE_COLS = [ 'id', 'slug', 'username', 'date', 'headline', 'lat', 'lng', 'body', 'html', 'active' ]
USER_COLS    = [ 'id', 'username', 'password', 'realname', 'avatar', 'thumb' ]

app = Flask(__name__)
app.config.from_object(__name__)

class RegistrationException(Exception) :
    pass

class UserException(Exception) :
    pass

class ImageException(Exception) :
    pass

class CitationException(Exception) :
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

def make_external(url):
    return urljoin(request.url_root, url)

def md_to_html( md ) :
    doc = pandoc.Document()
    doc.add_argument( 'mathjax' )
    doc.add_argument( 'ascii' )
    doc.add_argument( 'smart' )
    doc.bib( BIBFILE )
    doc.csl( CSLFILE )
    doc.add_argument( 'indented-code-classes=prettyprint,linenums:1' )
    doc.markdown = md
    return unicode( doc.html )

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

def get_recent_articles( N ) :
    """
    Get the most recen N articles. If N = 0, return all articles.
    """
    if N == 0 :
        # get all the articles
        cur = g.db.execute( 'select ' + ', '.join(ARTICLE_COLS) + ' from articles order by date desc', () )
    else :
        # get the most recent N articles
        cur = g.db.execute( 'select ' + ', '.join(ARTICLE_COLS) + ' from articles order by date desc limit ?', (N,) )

    rows = cur.fetchall()
    articles = []
    # bag 'em up
    for row in rows :
        article = dict( zip( ARTICLE_COLS, row ) )
        article = append_YMD( article )
        articles.append( article )
    return articles

def get_articles_by_date( year, month=False, day=False, slug=False ) :
    """
    Get articles with a given date. Year is mandatory, month, day
    and slug are optional.
    """
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
    try :
        d = datetime.strptime( article['date'], '%Y-%m-%d %H:%M:%S.%f')
    except ValueError :
        d = datetime.strptime( article['date'], '%Y-%m-%d %H:%M:%S' )
    user = get_user( article['username'] )
    article['dtime']    = d
    article['year']     = format( d.year,   '04d' )
    article['month']    = format( d.month,  '02d' )
    article['day']      = format( d.day,    '02d' )
    article['hour']     = format( d.hour,   '02d' )
    article['minute']   = format( d.minute, '02d' )
    article['username'] = user['username']
    article['realname'] = user['realname']
    article['avatar']   = user['avatar']
    article['thumb']    = user['thumb']
    article['slug']     = str(article['slug'])
    article['headline'] = str(article['headline'])
    article['url']      = '/' + '/'.join( ( article['year'], article['month'], article['day'], article['slug'] ) )
    article['html']     = Markup( article['html'] )
   
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
    g.db.execute('update users set avatar=? where username=?', ( file_path, username) )
    g.db.execute('update users set thumb=? where username=?', ( thumb_path, username ) )
    g.db.commit()

def add_article( username, headline, body, lat=False, lng=False, postdate=False ) :
    """
    Add a new article.
    """
    if postdate :
        t = postdate
    else :
        t = datetime.now()
    
    # handle empty string for lat and lng
    if lat and lng :
        lat = float(lat)
        lng = float(lng)
    else :
        lat = float('nan')
        lng = float('nan')
    
    # handle empty string for headline
    if not headline :
        headline = u'Untitled article'
    
    # generate the HTML
    html = Markup( md_to_html( body ) )
    
    # all new articles are created with active=False
    values = (  slugify(headline),
                username,
                t,
                lat,
                lng,
                headline,
                body,
                html,
                False )
    g.db.execute('insert into articles (slug, username, date, lat, lng, headline, body, html, active) values (?,?,?,?,?,?,?,?,?)', values )
    g.db.commit()
    
    return True

def add_citation( citation_name, doi, bibtex=None ) :
    """
    Add a new citation to the database.
    """
    if doi.startswith( 'http://' ) :
        identifier = doi.partition( 'doi.org/' )[-1]
    elif doi.startswith( 'doi:' ) :
        identifier = doi.partition( ':' )[-1]
    else :
        identifier = doi   
    
    # check to see if we already have this one
    citations = get_citation( doi=doi )
    if citations :
        raise CitationException( "Citation already in database." )
    
    # check to make sure we're not using this name already
    citation_name = slugify(citation_name)
    citations = get_citation( citation=citation_name )
    if citations :
        raise CitationException( "Citation name already used." )
    
    # if no bibtex is provided, get it from DOI.org
    if not bibtex :
        try :
            url = 'http://doi.org/' + identifier
            req = urllib2.Request(url, headers={'Accept': 'text/bibliography; style=bibtex'})
            response = urllib2.urlopen(req)
            bibtex = unicode( response.read().decode('utf8') )
        except urllib2.HTTPError :
            raise CitationException( "DOI not found." )        
        #replace DOI's name with our citation name
        old_name = bibtex.split(',')[0].split('{')[1]
        bibtex = bibtex.replace( old_name, citation_name.encode('utf-8') )

    values = (  citation_name,
                doi,
                bibtex )
   
    g.db.execute( 'insert into bibs ( citation, doi, bibtex ) values (?,?,?)', values )
    g.db.commit()
    
    # append BibTeX data to static file
    try :
        f = open( BIBFILE, 'a' )
        f.write( u'\n' + bibtex + u'\n' )
        f.close()
    except :
        raise CitationException( "Can't add citation to " + BIBFILE )
    
    return {    'citation'  : citation_name, 
                'doi'       : doi, 
                'bibtex'    : bibtex }

def get_citation( doi=None, citation=None ) :
    """
    Returns a citation if you ask for one, or all the citations if you
    don't.
    """
    if doi :
        # should match 1 or 0 records
        cur = g.db.execute('select * from bibs where doi = ? order by id desc', (doi,))
    if citation :
        # should match 1 or 0 records
        cur = g.db.execute('select * from bibs where citation = ? order by id desc', (citation,))
    if not doi and not citation :
        # should match all records
        cur = g.db.execute('select * from bibs order by id desc')
    
    rows = cur.fetchall()
    keys = ['id', 'citation', 'doi', 'bibtex']
    if not rows :
        return False
    else :
        return [ dict(zip(keys, value)) for value in rows ]

def modify_article( id, body, headline ) :
    """
    Replace an article's headline and body.
    """
    html = Markup( md_to_html( body ) )
    g.db.execute('update articles set body=? where id=?', (body, id,) )
    g.db.execute('update articles set html=? where id=?', (html, id,) )
    g.db.execute('update articles set headline=? where id=?', (headline, id) )
    g.db.execute('update articles set slug=? where id=?', (slugify(headline), id) )
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
    # if user signup is disabled, bail
    if not ALLOW_SIGNUP :
        flash( 'Sorry, we\'re not taking any new users now!', 'alert-error' )
        return redirect( url_for( 'index' ) )

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

@app.route( '/publish', methods = ['POST', 'GET'] )
def publish() :
    """
    Publish a new article.
    """
    # You have to be loggined in to publish stuff
    if not 'username' in session :
        flash( 'You must create an account to publish stuff!', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    username = session['username']   
 
    if request.method == 'POST' :
        user = get_user( username )
        
        # try to add the article
        result = add_article(   user['username'],
                                request.form['headline'],
                                request.form['body'],
                                lat = request.form['lat'],
                                lng = request.form['lng'] )
        
        if not result :
            flash( 'Something has gone wrong. Article not saved.', 'alert-error' )
        else :
            flash( 'Article ' + request.form['headline'] + ' uploaded!', 'alert-success' )
        return redirect( url_for( 'profile', username=username ) )

    if request.method == 'GET' :
        return render_template( 'edit.html',
                                username = username,
                                article = False,
                                authenticated = True )

@app.route( '/citation', methods = ['POST', 'GET'] )
def citation() :
    """
    Manipulate citations.
    """
    # You have to be loggined in to mess with citations
    if not 'username' in session :
        flash( 'You must create an account to register citations!', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    username = session['username']   
    
    if request.method == 'POST' :
       
        # make sure we at least have a citation and a doi
        if not request.form['citation'] or not request.form['doi'] :
            # HTTP response : Not acceptable
            return( 'Invalid citation request.', 406 )        
        try :
            if request.form.has_key('bibtex') :
                c = add_citation(   request.form['citation'], 
                                    request.form['doi'],
                                    bibtex=request.form['bibtex'] )
            else :
                c = add_citation(   request.form['citation'],
                                    request.form['doi'] )
        except CitationException, e :
            # HTTP response : Not found
            return( str(e), 404 )
        
        # HTTP response : OK
        return( json.dumps(c), 200 )
    
    if request.method == 'GET' :
        return json.dumps(get_citation())

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

@app.route( '/feeds/posts' )
def atom() :
    """
    Return ATOM feed of most recent articles
    """
    
    feed = AtomFeed( 'Recent Articles',
                     feed_url=request.url, 
                     url=request.url_root )
    
    articles = get_recent_articles( SERVING_SIZE )
    
    # build the feed
    for article in articles :
        feed.add(   article['headline'], unicode(article['html']),
                    content_type    = 'xhtml',
                    author          = article['realname'],
                    url             = make_external(article['url']),
                    updated         = article['dtime'] )
    
    return feed.get_response()

@app.route( '/' )
def index() :
    """
    The application root.
    """
    # get the most recent articles 
    articles = get_recent_articles( SERVING_SIZE )
    
    if 'username' in session :
        
        if not articles :
            # no posts yet! serve the default page
            return render_template( 'index.html', 
                                    username=session['username'],
                                    authenticated = True )
        return render_template( 'blog.html',
                                articles = articles,
                                username = session['username'],
                                authenticated = True )
    
    else :
        if not articles :
            # no posts yet! serve the default page
            return render_template( 'index.html' )

        return render_template( 'blog.html',
                                articles = articles )

@app.route( '/<int:year>', methods = ['GET'] )
def get_year_articles( year ) :
    """
    Harf up some articles for a given year.
    """
    articles = get_articles_by_date( year )

    if not 'username' in session :
        return render_template( 'blog.html',
                                articles = articles )
    else :
        return render_template( 'blog.html',
                                articles = articles,
                                username = session['username'],
                                authenticated = True )
   
@app.route( '/<int:year>/<int:month>', methods = ['GET'] )
def get_year_month_articles( year, month ) :
    """
    Harf up some articles for a given year.
    """
    articles = get_articles_by_date( year, month=month )

    if not 'username' in session :
        return render_template( 'blog.html',
                                articles = articles )
    else :
        return render_template( 'blog.html',
                                articles = articles,
                                username = session['username'],
                                authenticated = True )

@app.route( '/<int:year>/<int:month>/<int:day>', methods = ['GET'] )
def get_year_month_day_articles( year, month, day ) :
    """
    Harf up some articles for a given year.
    """
    articles = get_articles_by_date( year, month, day )

    if not 'username' in session :
        return render_template( 'blog.html',
                                articles = articles )
    else :
        return render_template( 'blog.html',
                                articles = articles,
                                username = session['username'],
                                authenticated = True )

@app.route( '/<int:year>/<int:month>/<int:day>/<slug>', methods = ['GET'] )
def get_year_month_day_slug_articles( year, month, day, slug ) :
    """
    Harf up an article.

    This is a stub.
    """
    articles = get_articles_by_date( year, month, day, slug )
    
    # if the request has the parameter ?markdown, serve up the
    # unprocessed article body of the first article that we find
    if 'markdown' in request.args :
        return articles[0]['body']
    
    # if no user is logged in, serve up a non-authenticated page...
    if not 'username' in session :
        return render_template( 'comments.html',
                                articles = articles,
                                disqus_shortname = DISQUS_SHORTNAME,
                                comments = True )

    # ...or an authenticated page.
    else :
        return render_template( 'comments.html',
                                articles = articles,
                                username = session['username'],
                                authenticated = True,
                                disqus_shortname = DISQUS_SHORTNAME,
                                comments = True )
 
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
