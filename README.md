#Erlenmeyer

### A blogging tool for science and research written in Python using Flask.

Homepage : [Erlenmeyer](http://ryneches.github.io/Erlenmeyer/)

This is Erlenmeyer, a simple blogging platform written in Python using
Flask, because, let's face it, the world needed another blogging
platform. Like all blogging tools, Erlenmeyer is incomplete,
unfinished, and will probably wind up being abandoned by the author as
soon as you get it working.

Because apathy and abandonment is the fate of all web tools
(especially blogging tools), Erlenmeyer is designed to be the 1963 VW
Bug of blogging software. It is not intended to be elegant. It is not
intended to be fast.  It is not intended to "scale," whatever that
means. It is not intended to be extendable. Instead, Erlenmeyer is
intended to be simple enough for you to modify, improve, optimize,
extend and hack yourself, even if you are not much of a web
programmer. Because, like the author, you just want to write things
and stick them on the internet, and you don't want your life to
include words like, "deploy" and "migrate."

That said, it isn't really intended to be minimalist either.
Erlenmeyer is designed to actually work. It is a People's Blogging
Tool, designed to provide many long years of use. The driver should be
able to keep it running herself with just a few basic tools and a
calm, responsible attitude. One shouldn't need to be a genius or a
professional to keep a blog running.

## Installing

Erlenmeyer depends on a relatively recent builds of some of its
dependencies, some of which may not be packaged for your lpatform yet.
Once you've cloned the repository, you should install Erlenmeyer's
submodules :
    
    $ git clone https://github.com/ryneches/Erlenmeyer.git
    $ git submodule status 
    -da2879a83572ab56633c44466f1439f64edf93f5 libs/bootstrap-markdown
    -570aa8a30936a122abb37b78d48e85c6c67157db libs/bootstrap3
    -13d58a9bec67356ecae0d6902cb634e52cebcf19 libs/jquery
    -503cb54167820fbdd811d6367cf8eca24108e017 libs/markdown-js
    -04cd95d3426c7665fc88a1774709e7b68fe226d7 libs/pyandoc
    $ git submodule init
    Submodule 'libs/bootstrap-markdown' 
        (https://github.com/toopay/bootstrap-markdown.git) 
        registered for path 'libs/bootstrap-markdown'
    Submodule 'libs/bootstrap3' 
        (https://github.com/twbs/bootstrap.git) 
        registered for path 'libs/bootstrap3'
    Submodule 'libs/jquery' 
        (https://github.com/jquery/jquery.git)
        registered for path 'libs/jquery'
    Submodule 'libs/markdown-js' 
        (https://github.com/evilstreak/markdown-js.git) 
        registered for path 'libs/markdown-js'
    Submodule 'libs/pyandoc'
        (https://github.com/kennethreitz/pyandoc.git) 
        registered for path 'libs/pyandoc'
    $ git submodule update

You'll also need to install pandoc. If you're on a Linux machine, this
is pretty easy. 

    $ sudo apt-get install pandoc   # Debian/Ubuntu

If you're on a Mac, I suggest getting  [Homebrew](http://brew.sh/) 
installed. You may want to follow [these excellent instructions](http://www.lowindata.com/2013/installing-scientific-python-on-mac-os-x/)
for getting a useable scientific python development environment onto 
your Mac using Homebrew, virtualenv and pip (seriously, follow the
guide). Once you've done that, you can obtain pandoc by doing
something like this :
    
    $ brew install haskell-platform
    $ cabal update
    $ cabal install pandoc

## Usage

After installing the dependencies, you should be able to launch
Erlenmeyer in two easy steps :

    $ ./init.sh
    $ ./erlenmeyer.py

Then point your browser at <code>http://localhost:5000</code>.

When you're ready to deploy, you probably shouldn't use the
development server. I suggest the
[uwsgi](http://projects.unbit.it/uwsgi/) application server and
[nginx](http://wiki.nginx.org/Main) for your web server. There are
[various guides](http://uwsgi-docs.readthedocs.org/en/latest/WSGIquickstart.html)
for doing this.

## Credits and dependencies

Erlenmeyer includes these awesome pieces of software :

* [Bootstrap](http://getbootstrap.com/)
* [markdown.js](https://github.com/evilstreak/markdown-js)
* [jQuery](http://jquery.com/)
* [Bootstrap-Markdown](http://toopay.github.io/bootstrap-markdown/)
* [MathJax](http://mathjax.org)
* [Prettify](https://code.google.com/p/google-code-prettify/)

Erlenmeyer depends on these awesome pieces of software :

* [Python](http://python.org)
* [Flask](http://flask.pocoo.org/)
* [PIL](http://www.pythonware.com/products/pil/)
* [sqlite3](http://www.sqlite.org/)
* [pandoc](http://johnmacfarlane.net/pandoc/)
* [pyandoc](https://github.com/kennethreitz/pyandoc)

## Inspiration

![Erlenmeyer Flask](http://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Duran_erlenmeyer_flask_narrow_neck_50ml.jpg/170px-Duran_erlenmeyer_flask_narrow_neck_50ml.jpg)
