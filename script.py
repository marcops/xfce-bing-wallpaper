#!/usr/bin/env python3
import sys
if sys.version_info[0] < 3:
    raise BaseException('Please run under python3 environment.')

import os
import requests
import json
import subprocess
import shutil
import re

current_dir = os.path.dirname(os.path.realpath(__file__))
base_url = 'http://www.bing.com'
hpimagearchive_url = '/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US'


def get_image_link():
    try:
        r = requests.get(base_url + hpimagearchive_url, timeout=10)
        r.raise_for_status()
        json_obj = r.json()
        return json_obj['images'][0]['url']
    except Exception as e:
        print('Failed to fetch image link:', e)
        return None


def download_image(img_link):
    """
    Downloads the image only if it doesn't already exist.
    Keeps original filename.
    """
    if not img_link:
        return None

    img_dir = os.path.expanduser('~/.local/share/xfce-bing-wallpaper/')
    os.makedirs(img_dir, exist_ok=True)

    filename = img_link.split('/')[-1]  # mantém o nome original
    filepath = os.path.join(img_dir, filename)

    if os.path.exists(filepath):
        print(f'Image already exists: {filepath}')
        return filepath

    # constrói URL completa se necessário
    if img_link.startswith('/'):
        img_link = base_url + img_link

    try:
        resp = requests.get(img_link, timeout=30)
        resp.raise_for_status()
        with open(filepath, 'wb') as fh:
            fh.write(resp.content)
        print(f'Image downloaded: {filepath}')
    except Exception as e:
        print('Failed to download image:', e)
        return None

    return filepath


def _get_xfconf_paths():
    """Return list of xfconf desktop property paths (raw lines)."""
    try:
        res = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-l'],
                             capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def detect_monitors_from_xrandr():
    import subprocess, re
    monitors = []

    try:
        res = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, check=False)
        for line in res.stdout.splitlines():
            m = re.match(r'^([A-Za-z0-9-]+)\s+connected', line)
            if m:
                monitors.append(m.group(1))
    except Exception:
        monitors = ['monitor0']

    xf_paths = _get_xfconf_paths()
    xf_monitors = []
    for out in monitors:
        found = False
        for path in xf_paths:
            if out in path:
                xf_monitors.append(path.split('/')[3])
                found = True
                break
        if not found:
            xf_monitors.append(f'monitor{out}')
    return xf_monitors

def detect_monitors():
    """
    Detect all monitors currently in XFCE by listing the last-image keys.
    Returns a list of monitor identifiers like 'monitorHDMI-1-1', 'monitoreDP-1', 'monitor0'.
    """
    xf_paths = _get_xfconf_paths()
    monitors = []
    for path in xf_paths:
        if path.startswith('/backdrop/screen0/') and path.endswith('/last-image'):
            parts = path.split('/')
            if len(parts) > 3:
                monitors.append(parts[3])
    # dedupe while preserving order
    seen = set()
    monitors = [m for m in monitors if not (m in seen or seen.add(m))]
    return monitors if monitors else ['monitor0']


def set_wallpaper():
    img_link = get_image_link()
    if not img_link:
        return

    image_path = download_image(img_link)
    if not image_path or not os.path.exists(image_path):
        print('No image to set.')
        return

    monitors = detect_monitors_from_xrandr()
    print(monitors)
    for m in monitors:
        prop = f'/backdrop/screen0/{m}/workspace0/last-image'
        subprocess.run([
            'xfconf-query', '-c', 'xfce4-desktop',
            '-p', prop,
            '--create', '-t', 'string', '-s', image_path
        ], check=False)

    # reload desktop
    subprocess.run(['xfdesktop', '--reload'], check=False)
    print('Wallpaper set for monitors:', ', '.join(monitors))


def copy_self_to_usr_local(dest_name='xfce-bing-wallpaper'):
    src = os.path.realpath(__file__)
    dest = os.path.join('/usr/local/bin', dest_name)
    try:
        shutil.copyfile(src, dest)
        os.chmod(dest, 0o755)
        return dest
    except PermissionError:
        print('Permission denied: need to run as root to copy to /usr/local/bin')
        return None
    except Exception as e:
        print('Failed to copy to /usr/local/bin:', e)
        return None


def install_cron_job(dest_executable='/usr/local/bin/xfce-bing-wallpaper'):
    cronfile = '/etc/cron.d/xfce-bing-wallpaper'
    cron_lines = [
        f"0 3 * * * root {dest_executable} --set-wallpaper\n",
        f"0 15 * * * root {dest_executable} --set-wallpaper\n"
    ]
    try:
        with open(cronfile, 'w') as fh:
            fh.writelines(cron_lines)
        os.chmod(cronfile, 0o644)
        print('Cron job installed at', cronfile)
        return cronfile
    except PermissionError:
        print('Permission denied: need to run as root to write to /etc/cron.d')
        return None
    except Exception as e:
        print('Failed to install cron job:', e)
        return None


def interactive_prompt():
    print('What would you like to do?')
    print('1) Set wallpaper now')
    print('2) Install scheduled job (cron at 03:00 and 15:00)')
    choice = input('Choose 1 or 2: ').strip()
    return choice


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('set-wallpaper', '--set-wallpaper'):
        set_wallpaper()
        return

    choice = interactive_prompt()
    if choice == '1':
        set_wallpaper()
    elif choice == '2':
        if os.geteuid() != 0:
            print('\nThis action requires root privileges.')
            print('Please run the script with sudo, e.g.:')
            print(f'  sudo python3 {os.path.realpath(__file__)}')
            return
        print('Installing scheduled job.')
        install_cron_job('/usr/local/bin/xfce-bing-wallpaper')
    else:
        print('Invalid choice, exiting.')


if __name__ == '__main__':
    main()
