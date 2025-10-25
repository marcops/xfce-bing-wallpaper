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

def get_max_resolution():
    import subprocess, re

    max_width, max_height = 0, 0

    try:
        res = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, check=False)
        for line in res.stdout.splitlines():
            m = re.match(r'^([A-Za-z0-9-]+)\s+connected.*?(\d+)x(\d+)\+.*', line)
            if m:
                width = int(m.group(2))
                height = int(m.group(3))
                if width * height > max_width * max_height:
                    max_width, max_height = width, height
    except Exception:
        # fallback genérico
        max_width, max_height = 1920, 1080

    return max_width, max_height


def get_base_url():
    return 'http://www.bing.com'

def get_url(days_back=0, width=1920, height=1080, market='en-US'):
    hpimagearchive_url = (
        f'/HPImageArchive.aspx?format=js&idx={days_back}&n=1&mkt={market}'
        f'&uhd=1&uhdwidth={width}&uhdheight={height}'
    )
    return get_base_url() + hpimagearchive_url


def get_image_link_from_json(days: int):
    try:
        max_width, max_height = get_max_resolution()
        url = get_url(days_back=days, width=max_width, height=max_height) 
        print(url)
        r = requests.get(url)
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
    print(img_link)
    if not img_link:
        return None

    img_dir = os.path.expanduser('~/.local/share/xfce-bing-wallpaper/')
    os.makedirs(img_dir, exist_ok=True)

    filename = img_link.split('/')[-1]
    filepath = os.path.join(img_dir, filename)

    if os.path.exists(filepath):
        print(f'Image already exists: {filepath}')
        return filepath

    if img_link.startswith('/'):
        img_link = get_base_url() + img_link

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


def set_wallpaper(days: int):
    img_link = get_image_link_from_json(days)
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

def copy_script_to_local_bin(dest_executable=os.path.expanduser('~/.local/bin/xfce-bing-wallpaper')):
    import shutil

    os.makedirs(os.path.dirname(dest_executable), exist_ok=True)

    try:
        shutil.copyfile(os.path.realpath(__file__), dest_executable)
        os.chmod(dest_executable, 0o755)
        print(f'Script copied to {dest_executable} and made executable.')
    except Exception as e:
        print(f'Failed to copy script to {dest_executable}:', e)
        return False
    return True

def install_user_cron(dest_executable=os.path.expanduser('~/.local/bin/xfce-bing-wallpaper')):
    
    python_path = '/usr/bin/python3'
    monitor = 'DISPLAY=:0 XAUTHORITY=/home/marco/.Xauthority'
    dbus = 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus'

    new_cron = (
        f"@reboot sleep 120 && {dbus} {monitor} {python_path} {dest_executable} --set-wallpaper\n"
        f"0 */6 * * * {dbus} {monitor} {python_path} {dest_executable} --set-wallpaper\n"
    )
    try:
        subprocess.run(['crontab', '-'], input=new_cron, text=True)
        print('User cron job installed.')
        return True
    except Exception as e:
        print('Failed to install user cron:', e)
        return False


def interactive_prompt():
    print('What would you like to do?')
    print('1) Set wallpaper now')
    print('2) Install scheduled job (cron at 03:00 and 15:00)')
    print('3) Set wallpaper from N days ago')
    print('4) Remove cron job')
    return input('Choose 1, 2, 3, or 4: ').strip()

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('set-wallpaper', '--set-wallpaper'):
        set_wallpaper()
        return

    choice = interactive_prompt()
    if choice == '1':
        set_wallpaper(0)
    elif choice == '2':
        print('Installing scheduled job.')
        copy_script_to_local_bin()
        install_user_cron()
    elif choice == '3':
        days = input('How many days back? ').strip()
        try:
            days = int(days)
        except ValueError:
            print('Invalid number, exiting.')
            return
        set_wallpaper(days)

    elif choice == '4':
        try:
            subprocess.run(['crontab', '-r'], check=True)
            print('Cron job removed.')
        except Exception as e:
            print('Failed to remove cron:', e)
    else:
        print('Invalid choice, exiting.')


if __name__ == '__main__':
    main()
