#!/usr/bin/env python3
import sys
if sys.version_info[0] < 3: # raise an exception in case of running under python2 environment.
    raise BaseException('Please run under python3 environment.')

import os
import requests
import json
import subprocess
import shutil

current_dir = os.path.dirname(os.path.realpath(__file__))   # get this script current path.
base_url = 'http://www.bing.com'    # bing website base url.
hpimagearchive_url = '/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US'  # this part makes a request to get image of the day.
target_image = None # target image to set as wallpaper.


def get_image_link():
    """
        Fetches json object received from bing.com and gets target image link.
    """

    GET_DATA = requests.get(base_url + hpimagearchive_url)  # send a get request to bing.com to read json data.
    json_obj = json.loads(GET_DATA.content.decode('utf-8'))
    return json_obj['images'][0]['url']


def download_image(img_link):
    """
    Checks for a valid full-size image file and if valid, downloads the image.
    Saves in the XFCE default wallpaper location.
    """

    if img_link is not None:  # ensure that we got a valid full-size jpeg background image.
        img_dir = os.path.expanduser('~/.local/share/xfce-bing-wallpaper/')
        os.makedirs(img_dir, exist_ok=True)
        
        img = requests.get(img_link)    # download image
        filename = img_link.split('/')[-1]
        filepath = os.path.join(img_dir, filename)
        
        with open(filepath, 'wb') as img_file:
            img_file.write(img.content)  # write bytes to file
        
        return filepath
    return None


def detect_monitors():
    """
        Detect monitor IDs under /backdrop/screen0/... using xfconf-query -l.
        Returns a list like ['monitor0', 'monitor1', ...]. Falls back to ['monitor0'] if none found.
    """
    monitors = []
    try:
        res = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-l'],
                             capture_output=True, text=True, check=False)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if line.startswith('/backdrop/screen0/'):
                    parts = line.split('/')
                    # path: ['', 'backdrop', 'screen0', 'monitorX', 'workspaceY', ...]
                    if len(parts) > 3:
                        monitors.append(parts[3])
        # dedupe while preserving order
        seen = set()
        monitors = [m for m in monitors if not (m in seen or seen.add(m))]
    except Exception:
        monitors = []

    if not monitors:
        monitors = ['monitor0']  # fallback
    return monitors


def set_wallpaper():
    """
        Downloads and sets received image from bing.com as xfce4 current wallpaper.
    """

    image_path = download_image(base_url + get_image_link())  # make complete image link and download it.
    if not image_path:
        return

    monitors = detect_monitors()

    # set wallpaper for each detected monitor; use --create -t string so property is created if missing
    for m in monitors:
        prop = f'/backdrop/screen0/{m}/workspace0/last-image'
        cmd = [
            'xfconf-query', '-c', 'xfce4-desktop',
            '-p', prop,
            '--create', '-t', 'string', '-s', image_path
        ]
        subprocess.run(cmd, check=False)


def copy_self_to_usr_local(dest_name='xfce-bing-wallpaper'):
    """
    Copy this script to /usr/local/bin with executable permissions.
    Returns the destination path written.
    """
    src = os.path.realpath(__file__)
    dest = os.path.join('/usr/local/bin', dest_name)
    try:
        shutil.copyfile(src, dest)
        # ensure executable
        os.chmod(dest, 0o755)
        return dest
    except PermissionError:
        print('Permission denied: need to run as root to copy to /usr/local/bin')
        return None
    except Exception as e:
        print('Failed to copy to /usr/local/bin:', e)
        return None
    
def copy_self_to_usr_local(dest_name='xfce-bing-wallpaper'):
    """
    Copy this script to /usr/local/bin with executable permissions.
    Returns the destination path written.
    """
    src = os.path.realpath(__file__)
    dest = os.path.join('/usr/local/bin', dest_name)
    try:
        shutil.copyfile(src, dest)
        # ensure executable
        os.chmod(dest, 0o755)
        return dest
    except PermissionError:
        print('Permission denied: need to run as root to copy to /usr/local/bin')
        return None
    except Exception as e:
        print('Failed to copy to /usr/local/bin:', e)
        return None


def install_cron_job(dest_executable='/usr/local/bin/xfce-bing-wallpaper'):
    """
    Install a cron job in /etc/cron.d to run the script at 03:00 and 15:00 every day.

    Note: The user requested anacron, but anacron does not support sub-daily schedules
    (it works with days). For exact 03:00 and 15:00 daily runs we use cron. If you
    really need anacron semantics (run when system is up, at least once a day), we
    can create a daily anacron job instead — tell me if you prefer that.
    """
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
    """Ask user whether to set wallpaper now, install scheduler, or both."""
    print('What would you like to do?')
    print('1) Set wallpaper now')
    print('2) Install scheduled job (cron at 03:00 and 15:00)')
    choice = input('Choose 1 or 2: ').strip()
    return choice


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'set-wallpaper':
        set_wallpaper()
        return
    
    # Interactive-only flow: running the script asks the user what to do.
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
