import os
import re
import tmdbsimple as tmdb
import sqlite3
import datetime
import json
import locale
import filminfo_html

# Searches for and returns the title in the name of the item
def clean_title(item_1st_part, is_tv):
    if is_tv:
        match = re.search(r'(.*?)(S\d{2}(-S\d{2})?|Complete|Season)', item_1st_part, re.IGNORECASE)
        if match:
            return re.sub(r'\.', ' ', match.group(1)).strip()
        return re.sub(r'\.', ' ', item_1st_part).strip()  # If there is no season designation, the entire name
    else:
        match = re.search(r'(.*?)(\d{4})', item_1st_part)
        if match:
            return re.sub(r'\.', ' ', match.group(1)).strip()
        return re.sub(r'\.', ' ', item_1st_part).strip()  # If there is no year, the whole name

# Determines the title of the item and the year (if any)
def extract_title_and_year(item, directory, film_type):
    # If the item is a file, delete its extension.
    if os.path.isfile(os.path.join(directory, item)):
        item = item.rsplit(".", 1)[0]

    # Search for title and year in the item.
    match = re.search(r'(.+?)(\d{4})', item)
    if match:
        title = clean_title(match.group(1), film_type == "tv")
        year = match.group(2)
        return title, year
    # If there is no year, just return the cleaned title
    return clean_title(item, film_type == "tv"), None

# Determines whether the item is a TV series.
def get_film_type(item):
    return 'tv' if re.search(r'(?<!\w)(S\d{2}(-S\d{2})?|Season|Complete)(?!\d|\w)', item, re.IGNORECASE) is not None else 'movie'

# Performs an SQL query and returns the result in a dictionary.
def query_as_dict(cursor, query, params=None):
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    column_names = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    if row is not None:
        return dict(zip(column_names, row))
    else:
        return None

# Based on the title and year of the item, it queries the movie data from the tmdb.
def get_movie_details(db, directory, item, lang):
    cursor =  db.cursor()
    search_title, search_year = extract_title_and_year(item, directory,'movie')
    if search_year:
        values = query_as_dict(cursor, "SELECT * FROM movie WHERE search_title = ? AND search_year=?", (search_title, search_year))
    else:
        values = query_as_dict(cursor, "SELECT * FROM movie WHERE search_title = ?", (search_title,))

    if values:
        del values['id']
    else:
        values = {"item": item,
                  "search_title": search_title,
                  "search_year": search_year,
                  "query_date": datetime.datetime.now().strftime("%x")}

        details = None
        movie_id = None
        search = tmdb.Search()
        response = search.movie(query=search_title, year=search_year, language=lang) if search_year else search.movie(query=search_title, language=lang)
        if response['results']:
            movie_id = response['results'][0]['id']
            details = tmdb.Movies(movie_id).info(language=lang)
        elif lang != 'en':
            response = search.movie(query=search_title, year=search_year, language='en') if search_year else search.movie(query=search_title, language='en')
            if response['results']:
                movie_id = response['results'][0]['id']
                details = tmdb.Movies(movie_id).info(language='en')

        if details and movie_id:
            values["movie_id"] = movie_id
            for key in ["title", "original_title", "overview", "release_date", "runtime", "vote_average", "poster_path"]:
                values[key] = details[key]

            values["genres"] = ', '.join([genre['name'] for genre in details.get('genres', [])])

            movie_credits = tmdb.Movies(movie_id).credits()
            cast = movie_credits.get('cast', [])
            for i in range(5):
                if i<len(cast):
                    actor = cast[i]
                    values[f'cast_{i + 1}'] = f"{actor['name']} - {actor['character']}"
                else:
                    values[f'cast_{i + 1}'] = ''

            sql = '''INSERT INTO movie(item, search_title, search_year, movie_id, query_date, title, original_title, overview, release_date, runtime, vote_average, genres, poster_path, cast_1, cast_2, cast_3, cast_4, cast_5)
                     VALUES(:item, :search_title, :search_year, :movie_id, :query_date, :title, :original_title, :overview, :release_date, :runtime, :vote_average, :genres, :poster_path, :cast_1, :cast_2, :cast_3, :cast_4, :cast_5)'''
        else:
            sql = '''INSERT INTO movie(item, search_title, search_year, query_date)
                     VALUES(:item, :search_title, :search_year, :query_date)'''
        cursor.execute(sql, values)
        db.commit()
    return values

# Based on the title of the item, it queries the TV series data from the tmdb
def get_tv_details(db, directory, item, lang):
    cursor = db.cursor()
    search_title, _ = extract_title_and_year(item, directory, 'tv')
    values = query_as_dict(cursor, "SELECT * FROM tv WHERE search_title = ?", (search_title,))

    if values:
        del values['id']
    else:
        values = {"item": item,
                  "search_title": search_title,
                  "query_date": datetime.datetime.now().strftime("%x")}

        details = None
        tv_id = None
        search = tmdb.Search()
        response = search.tv(query=search_title, language=lang)
        if response['results']:
            tv_id = response['results'][0]['id']
            details = tmdb.TV(tv_id).info(language=lang)
        elif lang != 'en':
            response = search.tv(query=search_title, language='en')
            if response['results']:
                tv_id = response['results'][0]['id']
                details = tmdb.TV(tv_id).info(language='en')

        if details and tv_id:
            values["tv_id"] = tv_id
            for key in ["name", "original_name", "overview", "first_air_date", "last_air_date", "number_of_episodes", "number_of_seasons", "vote_average", "poster_path"]:
                values[key] = details[key]

            values["genres"] = ', '.join([genre['name'] for genre in details.get('genres', [])])

            tv_credits = tmdb.TV(tv_id).credits()
            cast = tv_credits.get('cast', [])
            for i in range(5):
                if i < len(cast):
                    actor = cast[i]
                    values[f'cast_{i + 1}'] = f"{actor['name']} - {actor['character']}"
                else:
                    values[f'cast_{i + 1}'] = ''

            sql = '''INSERT INTO tv(item, search_title, tv_id, query_date, name, original_name, overview, first_air_date, last_air_date, number_of_episodes, number_of_seasons, vote_average, genres, poster_path, cast_1, cast_2, cast_3, cast_4, cast_5)
                     VALUES(:item, :search_title, :tv_id, :query_date, :name, :original_name, :overview, :first_air_date, :last_air_date, :number_of_episodes, :number_of_seasons, :vote_average, :genres, :poster_path, :cast_1, :cast_2, :cast_3, :cast_4, :cast_5)'''
        else:
            sql = '''INSERT INTO tv(item, search_title, query_date)
                     VALUES(:item, :search_title, :query_date)'''
        cursor.execute(sql, values)
        db.commit()
    return values

# Create the sqlite3 database if it does not already exist.
def create_sqlite_db():
    db = sqlite3.connect('filminfo.db')

    db.execute(  '''CREATE TABLE IF NOT EXISTS movie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT NOT NULL,
                    search_title TEXT NOT NULL,
                    search_year TEXT,
                    query_date TEXT NOT NULL,
                    movie_id INTEGER,
                    title TEXT,
                    original_title TEXT,
                    overview TEXT,
                    release_date TEXT,
                    runtime INTEGER,
                    vote_average REAL,
                    genres TEXT,
                    poster_path TEXT,
                    cast_1 TEXT,
                    cast_2 TEXT,
                    cast_3 TEXT,
                    cast_4 TEXT,
                    cast_5 TEXT )''')


    db.execute(  '''CREATE TABLE IF NOT EXISTS tv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT NOT NULL,
                    search_title TEXT NOT NULL,
                    query_date TEXT NOT NULL,
                    tv_id INTEGER,
                    name TEXT,
                    original_name TEXT,
                    overview TEXT,
                    first_air_date TEXT,
                    last_air_date TEXT,
                    number_of_episodes INTEGER,
                    number_of_seasons INTEGER,
                    vote_average REAL,
                    genres TEXT,
                    poster_path TEXT,
                    cast_1 TEXT,
                    cast_2 TEXT,
                    cast_3 TEXT,
                    cast_4 TEXT,
                    cast_5 TEXT )''')
    return db

# A comparison function for the sorted() function.
def sort_by_key(film, key, loc):
    try:
        locale.setlocale(locale.LC_ALL, loc)
    except Exception as e:
        print(f"Incorrect locale setting ({loc}): {e}")
        print("Please check the filminfo.json file and try again.")
        exit(1)
    return locale.strxfrm(film[key].lower())

# Delete unnecessary database rows.
def delete_unnecessary_db_rows(db, table_name, films):
    cursor = db.cursor()
    films = [s.replace("'", "''") for s in films]
    cmd = "DELETE FROM " + table_name + " WHERE item NOT IN ({})".format(', '.join("'" + str(kulcs) + "'" for kulcs in films))
    cursor.execute(cmd)
    db.commit()

# The main program
def main():
    with open('filminfo.json', 'r') as f:
        data = json.load(f)
        f.close()

    # Setting up the API key
    tmdb.API_KEY = data['tmdb_API_key']

    # Setting the folder containing videos
    directory = data['film_dir']

    # Setting the language
    lang = data['lang']

    # Setting the locale
    loc = data['locale']

    db = create_sqlite_db()
    # Separate TV, movie and unidentified films:
    tv_films = []
    movie_films = []
    unknown_items = []

    # The films that still exist, have not been deleted:
    existing_movie_films = []
    existing_tv_films = []

    for item in os.listdir(directory):
        film_type = get_film_type(item)

        if film_type == 'tv':
            result = get_tv_details(db, directory, item, lang)
            result["item"] = item
            existing_tv_films.append(item)
            if result.get("tv_id") is not None:
                tv_films.append(result)
            else:
                unknown_items.append(result)
        else:
            result = get_movie_details(db, directory, item, lang)
            result["item"] = item
            existing_movie_films.append(item)
            if result.get("movie_id") is not None:
                movie_films.append(result)
            else:
                unknown_items.append(result)

    movie_films = sorted(movie_films, key=lambda film: sort_by_key(film, 'title', loc))
    tv_films = sorted(tv_films, key=lambda film: sort_by_key(film, 'name', loc))
    unknown_items = sorted(unknown_items, key=lambda film: sort_by_key(film, 'item', loc))

    delete_unnecessary_db_rows(db, 'movie', existing_movie_films)
    delete_unnecessary_db_rows(db, 'tv', existing_tv_films)
    db.close()

    filminfo_html.create_tables(movie_films, tv_films, unknown_items)

# Program entry point
if __name__ == "__main__":
  main()