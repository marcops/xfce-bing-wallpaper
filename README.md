# XFCE4 Bing Wallpaper

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![XFCE](https://img.shields.io/badge/Desktop-XFCE4-orange.svg)](https://www.xfce.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Set [Bing](http://bing.com) daily image as your **XFCE4** wallpaper automatically.  

Inspired by [moeenz/xfce-bing-wallpaper](https://github.com/moeenz/xfce-bing-wallpaper).  

---

## Features

- Downloads the daily **Bing image**.  
- Automatically sets it as your **XFCE4 wallpaper**.  
- Supports multiple monitors.  
- Optional **cron job** to update wallpaper twice daily (03:00 & 15:00).  

---

## Requirements

- Python 3 (≥3.6)  
- XFCE4 Desktop Environment  

> No extra libraries required except `requests` (install via `pip install requests` if missing).

---

## Installation

### Download Script

```bash
wget https://raw.githubusercontent.com/marcops/xfce-bing-wallpaper/main/xfce-bing-wallpaper.py -O xfce-bing-wallpaper.py
```

## Usage
### Interactive Mode
```bash
python3 xfce-bing-wallpaper.py
```
1 → Set wallpaper now.

2 → Install cron job (requires root).

### Direct Command
```bash
python3 xfce-bing-wallpaper.py --set-wallpaper
```