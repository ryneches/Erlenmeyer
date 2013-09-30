#!/usr/bin/env python
import erlenmeyer
import argparse
import sqlite3
import datetime
from datetime import datetime


try :
    import argcomplete
    argcomplete_present = True
except ImportError :
    argcomplete_present = False

def add_article( username, headline, date, body ) :
    """
    Add an article to the database (assumes you have a database).
    """
    con = sqlite3.connect( 'erlenmeyer.db' )
    cur = con.cursor()
    values = (  erlenmeyer.slugify( headline ),
                username,
                datetime.strptime( date, '%Y-%m-%d %H:%M:%S' ),
                float('nan'),
                float('nan'),
                headline,
                body,
                False )
    
    cur.execute( 'insert into articles (slug, username, date, lat, lng, headline, body, active) valules (?,?,?,?,?,?,?,?)', values )
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

def articles( args ) :
    if args.list_articles :
        articles = get_articles()
        for article in articles :
            print str(article['id']) + ' : ' + article['headline']

        

def db( args ) :
    print args

parser = argparse.ArgumentParser(
                    description = 'The Erlenmeyer control script.',
                    prog        = 'init.py' )

subparsers = parser.add_subparsers( help='', title = 'commands' )

parser_articles = subparsers.add_parser( 'articles', 
                    help='Load, dump and manipulate articles.' )

parser_articles.set_defaults( func=articles )

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
