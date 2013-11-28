#!/bin/bash

sqlite3 erlenmeyer.db < schema.sql
rm data/erlenmeyer.bib
touch data/erlenmeyer.bib
