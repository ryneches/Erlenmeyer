drop table if exists users;
create table users (
    id integer primary key autoincrement,
    username    string not null unique,
    password    string not null,
    realname    string not null,
    avatar      string not null,
    thumb       string not null
);

drop table if exists articles;
create table articles (
    id integer primary key autoincrement,
    slug                string not null,
    username            string not null,
    date                date not null,
    headline            string not null,
    lat                 real,
    lng                 real,
    body                text,
    html                text,
    published           boolean,
    doi                 text,
    active              boolean,
    foreign key(username) references users(username)
);

drop table if exists tags;
create table tags (
    id integer primary key autoincrement,
    tag         string not null unique
);

drop table if exists articletags;
create table articletags (
    tag_id              integer,
    article_id          integer,
    foreign key(tag_id) references tags(id) on delete cascade,
    foreign key(article_id) references articles(id) on delete cascade
);
create index tags_to_articles on articletags(tag_id);
create index articles_to_tags on articletags(article_id);

drop table if exists bibs;
create table bibs (
    id integer primary key autoincrement,
    citation    string not null unique,
    doi         string not null,
    bibtex      string not null
);
