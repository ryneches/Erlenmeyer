#!/usr/bin/env python
import erlenmeyer
import argparse
import sqlite3
import datetime
from datetime import datetime
import os

try :
    import argcomplete
    argcomplete_present = True
except ImportError :
    argcomplete_present = False

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

def add_article( username, headline, date, body ) :
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
                headline,
                body,
                False )
    
    cur.execute( 'insert into articles (slug, username, date, lat, lng, headline, body, active) values (?,?,?,?,?,?,?,?)', values )
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

def delete_article( id ) :
    """
    Delete an article by ID.
    """
    con = sqlite3.connect( 'erlenmeyer.db' )
    cur = con.cursor()
    cur.execute( 'delete from articles where id = ?', (id,) )
    con.commit()
    con.close()

def articles( args ) :
    # list all the articles
    if args.list_articles :
        articles = get_articles()
        for article in articles :
            print str(article['id']) + ' : ' + str(article['headline'])
    # insert an article
    if args.mdfile and args.username :
        metadata,s,body = open( args.mdfile ).read().partition('\n\n')
        m = {}
        for item in metadata.split('\n') :
            key,s,value = item.partition(': ')
            m[key] = value
        add_article( args.username, m['Title'], m['Date'], body )
    # insert all the articles in a directory
    if args.mddir and args.username :
        articles = []
        for filename in os.listdir( args.mddir ) :
            path = os.path.join( args.mddir, filename )
            if os.path.isfile( path ) :
                metadata,s,body = open( path ).read().partition('\n\n')
                m = {}
                for item in metadata.split('\n') :
                    key,s,value = item.partition(': ')
                    m[key] = value
                print 'found article : ' + m['Title']
                article = { 'author' : args.username, 
                            'title'  : unicode(m['Title']), 
                            'date'   : m['Date'],
                            'body'   : unicode(body.decode('latin-1')),
                            'tags'   : m['Tags']    }
                articles.append( article )

        if confirm( prompt = 'add ' + str(len(articles)) + ' articles?' ) :
            for article in articles :
                add_article( article['author'], 
                             article['title'],
                             article['date'], 
                             article['body'] )
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
                                required    = False,
                                help        = 'Username to use for new articles.' )

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
