# -*- coding: utf-8 -*-

import os
import itertools
import re
import json
import platform
import ctypes
from subprocess import run
from os.path import join as pj
import urllib.request
import urllib.parse

from sys import stderr


def msg(s):
    print(s, file=stderr, flush=True)


def run_progress_bar(finished_event):
    chars = itertools.cycle(r'-\|/')
    while not finished_event.is_set():
        print('\b' + next(chars), end='', flush=True)
        finished_event.wait(0.2)
    print('\b ', end='')

def parse_num_book(lang, work_dir):
    dir_file = pj(work_dir, f'lang-{lang}.json')
    if os.path.exists(dir_file):
        with open(dir_file, 'r', encoding='utf-8') as json_file:
            return json.load(json_file)
    else:
        url_template = 'https://apps.jw.org/GETPUBMEDIALINKS' \
                       '?output=json&alllangs=0&langwritten={L}&txtCMSLang={L}' \
                       '&pub=nwt&booknum={i}'
        num_book = {}
        print(f'Getting booknum and bookname in {lang} language')
        for i in range(1, 67):
            url = url_template.format(L=lang, i=i)
            with urllib.request.urlopen(url) as response:
                response = json.loads(response.read().decode())
                # Check if the code is valid
                if lang not in response['languages']:
                    msg('language codes:')
                    for language in sorted(response['languages'], key=lambda x: response['languages'][x]['name']):
                        msg('{:>3}  {:<}'.format(language, response['languages'][language]['name']))
                    raise ValueError(lang + ': invalid language code')
                    exit()
                num_book.setdefault(format(i, '02'), response['pubName'])
                print(format(i, '02'), response['pubName'])

        with open(dir_file, 'w', encoding='utf-8') as json_file:
            json.dump(num_book, json_file, ensure_ascii=False, indent=4)
        attrib_hidden(dir_file)
        return num_book


def attrib_hidden(dir):
    if platform.system() == 'Windows':
        ctypes.windll.kernel32.SetFileAttributesW(dir, 0x02)
    elif platform.system() == 'Darwin':
        run(['chflags', 'hidden', dir], capture_output=True)


# FFPROBE = os.path.join(os.getcwd(), 'ffprobe')
# FFMPEG = os.path.join(os.getcwd(), 'ffmpeg')

FFPROBE = 'ffprobe'
FFMPEG = 'ffmpeg'


def ext(filename):
    return os.path.splitext(os.path.basename(filename))[-1]


def woext(filename):
    return os.path.splitext(os.path.basename(filename))[0]


def probe_markers(filename, bookname):
    """Returns markers (chapters) from video
    [
        {
            'parent': filename,
            'title': title,
            'booknum': booknum,
            'start': start,
            'end': end
        },
    ]
    """
    console = run([FFPROBE, '-v', 'quiet', '-show_chapters',
                   '-print_format', 'json', filename
                   ],
                  capture_output=True)
    if console.returncode == 0:
        raw = json.loads(console.stdout.decode('utf-8'))['chapters']
    else:
        print(f'error {filename}')
        return []

    markers = []
    for data in raw:
        t = data['tags']['title'].rstrip('\r').rstrip()
        chptr_verse = get_chptr_verse(t)
        if chptr_verse:
            markers.append(
                {
                    'parent': filename,
                    'title': f'{bookname} {chptr_verse}',
                    'booknum': get_nwt_video_info(filename, 'booknum'),
                    'start': float(data['start_time']),
                    'end': float(data['end_time']),
                }
            )
        else:
            # No match chpter verse
            pass
    return markers


def get_nwt_video_info(filename, info):
    if info == 'booknum':
        answer = os.path.basename(filename).split('_')[1]
    elif info == 'bookalias':
        answer = os.path.basename(filename).split('_')[2]
    elif info == 'lang':
        answer = os.path.basename(filename).split('_')[3]
    elif info == 'chapter':
        answer = os.path.basename(filename).split('_')[4]
    return answer


def get_chptr_verse(raw_title):
    """
        INPUT                     |   OUTPUT
        --------------------------|-----------
        Gén. 1:1                  |   01 01
        Juec. 4:14                |   04 14
        Rut 1:4                   |   01 04
        1 Sam. 1:4                |   01 04
        Cant. de Cant. 2:5        |   02 05
        Inicio                    |   None
        Mateo                     |   None
        Mat. 1:1                  |   01 01
        *Mat. 17:21 Nota          |   None
        * Juan 5:4 Nota           |   None
        * Juan 8:1-11 Nota        |   None
        Hech. 8:37 Nota           |   None
        Luc. 17:36 nota           |   None
        1 Corintios               |   None
    """
    match = re.search(r'((\d+)?:?\d+)$', raw_title)
    if match:
        try:
            chptr, verse = match.group().split(':')
        except ValueError:
            verse = match.group()
            return format(int(verse), '02')
        else:
            return format(int(chptr), '02') + ' ' + format(int(verse), '02')


def probe_general(video):
    cmd_probe_general = [FFPROBE, '-v', 'quiet', '-show_format',
                         '-print_format', 'json', video]
    console = run(cmd_probe_general, capture_output=True)
    return json.loads(console.stdout.decode('utf-8'))


def ffprobe_height(video):
    cmd = [FFPROBE, '-v', 'quiet', '-show_entries', 'stream=height',  '-of',
           'default=noprint_wrappers=1:nokey=1', '-select_streams', 'v:0',
           video]
    console = run(cmd, capture_output=True)
    height = console.stdout.decode('utf-8')
    try:
        return int(height)
    except ValueError:
        print(height, 'no se pudo')
        pass


def add_numeration(wd, num_bookname):
    for booknum, bookname in num_bookname.items():
        try:
            os.rename(pj(wd, bookname),
                      pj(wd, f'{booknum} {bookname}'))
        except FileNotFoundError:
            pass


def remove_numeration(wd, num_bookname):
    for booknum, bookname in num_bookname.items():
        try:
            os.rename(pj(wd, f'{booknum} {bookname}'),
                      pj(wd, bookname))
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    pass
