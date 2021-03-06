#!/usr/bin/env python
import erlenmeyer
import argparse
import sqlite3
import datetime
import pandoc
from datetime import datetime
import os

try :
    import argcomplete
    argcomplete_present = True
except ImportError :
    argcomplete_present = False

mdfile_keys = [ 'Title', 'Date', 'Slug', 'Author', 'Tags', 'Summary' ]

def confirm( prompt=None, resp=False ):
    """
    Prompts the user for a yes or no answer. Returns True for yes and
    False for no.
    
    
    from : http://code.activestate.com/recipes/541096-prompt-the-user-for-confirmation/
    """
    
    if prompt is None:
        prompt = 'Confirm'

    if resp:
        prompt = '%s [%s]|%s: ' % (prompt, 'y', 'n')
    else:
        prompt = '%s [%s]|%s: ' % (prompt, 'n', 'y')
        
    while True:
        ans = raw_input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print 'please enter y or n.'
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False

def add_article( username, headline, date, tags, body, active=False ) :
    """
    Add an article to the database (assumes you have a database).
    """
    con = sqlite3.connect( 'erlenmeyer.db' )
    cur = con.cursor()
    values = (  erlenmeyer.slugify( unicode(headline) ),
                username,
                datetime.strptime( date, '%Y-%m-%d %H:%M:%S' ),
                float('nan'),
                float('nan'),
                unicode(headline),
                body,
                erlenmeyer.md_to_html(body),
                active )

    cur.execute( 'insert into articles (slug, username, date, lat, lng, headline, body, html, active) values (?,?,?,?,?,?,?,?,?)', values )
    
    # commit the article and get a fresh cursor
    con.commit()
    cur = con.cursor()    
    # get the article id (it'll be the one with the highest id)
    cur.execute( 'select id from articles order by id desc' )
    article_id = cur.fetchone()[0]
    
    for tag in tags :
        # check to see if tag is already present, insert if not
        cur.execute( 'select * from tags where tag=?', (tag,) )
        rows = cur.fetchall()
        if not rows :
            cur.execute( 'insert into tags (tag) values (?)', (tag,) )
            cur.execute( 'select * from tags where tag=?', (tag,) )
            rows = cur.fetchall()
        tag_id = rows[0][0]
        # update many-to-many table
        cur.execute( 'insert into articletags (article_id, tag_id) values (?,?)', (article_id, tag_id,) )
    
    con.commit()
    con.close()

def get_articles() :
    """
    Fetch and return all articles.
    """
    con = sqlite3.connect( 'erlenmeyer.db' )
    cur = con.cursor()
    cur.execute( 'select * from articles order by date desc' )
    rows = cur.fetchall()
    con.close()
    return [ dict(zip( erlenmeyer.ARTICLE_COLS, row )) for row in rows ]

def get_article_by_id( id ) :
    """
    Fetch and return one article.
    """
    con = sqlite3.connect( 'erlenmeyer.db' )
    cur = con.cursor()
    cur.execute( 'select * from articles where id = ?  order by date desc', (id,) )
    rows = cur.fetchall()
    con.close()
    return dict(zip( erlenmeyer.ARTICLE_COLS, rows[0] ) )

def delete_article( id ) :
    """
    Delete an article by ID.
    """
    con = sqlite3.connect( 'erlenmeyer.db' )
    cur = con.cursor()
    cur.execute( 'delete from articles where id = ?', (id,) )
    con.commit()
    con.close()

def readmdfile( file ) :
    metadata,s,body = open( file ).read().partition('\n\n')
    m = {}
    for item in metadata.split('\n') :
        key,s,value = item.partition( ': ' )
        m[key] = value
    if reduce( lambda a, b : a and b, map( m.has_key, mdfile_keys ) ) :
        m['Tags'] = m['Tags'].split(', ')
    else :
        raise Exception('malformed header : ' + file )
    return {    'body'      : unicode(body.decode('latin-1')),
                'date'      : m['Date'],
                'title'     : unicode(m['Title']),
                'tags'      : m['Tags'] }

def articles( args ) :
    # list all the articles
    if args.list_articles :
        articles = get_articles()
        for article in articles :
            print str(article['id']) + ' : ' + str(article['headline'])
        return True
    # dump an article by its id
    if args.dump_id :
        article = get_article_by_id( args.dump_id )
        print article['body']
    # insert an article
    if args.mdfile and args.username :
        article = readmdfile( args.mdfile )
        add_article(    args.username,
                        article['title'],
                        article['date'], 
                        article['tags'],
                        article['body'],
                        args.active     )
        return True
    # insert all the articles in a directory
    if args.mddir and args.username :
        articles = []
        failed   = []
        for filename in os.listdir( args.mddir ) :
            path = os.path.join( args.mddir, filename )
            if os.path.isfile( path ) :
                article = readmdfile( path )
                articles.append( article )

        if confirm( prompt = 'add ' + str(len(articles)) + ' articles?' ) :
            for article in articles :
                print 'adding article : ' + article['title']
                try :
                    add_article( args.username, 
                                 article['title'],
                                 article['date'],
                                 article['tags'],
                                 article['body'],
                                 args.active    )
                except :
                    failed.append(article)
            for article in failed :
                print 'failed adding article : ' + article['title']
        return True
    # delete an article
    if args.del_id :
        delete_article( args.del_id )    


def db( args ) :
    print args

parser = argparse.ArgumentParser(
                    description = 'The Erlenmeyer control script.',
                    prog        = 'init.py' )

subparsers = parser.add_subparsers( help='', title = 'commands' )

parser_articles = subparsers.add_parser( 'articles', 
                    help='Load, dump and manipulate articles.' )

parser_articles.set_defaults( func=articles )

parser_articles.add_argument(   '-delete',
                                action      = 'store',
                                dest        = 'del_id',
                                type        = int,
                                required    = False,
                                help        = 'Delete article by ID.' )

parser_articles.add_argument(   '-loadfile',
                                action      = 'store',
                                dest        = 'mdfile',
                                required    = False,
                                help        = 'Load a Markdown article.' )

parser_articles.add_argument(   '-loaddir',
                                action      = 'store',
                                dest        = 'mddir',
                                required    = False,
                                help        = 'Load a directory of Markdown articles.' )

parser_articles.add_argument(   '-user',
                                action      = 'store',
                                dest        = 'username',
                                required    = True,
                                help        = 'Username to use for new articles.' )

parser_articles.add_argument(   '-active',
                                action      = 'store_true',
                                dest        = 'active',
                                required    = False,
                                help        = 'If set, store article(s) as published.' )

parser_articles.add_argument(   '-list',
                                action      = 'store_true',
                                dest        = 'list_articles',
                                required    = False,
                                help        = 'List all articles.' )

parser_articles.add_argument(   '-dump',
                                action      = 'store',
                                dest        = 'dump_id',
                                required    = False,
                                help        = 'Dump one article.' )

parser_articles.add_argument(   '-dumpall',
                                action      = 'store',
                                dest        = 'dump_dir',
                                required    = False,
                                help        = 'Dump all articles into DIR.' )

parser_db = subparsers.add_parser( 'db', 
                                    help='Mess with the database.' )

parser_db.set_defaults( func=db )

parser_db.add_argument(         '-init',
                                action      = 'store_true',
                                dest        = 'init_db',
                                required    = False,
                                help        = 'Initialize the database (WARNING: Destroys all data).' )



if argcomplete_present :
    argcomplete.autocomplete(parser)

args = parser.parse_args()
args.func(args)
