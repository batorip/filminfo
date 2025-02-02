import os
import shutil

import requests
from urllib.parse import urljoin
import json
# from gettext import gettext as _
import gettext


with open('filminfo.json', 'r') as f:
    data = json.load(f)
    f.close()
# Setting the language
language = data['lang']
url_path = data['url_path']
html_dir=data["html_dir"]

# translate text
lang = gettext.translation('messages', localedir='locale', languages=['hu'])
lang.install()
_ = lang.gettext

# Downloads the image or loads it from the cache.
def download_image(poster_path, image_dir):
    # image sizes: w95, w154, w185, w342, w500, ...
    # url: https://image.tmdb.org/t/p/<size>/<filename>

    url = urljoin("https://image.tmdb.org/t/p/w342/", poster_path.lstrip("/"))
    file_path = os.path.join(image_dir.rstrip("/"), os.path.basename(poster_path))

    # If the image is not in cache, download and save it.
    if not os.path.exists(file_path):
        response = requests.get(url, stream=True)
        if response.status_code == 200:  # Sikeres válasz
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):  # Részenként írja a fájlt
                    f.write(chunk)
                f.close()
            print(poster_path+' '+_('image downloaded successfully.'))
        else:
            print(poster_path + ' ' + _('image download failed.'))

def create_html_files(table_name, table_data, table_names_and_texts):
    image_dir = html_dir.rstrip("/") + "/images"

    # Create html folder if it doesn't exist
    if not os.path.exists(html_dir):
        os.makedirs(html_dir)

    # Create image folder if it doesn't exist
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    tmdb_svg_path = os.path.join(image_dir, "tmdb.svg")
    if not os.path.isfile(tmdb_svg_path):
        shutil.copy("tmdb.svg", tmdb_svg_path)

    style_css_path = os.path.join(html_dir, "style.css")
    if os.path.exists(style_css_path):
        os.remove(style_css_path)
    shutil.copy("style.css", style_css_path)

    script_path = os.path.join(html_dir, "sort.js")
    if os.path.exists(script_path):
        os.remove(script_path)
    shutil.copy("sort.js", script_path)

    li_items =[]
    for key, value in table_names_and_texts.items():
        if key == table_name:
            li_items.append(f'<li><A CLASS="active" HREF="{key}.html">{value}</A></li>')
        else:
            li_items.append(f'<li><A HREF="{key}.html">{value}</A></li>')

    html_begin = [
        '<!DOCTYPE html>',
        f'<html lang="{language}">',
        '<head>',
        '<meta charset="utf-8">',
        '<title>filminfo</title>',
        '<link rel="stylesheet" href="style.css" type="text/css">',
        '<link rel="stylesheet" href="custom.css" type="text/css">',
        '<script src="sort.js"></script>',
        '</head>',
        '<body>',
        '<header>',
        '<h1>filminfo</h1>',
        '</header>',
        '<nav>',
        '<ul class="menu">' ]
    html_begin += li_items
    html_begin += [
        '</ul>',
        '</nav>',
        '<article>']
    if table_name == "Movie" or table_name == "TV":
        html_begin += [
        '<button id="sortButton" onclick="sortTableByDate()">'+_("Sort by download date")+'</button>',
        '<span id="sortTextSort" hidden>'+_("Sort by download date")+'</span>',
        '<span id="sortTextOriginal" hidden>'+_("Original order")+'</span>']
    html_begin += [
        '<table id="film_table">' ]
    html_end = [
        '</table>',
        '</article>',
        '<footer>',
        '<A HREF="https://www.themoviedb.org/" TARGET="_blank"><IMG SRC="images/tmdb.svg" WIDTH="80"></A>&nbsp;',
        'This program uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.',
        '</footer>',
        '</body>',
        '</html>' ]
    html_file = open(html_dir +"/" + table_name + ".html", "w")
    for line in html_begin:
        html_file.write(line+'\n')

    if "grid" in table_data:
        html_file.write('<colgroup>\n')
        for i in range(1, len(table_data["grid"][0]) + 1):
            html_file.write(f'<col class="col_{i}">\n')
        html_file.write('</colgroup>\n')
        html_file.write('<tbody>\n')
        for film in table_data["film"]:
            html_file.write(f'<tr><td colspan="{len(table_data["grid"][0])}" class="empty"></td></tr>\n')
            for grid_row, grid_line in enumerate(table_data["grid"]):
                html_file.write(f'<tr class="tr_{grid_row+1}">\n')
                for grid_col, grid_cell in enumerate(grid_line):
                    # If this is the first row, or it is NOT part of the cell above it (not rowspan):
                    if grid_row == 0 or grid_cell != table_data["grid"][grid_row - 1][grid_col]:
                        if isinstance(grid_cell, tuple):
                            cell_value = table_data["separator"][grid_row][grid_col].join([str(film[key]) for key in grid_cell if key in film and film[key]])
                        elif grid_cell is not None:
                            cell_value = film[grid_cell]
                        else:
                            cell_value = _("ERROR")

                        row_span = 1
                        while grid_row + row_span < len(table_data["grid"]) and grid_cell == \
                                table_data["grid"][grid_row + row_span][grid_col]:
                            row_span += 1
                        td_class = table_data["class"][grid_row][grid_col]
                        if td_class:
                            td_params = f' class="td_{td_class}"'
                        else:
                            td_params = ''

                        if row_span>1:
                            td_params += f' rowspan = "{row_span}"'

                        html_file.write(f'<td{td_params}>\n')

                        cell_title = table_data["cell_title"][grid_row][grid_col]
                        cell_value_suffix = table_data["suffix"][grid_row][grid_col]
                        cell_value_suffix = cell_value_suffix if cell_value_suffix is not None else ''

                        cell_specialty = table_data["specialty"][grid_row][grid_col]
                        if cell_specialty == "IMG":
                            download_image(cell_value, image_dir)
                            html_file.write(f'<img src="images/{cell_value.lstrip("/")}" class="{table_data["class"][grid_row][grid_col]}_img">')
                        else:
                            if cell_title:
                                html_file.write(f'<div class="cell_title">{cell_title}:</div>\n')
                            cell_value_class = table_data["class"][grid_row][grid_col]
                            start_of_anchor = f'<a href="{url_path.rstrip("/")}/{film["item"].lstrip("/")}" class="film_link">' if cell_specialty == "URL" else ''
                            end_of_anchor = '</A>' if cell_specialty == "URL" else ''
                            html_file.write(f'<div class="{cell_value_class}">'
                                            f'{start_of_anchor}{str(cell_value)} {str(cell_value_suffix)}{end_of_anchor}</div>\n')
                        html_file.write('</td>\n')
                html_file.write('</tr>\n')
            # html_file.write(f'<tr><td colspan="{len(table_data["grid"][0])}" class="empty"></td></tr>\n')


    else:
        for film in table_data["film"]:
            html_file.write(f'<tr><td>{film["item"]}</td></tr>')
    for line in html_end:
        html_file.write(line + '\n')
    html_file.write('</tbody>\n')
    html_file.close()

def create_tables(movie_films, tv_films, unknown_items):
    cast = tuple(f"cast_{i}" for i in range(1, 6))
    air_dates = ('first_air_date', 'last_air_date')
    seasons_episodes = ('number_of_seasons', 'number_of_episodes')
    table_data = {
        "Movie": {"film": movie_films,
                  "button_text": _("Movie"),
                  "grid": (
                      ('poster_path', 'title',          'overview', cast),
                      ('poster_path', 'original_title', 'overview', cast),
                      ('poster_path', 'genres',         'overview', cast),
                      ('poster_path', 'vote_average',   'overview', cast),
                      ('poster_path', 'release_date',   'overview', cast),
                      ('poster_path', 'runtime',        'overview', cast),
                      ('poster_path', 'download_date',  'overview', cast)
                  ),
                  "class": (
                      ('poster',      'title',          'overview', 'cast'),
                      (None,          'o_title',        None,       None),
                      (None,          'genres',         None,       None),
                      (None,          'vote',           None,       None),
                      (None,          'date',           None,       None),
                      (None,          'runtime',        None,       None),
                      (None,          'download_date',  None,       None)
                  ),
                  "separator": (
                      (None,          None,             None,       '<br>'),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None)
                  ),
                  "cell_title": (
                      (None,       _("Title"),      _("Overview"), _("Cast")),
                      (None,       _("Original title"), None,       None),
                      (None,       _("Genres"),         None,       None),
                      (None,       _("Vote"),           None,       None),
                      (None,       _("Release date"),   None,       None),
                      (None,       _("Runtime"),        None,       None),
                      (None,       _("Download date"),  None,       None)
                  ),
                  "suffix": (
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          _("minutes"),     None,       None),
                      (None,          None,             None,       None)
                  ),

                  "specialty": (
                      ("IMG",         "URL",            None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None)
                  )
                  },

        "TV": {"film": tv_films,
               "button_text": _("TV"),

               "grid": (
                      ('poster_path', 'name',           'overview', cast),
                      ('poster_path', 'original_name',  'overview', cast),
                      ('poster_path', 'genres',         'overview', cast),
                      ('poster_path', 'vote_average',   'overview', cast),
                      ('poster_path',  air_dates,       'overview', cast),
                      ('poster_path',  seasons_episodes,'overview', cast),
                      ('poster_path', 'download_date',  'overview', cast)
                  ),
                  "class": (
                      ('poster',      'name',          'overview', 'cast'),
                      (None,          'o_name',         None,       None),
                      (None,          'genres',         None,       None),
                      (None,          'vote',           None,       None),
                      (None,          'date',           None,       None),
                      (None,          'seasons_episodes',None,      None),
                      (None,          'download_date',  None,       None)
                  ),
                  "separator": (
                      (None,          None,             None,       '<br>'),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          ' - ',            None,       None),
                      (None,          '/',              None,       None),
                      (None,          None,             None,       None)
                  ),
                  "cell_title": (
                      (None,       _("Name"),      _("Overview"), _("Cast")),
                      (None,       _("Original name"),  None,       None),
                      (None,       _("Genres"),         None,       None),
                      (None,       _("Vote"),           None,       None),
                      (None,       _("Air dates"),      None,       None),
                      (None,       _("Seasons/Episodes"),None,      None),
                      (None,       _("Download date"),  None,       None)
                  ),
                  "suffix": (
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None)
                  ),

                  "specialty": (
                      ("IMG",         "URL",            None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None),
                      (None,          None,             None,       None)
                  )
                  },

        "Unknown": {"film": unknown_items,
                    "button_text": _("Unknown")
                    }
    }

    table_names_and_texts ={key:table_data[key]["button_text"] for key in table_data.keys()}

    for name in table_data.keys():
        create_html_files(name, table_data[name], table_names_and_texts)

    # Delete unnecessary image files.
    image_dir = html_dir.rstrip("/") + "/images"
    all_files = set()
    req_files = {'tmdb.svg'} # Required for the footer.
    for filename in os.listdir(image_dir):
        file_path = os.path.join(image_dir, filename)
        if os.path.isfile(file_path):
            all_files.add(filename)

    for name in table_data.keys():
        for film in table_data[name]["film"]:
            if film.get("poster_path") is not None:
                req_files.add(film["poster_path"].lstrip("/"))
    to_delete = all_files - req_files
    for filename in to_delete:
        file_path = os.path.join(image_dir, filename)
        os.remove(file_path)

# Program entry point
if __name__ == "__main__":
  print("Do not run this script directly.\nThe filminfo.py script uses this.")