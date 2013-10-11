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
    active              boolean,
    foreign key(username) references users(username)
);

drop table if exists tags;
create table tags (
    id integer primary key autoincrement,
    tag         string not null
);

drop table if exists bibs;
create table bibs (
    id integer primary key autoincrement,
    citation    string not null unique,
    doi         string not null,
    bibtex      string not null
);
